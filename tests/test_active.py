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
import yaml

from .utils import logs, server


def test_active_wrong_proportion(server, logs):
    server.authorize()
    exp = {
        "targets": 10,
        "sampling": {"probs": {"a1": 50, "a2": 40}},
        "samplers": {
            "a1": {"class": "Random"},
            "a2": {"class": "Random"},
        },
    }
    r = server.post("/init_exp", data={"exp": json.dumps(exp)}, error=True)
    assert r.status_code == 500
    assert "values in sampling.probs should add up to 100" in r.text


def test_active_bad_keys(server, logs):
    server.authorize()
    exp = {
        "targets": 10,
        "sampling": {"probs": {"a1": 50, "a2": 40}},
        "samplers": {"a1": {"class": "Random"}},
    }
    r = server.post("/init_exp", data={"exp": exp}, error=True)
    assert r.status_code == 500
    assert all(
        x in r.text.lower()
        for x in ["sampling.probs keys", "are not the same as samplers keys"]
    )


def test_active_basics(server, logs):
    server.authorize()
    exp = Path(__file__).parent / "data" / "active.yaml"
    print("init'ing exp")
    server.post("/init_exp", data={"exp": exp.read_text()})
    print("done")

    with open(exp, "r") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    samplers = list(config["samplers"].keys())

    with logs:
        for k in range(len(samplers) * 2):
            print(k)
            q = server.get("/query").json()

            # Jerry rig this so this test isn't random (an algorithm is chosen at random)
            q["alg_ident"] = samplers[k % len(samplers)]

            ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
            server.post("/answer", json=ans)

        r = server.get("/responses")
        d = r.json()
        df = pd.DataFrame(d)
        assert (df["score"] <= 1).all()
        algs = df.alg_ident.unique()
        assert set(algs) == {"TSTE", "ARR", "CKL", "tste2", "GNMDS"}


def test_samplers_per_user(server, logs):
    server.authorize()
    exp = Path(__file__).parent / "data" / "active.yaml"
    print("init'ing exp")
    exp2 = yaml.safe_load(exp.read_bytes())
    exp2["sampling"] = {"samplers_per_user": 1}
    server.post("/init_exp", data={"exp": str(exp2)})
    print("done")

    with open(exp, "r") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    samplers = list(config["samplers"].keys())

    ident = random.choice(samplers)
    with logs:
        for k in range(len(samplers) * 2):
            q = server.get(f"/query?ident={ident}").json()
            ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
            server.post("/answer", json=ans)

        r = server.get("/responses")
        d = r.json()
        df = pd.DataFrame(d)
        algs = df.alg_ident.unique()
        assert len(set(algs)) == 1


def test_round_robin(server, logs):
    server.authorize()
    exp = Path(__file__).parent / "data" / "round-robin.yaml"
    server.post("/init_exp", data={"exp": exp.read_text()})

    with open(exp, "r") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    n = len(config["targets"])

    with logs:
        for k in range(2 * n):
            print(k)
            q = server.get("/query").json()

            ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
            server.post("/answer", json=ans)
            sleep(0.1)

        r = server.get("/responses")
        df = pd.DataFrame(r.json())
        assert set(df["head"].unique()) == set(range(11))
        diffs = np.abs(df["head"].diff().unique())
        assert {int(d) for d in diffs if not np.isnan(d)}.issubset({0, 1, 10})
        diffs = diffs.astype(int)
        assert (diffs == 0).sum() <= 2  # make sure zeros don't happen too often

    # A traceback I got in this test once. I think I've fixed but am not sure;
    # my tests pass, but I'm not certain this error is deterministic.
    #
    #  Traceback (most recent call last):
    #    File "./salmon/backend/alg.py", line 92, in run
    #      answers = self.get_answers(rj, clear=True)
    #    File "./salmon/backend/alg.py", line 210, in get_answers
    #      answers, success = pipe.execute()
    #    File "/opt/conda/lib/python3.7/site-packages/redis/client.py", line 4019, in execute
    #      return execute(conn, stack, raise_on_error)
    #    File "/opt/conda/lib/python3.7/site-packages/redis/client.py", line 3943, in _execute_transaction
    #      r = self.response_callbacks[command_name](r, **options)
    #    File "/opt/conda/lib/python3.7/json/decoder.py", line 337, in decode
    #      obj, end = self.raw_decode(s, idx=_w(s, 0).end())
    #  TypeError: expected string or bytes-like object
