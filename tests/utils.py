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
            kwargs.update(timeout=80)

        logger.info(f"Getting {endpoint}")
        r = requests.get(self.url + endpoint, **kwargs)
        logger.info("done")
        assert r.status_code == status_code, (r.status_code, status_code, r.text)
        return r

    def post(self, endpoint, data=None, status_code=200, error=False, **kwargs):
        if "auth" not in kwargs and self._authorized:
            kwargs.update(auth=self.creds)
        if "init_exp" in endpoint and "timeout" not in kwargs:
            kwargs.update(timeout=80)
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


def _clear_logs(log=None):
    if log:
        log.write_text("")
    else:
        this_dir = Path(__file__).absolute().parent
        root_dir = this_dir.parent
        log_dir = root_dir / "out"
        for log in log_dir.glob("*.log"):
            log.write_text("")


@pytest.fixture()
def server():
    server = Server("http://127.0.0.1:8421")
    server.authorize()
    r = server.delete("/reset?force=1", auth=server.creds, timeout=20)
    assert r.json() == {"success": True}
    _clear_logs()
    yield server
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
        _clear_logs()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            raise exc_type(exc_value)
        sleep(1)
        for log in self.log_dir.glob("*.log"):
            lines = log.read_text().split("\n")
            for line in lines:
                if self.catch and ("error" in line or "except" in line):
                    raise LogError("{}\n{}".format(log, line))
                if self.warn and "warn" in line:
                    warn("{}\n{}".format(log, line))
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
