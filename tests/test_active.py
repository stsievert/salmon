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

from .utils import server


def test_active_basics(server):
    server.authorize()
    exp = Path(__file__).parent / "data" / "active.yaml"
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    for k in range(6 * 3):
        print(k)
        q = server.get("/query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
        server.post("/answer", data=ans)

    r = server.get("/responses")
    df = pd.DataFrame(r.json())
    assert (df["score"] <= 0).all()
    assert set(df.alg_ident.unique()) == {"TSTE", "STE", "RandomSampling", "CKL", "tste2", "GNMDS"}
