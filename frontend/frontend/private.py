import sys
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
import pprint
from functools import lru_cache
import traceback
from textwrap import dedent
import asyncio
from time import sleep

import numpy as np

from rejson import Client, Path
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import requests as httpx

from fastapi import File, UploadFile, Depends, HTTPException, Form
from fastapi.logger import logger as fastapi_logger
from starlette.requests import Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import HTMLResponse, JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED
from fastapi.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .public import _ensure_initialized, app, templates
from .utils import ServerException, get_logger, _extract_zipfile, _format_target
from .plotting import time_histogram, _any_outliers, time_human_delay, network_latency
from . import manager

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
    warning = ""
    if rj.jsonget("exp_config"):
        warning = dedent(
            """<div style="color: #f00;">
            <p>Warning: an experiment is already set!
               Visit [url]:8421/reset to reset the expeirment</p>
            </div>
            """
        )
    body = dedent(
        f"""<body>
        <div style="text-align: center; padding: 10px;">
        <form action="/init_exp" enctype="multipart/form-data" method="post">
        <ul>
          <li>Experiment parameters (YAML file): <input name="exp" type="file"></li>
          <li>Images/movies (ZIP file, optional): <input name="targets_file" type="file"></li>
        </ul>
        <input type="submit">
        </form>
        {warning}
        </div>
        </body>
        """
    )
    return HTMLResponse(content=body)


async def _get_config(exp: bytes, targets_file: bytes) -> Dict[str, Any]:
    config = yaml.load(exp, Loader=yaml.SafeLoader)
    exp_config: Dict = {
        "instructions": "Default instructions (can include <i>arbitrary</i> HTML)",
        "max_queries": None,
        "debrief": "Thanks!",
        "samplers": {"random": {"class": "RandomSampling"}},
    }
    exp_config.update(config)
    exp_config["targets"] = [str(x) for x in exp_config["targets"]]

    if targets_file:
        fnames = _extract_zipfile(targets_file)
        targets = [_format_target(f) for f in fnames]
        exp_config["targets"] = targets

    exp_config["n"] = len(exp_config["targets"])
    logger.info("initializing experinment with %s", exp_config)
    return exp_config


def exception_to_string(excp):
    stack = traceback.extract_stack()[:-3] + traceback.extract_tb(
        excp.__traceback__
    )  # add limit=??
    pretty = traceback.format_list(stack)
    return "Error!\n\n\nSummary:\n\n{} {}\n\nFull traceback:\n\n".format(
        excp.__class__, excp
    ) + "".join(pretty)


class ExpParsingError(StarletteHTTPException):
    pass


@app.exception_handler(ExpParsingError)
async def http_exception_handler(request, exc):
    return PlainTextResponse(exc.detail, status_code=exc.status_code)


@app.post("/init_exp", tags=["private"])
async def process_form(
    request: Request,
    exp: bytes = File(default=""),
    targets_file: bytes = File(default=""),
    authorized: bool = Depends(_authorize),
):
    try:
        return await _process_form(request, exp, targets_file)
    except Exception as e:
        msg = exception_to_string(e)
        logger.error(msg)
        raise ExpParsingError(status_code=500, detail=msg)


