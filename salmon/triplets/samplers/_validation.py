import logging
import random

import numpy as np

from salmon.triplets.samplers._round_robin import (
    RoundRobin, _get_query, _score_query
)
from salmon.triplets.samplers.utils import Answer, Query

logger = logging.getLogger(__name__)


def _random_query(n: int):
    return np.random.choice(n, size=3, replace=False).tolist()


class Validation(RoundRobin):
    """Ask about the same queries repeatedly"""

    def __init__(self, n, d=2, n_queries=20, queries=None, ident=""):
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
        queries : List[Tuple[int, int, int]]
            The list of queries to ask about. Each query is
            ``(head, obj1, obj2)`` where ``obj1`` and ``obj2`` are
            randomly shown on the left and right. Each item in the tuple
            is the `index` of the target to ask about. For example:

            .. code-block:: python

                queries=[(0, 1, 2), (3, 4, 5), (6, 7, 8)]

            will first ask about a query with ``head_index=0``, then
            ``head_index=3``, then ``head_index=6``.
        """
        self.n_queries = n_queries
        if queries is None:
            queries = []
            while True:
                q = _random_query(n)
                if q not in queries:
                    queries.append(q)
                if len(queries) == n_queries:
                    break
        idx = [i for query in queries for i in query]
        if n - 1 < max(idx):
            raise ValueError(
                f"The index {max(idx)} is included as an index for validation "
                f"sampling, which is too large for the n={n} targets."
            )
        self._val_queries = queries
        super().__init__(n=n, d=d, ident=ident)

    def get_query(self, **kwargs):
        idx = self.counter % len(self._val_queries)
        if idx == 0:
            random.shuffle(self._val_queries)

        self.counter += 1
        h, l, r = self._val_queries[idx]
        if random.choice([True, False]):
            l, r = r, l
        return {"head": int(h), "left": int(l), "right": int(r)}, float(idx)
