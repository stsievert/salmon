import logging
import logging.config
from pathlib import Path

from fastapi import HTTPException


def get_logger(name, file_handler=True):
    # Config from https://docs.python-guide.org/writing/logging/ and
    # https://docs.python-guide.org/writing/logging/
    logger = logging.getLogger(name)
    formatter = logging.Formatter(
        "%(asctime)s -- %(name)-12s -- %(levelname)-8s -- %(message)s"
    )

    logs = Path(__file__).absolute().parent / "logs"
    if not logs.exists():
        logs.mkdir()
    handler = logging.FileHandler(str(logs / f"{name}.log"))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    handler2 = logging.StreamHandler()
    handler2.setFormatter(formatter)
    logger.addHandler(handler2)

    logger.setLevel(logging.INFO)

    return logger


class ServerException(HTTPException):
    def __init__(self, msg):
        raise HTTPException(status_code=500, detail=msg)
