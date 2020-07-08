import asyncio
import hashlib
import os
import itertools
import json
import pathlib
import pprint
import sys
import shutil
import traceback
from copy import deepcopy
from datetime import datetime, timedelta
from io import StringIO
from textwrap import dedent
from time import sleep, time
from typing import Any, Dict, Optional

import pandas as pd
import requests as httpx
import yaml
from bokeh.embed import json_item
from fastapi import Depends, File, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from rejson import Client, Path
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from ..triplets import manager
from . import plotting
from .public import _ensure_initialized, app, templates
from .utils import ServerException, _extract_zipfile, _format_target, get_logger, _format_targets

security = HTTPBasic()

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)
logger = get_logger(__name__)
DIR = pathlib.Path(__file__).absolute().parent

EXPECTED_PWORD = "331a5156c7f0a529ed1de8d9aba35da95655c341df0ca0bbb2b69b3be319ecf0"


def _salt(password: str) -> str:
    pword = bytes(password, "utf8")
    salt = b"\x87\xa4\xb0\xc6k\xb7\xcf!\x8a\xc8z\xc6Q\x8b_\x00i\xc4\xbd\x01\x15\xabjn\xda\x07ZN}\xfd\xe1\x0e"
    m = hashlib.sha256()
    m.update(pword + salt)
    return m.digest().hex()


