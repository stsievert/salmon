import logging
import random

import numpy as np

from ...backend.sampler import Path, Runner
from .utils import Answer, Query
from ._round_robin import _get_query, _score_query, RoundRobin
logger = logging.getLogger(__name__)


class Validation(RoundRobin):
    """Ask about the same queries repeatedly"""
    def __init__(self, n, d=2, n_queries=20, ident=""):
        """
        This sampler asks the same questions repeatedly, useful to evaluate
        query difficulty.

        Parameters
        ----------
        n : int
            Number of objects
        ident : str
            Identifier of the algorithm
        n_queries : int, optional (default=20)
            Number of validation queries.
        d : int
            Embedding dimension.
        """
        self.n_queries = n_queries
        Q = [np.random.choice(n, size=3, replace=False) for _ in range(n_queries)]
        self._val_queries = Q
        super().__init__(n=n, d=d, ident=ident)

    def get_query(self):
        idx = self.counter % len(self._val_queries)
        if idx == 0:
            random.shuffle(self._val_queries)

        self.counter += 1
        h, l, r = self._val_queries[idx]
        if random.choice([True, False]):
            l, r = r, l
        return {"head": int(h), "left": int(l), "right": int(r)}, float(idx)
