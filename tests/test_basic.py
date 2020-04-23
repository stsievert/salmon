import os
from pathlib import Path
from time import sleep
import random
import json
import yaml
from time import time

import numpy as np
import pandas as pd
from typing import Tuple
from joblib import Parallel, delayed

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from .utils import server


def test_basics(server):
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
    server.post(
        "/init_exp", data={"exp": exp.read_bytes()}, auth=(username, password),
    )
    exp_config = yaml.safe_load(exp.read_bytes())
    puid = "puid-foo"
    answers = []
    print("Starting loop...")
    for k in range(30):
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
        "time_received_since_start",
        "time_received",
        "head",
        "right",
        "left",
        "winner",
        "winner_object",
        "right_object",
        "head_object",
        "left_object",
        "winner_filename",
        "right_filename",
        "left_filename",
        "head_filename",
        "puid",
        "response_time",
        "network_latency",
        "datetime_received",
        "name",
        "score",
    }
    n = len(exp_config["targets"])
    assert (0 == df["head"].min()) and (df["head"].max() == n - 1)
    assert (0 == df["left"].min()) and (df["left"].max() == n - 1)
    assert (0 == df["right"].min()) and (df["right"].max() == n - 1)
    assert 10e-3 < df.response_time.min()
    assert expected_cols == set(df.columns)
    assert df.puid.nunique() == 1

    # Scores have to be unique => weaker test (random chooses scores
    # uniformly at random between 0, 1; can't test that here)
    #  assert np.allclose(df.score, 0)
    assert (df.score > 0).all()

    r = server.get("/responses", auth=(username, password))
    assert r.status_code == 200
    assert "exception" not in r.text


def test_bad_file_upload(server):
    server.authorize()
    server.get("/init_exp")
    exp = Path(__file__).parent / "data" / "bad_exp.yaml"
    r = server.post(
        "/init_exp",
        data={"exp": exp.read_bytes()},
        error=True,
    )
    assert r.status_code == 500
    assert "Error!" in r.text
    assert "yaml" in r.text
    assert "-\tfoo" in r.text


def test_no_repeats(server):
    server.authorize()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    server.post(
        "/init_exp", data={"exp": exp.read_bytes()}
    )
    for k in range(100):
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
        server.post("/answer", data=ans)

    r = server.get("/responses")
    df = pd.DataFrame(r.json())
    equal_targets = (
        (df["head"] == df["right"]).any()
        or (df["head"] == df["left"]).any()
        or (df["left"] == df["right"]).any()
    )
    assert not equal_targets