def _authorize(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    SALMON_NO_AUTH = os.environ.get("SALMON_NO_AUTH", False)
    logger.warning(f"Seeing if authorized access with SALMON_NO_AUTH={SALMON_NO_AUTH}")
    print("SALMON_NO_AUTH={SALMON_NO_AUTH}")
    if SALMON_NO_AUTH:
        return True

    logger.info("SALMON_NO_AUTH is False")
    if credentials.username != "foo" or _salt(credentials.password) != EXPECTED_PWORD:
        logger.info("Not authorized")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    logger.info("Authorized: true")
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
        <div style="display: table; margin: 0 auto; max-width: 600px;">
        <div>
        <ul>
          <li>
            <a href="https://stsievert.com/salmon/">
              General Salmon documentation
            </a>
          </li>
          <li>
            <a href="/docs#/private/process_form_init_exp_post">
              Detailed /init_exp endpoint documentation
            </a>
          </li>
        </div>
        <h3 style="text-align: center;">Option 1: initialize new experiment.</h3>
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
        <h3 style="text-align: center;">Option 2: restore from old experiment.</h3>
        <div style="text-align: center; padding: 10px;">
        <p>Instructions:
        <ol style="text-align: left;">
        <li>Upload database dump from Salmon. The name should look like
          <code>exp-2020-03-12.rdb</code> if downloaded on March 12th, 2020.</li>
        <li>Restart the server. On Amazon EC2, this means choosing the EC2 instance state "reboot".</li>
        </ol>
        </p>
        <form action="/init_exp" enctype="multipart/form-data" method="post">
        <ul>
          <li>Database file : <input name="rdb" type="file"></li>
        </ul>
        <input type="submit">
        </form>
        </div>
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
        logger.info("fnames = %s", fnames)
        if len(fnames) == 1 and ".csv" in fnames[0].suffixes:
            exp_config["targets"] = _format_targets(fnames[0])
        else:
            targets = [_format_target(f) for f in fnames]
            exp_config["targets"] = targets

    exp_config["n"] = len(exp_config["targets"])
    logger.info("initializing experinment with %s", exp_config)
    return exp_config


def exception_to_string(excp):
    stack = traceback.extract_stack() + traceback.extract_tb(
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
    rdb: bytes = File(default=""),
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
    try:
        return await _process_form(request, exp, targets_file, rdb)
    except Exception as e:
        reset(force=True, timeout=2)
        if isinstance(e, ExpParsingError):
            raise e
        msg = exception_to_string(e)
        logger.error(msg)
        raise ExpParsingError(status_code=500, detail=msg)


async def _process_form(
    request: Request,
    exp: bytes = File(default=""),
    targets_file: bytes = File(default=""),
    rdb: bytes = File(default=""),
):
    if rdb:
        return await restore(rdb=rdb)
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
        logger.info(f"initializing algorithm {name}...")
        r = httpx.post(f"http://localhost:8400/init/{name}")
        if r.status_code != 200:
            msg = "Algorithm errored on initialization.\n\n" + r.text
            logger.error("Error! r.text = %s", r.text)
            logger.error(msg)
            raise ExpParsingError(status_code=500, detail=msg)
        logger.info(f"done initializing {name}.")

    _time = time()
    rj.jsonset("start_time", root, _time)
    rj.jsonset("start_datetime", root, datetime.now().isoformat())
    rj.jsonset("all-responses", root, [])
    rj.bgsave()

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
def reset(
    force: int = 0, authorized=Depends(_authorize), tags=["private"], timeout: int = 2,
):
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
        rj.save()
        now = datetime.now().isoformat()[: 10 + 6]

        save_dir = DIR.parent / "out"
        files = [f.name for f in save_dir.glob("*")]
        logger.info(files)
        logger.info("dump.rdb" in files)
        if "dump.rdb" in files:
            logger.error(f"Moving dump.rdb to dump-{now}.rdb")
            shutil.move(str(save_dir / "dump.rdb"), str(save_dir / f"dump-{now}.rdb"))

        # Stop background jobs (ie adaptive algs)
        rj.jsonset("reset", root, True)
        if "samplers" in rj.keys():
            samplers = rj.jsonget("samplers")
            stopped = {name: False for name in samplers}
            for k in itertools.count():
                rj.jsonset("reset", root, True)
                for name in stopped:
                    if f"stopped-{name}" in rj.keys():
                        stopped[name] = rj.jsonget(f"stopped-{name}")
                if all(stopped.values()):
                    logger.info(f"stopped={stopped}")
                    break
                sleep(1)
                logger.info(f"Waited {k + 1} seconds for {name} to stop...")
                if timeout and k > timeout:
                    logger.info(f"Hit timeout={timeout} for {name}. Brekaing")
                    break

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
    """
    Get the recorded responses from the current experiments. This includes
    the following columns:

    * `left`, `right`, `head`: Indices describing the objects in the
      head/left/right positions.
    * `head_object`, `right_object`, `head_object`: the HTML
      representation of the target in the head/left/right position.
    * `datetime_received`: the time the response was received.
    * `response_time`: the time spent between the providing the query and
      receiving the answer.

    Returns
    -------
    The list of responses as a JSON file. This file can be read by
    Panda's `read_json` function.

    """
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
    responses = rj.jsonget("all-responses", root)
    return responses


async def _format_responses(responses, targets, start):
    logger.info("getting %s responses", len(responses))
    out = manager.get_responses(responses, targets, start_time=start)
    return out


@app.get("/dashboard", tags=["private"])
@app.post("/dashboard", tags=["private"])
async def get_dashboard(request: Request, authorized: bool = Depends(_authorize)):
    """
    The primary method to view information about the experiment.
    It displays the following information:

    * Basic meta information: how many responses have been received, when
      were they received, etc.
    * Links to other API endpoints. These endpoint allow experiment
      download, getting the resposnes, resetting the experiment, etc.
    * Relevant graphs. Some answered questions are "how long did
      participants take to respond?" and "how long did it take to serve a
      query page?"
    """
    logger.info("Getting dashboard")
    rj.bgsave()
    exp_config = await _ensure_initialized()
    exp_config = deepcopy(exp_config)
    targets = exp_config.pop("targets")
    start = rj.jsonget("start_time")
    start_datetime = timedelta(seconds=start) + datetime(1970, 1, 1)

    responses = await _get_responses()
    df = pd.DataFrame(
        responses, columns=["puid", "time_received", "response_time", "network_latency"]
    )
    df["start_time"] = start

    try:
        activity = await plotting.activity(df, start)
        response_times = await plotting.response_time(df)
        network_latency = await plotting.network_latency(df)
        plots = {
            "activity": activity,
            "response_times": response_times,
            "network_latency": network_latency,
        }
        plots = {k: json.dumps(json_item(v)) for k, v in plots.items()}
    except Exception as e:
        logger.exception(e)
        activity = response_times = network_latency = f"Exception! {e}"
        plots = {
            "activity": activity,
            "response_times": response_times,
            "network_latency": network_latency,
        }
    try:
        endpoint_timing = await plotting.get_endpoint_time_plots()
        plots["endpoint_timings"] = {
            k: json.dumps(json_item(v)) for k, v in endpoint_timing.items()
        }
    except Exception as e:
        logger.exception(e)
        endpoint_timing = {"/": "exception"}
        plots["endpoint_timings"] = endpoint_timing

    endpoints = list(reversed(sorted(endpoint_timing.keys())))
    if "/query" in endpoints:
        i = endpoints.index("/query")
        endpoints[0], endpoints[i] = endpoints[i], endpoints[0]
    if "/answer" in endpoints:
        i = endpoints.index("/answer")
        endpoints[1], endpoints[i] = endpoints[i], endpoints[1]
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "start": start_datetime.isoformat()[: 10 + 6],
            "request": request,
            "targets": targets,
            "exp_config": exp_config,
            "num_responses": len(responses),
            "num_participants": df.puid.nunique(),
            "filenames": [_get_filename(html) for html in targets],
            "endpoints": endpoints,
            **plots,
        },
    )


