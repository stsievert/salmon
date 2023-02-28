import logging
import pickle
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel

from salmon.utils import get_logger

Query = Tuple[int, Tuple[int, int]]  # head, (choice 1, choice 2)

logger = get_logger(__name__)


class Answer(BaseModel):
    head: int
    left: int
    right: int
    winner: int
