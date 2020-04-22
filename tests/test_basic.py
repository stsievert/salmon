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

URL = "http://127.0.0.1:8421"


def _get_auth() -> Tuple[str, str]:
    p = Path(__file__).parent.parent / "creds.yaml"
    if p.exists():
        creds = yaml.safe_load(p.read_text())
        return (creds["username"], creds["password"])

    return ("username", "password")


def _get(endpoint, URL=URL, status_code=200, **kwargs):
    r = requests.get(URL + endpoint, **kwargs)
    assert r.status_code == status_code
    return r


def _post(endpoint, data=None, URL=URL, status_code=200, error=False, **kwargs):
    #  data = data or {}
    if isinstance(data, dict) and "exp" not in data:
        data = json.dumps(data)
    r = requests.post(URL + endpoint, data=data, **kwargs)
    if not error:
        assert r.status_code == status_code
    return r


def _delete(endpoint, data=None, URL=URL, status_code=200, **kwargs):
    #  data = data or {}
    if isinstance(data, dict) and "exp" not in data:
        data = json.dumps(data)
    r = requests.delete(URL + endpoint, data=data, **kwargs)
    assert r.status_code == status_code
    return r


def test_basics():
    """
    Requires `docker-compose up` in salmon directory
    """
    username, password = _get_auth()
    print(username, password)
    _delete("/reset", status_code=401)
    r = _delete("/reset?force=1", auth=(username, password))
    assert r.json() == {"success": True}
    _get("/reset", status_code=401)
    r = _get("/reset?force=1", auth=(username, password))
    assert r.json() == {"success": True}
    _get("/init_exp")
    exp = Path(__file__).parent / "data" / "exp.yaml"
    _post(
        "/init_exp", data={"exp": exp.read_bytes()}, auth=(username, password),
    )
    exp_config = yaml.safe_load(exp.read_bytes())
    puid = "puid-foo"
    answers = []
    for k in range(30):
        _start = time()
        q = _get("/get_query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": puid, **q}
        answers.append(ans)
        sleep(10e-3)
        ans["response_time"] = time() - _start
        _post("/process_answer", data=ans)

    r = _get("/get_responses", auth=(username, password))
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
        "query_randomly_selected",
    }
    n = len(exp_config["targets"])
    assert (0 == df["head"].min()) and (df["head"].max() == n - 1)
    assert (0 == df["left"].min()) and (df["left"].max() == n - 1)
    assert (0 == df["right"].min()) and (df["right"].max() == n - 1)
    assert 10e-3 < df.response_time.min()
    assert expected_cols == set(df.columns)
    assert df.puid.nunique() == 1

    r = _get("/get_responses", auth=(username, password))
    assert r.status_code == 200
    assert "exception" not in r.text


def test_bad_file_upload():
    username, password = _get_auth()
    print(username, password)
    _get("/init_exp")
    exp = Path(__file__).parent / "data" / "bad_exp.yaml"
    r = _post(
        "/init_exp",
        data={"exp": exp.read_bytes()},
        auth=(username, password),
        error=True,
    )
    assert r.status_code == 500
    assert "Error!" in r.text
    assert "yaml" in r.text
    assert "-\tfoo" in r.text


def test_no_repeats():
    username, password = _get_auth()
    exp = Path(__file__).parent / "data" / "exp.yaml"
    _post(
        "/init_exp", data={"exp": exp.read_bytes()}, auth=(username, password),
    )
    for k in range(100):
        q = _get("/get_query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
        _post("/process_answer", data=ans)

    r = _get("/get_responses", auth=(username, password))
    df = pd.DataFrame(r.json())
    equal_targets = (
        (df["head"] == df["right"]).any()
        or (df["head"] == df["left"]).any()
        or (df["left"] == df["right"]).any()
    )
    assert not equal_targets
