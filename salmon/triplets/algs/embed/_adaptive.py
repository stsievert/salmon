from sklearn.base import BaseEstimator
from numba import jit, prange
import numpy as np

from .search import gram_utils, score


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
        self.initialized = True
        n = len(self.embedding)
        self._tau_ = np.zeros((n, n), dtype="float32")
        self.update([])

    @jit
    def __random_query(self, n):
        while True:
            h = self.random_state_.choice(n)
            o1 = self.random_state_.choice(n)
            o2 = self.random_state_.choice(n)
            if h != o1 and h != o2 and o1 != o2:
                return [h, o1, o2]

    @jit
    def _random_queries(self, num=1000):
        n = len(self.embedding)
        return [self.__random_query(n) for _ in prange(num)]

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

        for head, w, l in history:
            self._tau_[head] += np.log(self.probs(D[w], D[l]))

        tau = np.exp(self._tau_)
        s = tau.sum(axis=1)  # the sum of each row
        tau = (tau.T / s).T
        return tau

    def update(self, history):
        D = self._distances()
        self.posterior_ = self._posterior(D, history)
        return self


class InfoGainScorer(QueryScorer):
    def score(self, *, num=1000):
        D = self._distances()
        _Q = self._random_queries(num=num)
        Q = np.array(_Q).astype("int64")
        H, O1, O2 = Q[:, 0], Q[:, 1], Q[:, 2]

        scores = score(H, O1, O2, self.posterior_, D, probs=self.probs)
        return Q, scores
