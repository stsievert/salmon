from sklearn.base import BaseEstimator
from numba import jit, prange
import numpy as np
from joblib import Parallel, delayed

from .search import gram_utils, score
import salmon.utils as utils

logger = utils.get_logger(__name__)


class QueryScorer:
    """
    A class to score queries for adaptive searches.

    Parameters
    ----------
    random_state : None, int, RandomState
        The random state for query searches

    embedding : array-like
        The embedding of points.

    probs : callable
        Function to call to get probabilities. Called with
        ``probs(win2, lose2)``
        where ``win2`` and ``lose2`` are the squared Euclidean distances
        between the winner and loser.

    Attributes
    ----------
    random_state_ : RandomState
        Initialized random state

    Notes
    -----
    Inputs: include an embedding, noise model and history of answers
    received.

    Outputs: query scores.

    Internal state: the posterior, history.

    Public API:

    * Update posterior.
    * Get scores.

    """

    def __init__(self, random_state=None, embedding=None, probs=None):
        self.random_state = random_state
        self.embedding = embedding
        self.probs = probs

    def _initialize(self):
        self.random_state_ = np.random.RandomState(self.random_state)
        self.initialized_ = True
        n = len(self.embedding)
        self._tau_ = np.zeros((n, n), dtype="float32")
        self.push([])

    def _random_queries(self, n, num=1000):
        new_num = int(num * 1.1)
        queries = self.random_state_.choice(n, size=(new_num, 3))
        repeated = (
            (queries[:, 0] == queries[:, 1])
            | (queries[:, 1] == queries[:, 2])
            | (queries[:, 0] == queries[:, 2])
        )
        queries = queries[~repeated]
        return queries[:num]

    def _distances(self):
        G = gram_utils.gram_matrix(self.embedding)
        return gram_utils.distances(G)

    def score(self):
        raise NotImplementedError

    def _posterior(self, D, history):
        """
        Calculate the posterior.

        Parameters
        ----------
        D : array-like
            Distance array. D[i, j] = ||x_i - x_j||_2^2
        S : array-like, shape=(num_ans, 3)
            History of answers.

        Returns
        -------
        posterior : array-like, shape=(self.n, self.n)
        """
        n = D.shape[0]

        logger.info("history = %s", history)
        if len(history):
            for k, (head, w, l) in enumerate(history):
                a = np.log(self.probs(D[w], D[l]))
                self._tau_[head] += a

        tau = np.exp(self._tau_)
        s = tau.sum(axis=1)  # the sum of each row
        tau = (tau.T / s).T
        return tau

    def push(self, history):
        if not hasattr(self, "initialized_"):
            self._initialize()
        D = self._distances()
        self.posterior_ = self._posterior(D, history)
        return self


class InfoGainScorer(QueryScorer):
    def score(self, *, queries=None, num=1000):
        """
        Score the queries using (almost) the information gain.

        Parameters
        ----------
        queries : List[int, int, int]
            The list of queries to score.
        num : int
            Number of random queries to generate.

        """
        if not hasattr(self, "initialized_"):
            self._initialize()
        D = self._distances()
        if queries is not None and num != 1000:
            raise ValueError("Only specify one of `queries` or `num`")
        if queries is None:
            queries = self._random_queries(len(self.embedding), num=num)
        Q = np.array(queries).astype("int64")
        H, O1, O2 = Q[:, 0], Q[:, 1], Q[:, 2]

        scores = score(H, O1, O2, self.posterior_, D, probs=self.probs)
        return Q, scores
