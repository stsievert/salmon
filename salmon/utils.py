import asyncio
import logging
import logging.handlers
import os
from logging import LogRecord
from logging.handlers import QueueHandler
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
    LEVEL = getattr(logging, LOG_LEVEL)
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s")
    handlers = []

    ph = logging.StreamHandler()
    ph.setFormatter(formatter)
    ph.setLevel(LEVEL)
    handlers.append(ph)

    SRC = Path(__file__).absolute().parent
    assert SRC.is_dir()  # points to salmon/ source directory
    assert (SRC / "_out").exists(), str(SRC / "_out")
    out = SRC / "_out" / f"{name}.log"

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


def flush_logger(logger):
    for handler in logger.handlers:
        try:
            handler.flush()
        except:
            pass
