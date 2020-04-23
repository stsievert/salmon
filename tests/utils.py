from pathlib import Path
import json
import yaml
from typing import Tuple

import pytest
import requests

URL = "http://127.0.0.1:8421"


class Server:
    def __init__(self, url=URL):
        self.url = URL

    def auth(self) -> Tuple[str, str]:
        p = Path(__file__).parent.parent / "creds.yaml"
        if p.exists():
            creds = yaml.safe_load(p.read_text())
            return (creds["username"], creds["password"])
        return ("username", "password")

    def get(self, endpoint, URL=URL, status_code=200, **kwargs):
        r = requests.get(URL + endpoint, **kwargs)
        assert r.status_code == status_code
        return r

    def post(
        self, endpoint, data=None, URL=URL, status_code=200, error=False, **kwargs
    ):
        if isinstance(data, dict) and "exp" not in data:
            data = json.dumps(data)
        r = requests.post(URL + endpoint, data=data, **kwargs)
        if not error:
            assert r.status_code == status_code
        return r

    def delete(self, endpoint, data=None, URL=URL, status_code=200, **kwargs):
        if isinstance(data, dict) and "exp" not in data:
            data = json.dumps(data)
        r = requests.delete(URL + endpoint, data=data, **kwargs)
        assert r.status_code == status_code
        return r


@pytest.fixture()
def server():
    server = Server()
    yield server
    username, password = server.auth()
    r = server.get("/reset?force=1", auth=(username, password))
    assert r.json() == {"success": True}
