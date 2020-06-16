import itertools
from copy import copy

import torch
import torch.optim as optim
from skorch.net import NeuralNet
from torch.nn.modules.loss import _Loss
from sklearn.base import BaseEstimator
from sklearn.utils import check_random_state
from scipy.special import binom


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
        return (win2 < lose2).numpy().astype("float16").mean().item()


class Reduce(_Loss):
    def forward(self, input: torch.Tensor, target=None) -> torch.Tensor:
        assert self.reduction == "mean"
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
        module_kwargs=None,
        optimizer=None,
        optimizer_kwargs=None,
        random_state=None,
        initial_batch_size=64,
    ):
        self.module = module
        self.module_kwargs = module_kwargs
        self.optimizer = optimizer
        self.optimizer_kwargs = optimizer_kwargs
        self.random_state = random_state
        self.initial_batch_size = initial_batch_size
        super().__init__()

    def _set_seed(self, rng):
        seed = rng.choice(2 ** 31)
        torch.manual_seed(seed)

    def initialize(self):
        mod_kwargs = {f"module__{k}": v for k, v in self.module_kwargs.items()}
        opt_kwargs = {f"optimizer__{k}": v for k, v in self.optimizer_kwargs.items()}

        rng = check_random_state(self.random_state)
        self._set_seed(rng)
        est = _Embedding(
            module=self.module,
            criterion=Reduce,
            **mod_kwargs,
            optimizer=self.optimizer,
            **opt_kwargs,
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

    @property
    def batch_size(self):
        return self.initial_batch_size

    def partial_fit(self, answers, y=None):
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize()

        num_examples = 0
        num_targets = answers.max()
        len_dataset = num_targets * binom(num_targets, 2)
        beginning_meta = copy(self.meta_)
        for k in itertools.count():
            idx = self.random_state_.choice(len(answers), size=self.batch_size)
            train_ans = answers[idx]
            _ = self.est_.partial_fit(train_ans)
            num_examples += self.batch_size
            self.meta_["num_answers"] += self.batch_size
            self.meta_["model_updates"] += 1
            if self._completed(beginning_meta, answers):
                break
        return self

    def _completed(self, beginning_meta, answers):
        mu_diff = self.meta_["model_updates"] - beginning_meta["model_updates"]
        return mu_diff > 50

    def score(self, answers, y=None):
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize()
        return self.est_.score(answers)

    def fit(self, X, y=None):
        raise NotImplementedError

    @property
    def embedding(self):
        return self.est_.module_.embedding.detach().numpy()
