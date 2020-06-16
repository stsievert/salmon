from typing import Union

import numpy as np
from sklearn.utils import check_random_state
import torch
import torch.nn as nn

ArrayLike = Union[np.ndarray, torch.Tensor]


class TripletDist(nn.Module):
    """
    A base class to find losses for the triplet embedding problem.

    Parameters
    ----------
    n : int
    d : int
    random_state : None, int, np.random.RandomState

    Attributes
    ----------
    embedding : np.ndarray
        The current embedding.

    """

    def __init__(self, n: int = None, d: int = 2, random_state=None):
        super().__init__()
        self.random_state = random_state
        self.n = n
        self.d = d
        rng = check_random_state(self.random_state)
        embedding = 1e-4 * rng.randn(n, d).astype("float32")
        self._embedding = torch.nn.Parameter(
            torch.from_numpy(embedding), requires_grad=True
        )

    def losses(self, win2: ArrayLike, lose2: ArrayLike) -> ArrayLike:
        """
        Calculate the losses of a this triplet model with the triplet
        distances ``win2`` and ``lose2``.

        Parameters
        ----------
        win2 : torch.Tensor, shape=(num_answers)
            The squared Euclidean distance between the head vector and
            winner vector. Formally, :math:`\|x_h - x_w\|_2^2`.
        lose2 : torch.Tensor, shape=(num_answers)
            The squared Euclidean distance between the head vector and
            loser vector. Formally, :math:`\|x_h - x_l\|_2^2`.

        Returns
        -------
        prob : torch.Tensor, shape=(num_answers)
            The probability of triplets with those distances being satisfied.
        """
        raise NotImplementedError

    @property
    def embedding(self):
        return self._embedding

    def _get_dists(self, h_w_l):
        heads = self._embedding[h_w_l[:, 0]]
        winners = self._embedding[h_w_l[:, 1]]
        losers = self._embedding[h_w_l[:, 2]]

        win_dist2 = torch.norm(heads - winners, dim=1) ** 2
        lose_dist2 = torch.norm(heads - losers, dim=1) ** 2
        return win_dist2, lose_dist2

    def forward(self, h_w_l: ArrayLike, y=None) -> ArrayLike:
        """
        Calculate the probability of a triplet being satisified

        Parameters
        ----------
        h_w_l : torch.Tensor, shape=(num_answers, 3)
            Each row in this 2D array is (head, winner, loser) from
            triplet query.

        Returns
        -------
        losses : torch.Tensor, shape=(num_answers)
            The loss of each individual triplet.
        """
        win2, lose2 = self._get_dists(h_w_l)
        return self.losses(win2, lose2)


class STE(TripletDist):
    def losses(self, win2, lose2):
        num = torch.exp(-win2)
        probs = num / (num + torch.exp(-lose2))
        return (-1 * torch.log(probs)).mean()


class TSTE(TripletDist):
    def __init__(self, n=None, d=2, alpha=1):
        super().__init__(n=n, d=d)
        self.alpha = alpha

    def losses(self, win2, lose2):
        a = self.alpha
        num = (1 + (win2 / a)) ** (-1 * (a + 1) / 2)
        probs = num / (num + (1 + (lose2 / a)) ** (-1 * (a + 1) / 2))
        return -1 * torch.log(probs)


class CKL(TripletDist):
    def __init__(self, n=None, d=2, mu=1e-4):
        super().__init__(n=n, d=d)
        self.mu = mu

    def losses(self, win2, lose2):
        num = self.mu + lose2
        probs = num / (num + self.mu + win2)
        return -1 * torch.log(probs)


class GNMDS(TripletDist):
    def losses(self, win2, lose2):
        zeros = torch.zeros(len(win2))
        return torch.max(zeros, win2 - lose2 + 1)
