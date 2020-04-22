from pathlib import Path
import json
import yaml
from typing import Tuple

import requests

URL = "http://127.0.0.1:8421"

def _get_auth() -> Tuple[str, str]:
    p = Path(__file__).parent.parent / "creds.yaml"
    if p.exists():
        creds = yaml.safe_load(p.read_text())
        return (creds["username"], creds["password"])

    return ("username", "password")


def _get(endpoint, URL=URL, status_code=200, **kwargs):
    r = requests.get(URL + endpoint, **kwargs)
    assert r.status_code == status_code
    return r


def _post(endpoint, data=None, URL=URL, status_code=200, error=False, **kwargs):
    #  data = data or {}
    if isinstance(data, dict) and "exp" not in data:
        data = json.dumps(data)
    r = requests.post(URL + endpoint, data=data, **kwargs)
    if not error:
        assert r.status_code == status_code
    return r


def _delete(endpoint, data=None, URL=URL, status_code=200, **kwargs):
    #  data = data or {}
    if isinstance(data, dict) and "exp" not in data:
        data = json.dumps(data)
    r = requests.delete(URL + endpoint, data=data, **kwargs)
    assert r.status_code == status_code
    return r


