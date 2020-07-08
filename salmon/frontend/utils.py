import hashlib
import os
from io import BytesIO
from pathlib import Path
from textwrap import dedent
from typing import Any
from zipfile import ZipFile

from fastapi import HTTPException

from ..utils import get_logger


class ServerException(HTTPException):
    def __init__(self, msg):
        raise HTTPException(status_code=500, detail=msg)


def _extract_zipfile(raw_zipfile, directory="targets"):
    p = Path(__file__).absolute().parent  # directory to this file
    imgs = p / "static" / directory

    if imgs.exists():
        for _f in imgs.glob("**/*"):
            _f.unlink()
        imgs.rmdir()
    if not imgs.exists():
        imgs.mkdir()
    with BytesIO(raw_zipfile) as f:
        with ZipFile(f) as myzip:
            infos = [f for f in myzip.infolist() if f.filename[0] != "."]
            for info in infos:
                if info.filename[-1] == "/" or "/." in info.filename:
                    continue
                info.filename = os.path.basename(info.filename)
                myzip.extract(info, path=str(imgs))
    return list(sorted(list(imgs.glob("**/*"))))


def _format_target(file: Path):
    logger = get_logger(__name__)
    static = Path(__file__).absolute().parent
    p = file.relative_to(static)
    logger.info(str(p))
    url = "/" + str(p)
    if any(ext in url.lower() for ext in ["png", "gif", "jpg", "bmp", "jpeg", "svg"]):
        return f"<img src='{url}' />"
    elif any(ext in url for ext in ["mov", "mp4"]):
        return dedent(
            f"""
            <video autoplay controls>
            <source src='{url}' type='video/mp4' />
            Your browser does not support the video tag.
            </video>
            """
        )
    else:
        raise ValueError(
            f"Unsupported extension for file={file}. "
            "Supported extensions are ['png', 'gif', 'jpg', 'bmp', "
            "'jpeg', 'svg', 'mov' or 'mp4']"
        )


def sha256(x: Any) -> str:
    if not isinstance(x, (str, bytes)):
        x = str(x)
    if isinstance(x, str):
        x = x.encode(encoding="ascii")
    m = hashlib.sha256()
    m.update(x)
    return m.hexdigest()
