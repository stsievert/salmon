import asyncio
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

from .utils import LogError, logs, server


def test_samplers_per_user(server, logs):
    exp = Path(__file__).parent / "data" / "active.yaml"
    print("init'ing exp")
    exp2 = yaml.safe_load(exp.read_bytes())
    exp2["sampling"] = {"samplers_per_user": 1}

    print("done")

    with open(exp, "r") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    samplers = list(config["samplers"].keys())

    sampler = random.choice(samplers)
    with logs:
        server.authorize()
        server.post("/init_exp", data={"exp": str(exp2)})
        for k in range(len(samplers) * 2):
            q = server.get(f"/query?sampler={sampler}").json()
            ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
            server.post("/answer", json=ans)
            sleep(0.1)

        r = server.get("/responses")
        d = r.json()
        df = pd.DataFrame(d)
        algs = df.sampler.unique()
        assert len(set(algs)) == 1
        _ = len(set(algs))


def test_active_wrong_proportion(server, logs):
    exp = {
        "targets": 16,
        "sampling": {"probs": {"a1": 50, "a2": 40}},
        "samplers": {"a1": {"class": "Random"}, "a2": {"class": "Random"},},
    }
    with pytest.raises(LogError):
        with logs:
            server.authorize()
            r = server.post("/init_exp", data={"exp": json.dumps(exp)}, error=True)
            assert r.status_code == 500
            assert "values in sampling.probs should add up to 100" in r.text


def test_active_bad_keys(server, logs):
    exp = {
        "targets": 16,
        "sampling": {"probs": {"a1": 50, "a2": 40}},
        "samplers": {"a1": {"class": "Random"}},
    }
    with pytest.raises(LogError):
        with logs:
            server.authorize()
            r = server.post("/init_exp", data={"exp": exp}, error=True)
            assert r.status_code == 500
            assert all(
                x in r.text.lower()
                for x in ["sampling.probs keys", "are not the same as samplers keys"]
            )


@pytest.mark.parametrize("sampler", ["ARR", "CKL"])
def test_active_queries_generated(server, sampler, logs):
    # R=1 chosen because that determines when active sampling starts; this
    # test is designed to make sure no unexpected errors are thrown in
    # active portion (not that it generates a good embedding)

    n = 6
    config = {
        "targets": [_ for _ in range(n)],
        "samplers": {sampler: {}},
        "sampling": {"common": {"d": 1, "R": 1}},
    }
    with logs:
        server.authorize()
        server.post("/init_exp", data={"exp": config})
        n_active_queries = 0
        for k in range(6 * n + 1):
            q = server.get("/query").json()

            ans = random.choice([q["left"], q["right"]])
            ans = {"winner": ans, "puid": "foo", **q}
            print(q)
            server.post("/answer", json=ans)

            if q["score"] != -9999:
                # scored queries have been posted to the database
                # now, only thing to test is popping off database
                n_active_queries += 1
            if n_active_queries == n:
                sleep(1)
                break

            sleep(100e-3)
            if k % n == 0:
                sleep(1)

    d = server.get("/responses").json()

    df = pd.DataFrame(d)
    random_queries = df["score"] == -9999
    active_queries = ~random_queries
    assert active_queries.sum()
    assert random_queries.sum()

    samplers = set(df.sampler.unique())
    assert samplers == {sampler}


def test_active_basics(server, logs):
    exp = Path(__file__).parent / "data" / "active.yaml"
    print("init'ing exp")
    print("done")

    with open(exp, "r") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    samplers = list(config["samplers"].keys())

    with logs:
        server.authorize()
        server.post("/init_exp", data={"exp": exp.read_text()})
        for k in range(len(samplers) * 2):
            print(k)
            q = server.get("/query").json()

            # Jerry rig this so this test isn't random (an algorithm is chosen at random)
            q["sampler"] = samplers[k % len(samplers)]
            ans = random.choice([q["left"], q["right"]])

            ans = {"winner": ans, "puid": "foo", **q}
            server.post("/answer", json=ans)

        r = server.get("/responses")
        d = r.json()
        df = pd.DataFrame(d)
        assert (df["score"] <= 1).all()
        algs = df.sampler.unique()
        assert set(algs) == {"TSTE", "ARR", "CKL", "tste2", "GNMDS"}
