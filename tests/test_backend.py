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

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from .utils import server


def test_backend_basics(server):
    username, password = server.auth()
    exp = Path(__file__).parent / "data" / "exp-active.yaml"
    server.post(
        "/init_exp", data={"exp": exp.read_bytes()}, auth=(username, password),
    )
    exp_config = yaml.safe_load(exp.read_bytes())
    puid = "puid-foo"
    for k in range(30):
        print(k)
        _start = time()
        q = server.get("/get_query").json()
        ans = {"winner": random.choice([q["left"], q["right"]]), "puid": puid, **q}
        ans["response_time"] = time() - _start
        server.post("/process_answer", data=ans)

    r = server.get("/get_responses", auth=(username, password))
    df = pd.DataFrame(r.json())
    assert (df.score > 0).all()
