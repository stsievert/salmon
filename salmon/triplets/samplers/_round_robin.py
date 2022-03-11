import logging
from typing import List, Tuple
import random
from copy import deepcopy

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

    def __init__(self, n, d=2, ident="", allowable=None):
        """
        Parameters
        ----------
        n : int
            Number of objects
        ident : str
            Identifier of the algorithm
        allowable : Optional[List[int]]
            The allowable indexes to ask about.
        """
        self.n = n
        self.d = d
        self.answers = []
        self.counter = 0

        self.order = None
        self.targets = allowable or list(range(n))

        if allowable is not None:
            if not isinstance(allowable, list):
                msg = "Specify a list for allowable. Got {} or type {}"
                raise ValueError(msg.format(allowable, type(allowable)))
            if not all(isinstance(i, int) for i in allowable):
                msg = "Not all items in allowable are integers. Bad values are {}"
                bad_vals = [v for v in allowable if not isinstance(v, int)]
                raise ValueError(msg.format(bad_vals))
            if len(allowable) < 3:
                msg = "Specify at least 3 allowable items. Got {} allowable items"
                raise ValueError(msg.format(len(allowable)))
            if max(allowable) >= n:
                msg = "At least one allowable target is too large. Values too large include {}, larger than {}"
                bad_vals = [v for v in allowable if v >= n]
                raise ValueError(msg.format(bad_vals, n))

        super().__init__(ident=ident)

    def get_query(self) -> Tuple[Query, float]:
        if (self.order is None) or (self.counter % len(self.targets) == 0):
            self.order = deepcopy(self.targets)
            np.random.shuffle(self.order)

        head = self.order[self.counter % len(self.order)]
        kids = list(set(self.targets) - {head})
        a, b = np.random.choice(list(kids), size=2, replace=False)
        self.counter += 1
        score = max(abs(head - a), abs(head - b))
        return {"head": int(head), "left": int(a), "right": int(b)}, float(score)

    def process_answers(self, ans: List[Answer]):
        return self, False

    def run(self, *args, **kwargs):
        rj = self.redis_client()
        rj.jsonset(f"stopped-{self.ident}", Path("."), True)
        return None
