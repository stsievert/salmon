import ast
import json
import os
import pickle
import random
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep, time
from typing import Tuple

import numpy as np
import pandas as pd
import pytest
import yaml

from salmon.triplets.manager import Config

from .utils import LogError, logs, server


def test_basics(server, logs):
    """
    Requires `docker-compose up` in salmon directory
    """
    server._authorized = False  # mock not unauthorized
    server.delete("/reset", status_code=401, timeout=20)
    server.authorize()
    r = server.delete("/reset?force=1", timeout=20)
    assert r.json() == {"success": True}
    server.delete("/reset", status_code=401, auth=("foo", "bar"))

    r = server.authorize()
    assert r.status_code == 200
    r = server.delete("/reset?force=1", timeout=20)
    server.authorize()

    assert r.json() == {"success": True}
    server.get("/init")
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_text()})
    exp_config = yaml.safe_load(exp.read_bytes())
    puid = "puid-foo"
    answers = []
    print("Starting loop...")
    n_ans = 40
    for k in range(n_ans):
        _start = time()
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": puid, **q}
        answers.append(ans)
        sleep(10e-3)
        ans["response_time"] = time() - _start
        server.post("/answer", data=ans)

    r = server.get("/responses")
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
        "winner_html",
        "loser_html",
        "right_html",
        "head_html",
        "left_html",
        "winner_filename",
        "right_filename",
        "left_filename",
        "loser_filename",
        "head_filename",
        "puid",
        "response_time",
        "network_latency",
        "datetime_received",
        "sampler",
        "score",
        "puid_num_responses",
        "num_responses",
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

    r = server.get("/responses")
    assert r.status_code == 200
    assert "exception" not in r.text
    df = pd.DataFrame(r.json())
    assert len(df) == n_ans

    r = server.get("/dashboard")
    assert r.status_code == 200
    assert "Embedding dimension: 2" in r.text
    assert "Number of targets: 6" in r.text
    assert "Samplers: [&#39;random&#39;]" in r.text  # &#39; is HTML for the apostrophe

    assert (df["num_responses"] == (np.arange(len(df)) + 1)).all()


def test_bad_file_upload(server):
    server.authorize()
    server.get("/init")
    exp = Path(__file__).parent / "data" / "bad_exp.yaml"
    r = server.post("/init_exp", data={"exp": exp.read_text()}, error=True)
    assert r.status_code == 500
    assert "Error" in r.text
    assert "yaml" in r.text
    assert "-\tfoo" in r.text


def test_no_repeats(server):
    server.authorize()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_text()})
    for k in range(50):
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
        server.post("/answer", data=ans)
        sleep(10e-3)

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
    server.post("/init_exp", data={"exp": exp.read_text()})
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
    server.delete("/reset?force=1", timeout=20)
    sleep(0.1)

    this_dir = Path(__file__).absolute().parent
    root = this_dir.parent
    dump_dir = root / "salmon" / "_out"
    assert dump_dir.exists()
    dump = dump_dir / "dump.rdb"
    assert not dump.exists()
    exp = this_dir / "data" / "exp.yaml"

    server.authorize()
    server.post("/init_exp", data={"exp": exp.read_text()})
    for k in range(10):
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": str(k), **q}
        server.post("/answer", data=ans)
    r = server.get("/dashboard")
    assert r.status_code == 200
    sleep(1)
    assert dump.exists()

    # Clear all dump files; reset state
    dump_files = list(dump_dir.glob("*.rdb"))
    for d in dump_files:
        d.unlink()
    files = [f.name for f in dump_dir.glob("*.rdb")]
    assert len(files) == 0

    # Make sure saved resetting saves experiment state
    before_reset = datetime.now()
    server.delete("/reset?force=1", timeout=20)
    files = [f.name for f in dump_dir.glob("*.rdb")]
    assert len(files) == 1
    written = datetime.strptime(files[0], "dump-%Y-%m-%dT%H:%M.rdb")
    assert isinstance(written, datetime)

    # Because docker container time zones are screwy... this is a check to
    # make sure this new file was written sometime today
    day = timedelta(hours=24)
    assert datetime.now() - day < written < datetime.now() + day


def test_download_restore(server):
    server.authorize()
    dump = Path(__file__).absolute().parent.parent / "salmon" / "_out" / "dump.rdb"
    assert not dump.exists()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_text()})
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
    server.authorize()
    dump = Path(__file__).absolute().parent.parent / "salmon" / "out" / "dump.rdb"
    assert not dump.exists()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.delete("/reset?force=1", timeout=20)
    server.authorize()
    server.post("/init_exp", data={"exp": exp.read_text()})
    data = []
    puid = "adsfjkl4awjklra"
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


