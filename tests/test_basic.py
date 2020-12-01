import ast
import json
import os
import pickle
import random
from pathlib import Path
from time import sleep, time
from typing import Tuple
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import pytest
import yaml
from joblib import Parallel, delayed
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from .utils import server, logs


def test_basics(server, logs):
    """
    Requires `docker-compose up` in salmon directory
    """
    username, password = server.auth()
    print(username, password)
    server.delete("/reset", status_code=401)
    r = server.delete("/reset?force=1", auth=(username, password))
    assert r.json() == {"success": True}
    server.get("/reset", status_code=401)
    r = server.get("/reset?force=1", auth=(username, password))
    assert r.json() == {"success": True}
    server.get("/init_exp")
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_bytes()}, auth=(username, password))
    exp_config = yaml.safe_load(exp.read_bytes())
    puid = "puid-foo"
    answers = []
    print("Starting loop...")
    with logs:
        for k in range(70):
            _start = time()
            q = server.get("/query").json()
            ans = {"winner": random.choice([q["left"], q["right"]]), "puid": puid, **q}
            answers.append(ans)
            sleep(10e-3)
            ans["response_time"] = time() - _start
            server.post("/answer", data=ans)

    r = server.get("/responses", auth=(username, password))
    for server_ans, actual_ans in zip(r.json(), answers):
        assert set(actual_ans).issubset(server_ans)
        assert all(
            actual_ans[k] == server_ans[k] for k in ["head", "winner", "left", "right"]
        )
        assert server_ans["puid"] == puid
    df = pd.DataFrame(r.json())
    expected_cols = {
        "start_time",
        "time_received_since_start",
        "time_received",
        "head",
        "right",
        "left",
        "winner",
        "loser",
        "winner_object",
        "loser_object",
        "right_object",
        "head_object",
        "left_object",
        "winner_filename",
        "right_filename",
        "left_filename",
        "loser_filename",
        "head_filename",
        "puid",
        "response_time",
        "network_latency",
        "datetime_received",
        "alg_ident",
        "score",
    }
    assert (df["winner"] != df["loser"]).all()
    assert ((df["winner"] == df["left"]) | (df["winner"] == df["right"])).all()
    assert ((df["loser"] == df["left"]) | (df["loser"] == df["right"])).all()
    n = len(exp_config["targets"])
    assert (0 == df["head"].min()) and (df["head"].max() == n - 1)
    assert ((0 == df["left"].min()) or (df["right"].min() == 0)) and (
        (df["left"].max() == n - 1) or (df["right"].max() == n - 1)
    )
    assert 10e-3 < df.response_time.min()
    assert expected_cols == set(df.columns)
    assert df.puid.nunique() == 1

    assert np.allclose(df.score, -9999)  # -9999 is a proxy for nan here

    # Make sure ordered by time
    assert df.time_received_since_start.diff().min() > 0

    r = server.get("/responses", auth=(username, password))
    assert r.status_code == 200
    assert "exception" not in r.text
    df = pd.DataFrame(r.json())
    assert len(df) == 70

    r = server.get("/dashboard", auth=(username, password))
    assert r.status_code == 200


def test_bad_file_upload(server):
    server.authorize()
    server.get("/init_exp")
    exp = Path(__file__).parent / "data" / "bad_exp.yaml"
    r = server.post("/init_exp", data={"exp": exp.read_bytes()}, error=True)
    assert r.status_code == 500
    assert "Error" in r.text
    assert "yaml" in r.text
    assert "-\tfoo" in r.text


def test_no_repeats(server):
    server.authorize()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    for k in range(50):
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
        server.post("/answer", data=ans)

    r = server.get("/responses")
    df = pd.DataFrame(r.json())
    equal_targets = (
        (df["head"] == df["right"])
        | (df["head"] == df["left"])
        | (df["left"] == df["right"])
    )
    assert not equal_targets.all()


def test_meta(server):
    server.authorize()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    num_ans = 10
    for k in range(num_ans):
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": str(k), **q}
        server.post("/answer", data=ans)
    meta = server.get("/meta").json()
    assert meta["participants"] == num_ans
    assert meta["responses"] == num_ans


