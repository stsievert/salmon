from typing import Union

import numpy as np
from sklearn.utils import check_random_state
import torch
import torch.nn as nn

ArrayLike = Union[np.ndarray, torch.Tensor]


def numpy_or_torch(f):
    def wrapper(_, win2, lose2):
        converted = False
        if isinstance(win2, np.ndarray):
            win2 = torch.from_numpy(win2)
            lose2 = torch.from_numpy(lose2)
            converted = True
        r = f(_, win2, lose2)
        if converted:
            r = r.numpy()
        return r

    return wrapper


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
        distances ``win2`` and ``lose2``. By default, the negative log
        loss of ``self.probs(win2, lose2)``.

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
        return -1 * torch.log(self.probs(win2, lose2))

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
    @numpy_or_torch
    def probs(self, win2, lose2):
        ## Double the computation
        #  num = torch.exp(-win2)
        #  return num / (num + torch.exp(-lose2))

        ## Less computation
        # dist>0: agrees with embedding. <0: does not agree.
        # d1 = win2, d2 = lose2
        # 1 / (1 + exp(d1 - d2))
        # = 1 / (1 + exp(-d2 + d1))
        # = 1 / (1 + exp(-d2 / -d1))
        # = exp(-d1) / (exp(-d1) + exp(d2))
        # = prob of winning by STE
        return 1 / (1 + np.exp(win2 - lose2))


class TSTE(TripletDist):
    def __init__(self, n=None, d=2, alpha=1, random_state=None):
        super().__init__(n=n, d=d, random_state=random_state)
        self.alpha = alpha

    @numpy_or_torch
    def probs(self, win2, lose2):
        pwr = -(self.alpha + 1) / 2
        t1 = (1 + (win2 / self.alpha)) ** pwr
        t2 = (1 + (lose2 / self.alpha)) ** pwr
        return t1 / (t1 + t2)


class CKL(TripletDist):
    def __init__(self, n=None, d=2, mu=1e-4, random_state=None):
        super().__init__(n=n, d=d, random_state=random_state)
        self.mu = mu

    @numpy_or_torch
    def probs(self, win2, lose2):
        num = self.mu + lose2
        return num / (num + self.mu + win2)


class GNMDS(TripletDist):
    def losses(self, win2, lose2):
        zeros = torch.zeros(len(win2))
        return torch.max(zeros, win2 - lose2 + 1)