async def _process_form(
    request: Request,
    exp: bytes = File(default=""),
    targets_file: bytes = File(default=""),
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
    logger.info("salmon.__version__ = %s", app.version)
    exp_config = await _get_config(exp, targets_file)

    rj.jsonset("exp_config", root, exp_config)

    # Start the backend
    names = list(exp_config["samplers"].keys())
    rj.jsonset("samplers", root, names)
    for name in names:
        rj.jsonset(f"alg-{name}-answers", root, [])
        # Not set because rj.zadd doesn't require it
        # don't touch! rj.jsonset(f"alg-{name}-queries", root, [])
        r = httpx.post(f"http://backend:8400/init/{name}")
        if r.status_code != 200:
            raise HTTPException(500, Exception(r))

    _time = time()
    rj.jsonset("start_time", root, _time)
    rj.jsonset("start_datetime", root, datetime.now().isoformat())
    rj.jsonset("all-responses", root, [])

    nice_config = pprint.pformat(exp_config)
    logger.info("Experiment initialized with\nexp_config=%s", nice_config)
    response = dedent(
        """<html><body>
        <br><br>
        <p>
        Now, Salmon presents the following interfaces:
        </p>
        <p><ul style="text-align: center;">
        <li><a href="/">Query page</a>. Send this page to crowdsourcing participants.</li>
        <li><a href="/dashboard">Dashboard</a>. Use this page to monitor experimental progress.</li>
        </ul></p>
        </body></html>
        """
    )
    return HTMLResponse(content=response)


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

        # Stop background jobs (ie adaptive algs)
        rj.jsonset("reset", root, True)
        if "samplers" in rj.keys():
            samplers = rj.jsonget("samplers")
            stopped = {name: False for name in samplers}
            while True:
                for name in stopped:
                    if f"stopped-{name}" in rj.keys():
                        stopped[name] = rj.jsonget(f"stopped-{name}")
                if all(stopped.values()):
                    logger.info(f"stopped={stopped}")
                    break
                sleep(1)

        r = httpx.post(f"http://backend:8400/reset")
        if r.status_code != 200:
            raise HTTPException(500, Exception(r))

        rj.flushdb()
        logger.info("After reset, rj.keys=%s", rj.keys())
        rj.jsonset("responses", root, {})
        rj.jsonset("start_time", root, -1)
        rj.jsonset("start_datetime", root, "-1")
        rj.jsonset("exp_config", root, {})
        return {"success": True}

    return {"success": False}


@app.get("/responses", tags=["private"])
async def get_responses(authorized: bool = Depends(_authorize)) -> Dict[str, Any]:
    exp_config = await _ensure_initialized()
    targets = exp_config["targets"]
    start = rj.jsonget("start_time")
    responses = await _get_responses()
    out = await _format_responses(responses, targets, start)
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
      (and `_object`/`_src` as their HTML string/HTML `src` tag)
    * `puid` as the participant unique ID
    * `time_received_since_start`, an integer describing the time in
      seconds since launch start
    * `time_received`: the time in seconds since Jan. 1st, 1970.

    This file will be downloaded.

    """
    responses = rj.jsonget("all-responses")
    return responses

async def _format_responses(responses, targets, start):
    logger.info("getting %s responses", len(responses))
    out = manager.get_responses(responses, targets, start_time=start)
    return out


@app.get("/dashboard", tags=["private"])
@app.post("/dashboard", tags=["private"])
async def get_dashboard(request: Request, authorized: bool = Depends(_authorize)):
    logger.info("Getting dashboard")
    exp_config = await _ensure_initialized()
    exp_config = deepcopy(exp_config)
    targets = exp_config.pop("targets")
    start = rj.jsonget("start_time")

    r = await _get_responses()
    df = pd.DataFrame(r)
    r["time_received_since_start"] -= start

    if len(responses) >= 2:
        try:
            r = await time_histogram(df.time_received_since_start)
        except:
            name, descr, tr = sys.exc_info()
            hist_time_responses = f"Time responses received:\n{name} exception: {descr}"
        else:
            fig, ax = r
            ax.set_title("Time responses received")
            with StringIO() as f:
                fig.savefig(f, format="svg", bbox_inches="tight")
                hist_time_responses = f.getvalue()
        try:
            r = await time_human_delay(df.response_time.to_numpy())
        except:
            name, descr, tr = sys.exc_info()
            hist_human_delay = (
                f"Histogram of human response time:\n{name} exception: {descr}"
            )
        else:
            fig, ax = r
            with StringIO() as f:
                fig.savefig(f, format="svg", bbox_inches="tight")
                hist_human_delay = f.getvalue()
        try:
            r = await network_latency(df.network_latency.to_numpy())
        except Exception as e:
            name, descr, traceback = sys.exc_info()
            hist_network_latency = f"Network latency:\n{name} exception: {descr}"
        else:
            fig, ax = r
            with StringIO() as f:
                fig.savefig(f, format="svg", bbox_inches="tight")
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
            "filenames": [_get_filename(html) for html in targets],
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


@app.get("/meta", tags=["private"])
async def get_meta(request: Request, authorized: bool = Depends(_authorize)):
    responses = await _get_responses()
    df = pd.DataFrame(responses)
    out = {
        "responses": len(df),
        "participants": df.puid.nunique(),
    }
    return JSONResponse(out)


def _get_filename(html):
    html = str(html)
    if "<img" in html or "<video" in html:
        i = html.find("src=")
        j = html[i:].find(" ")
        return html[i + 5 : i + j - 1].replace("/static/targets/", "")
    return html