def test_zip_upload(server):
    server.authorize()
    exp = Path(__file__).parent / "data" / "upload_w_zip.yaml"
    targets = Path(__file__).parent / "data" / "imgs.zip"
    assert targets.exists()
    t = targets.read_bytes()
    assert len(t) > 0
    assert t[:4] == b"\x50\x4B\x03\x04"
    server.post("/init_exp", data={"exp": exp.read_text()}, files={"targets": t})


def test_get_config(server):
    server.authorize()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_text()})
    my_config = yaml.safe_load(exp.read_text())
    rendered_config = server.get("/config").json()
    assert set(my_config).issubset(rendered_config)
    user_html = my_config.pop("html")
    assert set(user_html).issubset(set(rendered_config["html"]))
    for k, v in my_config.items():
        if k == "targets":
            v = [str(t) for t in v]
        assert rendered_config[k] == v

    yaml_config = server.get("/config?json=0").text
    assert "\n" in yaml_config
    assert yaml.safe_load(yaml_config) == rendered_config


def test_config_defaults_update(server):
    server.authorize()
    html = {
        "instructions": "foo",
        "debrief": "bar",
        "max_queries": 42,
        "custom_tag": "foo",
    }
    exp = {"targets": 10, "html": html}
    server.post("/init_exp", data={"exp": exp})

    rendered = server.get("/config").json()
    assert "custom_tag" in rendered["html"] and rendered["html"]["custom_tag"] == "foo"
    assert rendered["html"]["instructions"] == "foo"
    assert rendered["html"]["debrief"] == "bar"
    assert rendered["html"]["max_queries"] == 42
    assert rendered["samplers"] == {"random": {"class": "Random"}}


def test_config_misplaced_error(server):
    server.authorize()
    exp = {"instructions": "foo", "debrief": "bar", "max_queries": 42, "targets": 10}
    r = server.post("/init_exp", data={"exp": exp}, error=500)
    assert "Move keys" in r.text and "YAML" in r.text
    assert "include this block of YAML" in r.text and "html:\n  debrief: bar" in r.text


def test_no_init_twice(server, logs):
    """
    Requires `docker-compose up` in salmon directory
    """
    server.authorize()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post("/init_exp", data={"exp": exp.read_text()}, timeout=20)
    query = server.get("/query")
    assert query

    # Make sure errors on re-initialization
    server.post("/init_exp", data={"exp": exp.read_text()}, status_code=403, timeout=20)

    # Make sure the prescribed method works (resetting, then re-init'ing)
    server.delete("/reset", status_code=403, timeout=20)
    server.delete("/reset?force=1", timeout=20)

    server.authorize()
    server.post("/init_exp", data={"exp": exp.read_text()}, timeout=20)
    query = server.get("/query")
    assert query


def test_auth_repeated_entries(server):
    server._authorized = False
    server.post("/init_exp", status_code=401)  # unauthorized
    name, pword = "dfjklasdfsdf32", "baz"
    server._authorized = True
    r = server.post(f"/create_user/{name}/{pword}", status_code=403)
    assert "maximum number of users" in r.text.lower()


def test_random_error(server, logs):
    n_val = 5
    exp = {"targets": [0, 1, 2, 3, 4, 5], "samplers": {"RandomSampling": {}, "ARR": {}}}

    with pytest.raises(LogError), logs:
        server.authorize()
        r = server.post("/init_exp", data={"exp": exp}, status_code=500)
        assert "The sampler `RandomSampling` has been renamed to `Random`" in r.text


def test_html_defaults_rendered(server):
    server.authorize()
    exp = {
        "targets": 10,
        "html": {"arrow_keys": True, "css": "/*css foo*/", "skip_button": True},
    }
    server.post("/init_exp", data={"exp": exp})
    rendered = server.get("/").text

    html = Config().html.dict()

    assert f"<title>{html['title']}</title>" in rendered
    assert f"<p id=\"instructions\">{html['instructions']}</p>" in rendered
    assert f"id=\"debrief\">{html['debrief']}" in rendered
    assert f"var max_queries = {html['max_queries']};" in rendered
    assert 'id="skip-button"' in rendered and "Skip this question" in rendered
    assert "/*css foo*/" in rendered
    assert (
        "document.onkeydown = function checkKey(e) {" in rendered
        and "e.keyCode == '37') { // left arrow" in rendered
    )


def test_defaults_acceptable_config(server):
    server.authorize()
    r = server.post("/init_exp", data={"exp": {"targets": 10}})
    assert r.status_code == 200
    config = server.get("/config").json()

    server.reset()
    server.authorize()
    r = server.post("/init_exp", data={"exp": config})
    assert r.status_code == 200
    config2 = server.get("/config").json()
    assert config == config2
