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

from .test_basic import _get_auth, _get, _post, _delete

URL = "http://127.0.0.1:8421"


def test_basics():
    """
    Requires `docker-compose up` in salmon directory
    """
    username, password = _get_auth()
    exp = Path(__file__).parent / "data" / "exp-active.yaml"
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
    assert (df.score > 0).all()
