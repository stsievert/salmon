import json
import os
import random
from pathlib import Path
from time import sleep, time
from typing import Tuple

import numpy as np
import pandas as pd
import pytest
import yaml

from salmon.triplets.samplers import TSTE

from .utils import LogError, logs, server


def test_backend_basics(server, logs):
    exp = Path(__file__).parent / "data" / "round-robin.yaml"
    exp_config = yaml.safe_load(exp.read_text())

    assert len(exp_config["samplers"]) == 1
    puid = "puid-foo"
    with logs:
        server.authorize()
        server.post("/init_exp", data={"exp": exp.read_text()})
        for k in range(30):
            _start = time()
            q = server.get("/query").json()
            score = max(abs(q["head"] - q["left"]), abs(q["head"] - q["right"]))
            assert q["score"] == score
            ans = {"winner": random.choice([q["left"], q["right"]]), "puid": puid, **q}
            ans["response_time"] = time() - _start
            server.post("/answer", data=ans)
        sleep(5)

    print("Getting responses...")
    r = server.get("/responses")
    print("Done responses...")
    df = pd.DataFrame(r.json())
    assert len(df) == 30


def test_init_errors_propogate(server):
    exp = Path(__file__).parent / "data" / "exp-active-bad.yaml"

    server.authorize()
    server.get("/init")
    r = server.post("/init_exp", data={"exp": exp.read_text()}, error=True)
    assert r.status_code == 500
    assert "module 'salmon.triplets.samplers' has no attribute 'FooBar'" in r.text


def test_run_errors_logged(server, logs):
    # This test is only designed to make sure errors are raised during pytest
    # it's not designed to make sure errors have much detail; the docker logs
    # will reflect more of that.
    config = {
        "targets": list(range(10)),
        "sampling": {"common": {"d": 1}},
        "samplers": {"ARR": {}},
    }
    with pytest.raises(LogError):
        with logs:
            server.authorize()
            server.get("/init")
            r = server.post("/init_exp", data={"exp": config})
            for k in range(10):
                q = server.get("/query").json()
                winner = random.choice([q["left"], q["right"]])
                ans = {"winner": winner, "puid": "", **q}
                ans["left"] = 12
                server.post("/answer", data=ans)
                sleep(2 if k == 3 else 1)
            sleep(5)


def test_backend_random_state():
    n, d = 85, 2
    random_state = 42
    alg1 = TSTE(n=n, d=d, ident="alg1", random_state=random_state)
    alg2 = TSTE(n=n, d=d, ident="alg2", random_state=random_state)
    assert np.allclose(alg1.opt.embedding_, alg2.opt.embedding_)