def test_saves_state(server):
    server.authorize()
    server.get("/reset?force=1")
    sleep(0.1)
    dump = Path(__file__).absolute().parent.parent / "out" / "dump.rdb"
    assert not dump.exists()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    for k in range(10):
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": str(k), **q}
        server.post("/answer", data=ans)
    assert dump.exists()

    # Clear all dump files; reset state
    dir = Path(__file__).absolute().parent.parent / "out"
    dump_files = list(dir.glob("*.rdb"))
    for d in dump_files:
        d.unlink()
    files = [f.name for f in dir.glob("*.rdb")]
    assert len(files) == 0

    # Make sure saved resetting saves experiment state
    before_reset = datetime.now()
    server.get("/reset?force=1")
    files = [f.name for f in dir.glob("*.rdb")]
    assert len(files) == 1
    written = datetime.strptime(files[0], "dump-%Y-%m-%dT%H:%M.rdb")
    assert isinstance(written, datetime)

    # Because docker container time zones are screwy... this is a check to
    # make sure this new file was written sometime today
    day = timedelta(hours=24)
    assert datetime.now() - day < written < datetime.now() + day


def test_download_restore(server):
    dump = Path(__file__).absolute().parent.parent / "out" / "dump.rdb"
    assert not dump.exists()
    server.authorize()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    data = []
    for k in range(10):
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": str(k), **q}
        server.post("/answer", data=ans)
        data.append(ans)
    r = server.get("/download")
    assert all(x in r.headers["content-disposition"] for x in ["exp-", ".rdb"])

    # Does it restore?
    content = dump.read_bytes()
    dump.unlink()
    assert not dump.exists()
    server.post("/restore", data={"rdb": content})
    assert dump.exists()


def test_logs(server, logs):
    dump = Path(__file__).absolute().parent.parent / "salmon" / "out" / "dump.rdb"
    assert not dump.exists()
    server.authorize()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.get("/reset?force=1")
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    data = []
    puid = "adsfjkl4awjklra"
    with logs:
        for k in range(10):
            q = server.get("/query").json()
            ans = {"winner": random.choice([q["left"], q["right"]]), "puid": k, **q}
            server.post("/answer", data=ans)
            data.append(ans)

        r = server.get("/logs")
        assert r.status_code == 200
        logs = r.json()
        query_logs = logs["salmon.frontend.public.log"]

        str_answers = [q.strip("\n") for q in query_logs if "answer received" in q]
        answers = [ast.literal_eval(q[q.find("{") :]) for q in str_answers]
        puids = {ans["puid"] for ans in answers}
        assert {str(i) for i in range(10)}.issubset(puids)


@pytest.mark.xfail(
    reason="Works in browser with imgs.zip; having difficulty with this test"
)
def test_zip_upload(server):
    server.authorize()
    exp = Path(__file__).parent / "data" / "upload_w_zip.yaml"
    targets = Path(__file__).parent / "data" / "imgs.zip"
    assert targets.exists()
    t = targets.read_bytes()
    assert len(t) > 0
    assert t[:4] == b"\x50\x4B\x03\x04"
    server.post("/init_exp", data={"exp": exp.read_bytes(), "targets": t})


def test_get_config(server):
    server.authorize()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    my_config = yaml.safe_load(exp.read_text())
    rendered_config = server.get("/config").json()
    assert set(my_config).issubset(rendered_config)
    for k, v in my_config.items():
        assert rendered_config[k] == v

    yaml_config = server.get("/config?json=0").text
    assert "\n" in yaml_config
    assert yaml.safe_load(yaml_config) == rendered_config


def test_no_init_twice(server, logs):
    """
    Requires `docker-compose up` in salmon directory
    """
    server.authorize()
    username, password = server.auth()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    query = server.get("/query")
    assert query

    # Make sure errors on re-initialization
    server.post("/init_exp", data={"exp": exp.read_bytes()}, status_code=403)

    # Make sure the prescribed method works (resetting, then re-init'ing)
    server.delete("/reset", auth=(username, password), status_code=500)
    server.delete("/reset?force=1", auth=(username, password))

    server.post("/init_exp", data={"exp": exp.read_bytes()})
    query = server.get("/query")
    assert query
