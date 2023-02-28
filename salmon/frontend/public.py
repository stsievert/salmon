import pathlib
import random
from copy import copy
from datetime import datetime, timedelta
from textwrap import dedent
from time import time
from typing import Dict, Union

import numpy as np
import requests as httpx
import ujson
from fastapi import FastAPI
from redis.exceptions import ResponseError
from rejson import Client, Path
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette_exporter import PrometheusMiddleware, handle_metrics

from salmon.frontend.utils import ServerException, image_url, sha256
from salmon.triplets import manager
from salmon.utils import get_logger

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
app.add_route("/metrics", handle_metrics)

pkg_dir = pathlib.Path(__file__).absolute().parent
app.mount("/static", StaticFiles(directory=str(pkg_dir / "static")), name="static")
templates = Jinja2Templates(directory="templates")


async def _get_config():
    return rj.jsonget("exp_config")


async def _ensure_initialized():
    if "exp_config" not in rj:
        raise ServerException("No data has been uploaded")
    exp_config = await _get_config()
    expected_keys = ["targets", "samplers", "n", "sampling", "html"]
    html_keys = [
        "instructions",
        "max_queries",
        "debrief",
        "skip_button",
        "css",
        "arrow_keys",
    ]
    err = False
    if not set(exp_config) == set(expected_keys):
        err = True
        extra = set(exp_config) - set(expected_keys)
        missing = set(expected_keys) - set(exp_config)
    if "html" in exp_config and not set(html_keys).issubset(set(exp_config["html"])):
        err = True
        extra = set()  # exp_config["html"]) - set(expected_keys)
        missing = set(expected_keys) - set(exp_config["html"])
    if err:
        msg = (
            "Experiment keys are not correct. Expected {}, got {}.\n\n"
            "Extra keys: {}\n"
            "Missing keys: {}"
        )
        raise ServerException(
            msg.format(expected_keys, list(exp_config.keys()), extra, missing)
        )
    return exp_config


@app.get("/", tags=["public"])
async def get_query_page(request: Request, puid: str = ""):
    """
    Load the query page and present a "triplet query".
    """
    exp_config = await _ensure_initialized()
    if puid == "":
        uid = "salmon-{}".format(np.random.randint(2 ** 32 - 1))
        puid = sha256(uid)[:16]
    try:
        urls = [image_url(t) for t in exp_config["targets"]]
    except:
        urls = []
    items = {
        "puid": puid,
        "targets": exp_config["targets"],
        "samplers_per_user": exp_config["sampling"]["samplers_per_user"],
        "urls": urls,
        "details": exp_config["sampling"]["details"],
        "html": exp_config["html"],
    }
    items.update(request=request)
    return templates.TemplateResponse("query_page.html", items)


@app.get("/query", tags=["public"])
async def get_query(sampler="", puid="") -> Dict[str, Union[int, str, float]]:
    if sampler == "":
        samplers = rj.jsonget("samplers")
        probs = rj.jsonget("sampling_probs")

        idx = np.random.choice(len(samplers), p=probs)
        sampler = samplers[idx]

    host = f"http://localhost:8400"
    endpoint = f"/query/{sampler}"
    if puid:
        endpoint = endpoint + f"?puid={puid}"

    r = httpx.get(host + endpoint)
    if r.status_code == 200:
        logger.info(f"query r={r}")
        return r.json()

    key = f"alg-{sampler}-queries"
    logger.info(f"zpopmax'ing {key}")
    queries = rj.zpopmax(key)
    if len(queries):
        serialized_query, score = queries[0]
        q = manager.deserialize_query(serialized_query)
    else:
        config = await _get_config()
        q = manager.random_query(config["n"])
        score = -9999

    return {"sampler": sampler, "score": score, **q}


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
    _update = {
        "time_received": round(time(), 3),
        "loser": d["left"] if d["winner"] == d["right"] else d["right"],
    }
    d.update(_update)
    ident = d["sampler"]
    logger.warning(f"answer received: {d}")
    rj.jsonarrappend(f"alg-{ident}-answers", root, d)
    # on backend,  key = f"alg-{self.ident}-answers"
    rj.jsonarrappend("all-responses", root, d)
    last_save = rj.lastsave()

    # Save every 15 minutes
    if (datetime.now() - last_save) >= timedelta(seconds=60 * 15):
        try:
            rj.bgsave()
        except ResponseError as e:
            if "Background save already in progress" not in str(e):
                raise e

    return {"success": True}
