from typing import Dict, List, Any
from functools import lru_cache
from time import time
import yaml
from copy import copy
from textwrap import dedent
import pathlib
import threading

from rejson import Client, Path
from fastapi import FastAPI

import numpy as np
import pandas as pd

from .utils import get_logger
from . import algs

logger = get_logger(__name__)

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)

app = FastAPI(title="salmon-backend")

samplers = {}


async def _get_config():
    return rj.jsonget("exp_config")


@app.post("/init")
async def init() -> bool:
    # TODO: Better handling of exceptions if params keys don't match
    logger.info("backend: initialized")
    config = await _get_config()
    for name, params in config["samplers"].items():
        _class = params.pop("class")
        Alg = getattr(algs, _class)
        samplers[name] = Alg(n=config["n"], **params)
    return list(samplers.keys())


@app.get("/model")
async def get_model(name: str):
    return 1
