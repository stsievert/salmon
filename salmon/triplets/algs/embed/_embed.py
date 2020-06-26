import itertools
from copy import copy
from typing import List, Tuple

import numpy as np
import torch
import torch.optim as optim
from numba import jit, prange
from skorch.net import NeuralNet
from torch.nn.modules.loss import _Loss
from sklearn.base import BaseEstimator
from sklearn.utils import check_random_state
from scipy.special import binom

from .search import gram_utils, score


class _Embedding(NeuralNet):
    def partial_fit(self, *args, **kwargs):
        r = super().partial_fit(*args, **kwargs)

        # Project back onto norm ball
        with torch.no_grad():
            norms = torch.norm(self.module_._embedding, dim=1)
            max_norm = 10 * self.module__d
            idx = norms > max_norm
            if idx.sum():
                self.module_._embedding[idx] *= max_norm / norms[idx]

        return r

    def score(self, answers, y=None):
        win2, lose2 = self.module_._get_dists(answers)
        acc = (win2 < lose2).numpy().astype("float32").mean().item()
        return acc


#  class Reduce(_Loss):
    #  def forward(self, input: torch.Tensor, target=None) -> torch.Tensor:
        #  assert self.reduction == "mean"
        #  return torch.mean(input)

class Reduce:
    def __call__(self, input: torch.Tensor, target=None) -> torch.Tensor:
        return torch.mean(input)

class Embedding(BaseEstimator):
    """
    An triplet embedding algorithm.

    Parameters
    ----------


    """

    def __init__(
        self,
        module,
        module__n: int=85,
        module__d: int =2,
        optimizer=optim.SGD,
        optimizer__lr=0.05,
        optimizer__momentum=0.9,
        random_state=None,
        initial_batch_size=64,
        max_eg=30_000,
        pf_eg=1000,
    ):
        self.module = module
        self.module__n = module__n
        self.module__d = module__d
        self.optimizer = optimizer
        self.optimizer__lr = optimizer__lr
        self.optimizer__momentum = optimizer__momentum
        self.random_state = random_state
        self.initial_batch_size = initial_batch_size
        self.pf_eg = pf_eg
        self.max_eg = max_eg
        super().__init__()

    def initialize(self):

        rng = check_random_state(self.random_state)
        est = _Embedding(
            module=self.module,
            criterion=Reduce,
            #  criterion=lambda x: torch.mean(x)
            module__n=self.module__n,
            module__d=self.module__d,
            module__random_state=self.random_state,
            optimizer=self.optimizer,
            optimizer__lr=self.optimizer__lr,
            optimizer__momentum=self.optimizer__momentum,
            optimizer__nesterov=True,
            batch_size=-1,
            max_epochs=1,
            train_split=None,
            verbose=False,
        )
        est.initialize()

        self.est_ = est
        self.meta_ = {"num_answers": 0, "model_updates": 0}
        self.initialized_ = True
        self.random_state_ = rng
        #  self.history_: List[Tuple[int, int, int]] = []
        #  self.posterior_ = self.posterior(self.distances(), self.history_)

    @property
    def batch_size(self):
        return self.initial_batch_size

    def partial_fit(self, answers, y=None):
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize()
        # history is only required for the posterior.
        # TODO: reformulate posterior so history isn't required (keep running sum).
        #  self.history_.extend(answers)
        if self.meta_.get("num_answers", 0) >= self.max_eg:
            return self

        num_examples = 0
        if isinstance(answers, list):
            answers = np.array(answers)
        beg_meta = copy(self.meta_)
        incidies = np.arange(len(answers), dtype="int")
        while True:
            bs = self.batch_size

            idx_train = self.random_state_.choice(len(answers), size=bs)
            train_ans = answers[idx_train]
            _ = self.est_.partial_fit(train_ans)

            num_examples += len(train_ans)
            self.meta_["num_answers"] += self.batch_size
            self.meta_["model_updates"] += 1

            cur_eg = self.meta_["num_answers"] - beg_meta["num_answers"]
            if cur_eg >= self.pf_eg:
                break

        return self

    @jit
    def _random_query(self, n):
        while True:
            h = self.random_state_.choice(n)
            o1 = self.random_state_.choice(n)
            o2 = self.random_state_.choice(n)
            if h != o1 and h != o2 and o1 != o2:
                return [h, o1, o2]

    @jit
    def random_queries(self, num=1000):
        n = self.module_kwargs["n"]
        return [self._random_query(n) for _ in prange(num)]

    def distances(self):
        G = gram_utils.gram_matrix(self.embedding)
        return gram_utils.distances(G)

    def score_queries(self, *, num=1000):
        D = self.distances()
        _Q = self.random_queries(num=num)
        Q = np.array(_Q).astype("int64")
        H, O1, O2 = Q[:, 0], Q[:, 1], Q[:, 2]

        #  self.posterior_ = self.posterior(D, self.history_)
        #  scores = score(H, O1, O2, self.posterior_, D, probs=self.probs)
        scores = [0 for _ in range(len(Q))]
        return Q, scores

    def posterior(self, D, S):
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
        gram_utils.assert_distance(D)
        n = D.shape[0]
        tau = np.zeros((n, n))

        # TODO: S is the entire history. Why not calculate this
        # partially?
        for head, w, l in S:
            tau[head] += np.log(self.probs(D[w], D[l]))

        tau = np.exp(tau)
        s = tau.sum(axis=1)  # the sum of each row
        tau = (tau.T / s).T
        return tau

    def probs(self, win2, lose2):
        return self.est_.module_.probs(win2, lose2)

    def score(self, answers, y=None):
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize()
        if self.meta_.get("last_score", 0) >= self.max_eg:
            return self.meta_["last_score"]
        score = self.est_.score(answers)
        self.meta_["last_score"] = score
        return score

    def fit(self, X, y=None):
        raise NotImplementedError

    @property
    def embedding(self):
        return self.est_.module_.embedding.detach().numpy()

