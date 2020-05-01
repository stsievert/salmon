import logging
from pathlib import Path


def get_logger(name):
    # Config from https://docs.python-guide.org/writing/logging/ and
    # https://docs.python-guide.org/writing/logging/
    logger = logging.getLogger(name)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s from %(name)s: %(message)s"
    )

    handler2 = logging.StreamHandler()
    handler2.setFormatter(formatter)
    logger.addHandler(handler2)

    logger.setLevel(logging.INFO)

    return logger
