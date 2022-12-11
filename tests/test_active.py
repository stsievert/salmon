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


@pytest.mark.parametrize("sampler", ["ARR", "Random"])
def test_active_queries_generated(server, sampler, logs):
    # R=1 chosen because that determines when active sampling starts; this
    # test is designed to make sure no unexpected errors are thrown in
    # active portion (not that it generates a good embedding)

    # tests ARR to make sure active scores are generated;
    # tests Random to make sure that's not a false positive and
    # random queries are properly identifies

    n = 6
    config = {
        "targets": [_ for _ in range(n)],
        "samplers": {sampler: {}},
        "sampling": {},
    }
    if sampler != "Random":
        config["sampling"]["common"] = {"d": 1, "R": 1}
    with logs:
        server.authorize()
        server.post("/init_exp", data={"exp": config})
        active_queries_generated = False
        for k in range(10 * n + 1):
            q = server.get("/query").json()
            query = "random" if q["score"] == -9999 else "active"
            if query == "active":
                active_queries_generated = True
                break

            sleep(200e-3)

            ans = random.choice([q["left"], q["right"]])
            ans = {"winner": ans, "puid": "foo", **q}
            server.post("/answer", json=ans)

            if k % n == 0:
                sleep(1)

    if sampler == "Random":
        assert not active_queries_generated
    else:
        assert active_queries_generated


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
        for k in range(len(samplers) * 3):
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
        assert True  # to see if a log error is caught in the traceback
