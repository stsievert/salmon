from typing import Dict, List, Any, Union
from functools import lru_cache
from time import time
import yaml
from copy import copy
from textwrap import dedent
import pathlib
import threading
import random

from fastapi import FastAPI, HTTPException, Form
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
import ujson

from rejson import Client, Path

import numpy as np
import pandas as pd

from .utils import ServerException, get_logger, sha256

logger = get_logger(__name__)

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)

app = FastAPI(
    title="Salmon",
    description=dedent(
        """A prototype platform for crowdsourcing triplet queries.
        \n\n***Warning!*** This platform is experimental and unstable.
        """
    ),
)
pkg_dir = pathlib.Path(__file__).absolute().parent
app.mount("/static", StaticFiles(directory=str(pkg_dir / "static")), name="static")
templates = Jinja2Templates(directory="templates")


def _get_config():
    return rj.jsonget("exp_config")


async def _ensure_initialized():
    if "exp_config" not in rj:
        raise ServerException("No data has been uploaded")
    exp_config = _get_config()
    expected_keys = [
        "targets",
        "samplers",
        "instructions",
        "n",
        "max_queries",
        "debrief",
    ]
    if not set(exp_config) == set(expected_keys):
        msg = "Experiment keys are not correct. Expected {}, got {}"
        raise ServerException(msg.format(expected_keys, list(exp_config.keys())))
    return exp_config


@app.get("/", tags=["public"])
async def get_query_page(request: Request):
    """
    Load the query page and present a "triplet query".
    """
    exp_config = await _ensure_initialized()
    uid = "salmon-{}".format(np.random.randint(2 ** 32 - 1))
    puid = sha256(uid)[:16]
    items = {
        "puid": puid,
        "instructions": exp_config["instructions"],
        "targets": exp_config["targets"],
        "max_queries": exp_config["max_queries"],
        "debrief": exp_config["debrief"],
    }
    items.update(request=request)
    return templates.TemplateResponse("query_page.html", items)


@app.get("/get_query", tags=["public"])
async def get_query() -> Dict[str, Union[int, str, float]]:
    """
    Get the objects for a triplet query

    Returns
    -------
    `d : Dict[str, int]`. Indices for different objects.

    """
    samplers = rj.jsonget("samplers")
    name = random.choice(samplers)
    key = f"alg-{name}-queries"
    queries = rj.bzpopmax(key)
    _, serialized_query, score = queries

    # How many queries have this score?
    h, l, r = serialized_query.split("-")
    return {
        "head": int(h),
        "left": int(l),
        "right": int(r),
        "name": name,
        "score": score,
    }


class Answer(BaseModel):
    """
    An answer to a triplet query. head, left and right are integers
    from '/get_query'. The 'winner' is an integer that is most similar to 'head',
    and must be one of 'left' and 'right'.

    'puid' is the "participant unique ID", and is optional.

    """

    head: int
    left: int
    right: int
    winner: int
    name: str
    score: float
    puid: str = ""
    response_time: float = -1
    network_latency: float = -1


@app.post("/process_answer", tags=["public"])
async def process_answer(ans: Answer):
    """
    Process the answer, and append the received answer (alongside participant
    UID) to the database.

    See the <a href='#model-Answer'>Answer schema</a> for more detail.

    Returns
    -------
    `d : Dict[str, bool]`. On success, `d == {"success": True}`

    """
    d = ujson.loads(ans.json())
    d.update({"time_received": time()})
    name = d["name"]
    rj.jsonarrappend(f"alg-{name}-answers", root, copy(d))
    rj.jsonarrappend("all-responses", root, copy(d))
    return {"success": True}
