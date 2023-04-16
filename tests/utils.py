import json
from logging import getLogger
from pathlib import Path
from time import sleep
from typing import Tuple
from warnings import warn

import httpx as requests
import numpy as np
import pytest
import yaml
from sklearn.utils import check_random_state

logger = getLogger(__name__)
TIMEOUT = 200


class Server:
    def __init__(self, url, async_client=None):
        self.url = url
        self.async_client = async_client
        self._authorized = False

    @property
    def creds(self) -> Tuple[str, str]:
        return ("foobar", "pass123")

    def get(self, endpoint, status_code=200, **kwargs):
        if "auth" not in kwargs and self._authorized:
            kwargs.update(auth=self.creds)
        if "reset" in endpoint and "timeout" not in kwargs:
            kwargs.update(timeout=TIMEOUT)
        if "timeout" not in kwargs:
            kwargs.update(timeout=TIMEOUT)

        logger.info(f"Getting {endpoint}")
        r = requests.get(self.url + endpoint, **kwargs)
        logger.info("done")
        if status_code:
            assert r.status_code == status_code, (r.status_code, status_code, r.text)
        return r

    def reset(self):
        r = self.delete("/reset?force=1", auth=self.creds, timeout=TIMEOUT)
        assert r.json() == {"success": True}

    def post(self, endpoint, data=None, status_code=200, error=False, **kwargs):
        if "auth" not in kwargs and self._authorized:
            kwargs.update(auth=self.creds)
        if "init_exp" in endpoint and "timeout" not in kwargs:
            kwargs.update(timeout=TIMEOUT)
        if "timeout" not in kwargs:
            kwargs.update(timeout=TIMEOUT)
        if isinstance(data, dict) and "exp" not in data and "rdb" not in data:
            data = json.dumps(data)
        logger.info(f"Getting {endpoint}")
        r = requests.post(self.url + endpoint, data=data, **kwargs)
        logger.info("done")
        if not error:
            assert r.status_code == status_code, (r.status_code, status_code, r.text)
        return r

    def delete(self, endpoint, status_code=200, **kwargs):
        if "auth" not in kwargs and self._authorized:
            kwargs.update(auth=self.creds)
        logger.info(f"Getting {endpoint}...")
        r = requests.delete(self.url + endpoint, **kwargs)
        logger.info("done")
        assert r.status_code == status_code, (r.status_code, status_code, r.text)
        return r

    def authorize(self):
        username, password = self.creds
        r = self.post(f"/create_user/{username}/{password}", error=True)
        assert r.status_code in {200, 403}
        self._authorized = True
        return r


def _clear_logs(log=None):
    if log:
        with log.open(mode="w") as f:
            print("", file=f)
    else:
        this_dir = Path(__file__).absolute().parent
        root_dir = this_dir.parent
        log_dir = root_dir / "salmon" / "_out"
        for log in log_dir.glob("*.log"):
            _clear_logs(log=log)


def _reset(server):
    server.authorize()
    server.reset()

    # Delete files
    _clear_logs()
    OUT = Path(__file__).absolute().parent.parent / "salmon" / "_out"
    dump = OUT / "dump.rdb"
    if dump.exists():
        dump.unlink()
    assert not dump.exists()

    #  server.authorize()
    #  server.reset()
    return server


@pytest.fixture()
def server():
    server = Server("http://127.0.0.1:8421")
    server.authorize()
    # server = _reset(server)
    sleep(1)
    yield server
    server = _reset(server)
    sleep(5)


class LogError(Exception):
    pass


class Logs:
    def __init__(self):
        this_dir = Path(__file__).absolute().parent
        root_dir = this_dir.parent
        self.log_dir = root_dir / "salmon" / "_out"
        self.catch = True
        self.warn = True
        self.delay = 0.5  # for files to finish flushing

    def __enter__(self):
        _clear_logs()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            raise exc_type(exc_value)
        sleep(self.delay)
        files = list(self.log_dir.glob("*.log"))
        msg = f"files for checking logs = {files}"
        logger.warning(msg)
        _errors = []
        _warnings = []
        for log in files:
            lines = log.read_text().split("\n")
            for line in lines:
                if any(x in line.lower() for x in ["error", "except"]):
                    _errors.append(line)
                if "warn" in line.lower() and "answer received:" not in line.lower():
                    _warnings.append(line)
        if self.warn and len(_warnings):
            warn("\n".join(_warnings))
        if self.catch and len(_errors):
            raise LogError("\n".join(_errors))
        _clear_logs()


@pytest.fixture()
def logs():
    return Logs()


def alien_egg(head, left, right, random_state=None):
    """
    Parameters
    ---------- head, left, right : int, int, int
        Number of spikes on the various objects

    Returns
    -------
    winner : str
        Either "left" or "right"

    Notes
    -----
    This is determined from human data.
    See datasets/strange-fruit-triplet/noise-model.ipynb for details.
    """
    ldiff = np.abs(head - left)
    rdiff = np.abs(head - right)

    r = np.maximum(ldiff, rdiff) / (ldiff + rdiff)
    rate = 19.5269746
    final = 0.9567
    p_correct = final / (1 + np.exp(-rate * (r - 0.5)))

    winner = 0 if ldiff < rdiff else 1
    random_state = check_random_state(random_state)

    if random_state.uniform() <= p_correct:
        return winner
    return 1 - winner
