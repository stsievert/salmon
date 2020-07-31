import json
from pathlib import Path
from typing import Tuple
from logging import getLogger
from warnings import warn

import pytest
import requests
import yaml

logger = getLogger(__name__)

class Server:
    def __init__(self, url):
        self.url = url
        self._authorized = False

    def auth(self) -> Tuple[str, str]:
        logger.info("Getting auth")
        p = Path(__file__).parent.parent / "creds.yaml"
        if p.exists():
            creds = yaml.safe_load(p.read_text())
            return (creds["username"], creds["password"])
        return ("username", "password")

    def get(self, endpoint, status_code=200, **kwargs):
        if self._authorized:
            kwargs.update({"auth": (self._username, self._password)})
        logger.info(f"Getting {endpoint}")
        r = requests.get(self.url + endpoint, **kwargs)
        logger.info("done")
        assert r.status_code == status_code, (r.status_code, status_code)
        return r

    def post(self, endpoint, data=None, status_code=200, error=False, **kwargs):
        if isinstance(data, dict) and "exp" not in data and "rdb" not in data:
            data = json.dumps(data)
        if self._authorized:
            kwargs.update({"auth": (self._username, self._password)})
        logger.info(f"Getting {endpoint}")
        r = requests.post(self.url + endpoint, data=data, **kwargs)
        logger.info("done")
        if not error:
            assert r.status_code == status_code, (r.status_code, status_code)
        return r

    def delete(self, endpoint, data=None, status_code=200, **kwargs):
        if isinstance(data, dict) and "exp" not in data:
            data = json.dumps(data)
        if self._authorized:
            kwargs.update({"auth": (self._username, self._password)})
        logger.info(f"Getting {endpoint}...")
        r = requests.delete(self.url + endpoint, data=data, **kwargs)
        logger.info("done")
        assert r.status_code == status_code, (r.status_code, status_code)
        return r

    def authorize(self):
        self._username, self._password = self.auth()
        self._authorized = True


@pytest.fixture()
def server():
    server = Server("http://127.0.0.1:8421")
    server.get("/reset?force=1", auth=server.auth())
    yield server
    username, password = server.auth()
    r = server.get("/reset?force=1", auth=(username, password))
    assert r.json() == {"success": True}
    dump = Path(__file__).absolute().parent.parent / "out" / "dump.rdb"
    if dump.exists():
        dump.unlink()

class LogError(Exception):
    pass

class Logs:
    def __init__(self):
        this_dir = Path(__file__).absolute().parent
        root_dir = this_dir.parent
        self.log_dir = root_dir / "out"
        self.catch = True
        self.warn = True

    def __enter__(self):
        # Clear logs
        for log in self.log_dir.glob("*.log"):
            log.write_text("")

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            raise exc_type(exc_value)
        for log in self.log_dir.glob("*.log"):
            lines = log.read_text().split("\n")
            for line in lines:
                if self.catch and ("error" in line or "except" in line):
                    raise LogError("{}\n{}".format(log, line))
                if self.warn and "warn" in line:
                    warn("{}\n{}".format(log, line))

@pytest.fixture()
def logs():
    return Logs()
