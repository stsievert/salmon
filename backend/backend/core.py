import random
from typing import Dict, Union

from fastapi import BackgroundTasks, FastAPI, HTTPException
from rejson import Client, Path

from . import algs
from .utils import get_logger

logger = get_logger(__name__)

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)

app = FastAPI(title="salmon-backend")

@app.post("/init/{name}")
async def init(name: str, background_tasks: BackgroundTasks) -> bool:
    # TODO: Better handling of exceptions if params keys don't match
    logger.info("backend: initialized")
    config = rj.jsonget("exp_config")

    params = config["samplers"][name]
    _class = params.pop("class")
    Alg = getattr(algs, _class)
    alg = Alg(n=config["n"], **params)

    if hasattr(alg, "get_query"):
        @app.get(f"/query-{name}")
        def _get_query():
            q, score = alg.get_query()
            return {"name": name, "score": score, **q}

    client = None
    logger.info(f"Starting algs={name}")
    background_tasks.add_task(alg.run, name, client, rj)
    return True



@app.get("/model")
async def get_model(name: str):
    return 1
