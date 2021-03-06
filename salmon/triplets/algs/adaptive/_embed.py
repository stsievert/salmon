import itertools
from copy import copy
from typing import List, Tuple, Union

import numpy as np
import torch
import torch.optim as optim
from numba import jit, prange
from skorch.net import NeuralNet
from skorch.dataset import Dataset as SkorchDataset
from torch.nn.modules.loss import _Loss
from torch.utils.data import TensorDataset

from sklearn.base import BaseEstimator
from sklearn.utils import check_random_state
from scipy.special import binom
from skorch.utils import is_dataset

from salmon.utils import get_logger

logger = get_logger(__name__)

from .search import gram_utils, score


class Reduce:
    def __call__(self, input: torch.Tensor, target=None) -> torch.Tensor:
        return torch.sum(input)


class NumpyDataset(SkorchDataset):
    def transform(self, X, y):
        return X, torch.from_numpy(np.array([0])) if y is None else y


class Embedding(BaseEstimator):
    """
    An triplet embedding algorithm.
    """

    def __init__(
        self,
        module,
        module__n: int = 85,
        module__d: int = 2,
        optimizer=optim.SGD,
        optimizer__lr=0.04,
        optimizer__momentum=0.9,
        random_state=None,
        warm_start=True,
        max_epochs=100,
        initial_batch_size=512,
        **kwargs,
    ):
        self.module = module
        self.module__n = module__n
        self.module__d = module__d
        self.optimizer = optimizer
        self.optimizer__lr = optimizer__lr
        self.optimizer__momentum = optimizer__momentum
        self.random_state = random_state
        self.warm_start = warm_start
        self.max_epochs = max_epochs
        self.initial_batch_size = initial_batch_size
        self.kwargs = kwargs

    def initialize(self):
        self.meta_ = {"num_answers": 0, "model_updates": 0, "num_grad_comps": 0}
        self.initialized_ = True
        self.random_state_ = check_random_state(self.random_state)
        self.answers_ = np.zeros((1000, 3), dtype="uint16")

        self.net_ = NeuralNet(
            module=self.module,
            module__n=self.module__n,
            module__d=self.module__d,
            module__random_state=self.random_state,
            optimizer=self.optimizer,
            optimizer__lr=self.optimizer__lr,
            optimizer__momentum=self.optimizer__momentum,
            warm_start=self.warm_start,
            **self.kwargs,
            criterion=Reduce,
            verbose=False,
            batch_size=-1,
            max_epochs=self.max_epochs,
            optimizer__nesterov=True,
            train_split=None,
            dataset=NumpyDataset,
        ).initialize()

    # def converged(self):
    #     answers = self.answers_[: self.meta_["num_answers"]]
    #     self.optimizer_.zero_grad()
    #     losses = self.module_.forward(answers)
    #     loss = losses.mean()
    #     loss.backward()
    #     G = self.module_._embedding.grad.detach().numpy().copy()
    #     self.optimizer_.zero_grad()

    #     n, d = G.shape

    #     grad_norms2 = (G ** 2).sum(axis=0)  # Forbenius norm squared
    #     assert grad_norms2.shape == (n, 1)

    #     max_grad_norm2 = grad_norms2.max()
    #     avg_grad_norm2 = grad_norms2.mean()

    #     grad_error = np.sqrt(max_grad_norm2 / avg_grad_norm2)
    #     return grad_error < self.epsilon

    def push(self, answers: Union[list, np.ndarray]):
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize()
        if isinstance(answers, list):
            answers = (
                np.array(answers) if len(answers) else np.empty((0, 3), dtype="uint16")
            )
        num_ans = copy(self.meta_["num_answers"])

        if num_ans + len(answers) >= len(self.answers_):
            n = len(answers) + len(self.answers_)
            new_ans = np.zeros((n, 3), dtype="uint16")
            self.answers_ = np.vstack((self.answers_, new_ans))
        self.answers_[num_ans : num_ans + len(answers)] = answers

        self.meta_["answers_bytes"] = self.answers_.nbytes
        self.meta_["num_answers"] += len(answers)
        return self.answers_.nbytes

    def partial_fit(self, answers, sample_weight=None):
        """
        Process the provided answers.

        Parameters
        ----------
        anwers : array-like
            The answers, with shape (num_ans, 3). Each row is
            [head, winner, loser].

        Returns
        -------
        self

        Notes
        -----
        This function runs one iteration of SGD.

        This impure function modifies

            * ``self.meta_`` keys ``model_updates`` and ``num_grad_comps``
            * ``self.module_``, the embedding.
        """
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize()
        if not isinstance(answers, np.ndarray):
            answers = np.array(answers, dtype="uint16")

        if self.meta_["num_answers"] <= self.module__n:
            return self

        beg_meta = copy(self.meta_)
        eg_deadline = copy(len(answers) + beg_meta["num_grad_comps"])

        if sample_weight is not None:
            sample_weight = torch.from_numpy(sample_weight)
        while True:
            idx_train = self.get_train_idx(self.meta_["num_answers"])
            train_ans = torch.from_numpy(answers[idx_train].astype("int64"))
            losses = self.module_.forward(train_ans)

            if sample_weight is not None:
                losses *= sample_weight[idx_train]

            self.optimizer_.zero_grad()
            loss = losses.mean()
            loss.backward()
            self.optimizer_.step()
            self.optimizer_.zero_grad()
            with torch.no_grad():
                self._project_onto_ball()
            self.optimizer_.zero_grad()

            self.meta_["num_grad_comps"] += len(train_ans)
            self.meta_["model_updates"] += 1
            logger.info("%s", self.meta_)
            if self.meta_["num_grad_comps"] >= eg_deadline:
                del loss, losses
                break
        return self

    def _project_onto_ball(self):
        norms = torch.norm(self.module_._embedding, dim=1)
        max_norm = 10 * self.module__d
        idx = norms > max_norm
        if idx.sum():
            factor = max_norm / norms[idx]
            d = self.module_._embedding.shape[1]
            if d == 1:
                factor = factor.reshape(-1, 1)
            else:
                factor = torch.stack((factor,) * d).T
            self.module_._embedding[idx] *= factor
        return True

    def score(self, answers, y=None) -> float:
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize()
        score = self._score(answers)
        self.meta_["last_score"] = score
        return score

    def _score(self, answers, y=None):
        win2, lose2 = self.module_._get_dists(answers)
        acc = (win2 < lose2).numpy().astype("float32").mean().item()
        return acc

    def fit(self, X, y=None):
        if not self.warm_start:
            msg = "Only warm_start=True is accepted, not warm_start={}"
            raise ValueError(msg.format(self.warm_start))
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize()
        for epoch in range(self.max_epochs):
            n_ans = copy(self.meta_["num_answers"])
            self.partial_fit(self.answers_[:n_ans])
        return self

    def embedding(self) -> np.ndarray:
        return self.net_.module_._embedding.detach().numpy()

    @property
    def embedding_(self) -> np.ndarray:
        return self.embedding()

    @property
    def module_(self) -> np.ndarray:
        return self.net_.module_

    @property
    def optimizer_(self) -> np.ndarray:
        return self.net_.optimizer_

    def get_train_idx(self, n_ans):
        bs = min(n_ans, self.initial_batch_size)
        idx = self.random_state_.choice(n_ans, replace=False, size=bs)
        return idx


