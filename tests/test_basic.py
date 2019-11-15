import os
from pathlib import Path
from time import sleep
import random
import json
import yaml

import numpy as np
import pandas as pd
from typing import Tuple

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

URL = "http://127.0.0.1:8000"


def _get_auth() -> Tuple[str, str]:
    p = Path(__file__).parent.parent / "creds.yaml"
    if p.exists():
        creds = yaml.safe_load(p.read_text())
        return (creds["username"], creds["password"])

    os.environ["SALMON_NO_AUTH"] = "1"
    return ("username", "password")


def _get(endpoint, URL=URL, status_code=200, **kwargs):
    r = requests.get(URL + endpoint, **kwargs)
    assert r.status_code == status_code
    return r


def _post(endpoint, data=None, URL=URL, status_code=200, **kwargs):
    #  data = data or {}
    if isinstance(data, dict) and "exp" not in data:
        data = json.dumps(data)
    r = requests.post(URL + endpoint, data=data, **kwargs)
    assert r.status_code == status_code
    return r


def _delete(endpoint, data=None, URL=URL, status_code=200, **kwargs):
    #  data = data or {}
    if isinstance(data, dict) and "exp" not in data:
        data = json.dumps(data)
    r = requests.delete(URL + endpoint, data=data, **kwargs)
    assert r.status_code == status_code
    return r


def test_basic():
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
    puid = np.random.randint(2 ** 20, 2 ** 32 - 1)
    answers = []
    for k in range(20):
        q = _get("/get_query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": puid, **q}
        answers.append(ans)
        sleep(10e-3)
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
        "winner",
        "head",
        "right",
        "winner_object",
        "right_object",
        "left",
        "head_object",
        "left_object",
        "puid",
    }
    assert expected_cols.issubset(set(df.columns))
