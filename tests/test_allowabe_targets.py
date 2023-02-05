import random

import numpy as np
import pandas as pd
import pytest

from .utils import server


@pytest.mark.parametrize("sampler", ["RoundRobin", "Random"])
def test_targets(sampler, server):
    samplers = {sampler: {"targets": [0, 2, 4]}, "Test": {"class": "Random"}}
    config = {"samplers": samplers, "targets": 5}
    server.authorize()
    server.post("/init_exp", data={"exp": config})

    for k in range(30):
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
        server.post("/answer", json=ans)
    r = server.get("/responses")
    df = pd.DataFrame(r.json())

    allow = df.loc[df.sampler == sampler, ["left", "right", "head"]].to_numpy()
    test = df.loc[df.sampler == "Test", ["left", "right", "head"]].to_numpy()

    assert set(np.unique(allow)) == {0, 2, 4}
    assert set(np.unique(test)) == {0, 1, 2, 3, 4}


@pytest.mark.parametrize("sampler", ["RoundRobin", "Random"])
def test_targets_too_large(sampler, server):
    samplers = {sampler: {"targets": [0, 2, 5]}}
    config = {"samplers": samplers, "targets": 5}
    server.authorize()
    r = server.post("/init_exp", data={"exp": config}, error=True)
    assert r.status_code == 500
    assert "At least one targets target is too large" in r.text


@pytest.mark.parametrize("sampler", ["RoundRobin", "Random"])
def test_targets_wrong_type(sampler, server):
    samplers = {sampler: {"targets": 0}}
    config = {"samplers": samplers, "targets": 5}
    server.authorize()
    r = server.post("/init_exp", data={"exp": config}, error=True)
    assert r.status_code == 500
    assert "Specify a list for targets. Got" in r.text


@pytest.mark.parametrize("sampler", ["RoundRobin", "Random"])
def test_targets_not_integers(sampler, server):
    samplers = {sampler: {"targets": [0.1, 0.2, 0.3]}}
    config = {"samplers": samplers, "targets": 5}
    server.authorize()
    r = server.post("/init_exp", data={"exp": config}, error=True)
    assert r.status_code == 500
    assert "Not all items in targets are integers" in r.text


@pytest.mark.parametrize("sampler", ["RoundRobin", "Random"])
def test_targets_too_small(sampler, server):
    samplers = {sampler: {"targets": [0, 1]}}
    config = {"samplers": samplers, "targets": 5}
    server.authorize()
    r = server.post("/init_exp", data={"exp": config}, error=True)
    assert r.status_code == 500
    assert "Specify at least 3 targets items. Got" in r.text
