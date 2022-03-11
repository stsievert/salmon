import random
from time import sleep
import pytest
import yaml
from pathlib import Path
import numpy as np

import pandas as pd

from .utils import LogError, logs, server


def test_round_robin_allowable(server):
    samplers = {"RoundRobin": {"allowable": [0, 2, 4]}, "Random": {}}
    config = {"samplers": samplers, "targets": 5}
    server.authorize()
    server.post("/init_exp", data={"exp": config})

    for k in range(20):
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
        server.post("/answer", json=ans)
    r = server.get("/responses")
    df = pd.DataFrame(r.json())
    RR = df.loc[df.sampler == "RoundRobin"]
    Rand = df.loc[df.sampler == "Random"]

    rr = RR[["left", "right", "head"]].to_numpy()
    rand = Rand[["left", "right", "head"]].to_numpy()

    assert set(np.unique(rr)) == {0, 2, 4}
    assert set(np.unique(rand)) == {0, 1, 2, 3, 4}

def test_round_robin_allowable_too_large(server):
    samplers = {"RoundRobin": {"allowable": [0, 2, 5]}, "Random": {}}
    config = {"samplers": samplers, "targets": 5}
    server.authorize()
    r = server.post("/init_exp", data={"exp": config}, error=True)
    assert r.status_code == 500
    assert "At least one allowable target is too large" in r.text

def test_round_robin_allowable_wrong_type(server):
    samplers = {"RoundRobin": {"allowable": 0}, "Random": {}}
    config = {"samplers": samplers, "targets": 5}
    server.authorize()
    r = server.post("/init_exp", data={"exp": config}, error=True)
    assert r.status_code == 500
    assert "Specify a list for allowable. Got" in r.text

def test_round_robin_allowable_not_integers(server):
    samplers = {"RoundRobin": {"allowable": [0.1, 0.2, 0.3]}, "Random": {}}
    config = {"samplers": samplers, "targets": 5}
    server.authorize()
    r = server.post("/init_exp", data={"exp": config}, error=True)
    assert r.status_code == 500
    assert "Not all items in allowable are integers" in r.text

def test_round_robin_allowable_too_small(server):
    samplers = {"RoundRobin": {"allowable": [0, 1]}, "Random": {}}
    config = {"samplers": samplers, "targets": 5}
    server.authorize()
    r = server.post("/init_exp", data={"exp": config}, error=True)
    assert r.status_code == 500
    assert "Specify at least 3 allowable items. Got" in r.text
