import logging
from time import sleep
from typing import List, Optional, Tuple

import numpy as np

from salmon.backend.sampler import DaskClient, Path, Sampler, root

from .utils import Answer, Query

logger = logging.getLogger(__name__)


def _get_query(targets: List[int]) -> Tuple[int, int, int]:
    a, b, c = np.random.choice(targets, size=3, replace=False)
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

    def __init__(self, n, d=2, ident="", allowable=None):
        self.n = n
        self.d = d
        self.allowable = allowable
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

    def get_query(self, **kwargs) -> Tuple[Query, Optional[float]]:
        h, a, b = _get_query(self.targets)
        query = {"head": int(h), "left": int(a), "right": int(b)}
        return query, -9999

    def process_answers(self, ans: List[Answer]):
        return self, False

    def run(self, *args, **kwargs):
        rj = self.redis_client()
        rj.jsonset(f"stopped-{self.ident}", Path("."), True)
        return None
