import os
import json
import random
import traceback
import threading
from typing import Dict, Union

import cloudpickle
from dask.distributed import Client as DaskClient
from dask.distributed import fire_and_forget
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from rejson import Client, Path

from salmon.frontend.utils import ServerException
from ..triplets import algs
from ..utils import get_logger

DEBUG = os.environ.get("SALMON_DEBUG", 0)

logger = get_logger(__name__)

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)

app = FastAPI(title="salmon-backend")
threads = []


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


@app.post("/init/{ident}")
async def init(ident: str, background_tasks: BackgroundTasks) -> bool:
    """
    Start running an algorithm.

    Parameters
    ----------
    ident : str
        The identifier paired with this algorithm.

    Returns
    -------
    success : bool

    Notes
    -----
    This function has side effects: it launches background job with
    algorithm class. This class runs the ``run`` function, which posts
    queries to Redis and process answers posted to Redis.

    If the algorithm class has a ``get_query`` method, the class will
    respond to the API request ``/get_query``. The method ``run`` should
    be modified to handle this.

    params : Dict[str, Any]
        Pulled from the experiment config and Redis.
        Here's an example YAML configuration:

    .. code:: yaml

       targets:
         - 1
         - 2
         - 3
         - 4
       samplers:
         - RandomSampling
         - random2
           - class: RandomSampling
           - foo: bar

    """
    # TODO: Better handling of exceptions if params keys don't match
    logger.info("backend: initializing %s", ident)
    config = rj.jsonget("exp_config")

    try:
        if f"state-{ident}" in rj.keys():
            # See https://github.com/andymccurdy/redis-py/issues/1006
            rj2 = Client(host="redis", port=6379, decode_responses=False)
            state = rj2.get(f"state-{ident}")
            alg = cloudpickle.loads(state)
        else:
            params = config["samplers"][ident]
            _class = params.pop("module", ident)
            Alg = getattr(algs, _class)
            params = {k: _fmt_params(k, v) for k, v in params.items()}
            logger.warning("Alg for %s = %s", ident, Alg)
            logger.warning("params = %s", params)
            alg = Alg(ident=ident, n=config["n"], d=config["d"], **params)
    except Exception as e:
        msg = exception_to_string(e)
        logger.error(f"Error on alg={ident} init: {msg}")
        raise ExpParsingError(status_code=500, detail=msg)

    logger.info(f"alg={ident} initialized; now, does it have get_quer")
    if hasattr(alg, "get_query"):
        logger.info(f"Init'ing /query-{ident}")

        @app.get(f"/query-{ident}")
        def _get_query():
            try:
                q, score = alg.get_query()
                logger.debug("q, score = %s, %s", q, score)
            except Exception as e:
                logger.exception(e)
                raise HTTPException(status_code=500, detail=str(e))
            if q is None:
                raise HTTPException(status_code=404)
            return {"alg_ident": ident, "score": score, **q}

    dask_client = DaskClient("127.0.0.2:8786")
    logger.info("Before adding init task")
    background_tasks.add_task(alg.run, dask_client)
    logger.info("Returning")
    return True


def _fmt_params(k, v):
    if isinstance(v, (str, int, float, bool, list)):
        return v
    elif isinstance(v, dict):
        return {f"{k}__{ki}": _fmt_params(ki, vi) for ki, vi in v.items()}
    raise ValueError(f"Error formatting key={k} with value {v}")


@app.get("/model/{alg_ident}")
async def get_model(alg_ident: str):
    samplers = rj.jsonget("samplers")
    if alg_ident not in samplers:
        raise ServerException(
            f"Can't find model for alg_ident='{alg_ident}'. "
            f"Valid choices for alg_ident are {samplers}"
        )
    if f"model-{alg_ident}" not in rj.keys():
        logger.warning("rj.keys() = %s", rj.keys())
        raise ServerException(f"Model has not been created for alg_ident='{alg_ident}'")
    rj2 = Client(host="redis", port=6379, decode_responses=False)
    ir = rj2.get(f"model-{alg_ident}")
    model = cloudpickle.loads(ir)
    return model


@app.get("/meta/perf/{alg_ident}")
async def get_timings(alg_ident: str):
    samplers = rj.jsonget("samplers")
    if alg_ident not in samplers:
        raise ServerException(
            f"Can't find key for alg_ident='{alg_ident}'. "
            f"Valid choices for alg_ident are {samplers}"
        )
    keys = list(sorted(rj.keys()))
    if f"alg-perf-{alg_ident}" not in keys:
        logger.warning("rj.keys() = %s", keys)
        raise ServerException(
            f"Performance data has not been created for alg_ident='{alg_ident}'. Database has keys {keys}"
        )
    return rj.jsonget(f"alg-perf-{alg_ident}")
