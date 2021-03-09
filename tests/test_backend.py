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
from joblib import Parallel, delayed

from .utils import server, logs, LogError
from salmon.triplets.algs import TSTE


def test_backend_basics(server, logs):
    exp = Path(__file__).parent / "data" / "round-robin.yaml"
    server.authorize()
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    exp_config = yaml.safe_load(exp.read_bytes())

    # ran into a bug that happened with len(samplers) > 1
    assert len(exp_config["samplers"]) == 1
    puid = "puid-foo"
    with logs:
        for k in range(30):
            _start = time()
            q = server.get("/query").json()
            score = max(abs(q["head"] - q["left"]), abs(q["head"] - q["right"]))
            assert q["score"] == score
            ans = {"winner": random.choice([q["left"], q["right"]]), "puid": puid, **q}
            ans["response_time"] = time() - _start
            server.post("/answer", data=ans)

    print("Getting responses...")
    r = server.get("/responses")
    print("Done responses...")
    df = pd.DataFrame(r.json())
    assert len(df) == 30


def test_init_errors_propogate(server):
    server.authorize()
    server.get("/init_exp")
    exp = Path(__file__).parent / "data" / "exp-active-bad.yaml"
    r = server.post("/init_exp", data={"exp": exp.read_bytes()}, error=True)
    assert r.status_code == 500
    assert "module 'salmon.triplets.algs' has no attribute 'FooBar'" in r.text


def test_run_errors_logged(server, logs):
    server.authorize()
    server.get("/init_exp")
    config = {"targets": list(range(10)), "d": 1, "samplers": {"Test": {}}}
    r = server.post("/init_exp", data={"exp": yaml.safe_dump(config)})
    with pytest.raises(LogError, match="Test error"):
        with logs:
            for k in range(10):
                q = server.get("/query").json()
                winner = random.choice([q["left"], q["right"]])
                ans = {"winner": winner, "puid": "", **q}
                ans["left"] = 12
                sleep(1)
                server.post("/answer", data=ans)


def test_backend_random_state():
    n, d = 85, 2
    random_state = 42
    alg1 = TSTE(n=n, d=d, ident="alg1", random_state=random_state)
    alg2 = TSTE(n=n, d=d, ident="alg2", random_state=random_state)
    assert np.allclose(alg1.opt.embedding_, alg2.opt.embedding_)
