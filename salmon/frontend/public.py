import random
import pathlib
from copy import copy
from datetime import datetime, timedelta
from textwrap import dedent
from time import time
from typing import Dict, Union

import numpy as np
import requests as httpx
from fastapi import FastAPI
from rejson import Client, Path
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette_prometheus import metrics, PrometheusMiddleware

import ujson

from ..triplets import manager
from .utils import ServerException, sha256
from ..utils import get_logger

logger = get_logger(__name__)

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)


def start_algs():
    """
    Start the algorithm backend. This function is necessary because the
    machine might be restarted (so the experiment isn't launched fresh).
    """
    if "samplers" not in rj.keys():
        return
    names = rj.jsonget("samplers")
    for name in names:
        logger.info(f"Restarting alg={name}...")
        r = httpx.post(f"http://localhost:8400/init/{name}")
        assert r.status_code == 200
    return True


def stop_algs():
    rj.jsonset("reset", root, True)
    return True


app = FastAPI(
    title="Salmon",
    description=dedent(
        """A prototype platform for crowdsourcing triplet queries.
        \n\n***Warning!*** This platform is experimental and unstable.
        """
    ),
    on_startup=[start_algs],
    on_shutdown=[stop_algs],
)
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics/", metrics)

pkg_dir = pathlib.Path(__file__).absolute().parent
app.mount("/static", StaticFiles(directory=str(pkg_dir / "static")), name="static")
templates = Jinja2Templates(directory="templates")


async def _get_config():
    return rj.jsonget("exp_config")


async def _ensure_initialized():
    if "exp_config" not in rj:
        raise ServerException("No data has been uploaded")
    exp_config = await _get_config()
    expected_keys = [
        "targets",
        "samplers",
        "instructions",
        "n",
        "max_queries",
        "debrief",
        "skip_button",
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
        "skip_button": exp_config["skip_button"],
    }
    items.update(request=request)
    return templates.TemplateResponse("query_page.html", items)


@app.get("/query", tags=["public"])
async def get_query() -> Dict[str, Union[int, str, float]]:
    idents = rj.jsonget("samplers")
    ident = random.choice(idents)

    r = httpx.get(f"http://localhost:8400/query-{ident}")
    logger.info(f"r={r}")
    if r.status_code == 200:
        return r.json()

    key = f"alg-{ident}-queries"
    logger.info(f"bzpopmax'ing {key}")
    queries = rj.bzpopmax(key)
    _, serialized_query, score = queries
    q = manager.deserialize_query(serialized_query)
    return {"alg_ident": ident, "score": score, **q}


@app.post("/answer", tags=["public"])
async def process_answer(ans: manager.Answer):
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
    ident = d["alg_ident"]
    logger.warning("answer received: %s", d)
    rj.jsonarrappend(f"alg-{ident}-answers", root, d)
    rj.jsonarrappend("all-responses", root, d)
    last_save = rj.lastsave()

    # Save every 15 minutes
    if (datetime.now() - last_save) >= timedelta(seconds=60 * 15):
        rj.bgsave()

    return {"success": True}
