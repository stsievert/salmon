import json
import os
import pickle
import random
from pathlib import Path
from time import sleep, time
from typing import Tuple
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import yaml
from joblib import Parallel, delayed
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from .utils import server, logs


def test_active_basics(server, logs):
    server.authorize()
    exp = Path(__file__).parent / "data" / "active.yaml"
    print("init'ing exp")
    server.post("/init_exp", data={"exp": exp.read_bytes()})
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
            server.post("/answer", data=ans)

        r = server.get("/responses")
        df = pd.DataFrame(r.json())
        assert (df["score"] <= 1).all()
        assert set(df.alg_ident.unique()) == {"TSTE", "STE", "CKL", "tste2", "GNMDS"}


def test_round_robin(server, logs):
    server.authorize()
    exp = Path(__file__).parent / "data" / "round-robin.yaml"
    server.post("/init_exp", data={"exp": exp.read_bytes()})

    with open(exp, "r") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    n = len(config["targets"])

    with logs:
        for k in range(2 * n):
            print(k)
            q = server.get("/query").json()

            ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
            server.post("/answer", data=ans)
            sleep(1)

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

