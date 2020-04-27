import json
from pathlib import Path
from typing import Tuple

import pytest
import requests
import yaml


class Server:
    def __init__(self, url):
        self.url = url
        self._authorized = False

    def auth(self) -> Tuple[str, str]:
        p = Path(__file__).parent.parent / "creds.yaml"
        if p.exists():
            creds = yaml.safe_load(p.read_text())
            return (creds["username"], creds["password"])
        return ("username", "password")

    def get(self, endpoint, status_code=200, **kwargs):
        if self._authorized:
            kwargs.update({"auth": (self._username, self._password)})
        r = requests.get(self.url + endpoint, **kwargs)
        assert r.status_code == status_code
        return r

    def post(self, endpoint, data=None, status_code=200, error=False, **kwargs):
        if isinstance(data, dict) and "exp" not in data and "rdb" not in data:
            data = json.dumps(data)
        if self._authorized:
            kwargs.update({"auth": (self._username, self._password)})
        r = requests.post(self.url + endpoint, data=data, **kwargs)
        if not error:
            assert r.status_code == status_code
        return r

    def delete(self, endpoint, data=None, status_code=200, **kwargs):
        if isinstance(data, dict) and "exp" not in data:
            data = json.dumps(data)
        if self._authorized:
            kwargs.update({"auth": (self._username, self._password)})
        r = requests.delete(self.url + endpoint, data=data, **kwargs)
        assert r.status_code == status_code
        return r

    def authorize(self):
        self._username, self._password = self.auth()
        self._authorized = True


@pytest.fixture()
def server():
    dump = Path(__file__).absolute().parent.parent / "frontend" / "dump.rdb"
    if dump.exists():
        dump.unlink()

    server = Server("http://127.0.0.1:8421")
    yield server
    username, password = server.auth()
    r = server.get("/reset?force=1", auth=(username, password))
    assert r.json() == {"success": True}
    dump.unlink(missing_ok=True)