@app.get("/logs", tags=["private"])
async def get_logs(request: Request, authorized: bool = Depends(_authorize)):
    """
    Get detailed information about the server. This might include detailed
    tracebacks and exceptions.

    Returns
    -------
    JSON response with structure Dict[str, List[str]]

    The keys are the names of the different loggers, and each element in
    the list is one log record.
    """
    logger.info("Getting logs")

    items = {"request": request}
    log_dir = DIR.parent / "out"
    files = log_dir.glob("*.log")
    out = {}
    for file in files:
        with open(str(file), "r") as f:
            out[file.name] = f.readlines()
    return JSONResponse(out)


@app.get("/meta", tags=["private"])
async def get_meta(request: Request, authorized: bool = Depends(_authorize)):
    """
    Get meta information about the experiment.
    How many responses and participants are there?

    Returns
    -------
    JSON response describing meta information.
    """
    responses = await _get_responses()
    df = pd.DataFrame(responses, columns=["puid"])
    out = {
        "responses": len(df),
        "participants": df.puid.nunique(),
    }
    return JSONResponse(out)


@app.get("/download", tags=["private"])
async def download(request: Request, authorized: bool = Depends(_authorize)):
    """
    Download any experiment state. Functionally, this endpoint allows
    moving the experiment to a new machine.

    Returns
    -------
    experiment_state : file

    This file can be used to restore the contents of the Redis
    database on a new machine.
    """
    rj.save()
    fname = datetime.now().isoformat()[: 10 + 6]
    headers = {"Content-Disposition": f'attachment; filename="exp-{fname}.rdb"'}
    save_dir = DIR.parent / "out"
    return FileResponse(str(save_dir / "dump.rdb"), headers=headers)


@app.post("/restore", tags=["private"])
async def restore(
    rdb: bytes = File(default=""), authorized: bool = Depends(_authorize)
):
    """
    Restore an experiment. This endpoint takes an experiment file from
    `/download` and restores it on the current machine.

    An experiment can be restored with the following steps:

    1. Download the experiment state at ``/download``
    2. Save the file on your machine.
    3. On a new machine, upload the file at ``/restore`` (this endpoint)
    4. Restart the machine, either via `docker-compose down; docker-
       compose up` or "Actions > Instance state > Reboot" on Amazon EC2.

    """
    save_dir = DIR.parent / "out"
    with open(str(save_dir / "dump.rdb"), "wb") as f:
        f.write(rdb)
    msg = dedent(
        """
        <div style="display: table; margin: 0 auto; max-width: 600px;">
        <br><br>
        <p><i><b>Your experiment is not initialized yet! Restart is required to restore experiment.</i></b></p>
        <p>
        To do this on Amazon EC2, select the \"Actions > Instance State > Reboot\"
        </p>
        <p>After you reboot, visit the dashboard.</p>
        </div>
        """
    )
    return HTMLResponse(msg)


def _get_filename(html):
    html = str(html)
    if "<img" in html or "<video" in html:
        i = html.find("src=")
        j = html[i:].find(" ")
        return html[i + 5 : i + j - 1].replace("/static/targets/", "")
    return html
