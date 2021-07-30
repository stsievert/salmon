import asyncio
import hashlib
import itertools
import json
import os
import pathlib
import pprint
import shutil
import sys
import traceback
from copy import deepcopy
from datetime import datetime, timedelta
from io import StringIO
from textwrap import dedent
from time import sleep, time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests as httpx
import yaml
from bokeh.embed import json_item
from fastapi import Depends, File, Form, HTTPException
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from redis import ResponseError
from rejson import Client, Path
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT

import salmon

from ..triplets import manager
from . import plotting
from .public import _ensure_initialized, app, templates
from .utils import (
    ServerException,
    _extract_zipfile,
    _format_target,
    _format_targets,
    get_logger,
)

security = HTTPBasic()

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)
logger = get_logger(__name__)
DIR = pathlib.Path(__file__).absolute().parent
ROOT_DIR = DIR.parent.parent

CREDS_FILE = ROOT_DIR / "creds.json"
EXPECTED_PWORD = "331a5156c7f0a529ed1de8d9aba35da95655c341df0ca0bbb2b69b3be319ecf0"


def _salt(password: str) -> str:
    pword = bytes(password, "utf8")
    salt = b"\x87\xa4\xb0\xc6k\xb7\xcf!\x8a\xc8z\xc6Q\x8b_\x00i\xc4\xbd\x01\x15\xabjn\xda\x07ZN}\xfd\xe1\x0e"
    m = hashlib.sha256()
    m.update(pword + salt)
    return m.digest().hex()


def _write_user_pass(user: str, password: str) -> bool:
    if not CREDS_FILE.exists():
        passwords = {}
    else:
        with open(CREDS_FILE, "r") as f:
            passwords = json.load(f)

    logger.warning(f"passwords={passwords}")
    if user in passwords:
        raise HTTPException(
            status_code=403, detail=f"user={user} already in password file.",
        )
    new_user = user not in passwords
    if new_user and len(passwords) > 0:
        raise HTTPException(
            status_code=403,
            detail="A maximum number of users have already been registered",
        )

    passwords[user] = _salt(password)
    with open(CREDS_FILE, "w") as f:
        json.dump(passwords, f)

    return True


@app.post("/create_user/{username}/{password}", tags=["private"])
def _create_user_v0(username: str, password: str):
    _write_user_pass(username, password)


@app.post("/create_user", tags=["private"])
def create_user(
    username: str = Form(...), password: str = Form(...), password2: str = Form(...)
) -> bool:
    logger.warning(f"In create_user with username={username}, password={password}")
    if password != password2:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail=f"password={password} does not match the confirmation password={password2}",
            headers={"WWW-Authenticate": "Basic"},
        )
    _write_user_pass(username, password)
    msg = dedent(
        f"""
        <p>
          Success! User=<code>{username}</code> successfully created with
          password=<code>{password}</code>.
        </p>
        <p>
          <b>Do NOT lose this information.</b> Salmon will be <b>unusable</b>
          without this, and this is the last time this information will be
          displayed. Tasks that require this information include downloading
          the responses collected by Salmon and viewing the dashboard.
        </p>
        <p>
          <b>Salmon will only accept this username/password.</b>
        </p>
        <p>
          <b>Next,</b> visit <a href='/init'>/init</a> to initialize a new
          experiment with this username={username} and password={password}.
        </p>
        """
    )
    return HTMLResponse(msg)


def _authorize(creds: HTTPBasicCredentials = Depends(security)) -> bool:
    if CREDS_FILE.exists():
        with open(CREDS_FILE, "r") as f:
            passwords = json.load(f)
    else:
        passwords = {}

    name = creds.username
    if (name in passwords and _salt(creds.password) == passwords[name]) or (
        name == "foo" and _salt(creds.password) == EXPECTED_PWORD
    ):
        logger.info("Authorized: true")
        return True

    logger.info("Not authorized!")
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )


