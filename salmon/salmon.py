from typing import Dict, List, Any
from functools import lru_cache
from time import time
import yaml
from copy import copy

from fastapi import FastAPI, File, UploadFile, HTTPException
from jinja2 import Template
from pathlib import Path
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import ujson

import numpy as np
import pandas as pd

from .utils import ServerException

app = FastAPI()
app.mount("/static", StaticFiles(directory="templates"), name="static")

responses: List[Dict[str, Any]] = []
start = time()
templates = Jinja2Templates(directory="templates")
exp_data: Dict = {
    "instructions": "Default instructions (can include <i>arbitrary</i> HTML)"
}


async def _ensure_initialized():
    if not exp_data:
        raise ServerException("No data has been uploaded")
    expected_keys = ["targets", "instructions", "n"]
    if not set(exp_data) == set(expected_keys):
        msg = "Experiment keys are not correct. Expected {}, got {}"
        raise ServerException(msg.format(expected_keys, list(exp_data.keys())))
    return exp_data


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
    global exp_data
    config = yaml.load(await exp.read(), Loader=yaml.SafeLoader)
    exp_data.update(config)
    exp_data["n"] = len(exp_data["targets"])
    return {"success": True}


@app.get("/")
async def get_query_page(request: Request):
    exp_data = await _ensure_initialized()
    items = {
        "puid": np.random.randint(2 ** 20, 2 ** 32 - 1),
        "instructions": exp_data["instructions"],
        "targets": exp_data["targets"],
    }
    items.update(request=request)
    return templates.TemplateResponse("query_page.html", items)


@app.get("/get_query")
async def get_query() -> Dict[str, int]:
    _ensure_initialized()
    n = exp_data["n"]
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
    d.update({"time_received": time() - start})
    responses.append(d)
    return {"success": True}


@app.get("/get_responses")
async def get_responses() -> Dict[str, Any]:
    exp_data = await _ensure_initialized()
    targets = exp_data["targets"]
    data = copy(responses)
    out: List[Dict[str, Any]] = []
    for datum in data:
        datum.update(
            {
                key + "_object": targets[datum[key]]
                for key in ["left", "right", "head", "winner"]
            }
        )
        out.append(datum)

    return JSONResponse(
        out, headers={"Content-Disposition": 'attachment; filename="responses.json"'}
    )
