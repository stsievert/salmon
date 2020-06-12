from typing import Union

import numpy as np
import torch
import torch.nn as nn

ArrayLike = Union[np.ndarray, torch.Tensor]


class TripletDist(nn.Module):
    def __init__(self, n: int=None, d: int = 2):
        super().__init__()
        embedding = 1e-4 * torch.randn((n, d), requires_grad=True)
        self.embedding = torch.nn.Parameter(embedding)

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

    def _get_dists(self, h_w_l):
        heads = self.embedding[h_w_l[:, 0]]
        winners = self.embedding[h_w_l[:, 1]]
        losers = self.embedding[h_w_l[:, 2]]

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
        probs = num / (num + self.mu + lose2)
        return -1 * torch.log(probs)


class GNMDS(TripletDist):
    def losses(self, win2, lose2):
        zeros = torch.zeros(len(win2))
        return torch.max(zeros, win2 - lose2 + 1)
