import asyncio
import logging
import logging.handlers
from logging.handlers import QueueHandler
from logging import LogRecord
from pathlib import Path

# Python 3.7 and newer, fast reentrant implementation
# without task tracking (not needed for that when logging)
from queue import SimpleQueue as Queue
from typing import List


def get_logger(name, level=logging.INFO):
    # Config from https://docs.python-guide.org/writing/logging/ and
    # https://docs.python-guide.org/writing/logging/
    logger = logging.getLogger(name)
    formatter = logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s: %(message)s"
    )

    ph = logging.StreamHandler()
    ph.setFormatter(formatter)
    ph.setLevel(level)

    DIR = Path(__file__).absolute().parent
    out = DIR / "out" / f"{name}.log"

    fh = logging.FileHandler(str(out))
    fh.setLevel(level)
    fh.setFormatter(formatter)

    logger = background_logger(logger, fh, ph)
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

    listener = logging.handlers.QueueListener(queue, *handlers, respect_handler_level=True)
    listener.start()
    return logger