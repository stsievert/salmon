import itertools
import pandas as pd
import numpy as np
from time import time
from copy import deepcopy, copy
from typing import Dict, Union
from numbers import Number

from sklearn.model_selection import train_test_split
from sklearn.base import BaseEstimator
from sklearn.exceptions import NotFittedError
import torch.optim as optim
import torch

from salmon.triplets.algs.adaptive import GD, OGD
from salmon.triplets.algs.adaptive import CKL
import salmon.triplets.algs.adaptive as adaptive


def _get_params(opt_):
    return {
        k: v
        for k, v in opt_.get_params().items()
        if k[-1] != "_"
        and all(ignore not in k for ignore in ["callback", "iterator"])
        and k not in ["optimizer", "module", "criterion", "dataset"]
    }


def _print_fmt(v):
    if isinstance(v, (str, int)):
        return v
    if isinstance(v, (float, np.floating)):
        return f"{v:0.3f}"
    return v


class OfflineEmbedding(BaseEstimator):
    """
    Generate an embedding offline (after responses are downloaded from Salmon).

    Parameters
    ----------
    n : int
        Number of targets.
    d : int
        Embedding dimension
    max_epochs : int
        Number of epochs or passes through the dataset to run for.
    opt : Optional[Optimizer]
    verbose : int
        Interval at which to score.
    random_state : Optional[int]
        Random state for initialization.
    noise_model : str, optional (default: ``SOE``)
        Noise model to optimize over.
    kwargs : dict, optional, default: ``{}``
        Arguments for :class:`~salmon.triplets.offline.OGD`.
        Only used when ``opt is None``.

    """

    def __init__(
        self,
        n=None,
        d=None,
        max_epochs=400_000,
        opt=None,
        verbose=1000,
        ident="",
        noise_model="SOE",
        random_state=None,
        **kwargs,
    ):
        self.opt = opt
        self.n = n
        self.d = d
        self.max_epochs = max_epochs
        self.verbose = verbose
        self.ident = ident
        self.noise_model = noise_model
        self.random_state = random_state
        self.kwargs = kwargs

    @property
    def history_(self):
        """
        The history that's recorded during ``fit``. Available keys include
        ``score_test`` and ``loss_test``.
        """
        if self.initialized_:
            return self._history_
        raise NotFittedError(
            "No history has been recorded because ``initialize`` has not been called"
        )

    @property
    def meta_(self):
        """
        Meta-information about this estimator. Available keys include
        ``score_train`` and ``loss_train``.
        """
        return self._meta

    @property
    def embedding_(self):
        """
        The current embedding. If there are ``n`` objects being embedded into
        ``d`` dimensions, then ``embedding_.shape == (n, d)``.
        """
        return self.opt_.embedding_

    def initialize(self, X_train):
        """
        Initialize this optimizer.

        Parameters
        ----------
        X_train : np.ndarray
            Responses organized to be [head, winner, loser].

        """
        if self.opt is None:
            assert self.n is not None and self.d is not None, "Specify n and d"
            noise_model = getattr(adaptive, self.noise_model)
            kwargs = dict(
                module=noise_model,
                module__n=self.n,
                module__d=self.d,
                module__random_state=self.random_state,
                optimizer=optim.Adadelta,
                max_epochs=self.max_epochs,
            )
            kwargs.update(self.kwargs)
            self.opt = OGD(**kwargs)
            # TODO: change defaults for Embedding and children
        self.opt.push(X_train)
        self._meta: Dict[str, Number] = {"pf_calls": 0}

        self.opt_ = self.opt
        self._history_ = []
        self.initialized_ = True
        return self

    def partial_fit(self, X_train):
        """
        Fit this optimizer for (approximately) one pass through the training data.

        Parameters
        ----------
        X_train : array-like
            The responses with shape ``(n_questions, 3)``.
            Each question is organized as ``[head, winner, loser]``.

        """
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize(X_train)

        self._partial_fit(X_train)
        return self

    def fit(self, X_train, X_test):
        """
        Fit the embedding with train and validation data.

        Parameters
        ----------
        X_train : array-like
            Data to fit the embedding too.

            The responses with shape ``(n_questions, 3)``.
            Each question is organized as ``[head, winner, loser]``.

        X_test : array-like
            Data to score the embedding on

            The responses with shape ``(n_questions, 3)``.
            Each question is organized as ``[head, winner, loser]``.
        """
        self.initialize(X_train)
        self._meta["pf_calls"] = 0
        _start = time()
        for k in itertools.count():
            self._partial_fit(X_train)
            if self.verbose and k == 0:
                print(self.opt_.optimizer, self.opt_.get_params())
            if self.opt_.meta_["num_grad_comps"] >= self.max_epochs * len(X_train):
                break

            if (
                (self.verbose and k % self.verbose == 0)
                or abs(self.max_epochs - k) <= 10
                or k <= 100
            ):
                datum = deepcopy(self._meta)
                datum.update(self.opt_.meta_)
                test_score, loss_test = self._score(X_test)
                datum["score_test"] = test_score
                datum["loss_test"] = loss_test
                keys = ["ident", "score_test", "train_data", "max_epochs", "_epochs"]
                datum["_elapsed_time"] = time() - _start
                show = {k: _print_fmt(datum[k]) for k in keys}
                self._history_.append(datum)
            if self.verbose and k % self.verbose == 0:
                print(show)

        test_score, loss_test = self._score(X_test)
        self._history_[-1]["score_test"] = test_score
        self._history_[-1]["loss_test"] = loss_test
        return self

    def _score(self, X):
        module_ = self.opt_.module_
        with torch.no_grad():
            score = self.opt_.score(X)
            loss = module_.losses(*module_._get_dists(X))
        return score, float(loss.mean().item())

    def _partial_fit(self, X_train):
        _start = time()
        _n_ans = len(X_train)
        k = deepcopy(self._meta["pf_calls"])

        self.opt_.partial_fit(X_train)
        self._meta["pf_calls"] += 1
        self._meta.update(deepcopy(self.opt_.meta_))

        train_score = self.opt_.score(X_train)
        module_ = self.opt_.module_
        loss_train = module_.losses(*module_._get_dists(X_train)).mean().item()

        prev_time = 0
        if len(self._history_):
            prev_time = self._history_[-1]["elapsed_time"]

        datum = {
            "score_train": train_score,
            "loss_train": loss_train,
            "k": k,
            "elapsed_time": time() - _start + prev_time,
            "train_data": len(X_train),
            "n": self.n,
            "d": self.d,
            "max_epochs": self.max_epochs,
            "verbose": self.verbose,
            "ident": self.ident,
        }
        datum["_epochs"] = self._meta["num_grad_comps"] / len(X_train)
        self._meta.update(datum)

        return self

    def score(self, X):
        """
        Score the responses against the current embedding. Record the loss and accuracy, and return the accuracy.

        Parameters
        ----------
        X : array-like

            The responses to score against the current embedding.

            The responses with shape ``(n_questions, 3)``.
            Each question is organized as ``[head, winner, loser]``.
        """
        acc, loss = self._score(X)
        self._meta["score__acc"] = acc
        self._meta["score__loss"] = loss
        return acc
