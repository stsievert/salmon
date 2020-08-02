import asyncio
import logging
import logging.handlers
import os
from logging.handlers import QueueHandler
from logging import LogRecord
from pathlib import Path

# Python 3.7 and newer, fast reentrant implementation
# without task tracking (not needed for that when logging)
from queue import SimpleQueue as Queue
from typing import List

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


def get_logger(name):
    # Config from https://docs.python-guide.org/writing/logging/ and
    # https://docs.python-guide.org/writing/logging/
    logger = logging.getLogger(name)
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s")
    handlers = []

    ph = logging.StreamHandler()
    ph.setFormatter(formatter)
    LEVEL = getattr(logging, LOG_LEVEL)
    ph.setLevel(LEVEL)
    handlers.append(ph)

    ROOT_DIR = Path(__file__).absolute().parent.parent

    out = ROOT_DIR / "out" / f"{name}.log"

    fh = logging.FileHandler(str(out))
    fh.setLevel(LEVEL)
    fh.setFormatter(formatter)
    handlers.append(fh)

    if False:
        # Works for uvicorn but not for gunicorn
        logger = background_logger(logger, *handlers)
    else:
        for handler in handlers:
            logger.addHandler(handler)
    logging.getLogger("fastapi").setLevel(LEVEL)
    logger.warning("initializing logger with LEVEL=%s", LEVEL)
    return logger


def background_logger(logger, *handlers):
    """Move log handlers to a separate thread.

    Replace handlers on the root logger with a LocalQueueHandler,
    and start a logging.QueueListener holding the original
    handlers.

    Adapted https://www.zopatista.com/python/2019/05/11/asyncio-logging/
    """
    queue = Queue()
    async_handler = QueueHandler(queue)
    logger.addHandler(async_handler)

    listener = logging.handlers.QueueListener(
        queue, *handlers, respect_handler_level=True
    )
    listener.start()
    return logger
