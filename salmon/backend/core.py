import random
import traceback
from typing import Dict, Union

import cloudpickle
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from rejson import Client, Path

from . import algs
from .utils import get_logger

logger = get_logger(__name__)

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)

app = FastAPI(title="salmon-backend")


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


@app.post("/init/{name}")
async def init(name: str, background_tasks: BackgroundTasks) -> bool:
    # TODO: Better handling of exceptions if params keys don't match
    logger.info("backend: initialized")
    config = rj.jsonget("exp_config")

    try:
        if f"state-{name}" in rj.keys():
            # See https://github.com/andymccurdy/redis-py/issues/1006
            rj2 = Client(host="redis", port=6379, decode_responses=False)
            state = rj2.get(f"state-{name}")
            alg = cloudpickle.loads(state)
        else:
            params = config["samplers"][name]
            _class = params.pop("class")
            Alg = getattr(algs, _class)
            alg = Alg(name=name, n=config["n"], **params)
    except Exception as e:
        msg = exception_to_string(e)
        logger.error(f"Error on alg={name} init: {msg}")
        raise ExpParsingError(status_code=500, detail=msg)

    if hasattr(alg, "get_query"):

        @app.get(f"/query-{name}")
        def _get_query():
            q, score = alg.get_query()
            return {"name": name, "score": score, **q}

    client = None
    logger.info(f"Starting algs={name}")
    background_tasks.add_task(alg.run, client, rj)
    return True


@app.get("/model")
async def get_model(name: str):
    return 1
