from typing import Dict, List, Any
from functools import lru_cache
from time import time
import yaml
from copy import copy

from fastapi import FastAPI, HTTPException
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
import ujson

from rejson import Client, Path

import numpy as np
import pandas as pd

from .utils import ServerException

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)
rj.jsonset("responses", root, [])
rj.jsonset("start_time", root, time())

app = FastAPI()
app.mount("/static", StaticFiles(directory="templates"), name="static")
templates = Jinja2Templates(directory="templates")


@lru_cache()
def _get_config():
    return rj.jsonget("exp_config")


async def _ensure_initialized():
    if "exp_config" not in rj:
        raise ServerException("No data has been uploaded")
    exp_config = _get_config()
    expected_keys = ["targets", "instructions", "n"]
    if not set(exp_config) == set(expected_keys):
        msg = "Experiment keys are not correct. Expected {}, got {}"
        raise ServerException(msg.format(expected_keys, list(exp_config.keys())))
    return exp_config


@app.get("/")
async def get_query_page(request: Request):
    """
    Load the query page and present a "triplet query".
    """
    exp_config = await _ensure_initialized()
    items = {
        "puid": np.random.randint(2 ** 20, 2 ** 32 - 1),
        "instructions": exp_config["instructions"],
        "targets": exp_config["targets"],
    }
    items.update(request=request)
    return templates.TemplateResponse("query_page.html", items)


@app.get("/get_query")
async def get_query() -> Dict[str, int]:
    """
    Get the objects for a triplet query

    Returns
    -------
    `d : Dict[str, int]`. Indices for different objects.

    """
    exp_config = await _ensure_initialized()
    n = exp_config["n"]
    h, l, r = list(np.random.choice(n, size=3, replace=False))
    return {"head": int(h), "left": int(l), "right": int(r)}


class Answer(BaseModel):
    head: int
    left: int
    right: int
    winner: int
    puid: int = -1


@app.post("/process_answer")
def process_answer(ans: Answer):
    """
    Process the answer, and append the received answer (alongside participant
    UID) to the database.

    Arguments
    ---------
    * `head, left, right : int, int, int`. The result of ``get_query``
    * `winner : int`. The item the user selected as most similar to ``head``
    * `puid : int`.  The participant UID

    Returns
    -------
    `d : Dict[str, bool]`. On success, `d == {"success": True}`

    """
    d = ujson.loads(ans.json())
    d.update({"time_received": time()})
    rj.jsonarrappend("responses", root, d)
    return {"success": True}
