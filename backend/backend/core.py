from typing import Dict, List, Any
from functools import lru_cache
from time import time
import yaml
from copy import copy
from textwrap import dedent
import pathlib
import threading
import asyncio

from rejson import Client, Path
from fastapi import FastAPI, BackgroundTasks

import numpy as np
import pandas as pd

from .utils import get_logger
from . import algs

logger = get_logger(__name__)

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)

app = FastAPI(title="salmon-backend")

samplers = {}


@app.post("/init")
async def init(background_tasks: BackgroundTasks) -> bool:
    # TODO: Better handling of exceptions if params keys don't match
    logger.info("backend: initialized")
    config = rj.jsonget("exp_config")
    for name, params in config["samplers"].items():
        _class = params.pop("class")
        Alg = getattr(algs, _class)
        samplers[name] = Alg(n=config["n"], **params)

    client = None
    logger.info(f"Starting algs={samplers.keys()}")
    for name, alg in samplers.items():
        background_tasks.add_task(algs.run, name, alg, client, rj)

    logger.info("samplers=%s", list(samplers.keys()))
    return list(samplers.keys())


@app.get("/model")
async def get_model(name: str):
    return 1
