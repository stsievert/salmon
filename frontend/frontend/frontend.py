from typing import Dict, List, Any
from functools import lru_cache
from time import time
import yaml
from copy import copy

from fastapi import FastAPI, File, UploadFile, HTTPException
from jinja2 import Template
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.responses import HTMLResponse, JSONResponse
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


@app.get("/init_exp")
def upload():
    """
    Upload a YAML file that specifies an experiment.

    Inputs
    ------

    Notes
    -----
    This YAML files needs to
    have keys

    * targets (list, required)
    * instructions (str, optional)

    Targets/instructions can render certain HTML tags.

    Example
    -------

        - targets:
          - object 1
          - object 2
          - <b>bold</i> object 3
          - <i>object</i> 4
          - <img src="https://en.wikipedia.org/wiki/File:2010_Winter_Olympics_Bode_Miller_in_downhill.jpg" />

    """
    body = """
    <body>
    <form action="/init_file" enctype="multipart/form-data" method="post">
    <input name="exp" type="file">
    <input type="submit">
    </form>
    </body>
    """
    return HTMLResponse(content=body)


@app.post("/init_file")
async def init_file(exp: UploadFile = File(default="")):
    config = yaml.load(await exp.read(), Loader=yaml.SafeLoader)
    exp_config: Dict = {
        "instructions": "Default instructions (can include <i>arbitrary</i> HTML)"
    }
    exp_config.update(config)
    exp_config["n"] = len(exp_config["targets"])
    rj.jsonset("exp_config", root, exp_config)
    return {"success": True}


@app.get("/")
async def get_query_page(request: Request):
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
    d = ujson.loads(ans.json())
    d.update({"time_received": time()})
    rj.jsonarrappend("responses", root, d)
    return {"success": True}


@app.get("/get_responses")
async def get_responses() -> Dict[str, Any]:
    exp_config = await _ensure_initialized()
    responses = rj.jsonget("responses")
    targets = exp_config["targets"]
    out: List[Dict[str, Any]] = []
    start = rj.jsonget("start_time")
    for datum in responses:
        out.append(datum)
        out[-1].update(
            {
                key + "_object": targets[datum[key]]
                for key in ["left", "right", "head", "winner"]
            }
        )
        out[-1].update({"time_received_since_start": datum["time_received"] - start})

    return JSONResponse(
        out, headers={"Content-Disposition": 'attachment; filename="responses.json"'}
    )
