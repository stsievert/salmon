import logging
from typing import List, Tuple
import numpy as np

from .utils import Answer, Query
from ...backend.sampler import Runner


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


class RoundRobin(Runner):
    """
    Let the head of the triplet query rotate through the available items while choosing the bottom two items randomly.

    Parameters
    ----------
    n : int
        Number of objects
    ident : str
        Identifier of the algorithm

    """

    def __init__(self, n, d=2, ident=""):
        self.n = n
        self.d = d
        self.answers = []
        self.counter = 0
        super().__init__(ident=ident)

    def get_query(self) -> Query:
        head = self.counter % self.n
        a, b = np.random.choice(self.n, size=2, replace=False)
        self.counter += 1
        score = max(abs(head - a), abs(head - b))
        return {"head": int(head), "left": int(a), "right": int(b)}, float(score)

    def process_answers(self, ans: List[Answer]):
        return self, False

    @property
    def sleep_(self):
        return 1