class Damper(Embedding):
    def __init__(
        self,
        module,
        module__n=85,
        module__d=85,
        optimizer=None,
        optimizer__lr=None,
        optimizer__momentum=0.9,
        random_state=None,
        initial_batch_size=64,
        max_batch_size=None,
        pf_eg=1000,
        max_eg=30_000,
    ):
        self.max_batch_size = max_batch_size
        super().__init__(
            module=module,
            module__n=module__n,
            module__d=module__d,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            random_state=random_state,
            initial_batch_size=initial_batch_size,
            pf_eg=pf_eg,
            max_eg=max_eg,
        )

    def _set_lr(self, lr):
        opt = self.est_.optimizer_
        for group in opt.param_groups:
            group["lr"] = lr

    @property
    def batch_size(self):
        bs = self.damping()
        self.meta_["batch_size"] = bs
        if self.max_batch_size and bs > self.max_batch_size:
            lr_decay = self.max_batch_size / bs
            new_lr = self.optimizer__lr * lr_decay
            self._set_lr(new_lr)
            self.meta_["lr_"] = new_lr
            self.meta_["batch_size"] = self.max_batch_size
        return self.meta_["batch_size"]

    def damping(self):
        raise NotImplementedError


class PadaDampG(Damper):
    def __init__(
        self,
        module,
        module__n=85,
        module__d=85,
        optimizer=None,
        optimizer__lr=None,
        optimizer__momentum=0.9,
        random_state=None,
        initial_batch_size=64,
        max_batch_size=None,
        dwell=10,
        growth_factor=1.01,
        pf_eg=1000,
        max_eg=30_000,
    ):
        super().__init__(
            module=module,
            module__n=module__n,
            module__d=module__d,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            random_state=random_state,
            initial_batch_size=initial_batch_size,
            max_batch_size=max_batch_size,
            pf_eg=pf_eg,
            max_eg=max_eg,
        )
        self.growth_factor = growth_factor
        self.dwell = dwell

    def damping(self):
        mu = self.meta_["model_updates"]
        if mu % self.dwell == 0:
            pwr = mu / self.dwell
            assert np.allclose(pwr, int(pwr))
            bs = self.initial_batch_size * (self.growth_factor ** (pwr + 1))
            self.meta_["damping"] = int(np.round(bs))
        return self.meta_["damping"]


class GeoDamp(Damper):
    def __init__(
        self,
        module,
        module__n=85,
        module__d=85,
        optimizer=None,
        optimizer__lr=None,
        optimizer__momentum=0.9,
        random_state=None,
        initial_batch_size=64,
        max_batch_size=None,
        dwell=10,
        growth_factor=1.01,
        pf_eg=1000,
        max_eg=30_000,
    ):
        super().__init__(
            module=module,
            module__n=module__n,
            module__d=module__d,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            random_state=random_state,
            initial_batch_size=initial_batch_size,
            max_batch_size=max_batch_size,
            pf_eg=pf_eg,
            max_eg=max_eg,
        )
        self.growth_factor = growth_factor
        self.dwell = dwell

    def damping(self):
        n_eg = self.meta_["num_answers"]
        if n_eg % self.dwell == 0:
            pwr = n_eg / self.dwell
            assert np.allclose(pwr, int(pwr))
            pwr = int(pwr)
            bs = self.initial_batch_size * (self.growth_factor ** (pwr + 1))
            self.meta_["damping"] = int(np.round(bs))
        return self.meta_["damping"]
