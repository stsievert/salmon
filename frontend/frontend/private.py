from typing import Dict, Any, List
import os
import yaml
from time import time
import hashlib, uuid
from functools import lru_cache

from rejson import Client, Path

from fastapi import File, UploadFile, Depends, HTTPException, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import HTMLResponse, JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from .public import _ensure_initialized, app
from .utils import ServerException

security = HTTPBasic()

root = Path.rootPath()
rj = Client(host="redis", port=6379, decode_responses=True)

EXPECTED_PWORD = "331a5156c7f0a529ed1de8d9aba35da95655c341df0ca0bbb2b69b3be319ecf0"


def _salt(password: str) -> str:
    pword = bytes(password, "utf8")
    salt = b"\x87\xa4\xb0\xc6k\xb7\xcf!\x8a\xc8z\xc6Q\x8b_\x00i\xc4\xbd\x01\x15\xabjn\xda\x07ZN}\xfd\xe1\x0e"
    m = hashlib.sha256()
    m.update(pword + salt)
    return m.digest().hex()


def _authorize(credentials: HTTPBasicCredentials = Depends(security)):
    if os.environ.get("SALMON_NO_AUTH", False):
        return True
    if credentials.username != "foo" or _salt(credentials.password) != EXPECTED_PWORD:
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
    <input name="exp" type="file">
    <input type="submit">
    </form>
    </body>
    """
    return HTMLResponse(content=body)


@app.post("/init_exp", tags=["private"])
async def process_form(
    exp: bytes = File(default=""), authorized: bool = Depends(_authorize)
):
    """
    The uploaded file needs to have the following keys:

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
        - instructions: "Foobar!"
    """

    config = yaml.load(exp, Loader=yaml.SafeLoader)
    print(config)
    exp_config: Dict = {
        "instructions": "Default instructions (can include <i>arbitrary</i> HTML)",
        "max_responses": -1,
        "debrief": "Thanks!",
    }
    exp_config.update(config)
    exp_config["n"] = len(exp_config["targets"])
    rj.jsonset("exp_config", root, exp_config)
    return {
        "success": True,
        "documentation": [
            "Visit main URL '[url]' to see query page.",
            "Visit '[url]/get_responses' to download responses.",
            "Visit '[url]/reset' to reset the experiment and delete all data.",
            "Visit '[url]/docs' or '[url]/redoc' to see API documentation",
        ],
    }


@app.delete("/reset", tags=["private"])
@app.get("/reset", tags=["private"])
def reset(force: int = 0, authorized=Depends(_authorize), tags=["private"]):
    """
    Delete all data from the database. This requires authentication.

    """
    if not force:
        msg = (
            "Do you really want to delete *all* data? This will delete all "
            "responses and all target information and *cannot be undone.*\n\n"
            "If you do really want to reset, go to '[url]/reset?force=1' "
            "instead of '[url]/reset'"
        )
        raise ServerException(msg)

    if authorized:
        rj.flushdb()
        rj.jsonset("responses", root, [])
        rj.jsonset("start_time", root, time())
        return {"success": True}

    return {"success": False}


@app.get("/get_responses", tags=["private"])
async def get_responses(authorized: bool = Depends(_authorize)) -> Dict[str, Any]:
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
    targets = exp_config["targets"]
    out: List[Dict[str, Any]] = []
    start = rj.jsonget("start_time")
    for datum in responses:
        out.append(datum)
        objects = {
            key + "_object": targets[datum[key]]
            for key in ["left", "right", "head", "winner"]
        }
        filenames = {
            key + "_src": _get_filename(targets[datum[key]])
            for key in ["left", "right", "head", "winner"]
        }
        out[-1].update(objects)
        out[-1].update(filenames)
        out[-1].update({"time_received_since_start": datum["time_received"] - start})

    return JSONResponse(
        out, headers={"Content-Disposition": 'attachment; filename="responses.json"'}
    )


@lru_cache()
def _get_filename(html: str) -> str:
    _tags = [x for x in html.split(" ") if "=" in x]
    tags = {x.split("=")[0]: x.split("=")[1] for x in _tags}
    if "src" in tags:
        return tags["src"][1:-1]
    return html
