from pathlib import Path
from zipfile import ZipFile
from time import sleep

import pytest
from .utils import server

EG_DIR = Path(__file__).parent.parent / "examples"
SUBDIRS = [
    f.name for f in EG_DIR.iterdir() if f.is_dir() and f.name[0] not in ["_", "."]
]


def _test_upload(exp: Path, target_zip: Path, server):
    server.authorize()
    targets = Path(target_zip)

    assert targets.exists()
    t = targets.read_bytes()
    assert len(t) > 0
    assert t[:4] == b"\x50\x4B\x03\x04"
    r = server.post(
        "/init_exp", data={"exp": exp.read_bytes()}, files={"targets": t}, timeout=60,
    )
    return r.status_code == 200


@pytest.mark.parametrize("eg_dir", SUBDIRS)
def test_directory_examples(eg_dir: str, server):
    server.authorize()
    _eg_dir = EG_DIR / eg_dir
    for exp in _eg_dir.glob("*.yaml"):
        for target_zip in _eg_dir.glob("*.zip"):
            success = _test_upload(exp, target_zip, server)
            assert success
            query = server.get("/", timeout=5)
            r = server.delete("/reset?force=1", timeout=20)
            assert r.json() == {"success": True}
            sleep(2)
