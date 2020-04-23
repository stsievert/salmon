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