@app.get("/init", tags=["private"])
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

    password = dedent(
        """
        <h2 style="text-align: center;">Step 1: create new username/password.</h2>
        <div style="text-align: center; padding: 10px;">
        <p>This username/password distinguishes you from any other internet
        user.</p>
        <form action="/create_user" enctype="multipart/form-data" method="post">
        <ul>
          <li>Username: <input name="username" placeholder="username"
                         type="text" /></li>
          <li>Password: <input name="password" placeholder="password"
                         type="text" /></li>
          <li>Confirm password: <input name="password2" placeholder="password"
                                 type="text" /></li>
        </ul>
        <input type="submit" value="Create user">
        </form>
        <p>
          <b>Do not lose this username/password!</b>
          After you've created a username/password <i>and written it down
          </i>, then you can create a new experiment. It'll ask for the
          username/password you just created.</p>
        </div>
        """
    )
    if CREDS_FILE.exists():
        with open(CREDS_FILE, "r") as f:
            passwords = json.load(f)
        logger.warning(f"passwords={passwords}")
        if len(passwords):
            user = list(passwords.keys())[0]
            letters = list(user)
            for k, letter in enumerate(letters):
                if k in [0, len(letters) - 1]:
                    continue
                letters[k] = "*"
            user = "".join(letters)
            password = (
                "<div style='text-align: center; padding: 10px;'>"
                f"<p>A user with name <code>{user}</code> has been created "
                "(only first and last letters shown). "
                "Do you know the password?</p>"
                "</div>"
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
        <div style="text-align: center; padding: 10px;">
        <p>Two steps are required:<p>
        <ol>
        <li>Creating a username/password.</li>
        <li>Creating a new experiment.</li>
        </ol>
        </div>
        {password}
        <h2 style="text-align: center;">Step 2: create new experiment.</h2>
        <h3 style="text-align: center;">Option 1: initialize new experiment.</h3>
        <div style="text-align: center; padding: 10px;">
        <form action="/init_exp" enctype="multipart/form-data" method="post">
        <ul>
          <li>Experiment parameters (YAML file): <input name="exp" type="file"></li>
          <li>Images/movies (ZIP file, optional): <input name="targets" type="file"></li>
        </ul>
        <input type="submit" value="Create experiment">
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
        <input type="submit" value="Create experiment">
        </form>
        </div>
        </div>
        </body>
        """
    )
    return HTMLResponse(content=body)


@app.get("/config", tags=["private"])
async def _get_config_endpoint(json: bool = True):
    exp_config = await _ensure_initialized()
    print("json=", json, bool(json), not json)
    if not json:
        return PlainTextResponse(yaml.dump(exp_config))
    return JSONResponse(exp_config)


async def _get_config(exp: bytes, targets: bytes) -> Dict[str, Any]:
    config = yaml.safe_load(exp)
    logger.warning(f"exp = {exp}")
    logger.warning(f"config = {config}")
    exp_config: Dict = {
        "instructions": "Default instructions (can include <i>arbitrary</i> HTML)",
        "max_queries": None,
        "debrief": "Thanks!",
        "samplers": {"random": {"class": "Random"}},
        "max_queries": -1,
        "d": 2,
        "skip_button": False,
        "css": "",
    }
    exp_config.update(config)
    if "sampling" not in exp_config:
        exp_config["sampling"] = {}

    if "probs" not in exp_config["sampling"]:
        n = len(exp_config["samplers"])
        freqs = [100 // n] * n
        freqs[0] += 100 % n
        sampling_percent = {k: f for k, f in zip(exp_config["samplers"], freqs)}
        exp_config["sampling"]["probs"] = sampling_percent

    if "samplers_per_user" not in exp_config["sampling"]:
        exp_config["sampling"]["samplers_per_user"] = 0

    if exp_config["sampling"]["samplers_per_user"] not in {0, 1}:
        s = exp_config["sampling"]["samplers_per_user"]
        raise NotImplementedError(
            "Only samplers_per_user in {0, 1} is implemented, not "
            f"samplers_per_user={s}"
        )
    if "RandomSampling" in exp_config["samplers"]:
        raise ValueError("The sampler `RandomSampling` has been renamed to `Random`.")

    if set(exp_config["sampling"]["probs"]) != set(exp_config["samplers"]):
        sf = set(exp_config["sampling"]["probs"])
        s = set(exp_config["samplers"])
        msg = (
            "sampling.probs keys={} are not the same as samplers keys={}.\n\n"
            "Keys in sampling.probs but not in samplers: {}\n"
            "Keys in samplers but but in sampling.probs: {}\n\n"
        )
        raise ValueError(msg.format(sf, s, sf - s, s - sf))
    if sum(exp_config["sampling"]["probs"].values()) != 100:
        msg = (
            "The values in sampling.probs should add up to 100; however, "
            "the passed sampling.probs={} adds up to {}"
        )
        s = exp_config["sampling"]["probs"]
        raise ValueError(msg.format(s, sum(s.values())))

    if targets:
        fnames = _extract_zipfile(targets)
        logger.info("fnames = %s", fnames)
        if len(fnames) == 1 and ".csv" in fnames[0].suffixes:
            exp_config["targets"] = _format_targets(fnames[0])
        else:
            targets = [_format_target(f) for f in fnames]
            exp_config["targets"] = targets
    elif isinstance(config["targets"], int):
        exp_config["targets"] = [str(x) for x in range(config["targets"])]
    else:
        exp_config["targets"] = [str(x) for x in exp_config["targets"]]

    exp_config["n"] = len(exp_config["targets"])
    logger.info("initializing experinment with %s", exp_config)
    return exp_config


def exception_to_string(excp):
    stack = traceback.extract_stack() + traceback.extract_tb(excp.__traceback__)
    pretty = traceback.format_list(stack)
    return "Error:\n\n{}\n\nMessage:\n\n{}\n\n\nSummary:\n\n{} {}\n\nTraceback:\n\n".format(
        str(excp), getattr(excp, "detail", ""), excp.__class__, excp
    ) + "".join(
        pretty
    )


class ExpParsingError(StarletteHTTPException):
    pass


@app.exception_handler(ExpParsingError)
async def http_exception_handler(request, exc):
    return PlainTextResponse(exc.detail, status_code=exc.status_code)


@app.post("/init_exp", tags=["private"])
async def process_form(
    request: Request,
    exp: bytes = File(default=""),
    targets: bytes = File(default=""),
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
        if rj.jsonget("exp_config"):
            detail = (
                "Incorrect username or password",
                "An experiment is already set! This experiment has not been "
                "deleted, and a new experiment has not been initialized."
                "\n\nIt is possible to clear this message; however, "
                "care needs to be taken to ensure you want to initialize a new"
                "experiment. To clear this error, follow these steps"
                "\n\n1. Verify which experiment is running. Uploading a new"
                "experiment will overwrite this experiment. Do you mean to upload?"
                "\n2. Visit /reset. Warning: this will *delete* the experiment"
                "\n3. Revisit /init and re-upload the experiment."
                "\n\n(visiting /foo means visiting '[url]:8421/foo'",
            )
            experiment_set = True
            raise HTTPException(status_code=403, detail=detail)
        experiment_set = False
        ret = await _process_form(request, exp, targets, rdb)

        if rdb:
            return ret

        await _ensure_initialized()
        return ret
    except Exception as e:
        logger.error(e)
        if authorized and not experiment_set:
            _reset(timeout=5)
        if isinstance(e, (ExpParsingError, HTTPException)):
            raise e
        msg = exception_to_string(e)
        logger.error(msg)
        raise ExpParsingError(status_code=500, detail=msg)


async def _process_form(
    request: Request,
    exp: bytes = File(default=""),
    targets: bytes = File(default=""),
    rdb: bytes = File(default=""),
):
    if rdb:
        return await restore(rdb=rdb)
    logger.info("salmon.__version__ = %s", app.version)
    exp_config = await _get_config(exp, targets)

    rj.jsonset("exp_config", root, exp_config)

    # Start the backend
    names = list(exp_config["samplers"].keys())
    _probs = exp_config["sampling"]["probs"]
    probs = [_probs[n] / 100 for n in names]
    rj.jsonset("samplers", root, names)
    rj.jsonset("sampling_probs", root, probs)
    for name in names:
        rj.jsonset(f"alg-{name}-answers", root, [])

        # Don't touch! Not set because rj.zadd doesn't require it.
        # rj.jsonset(f"alg-{name}-queries", root, [])

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
def reset_delete(
    force: int = 0,
    authorized=Depends(_authorize),
    tags=["private"],
    timeout: float = 10,
):
    if authorized:
        reset(force=force, authorized=authorized, timeout=timeout)
        return {"success": True}
    return {"success": False}


@app.get("/reset", tags=["private"])
def reset(
    force: int = 0,
    authorized=Depends(_authorize),
    tags=["private"],
    timeout: float = 10,
):
    """
    Delete all data from the database and a restart of the machine if *any*
    queries were answered.

    Restart the machine via `docker-compose stop; docker-compose up` or
    "Actions > Instance state > Reboot" on Amazon EC2.
    """
    if not authorized:
        return {"success": False}

    logger.warning("Resetting, force=%s, authorized=%s", force, authorized)
    if not force:
        logger.warning("Resetting, force=False. Erroring")
        msg = (
            "Do you really want to delete *all* data? This will delete all "
            "responses and all target information and *cannot be undone.*\n\n"
            "If you do really want to reset, go to '[url]/reset?force=1' "
            "instead of '[url]/reset'"
        )
        raise ServerException(msg, status_code=403)

    logger.error("Authorized reset, force=True. Removing data from database")
    meta = _reset(timeout=timeout)
    assert meta["success"]
    return HTMLResponse(
        "The Salmon databasse has (largely) been cleared. "
        "To completely clear the database, the server needs to be restarted "
        "(likely via 'Actions > Instance state > Reboot' on Amazon EC2 "
        "or `docker-compose stop; docker-compose up`."
    )


def _reset(timeout: float = 5):
    try:
        rj.save()
    except ResponseError as e:
        if "save already in progress" not in str(e):
            raise e

    # Stop background jobs (ie adaptive algs)
    rj.jsonset("reset", root, True)
    rj2 = Client(host="redis", port=6379, decode_responses=False)
    if "samplers" in rj.keys():
        samplers = rj.jsonget("samplers")
        stopped = {name: False for name in samplers}
        __deadline = time() + timeout
        for k in itertools.count():
            rj.jsonset("reset", root, True)
            for name in stopped:
                if f"stopped-{name}" in rj.keys():
                    stopped[name] = rj.jsonget(f"stopped-{name}", root)
            if all(stopped.values()):
                logger.warning(f"stopped={stopped}")
                break
            sleep(1)
            logger.warning(
                f"Waited {k + 1} seconds algorithms... stopped? {stopped}"
                f" (rj.keys() == {rj.keys()}"
            )
            if timeout and time() >= __deadline:
                logger.warning(f"Hit timeout={timeout} w/ stopped={stopped}. Breaking!")
                break

        logger.warning("    starting with clearing queries...")
        for ident in samplers:
            rj2.delete(f"alg-{ident}-queries")

    logger.warning("Trying to completely flush database...")

    rj.flushall(asynchronous=True)
    rj2.flushall(asynchronous=True)
    rj.flushdb(asynchronous=True)
    rj2.flushdb(asynchronous=True)
    for _rj in [rj, rj2]:
        _rj.memory_purge()
        sleep(1)
        for k in _rj.keys():
            _rj.delete(k)
        _rj.flushall(asynchronous=True)
        _rj.flushdb(asynchronous=True)
        sleep(1)
        _rj.flushdb(asynchronous=False)
        sleep(1)
        _rj.flushall(asynchronous=False)

    now = datetime.now().isoformat()[: 10 + 6]

    save_dir = ROOT_DIR / "out"
    files = [f.name for f in save_dir.glob("*")]
    logger.warning(f"dump_rdb in files? {'dump.rdb' in files}")
    if "dump.rdb" in files:
        logger.error(f"Moving dump.rdb to dump-{now}.rdb")
        shutil.move(str(save_dir / "dump.rdb"), str(save_dir / f"dump-{now}.rdb"))
        files = [f.name for f in save_dir.glob("*")]
        logger.warning(f"after moving, dump_rdb in files? {'dump.rdb' in files}")
    files = [f.name for f in save_dir.glob("*")]
    assert "dump.rdb" not in files

    logger.warning("After reset, rj.keys=%s", rj.keys())
    rj.jsonset("responses", root, {})
    rj.jsonset("start_time", root, -1)
    rj.jsonset("start_datetime", root, "-1")
    rj.jsonset("exp_config", root, {})
    return {"success": True}


@app.get("/responses", tags=["private"])
async def get_responses(
    authorized: bool = Depends(_authorize), json: Optional[bool] = True
) -> Dict[str, Any]:
    """
    Get the recorded responses from the current experiments. This includes
    the following columns:

    * `left`, `right`, `head`: Indices describing the objects in the
      head/left/right positions.
    * `head_html`, `right_html`, `left_html`: the HTML
      representation of the target in the head/left/right position.
    * `datetime_received`: the time the response was received.
    * `response_time`: the time spent between the providing the query and
      receiving the answer.

    There may be additional columns.

    Returns
    -------
    The list of responses as a CSV file. This file can be read by
    Panda's `read_csv` function.

    """
    exp_config = await _ensure_initialized()
    targets = exp_config["targets"]
    start = rj.jsonget("start_time")
    responses = await _get_responses()
    json_responses = await _format_responses(responses, targets, start)
    if json:
        return JSONResponse(
            json_responses,
            headers={"Content-Disposition": 'attachment; filename="responses.json"'},
        )
    with StringIO() as f:
        df = pd.DataFrame(json_responses)
        df.to_csv(f, index=False)
        out = f.getvalue()

    return PlainTextResponse(
        out, headers={"Content-Disposition": 'attachment; filename="responses.csv"'}
    )


def _fmt_embedding(
    embedding: List[List[float]], targets: List[str], **kwargs
) -> pd.DataFrame:
    df = pd.DataFrame({"target_html": targets})
    df["target_id"] = np.arange(len(df)).astype(int)
    for k, v in kwargs.items():
        df[k] = v

    embedding = np.asarray(embedding)
    if embedding.ndim == 1:
        embedding = embedding.reshape(1, -1)
    for k, col in enumerate(range(embedding.shape[1])):
        df[k] = embedding[:, col]

    return df


@app.get("/embeddings", tags=["private"])
async def get_embeddings(
    authorized: bool = Depends(_authorize), alg: Optional[str] = None,
):
    """
    Get the embeddings for algorithms.

    Parameters
    ----------

    * alg : str, optional. The algorithm to get the embedding for.

    Returns
    -------
    CSV with columns for the target HTML, target ID, the embedding, and the
    algorithm generating the embedding.
    """
    exp_config = await _ensure_initialized()
    exp_config = deepcopy(exp_config)
    targets = exp_config.pop("targets")
    alg_idents = list(exp_config.pop("samplers").keys())
    embeddings = {}
    for alg in alg_idents:
        try:
            embeddings[alg] = await get_model(alg)
        except:
            pass
    if len(embeddings) == 0:
        raise ServerException(
            f"No model has been created for any sampler in {alg_idents}"
        )
    dfs = {
        alg: _fmt_embedding(model["embedding"], targets, alg=alg)
        for alg, model in embeddings.items()
    }

    if alg is not None:
        df = dfs[alg]
    else:
        df = pd.concat(dfs)

    with StringIO() as f:
        df.to_csv(f, index=False)
        out = f.getvalue()

    fname = "embeddings.csv" if alg is None else f"embedding-{alg}.csv"
    return PlainTextResponse(
        out, headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )


async def _get_responses():
    """
    Get the recorded responses. This JSON file is readable by Pandas:
    <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_json.html>

    Returns
    -------
    `json_file : str`. This file will have keys

    * `head`, `left`, `right`, `winner` as integers describing the arms
      (and `_html`/`_src` as their HTML string/HTML `src` tag)
    * `puid` as the participant unique ID
    * `time_received_since_start`, an integer describing the time in
      seconds since launch start
    * `time_received`: the time in seconds since Jan. 1st, 1970.

    This file will be downloaded.

    """
    responses = rj.jsonget("all-responses", root)
    return responses


async def _format_responses(responses, targets, start):
    logger.info("getting %s responses", len(responses or []))
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
        response_rate = await plotting.response_rate(df)
        plots = {
            "activity": activity,
            "response_times": response_times,
            "network_latency": network_latency,
            "response_rate": response_rate,
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
        x = df["time_received"]
        rr_cdf, gaps_hist, response_meta = await plotting._get_response_rate_plots(x)
        plots["response_rate_cdf"] = json.dumps(json_item(rr_cdf))
        plots["gaps_histogram"] = json.dumps(json_item(gaps_hist))
    except Exception as e:
        logger.exception(e)
        plots["response_rate_cdf"] = {"/": "exception"}
        plots["gaps_histogram"] = {"/": "exception"}
        response_meta = {}

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

    idents = rj.jsonget("samplers")
    models = {}
    for alg in idents:
        try:
            models[alg] = await get_model(alg)
        except Exception as e:
            models[alg] = None
    alg_plots = {
        alg: await plotting.show_embedding(model["embedding"], targets, alg=alg)
        for alg, model in models.items()
        if model
    }
    alg_plots = {k: json.dumps(json_item(v)) for k, v in alg_plots.items() if v}
    if not len(alg_plots):
        alg_plots = {"no embeddings": None}
    logger.info(f"idents = {idents}")

    perfs = {}
    for ident in idents:
        try:
            perfs[ident] = await _get_alg_perf(ident)
        except Exception as e:
            logger.exception(e)
            perfs[ident] = None

    _alg_perfs = {}
    for alg, data in perfs.items():
        if data:
            try:
                _alg_perfs[alg] = await plotting._get_alg_perf(pd.DataFrame(data))
            except Exception as e:
                logger.exception(e)
                _alg_perfs[ident] = "Error getting performace"
    alg_perfs = {
        k: json.dumps(json_item(v)) if not isinstance(v, str) else v
        for k, v in _alg_perfs.items()
    }
    if not len(alg_perfs):
        alg_perfs = {"no sampler timings": "none"}

    try:
        _query_db = {
            alg: await plotting._get_query_db(pd.DataFrame(data))
            for alg, data in perfs.items()
            if data
        }
        query_db = {k: json.dumps(json_item(v)) for k, v in _query_db.items() if v}
    except Exception as e:
        logger.exception(e)
        query_db = {"/": "Error getting query database stats"}
    if not len(query_db):
        query_db = {"no queries in database": "none"}

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "start": start_datetime.isoformat()[: 10 + 6],
            "request": request,
            "targets": targets,
            "exp_config": exp_config,
            "num_responses": len(responses or []),
            "num_participants": df.puid.nunique(),
            "filenames": [_get_filename(html) for html in targets],
            "endpoints": endpoints,
            "alg_models": models,
            "alg_model_plots": alg_plots,
            "alg_perfs": alg_perfs,
            "config": exp_config,
            "samplers": idents,
            "query_db_perfs": query_db,
            **plots,
            **response_meta,
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
    log_dir = ROOT_DIR / "out"
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
    version = salmon.__version__
    headers = {
        "Content-Disposition": f'attachment; filename="exp-{fname}-{version}.rdb"'
    }
    return FileResponse(str(ROOT_DIR / "out" / "dump.rdb"), headers=headers)


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
    with open(str(ROOT_DIR / "out" / "dump.rdb"), "wb") as f:
        f.write(rdb)
    msg = dedent(
        """
        <div style="display: table; margin: 0 auto; max-width: 600px;">
        <br><br>
        <p><i><b>Your experiment is not initialized yet! Restart is required to restore experiment.</i></b></p>
        <p>
        To do this on Amazon EC2, select the \"Actions > Instance State > Reboot\"
        </p>
        <p>For developers, a "restart" means <code>docker-compose stop; docker-compose start</code>.</p>
        <p>After you reboot, visit the dashboard at
        <code>[url]:8421/dashboard</code>.
        <b>Do not visit the dashboard now</b>.</p>
        </div>
        """
    )
    return HTMLResponse(msg)


@app.get("/model/{alg_ident}")
async def get_model(alg_ident: str) -> Dict[str, Any]:
    logger.info("In public get_model with rj.keys() == %s", rj.keys())
    r = httpx.get(f"http://localhost:8400/model/{alg_ident}")
    if r.status_code != 200:
        raise ServerException(r.json()["detail"])
    return r.json()


async def _get_alg_perf(ident: str) -> Dict[str, Any]:
    logger.info("In private _get_alg_perf with rj.keys() == %s", rj.keys())
    r = httpx.get(f"http://localhost:8400/meta/perf/{ident}")
    if r.status_code != 200:
        raise ServerException(r.json()["detail"])
    return r.json()


def _get_filename(html):
    html = str(html)
    if "<img" in html or "<video" in html:
        i = html.find("src=")
        j = html[i:].find(" ")
        return html[i + 5 : i + j - 1].replace("/static/targets/", "")
    return html
