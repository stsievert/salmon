import json
import os
import random
from pathlib import Path
from time import sleep, time
from typing import Tuple

import numpy as np
import pandas as pd
import yaml
from joblib import Parallel, delayed

from .utils import server


def test_backend_basics(server):
    exp = Path(__file__).parent / "data" / "exp-active.yaml"
    server.authorize()
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    exp_config = yaml.safe_load(exp.read_bytes())

    # ran into a bug that happened with len(samplers) > 1
    assert len(exp_config["samplers"]) == 2
    puid = "puid-foo"
    for k in range(30):
        _start = time()
        q = server.get("/query").json()
        score = max(abs(q["head"] - q["left"]), abs(q["head"] - q["right"]))
        assert q["score"] == score
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": puid, **q}
        ans["response_time"] = time() - _start
        server.post("/answer", data=ans)

    r = server.get("/responses")
    df = pd.DataFrame(r.json())
    assert (df.score > 0).all()


def test_init_errors_propogate(server):
    server.authorize()
    server.get("/init_exp")
    exp = Path(__file__).parent / "data" / "exp-active-bad.yaml"
    r = server.post("/init_exp", data={"exp": exp.read_bytes()}, error=True)
    assert r.status_code == 500
    assert "module 'salmon.backend.algs' has no attribute 'RoundRobinFooBad'" in r.text
