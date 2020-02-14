from typing import Dict, Any, List
import os
import yaml
from time import time
import hashlib, uuid
from copy import copy, deepcopy
import pathlib
from datetime import datetime, timedelta
import json
from io import StringIO
from pprint import pprint

import numpy as np
from rejson import Client, Path
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt

from fastapi import File, UploadFile, Depends, HTTPException, Form
from fastapi.logger import logger as fastapi_logger
from starlette.requests import Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from .public import _ensure_initialized, app, templates
from .utils import ServerException, get_logger, _extract_zipfile, _format_target
from .plotting import time_histogram, _any_outliers

security = HTTPBasic()

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)
logger = get_logger(__name__)

EXPECTED_PWORD = "331a5156c7f0a529ed1de8d9aba35da95655c341df0ca0bbb2b69b3be319ecf0"


def _salt(password: str) -> str:
    pword = bytes(password, "utf8")
    salt = b"\x87\xa4\xb0\xc6k\xb7\xcf!\x8a\xc8z\xc6Q\x8b_\x00i\xc4\xbd\x01\x15\xabjn\xda\x07ZN}\xfd\xe1\x0e"
    m = hashlib.sha256()
    m.update(pword + salt)
    return m.digest().hex()


def _authorize(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    logger.info("Seeing if authorized access")
    if os.environ.get("SALMON_NO_AUTH", False):
        return True
    if credentials.username != "foo" or _salt(credentials.password) != EXPECTED_PWORD:
        logger.info("Not authorized")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


@app.get("/init_exp", tags=["private"])
def upload_form():
    """
    Upload a YAML file that specifies an experiment. See
    <a href='#operations-private-process_form_init_exp_post'>
    the POST description</a> for more detail on the file.

    """
    body = """
    <body>
    <form action="/init_exp" enctype="multipart/form-data" method="post">
    <ul>
      <li>Experiment parameters (YAML file): <input name="exp" type="file"></li>
      <li>Images/movies (ZIP file, optional): <input name="targets_file" type="file"></li>
    </ul>
    <input type="submit">
    </form>
    </body>
    """
    return HTMLResponse(content=body)


@app.post("/init_exp", tags=["private"])
async def process_form(
    request: Request,
    exp: bytes = File(default=""),
    targets_file: bytes = File(default=""),
    authorized: bool = Depends(_authorize),
):
    """
    The uploaded file needs to have the following keys:

    * targets (List)
    * instructions (Optional[str])
    * max_queries (Optional[int])

    Targets/instructions can render most HTML tags.

    Example
    -------

        - targets:
          - object 1
          - object 2
          - <b>bold</i> object 3
          - <i>object</i> 4
          - <img src="https://en.wikipedia.org/wiki/File:2010_Winter_Olympics_Bode_Miller_in_downhill.jpg" />
        - instructions: "Foobar!"
        - max_queries: 25
    """

    config = yaml.load(exp, Loader=yaml.SafeLoader)
    exp_config: Dict = {
        "instructions": "Default instructions (can include <i>arbitrary</i> HTML)",
        "max_queries": None,
    }
    exp_config.update(config)
    exp_config["n"] = len(exp_config["targets"])
    if targets_file:
        fnames = _extract_zipfile(targets_file)
        targets = [_format_target(f) for f in fnames]
        exp_config["targets"] = targets
    else:
        targets = exp_config.pop("targets")
    rj.jsonset("exp_config", root, exp_config)
    rj.jsonset("responses", root, [])
    _time = time()
    rj.jsonset("start_time", root, _time)
    rj.jsonset("start_datetime", root, datetime.now().isoformat())
    logger.warning("Experiment initialized with exp_config=%s", exp_config)
    logger.warning("exp_config['targets'] = %s", targets)
    return RedirectResponse(url="/dashboard")


@app.delete("/reset", tags=["private"])
@app.get("/reset", tags=["private"])
def reset(force: int = 0, authorized=Depends(_authorize), tags=["private"]):
    """
    Delete all data from the database. This requires authentication.

    """
    logger.warning("Resetting, force=%s, authorized=%s", force, authorized)
    if not force:
        logger.warning("Resetting, force=False. Erroring")
        msg = (
            "Do you really want to delete *all* data? This will delete all "
            "responses and all target information and *cannot be undone.*\n\n"
            "If you do really want to reset, go to '[url]/reset?force=1' "
            "instead of '[url]/reset'"
        )
        raise ServerException(msg)

    if authorized:
        logger.error(
            "Resetting, force=True and authorized. Removing data from database"
        )
        rj.flushdb()
        rj.jsonset("responses", root, [])
        rj.jsonset("start_time", root, time())
        return {"success": True}

    return {"success": False}


@app.get("/get_responses", tags=["private"])
async def get_responses(authorized: bool = Depends(_authorize)) -> Dict[str, Any]:
    out = await _get_responses()
    return JSONResponse(
        out, headers={"Content-Disposition": 'attachment; filename="responses.json"'}
    )


async def _get_responses():
    """
    Get the recorded responses. This JSON file is readable by Pandas:
    <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_json.html>

    Returns
    -------
    `json_file : str`. This file will have keys

    * `head`, `left`, `right`, `winner` as integers describing the arms
      (and `_object` as their HTML string)
    * `puid` as the participant unique ID
    * `time_received_since_start`, an integer describing the time in
      seconds since launch start
    * `time_received`: the time in seconds since Jan. 1st 1970.

    This file will be downloaded.

    """
    exp_config = await _ensure_initialized()
    responses = rj.jsonget("responses")
    logger.info("getting %s responses", len(responses))
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
        datetime_received = timedelta(seconds=datum["time_received"]) + datetime(
            1970, 1, 1
        )
        datum = {
            "time_received_since_start": datum["time_received"] - start,
            "datetime_received": datetime_received.isoformat(),
        }
        out[-1].update(datum)
    return out


@app.get("/dashboard", tags=["private"])
@app.post("/dashboard", tags=["private"])
async def get_dashboard(request: Request, authorized: bool = Depends(_authorize)):
    logger.info("Getting dashboard")
    exp_config = await _ensure_initialized()
    exp_config = deepcopy(exp_config)
    targets = exp_config.pop("targets")
    responses = await _get_responses()
    df = pd.DataFrame(
        responses,
        columns=[
            "puid",
            "response_time",
            "time_received_since_start",
            "network_latency",
        ],
    )

    if len(responses) >= 2:
        r = await time_histogram(df.time_received_since_start)
        fig, ax = r
        ax.set_title("Time responses received")
        with StringIO() as f:
            plt.savefig(f, format="svg", bbox_inches="tight")
            hist_time_responses = f.getvalue()

        w = 3
        fig, ax = plt.subplots(figsize=(w, w))
        ax.hist(df.response_time, bins="auto")
        ax.set_xlabel("Response time (s)")
        ax.set_ylabel("Count")
        ax.grid(alpha=0.5)
        ax.set_title("Human delay in answering")
        ax.set_xlim(0, None)
        if _any_outliers(df.response_time, low=False):
            upper = np.percentile(df.response_time.values, 95)
            ax.set_xlim(None, max(10, upper))
        with StringIO() as f:
            plt.savefig(f, format="svg", bbox_inches="tight")
            hist_human_delay = f.getvalue()

        fig, ax = plt.subplots(figsize=(w, w))
        ax.hist(df.network_latency.values, bins="auto")
        ax.set_xlabel("Network latency (s)")
        ax.set_ylabel("Count")
        ax.grid(alpha=0.5)
        ax.set_title("Network latency between questions")
        ax.set_xlim(0, None)
        with StringIO() as f:
            plt.savefig(f, format="svg", bbox_inches="tight")
            hist_network_latency = f.getvalue()
    else:
        msg = (
            "Histogram of {} will appear here after at least 2 responses are collected"
        )

        hist_time_responses = msg.format("when responses are received")
        hist_network_latency = msg.format("network latency")
        hist_human_delay = msg.format("human response time")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "targets": targets,
            "exp_config": exp_config,
            "num_responses": len(responses),
            "num_participants": df.puid.nunique(),
            "hist_time_responses": hist_time_responses,
            "hist_human_delay": hist_human_delay,
            "hist_network_latency": hist_network_latency,
        },
    )


@app.get("/logs", tags=["private"])
async def get_logs(request: Request, authorized: bool = Depends(_authorize)):
    logger.info("Getting logs")

    items = {"request": request}
    log_dir = pathlib.Path(__file__).absolute().parent / "logs"
    files = log_dir.glob("*.log")
    out = {}
    for file in files:
        with open(str(file), "r") as f:
            out[file.name] = f.readlines()
    return JSONResponse(out)