class GD(Embedding):
    def get_train_idx(self, n_ans):
        return np.arange(n_ans).astype(int)


class OGD(Embedding):
    def get_train_idx(self, n_ans):
        bs = self.initial_batch_size + 4 * (self.meta_["model_updates"] + 1)
        return self.random_state_.choice(
            n_ans, size=min(bs, n_ans), replace=False
        ).astype(int)


class Damper(Embedding):
    def __init__(
        self,
        module,
        module__n=85,
        module__d=2,
        optimizer=None,
        optimizer__lr=None,
        optimizer__momentum=0.9,
        random_state=None,
        initial_batch_size=64,
        max_batch_size=None,
        **kwargs,
    ):
        self.initial_batch_size = initial_batch_size
        self.max_batch_size = max_batch_size
        super().__init__(
            module=module,
            module__n=module__n,
            module__d=module__d,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            random_state=random_state,
            **kwargs,
        )

    def get_train_idx(self, len_ans):
        bs = self.batch_size_
        idx_train = self.random_state_.choice(len_ans, size=bs)
        return idx_train

    def initialize(self):
        r = super().initialize()
        if hasattr(self, "max_batch_size"):
            self.max_batch_size_ = self.max_batch_size or 10 * self.module__n
        return r

    def _set_lr(self, lr):
        opt = self.optimizer_
        for group in opt.param_groups:
            group["lr"] = lr

    @property
    def batch_size_(self):
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


class LRDamper(Damper):
    def __init__(
        self,
        module,
        module__n=85,
        module__d=2,
        optimizer=None,
        optimizer__lr=None,
        optimizer__momentum=0.9,
        random_state=None,
        initial_batch_size=128,
        max_batch_size=None,
        **kwargs,
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
            **kwargs,
        )

        self.initial_batch_size = initial_batch_size
        self.max_batch_size = max_batch_size


class CntsLRDamper(LRDamper):
    """
    Decays the learning rate like 1 / (1 + mu) like Thm. 4.7 of [1]_.

    References
    ----------
    1. Bottou, L. A. C., Frank E and Nocedal, Jorge. (2018).
       Optimization methods for large-scale machine learning.
       SIAM Review, 60, 223-223. Retrieved from https://arxiv.org/abs/1606.04838
    """

    def __init__(self, *args, rate=0.05, **kwargs):
        self.rate = rate
        super().__init__(*args, **kwargs)

    def damping(self):
        mu = self.meta_["model_updates"]
        damping = int(self.initial_batch_size * (1 + self.rate * mu))
        self.meta_["damping"] = damping
        return damping


class PadaDampG(Damper):
    def __init__(
        self,
        module,
        module__n=85,
        module__d=2,
        optimizer=None,
        optimizer__lr=None,
        optimizer__momentum=0.9,
        random_state=None,
        initial_batch_size=64,
        max_batch_size=None,
        growth_factor=1.01,
        dwell=10,
        **kwargs,
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
            **kwargs,
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
        module__d=2,
        optimizer=None,
        optimizer__lr=None,
        optimizer__momentum=0.9,
        random_state=None,
        initial_batch_size=64,
        max_batch_size=None,
        dwell=10,
        growth_factor=1.01,
        **kwargs,
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
            **kwargs,
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
