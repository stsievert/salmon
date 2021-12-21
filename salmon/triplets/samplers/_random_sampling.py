import logging
from time import sleep
from typing import List, Optional, Tuple

import numpy as np

from salmon.backend.sampler import DaskClient, Path, Sampler, root

from .utils import Answer, Query

logger = logging.getLogger(__name__)


def _get_query(n) -> Tuple[int, int, int]:
    a, b, c = np.random.choice(n, size=3, replace=False)
    return int(a), int(b), int(c)


class Random(Sampler):
    """
    Choose the triplet queries randomly, only ensuring objects are not repeated.

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
        super().__init__(ident=ident)

    def get_query(self) -> Tuple[Query, Optional[float]]:
        h, a, b = _get_query(self.n)
        query = {"head": int(h), "left": int(a), "right": int(b)}
        return query, -9999

    def process_answers(self, ans: List[Answer]):
        return self, False

    def run(self, *args, **kwargs):
        rj = self.redis_client()
        rj.jsonset(f"stopped-{self.ident}", Path("."), True)
        return None
