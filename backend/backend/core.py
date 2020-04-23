from typing import Dict, List, Any, Union
from functools import lru_cache
from time import time
import yaml
from copy import copy
from textwrap import dedent
import pathlib
import threading
import asyncio
import random

from rejson import Client, Path
from fastapi import FastAPI, BackgroundTasks
from starlette.background import BackgroundTasks

import numpy as np
import pandas as pd

from .utils import get_logger
from . import algs

logger = get_logger(__name__)

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)

app = FastAPI(title="salmon-backend")

samplers = {}


@app.post("/init/{name}")
async def init(name: str, background_tasks: BackgroundTasks) -> bool:
    # TODO: Better handling of exceptions if params keys don't match
    logger.info("backend: initialized")
    config = rj.jsonget("exp_config")

    params = config["samplers"][name]
    _class = params.pop("class")
    Alg = getattr(algs, _class)
    alg = Alg(n=config["n"], **params)
    samplers[name] = alg

    client = None
    logger.info(f"Starting algs={samplers.keys()}")
    background_tasks.add_task(alg.run, name, client, rj)

    logger.info("samplers=%s", list(samplers.keys()))
    return list(samplers.keys())


@app.get("/model")
async def get_model(name: str):
    return 1


@app.post("/reset")
def reset():
    global samplers
    samplers = {}
    return True


@app.get("/query")
async def get_query() -> Dict[str, Union[int, str, float]]:
    name = random.choice(list(samplers.keys()))
    alg = samplers[name]
    if hasattr(alg, "get_query"):
        query, score = alg.get_query()
        return {"name": name, "score": score, **query}
    key = f"alg-{name}-queries"
    queries = rj.bzpopmax(key)
    _, serialized_query, score = queries
    q = algs.utils.deserialize_query(serialized_query)
    return {"name": name, "score": score, **q}
