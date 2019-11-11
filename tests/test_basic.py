import os
from pathlib import Path
from time import sleep
import random
import json

import numpy as np
import pandas as pd

import requests

URL = "http://127.0.0.1:8000"


def _get(endpoint, URL=URL):
    r = requests.get(URL + endpoint)
    assert r.status_code == 200
    return r


def _post(endpoint, data=None, URL=URL):
    data = data or {}
    if "exp" not in data:
        data = json.dumps(data)
    r = requests.post(URL + endpoint, data=data)
    assert r.status_code == 200
    return r


def test_basic():
    """
    Requires `docker-compose up` in salmon directory
    """
    _post("/reset")
    _get("/init_exp")
    exp = Path(__file__).parent / "data" / "exp.yaml"
    _post("/init_file", data={"exp": exp.read_bytes()})
    puid = np.random.randint(2 ** 20, 2 ** 32 - 1)
    answers = []
    for k in range(20):
        q = _get("/get_query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": puid, **q}
        answers.append(ans)
        sleep(10e-3)
        _post("/process_answer", data=ans)

    r = _get("/get_responses")
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
