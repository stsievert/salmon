import logging
from typing import List, Tuple
import random

import numpy as np

from ...backend.sampler import Path, Sampler
from .utils import Answer, Query

logger = logging.getLogger(__name__)


def _get_query(n, head) -> Tuple[int, int, int]:
    a = head
    while True:
        b, c = np.random.choice(n, size=2)
        if a != b and b != c and c != a:
            break
    return a, b, c


def _score_query(q: Tuple[int, int, int]) -> float:
    h, l, r = q
    score = max(abs(h - l), abs(h - r))
    return float(score)


class RoundRobin(Sampler):
    """
    Let the head of the triplet query rotate through the available items while choosing the bottom two items randomly.
    """

    def __init__(self, n, d=2, ident=""):
        """
        Parameters
        ----------
        n : int
            Number of objects
        ident : str
            Identifier of the algorithm
        """
        self.n = n
        self.d = d
        self.answers = []
        self.counter = 0

        self.order = None
        super().__init__(ident=ident)

    def get_query(self) -> Tuple[Query, float]:
        if (self.order is None) or (self.counter % self.n == 0):
            self.order = list(range(self.n))
            np.random.shuffle(self.order)

        head = self.order[self.counter % self.n]
        targets = list(set(range(self.n)) - {head})
        a, b = np.random.choice(list(targets), size=2, replace=False)
        self.counter += 1
        score = max(abs(head - a), abs(head - b))
        return {"head": int(head), "left": int(a), "right": int(b)}, float(score)

    def process_answers(self, ans: List[Answer]):
        return self, False

    def run(self, *args, **kwargs):
        rj = self.redis_client()
        rj.jsonset(f"stopped-{self.ident}", Path("."), True)
        return None
