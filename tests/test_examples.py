import random
from pathlib import Path
from time import sleep
from zipfile import ZipFile

import pytest

from .utils import server

EG_DIR = Path(__file__).parent.parent / "examples"
SUBDIRS = [
    f.name for f in EG_DIR.iterdir() if f.is_dir() and f.name[0] not in ["_", "."]
]
YAMLS = [f.name for f in EG_DIR.glob("*.yaml")]


def _test_upload(exp: Path, target_zip: Path = None, server=None):
    assert server is not None
    server.authorize()
    if target_zip:
        targets = Path(target_zip)
        assert targets.exists()
        t = targets.read_bytes()
        assert len(t) > 0
        assert t[:4] == b"\x50\x4B\x03\x04"

        kwargs = {"files": {"targets": t}}
    else:
        kwargs = {}
    r = server.post("/init_exp", data={"exp": exp.read_text()}, timeout=60, **kwargs)
    return r.status_code == 200

def _test_example(exp, target_zip=None, server=None):
    assert server is not None
    success = _test_upload(exp, target_zip, server)
    assert success
    server.get("/", timeout=5)
    for _ in range(10):
        r = server.get("/query")
        assert r.status_code == 200
        query = r.json()
        query["winner"] = random.choice([query["left"], query["right"]])
        r = server.post("/answer", data=query)
        assert r.status_code == 200
    r = server.delete("/reset?force=1", timeout=20)
    assert r.json() == {"success": True}
    return True

@pytest.mark.parametrize("fname", YAMLS)
def test_basic_examples(fname: str, server):
    server.authorize()
    success = _test_example(EG_DIR / fname, server=server)
    assert success


@pytest.mark.parametrize("eg_dir", SUBDIRS)
def test_directory_examples(eg_dir: str, server):
    server.authorize()
    _eg_dir = EG_DIR / eg_dir
    for exp in _eg_dir.glob("*.yaml"):
        for target_zip in _eg_dir.glob("*.zip"):
            success = _test_example(exp, target_zip, server)
            assert success
