import logging
import random
from copy import deepcopy
from typing import List, Tuple

import numpy as np

from salmon.backend.sampler import Sampler
from salmon.triplets.samplers.utils import Answer, Query

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


class _RoundRobin(Sampler):
    """
    Let the head of the triplet query rotate through the available items while choosing the bottom two items randomly.
    """

    def __init__(self, n, d=2, ident="", targets=None):
        """
        Parameters
        ----------
        n : int
            Number of objects
        ident : str
            Identifier of the algorithm
        targets : Optional[List[int]]
            The allowable indexes to ask about.
        """
        self.n = n
        self.d = d
        self.answers = []
        self.counter = 0

        self.order = None
        self.targets = targets or list(range(n))

        if targets is not None:
            if not isinstance(targets, list):
                msg = "Specify a list for targets. Got {} or type {}"
                raise ValueError(msg.format(targets, type(targets)))
            if not all(isinstance(i, int) for i in targets):
                msg = "Not all items in targets are integers. Bad values are {}"
                bad_vals = [v for v in targets if not isinstance(v, int)]
                raise ValueError(msg.format(bad_vals))
            if len(targets) < 3:
                msg = "Specify at least 3 targets items. Got {} targets items"
                raise ValueError(msg.format(len(targets)))
            if max(targets) >= n:
                msg = "At least one targets target is too large. Values too large include {}, larger than {}"
                bad_vals = [v for v in targets if v >= n]
                raise ValueError(msg.format(bad_vals, n))

        super().__init__(ident=ident)

    def get_query(self, **kwargs) -> Tuple[Query, float]:
        if self.order is None:
            self.order = deepcopy(self.targets)

        idx = self.counter % len(self.order)
        logger.warning("idx=%s", idx)
        if idx == 0:
            np.random.shuffle(self.order)

        head = self.order[idx]

        kids = set(self.targets) - {head}
        a, b = np.random.choice(list(kids), size=2, replace=False)
        self.counter += 1
        score = max(abs(head - a), abs(head - b))
        return {"head": int(head), "left": int(a), "right": int(b)}, float(score)

    def process_answers(self, ans: List[Answer]):
        return self, False

    def run(self, *args, **kwargs):
        from rejson import Path
        root = Path.rootPath()

        rj = self.redis_client()
        rj.jsonset(f"stopped-{self.ident}", Path("."), True)
        return None


class RoundRobin(_RoundRobin):
    """
    Let the head of the triplet query rotate through the available items while choosing
    the bottom two items randomly. This class is user specific if the
    ``/query?puid=foo`` endpoint is hit.
    """
    def __init__(self, *args, **kwargs):
        self.rr_args = args
        self.rr_kwargs = kwargs
        self.samplers = {}  # puid to roundrobing

        super().__init__(*args, **kwargs)

    def get_query(self, puid: str = "") -> Tuple[Query, float]:
        if puid not in self.samplers:
            self.samplers[puid] = _RoundRobin(*self.rr_args, **self.rr_kwargs)
        return self.samplers[puid].get_query()

    def process_answers(self, ans: List[Answer]):
        return self, True
