import numpy as np
from sklearn.base import BaseEstimator

import salmon.utils as utils

from .search import gram_utils, score

logger = utils.get_logger(__name__)


class QueryScorer:
    """
    A class to score queries for adaptive searches.

    Parameters
    ----------
    embedding : array-like
        The embedding of points.

    probs : callable
        Function to call to get probabilities. Called with
        ``probs(win2, lose2)``
        where ``win2`` and ``lose2`` are the squared Euclidean distances
        between the winner and loser.

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

    def __init__(self, embedding=None, probs=None):
        self.embedding = embedding
        self.probs = probs

    def _initialize(self):
        self.initialized_ = True
        n = len(self.embedding)
        self._tau_ = np.zeros((n, n), dtype="float32")
        self.push([])

    def _random_queries(self, n, num=1000, trim=True):
        new_num = int(num * 1.1 + 3)
        rng = np.random.RandomState()
        queries = rng.choice(n, size=(new_num, 3))
        repeated = (
            (queries[:, 0] == queries[:, 1])
            | (queries[:, 1] == queries[:, 2])
            | (queries[:, 0] == queries[:, 2])
        )
        queries = queries[~repeated]
        if trim:
            return queries[:num]
        return queries

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
                probs = self.probs(D[w], D[l])
                probs[np.isnan(probs)] = 0
                _eps = 1e-80
                probs[probs <= _eps] = _eps
                a = np.log(probs + _eps)
                self._tau_[head] += a

        # idx = self._tau_ >= -np.inf
        tau = np.zeros_like(self._tau_)
        # tau[idx] = np.exp(self._tau_[idx])
        tau = np.exp(self._tau_)
        s = tau.sum(axis=1)  # the sum of each row

        gt0 = s > 0
        eps = s[gt0].min() if gt0.any() else s.min()

        s *= 1e4
        tau *= 1e4

        s = np.clip(s, eps, np.inf)

        tau2 = (tau.T / s).T  # transpose to make broadcasting work
        return tau2

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


class UncertaintyScorer(QueryScorer):
    def score(self, *, queries=None, num=1000, trim=True):
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
            queries = self._random_queries(len(self.embedding), num=num, trim=trim)
        Q = np.array(queries).astype("int64")
        H, O1, O2 = Q[:, 0], Q[:, 1], Q[:, 2]

        # score is distance to the decision boundary.
        scores = -np.abs(D[H, O1] - D[H, O2])
        return Q, scores
