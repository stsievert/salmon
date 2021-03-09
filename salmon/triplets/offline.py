import itertools
import pandas as pd
import numpy as np
from time import time
from copy import deepcopy, copy
from typing import Dict, Union
from numbers import Number

from sklearn.model_selection import train_test_split
from sklearn.base import BaseEstimator
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
    def __init__(
        self,
        n=None,
        d=None,
        max_epochs=100_000,
        opt=None,
        verbose=20,
        ident="",
        noise_model="CKL",
        shuffle=True,
        **kwargs,
    ):
        self.opt = opt
        self.n = n
        self.d = d
        self.max_epochs = max_epochs
        self.verbose = verbose
        self.ident = ident
        self.noise_model = noise_model
        self.shuffle = shuffle
        self.kwargs = kwargs

    def initialize(self, X_train):
        if self.opt is None:
            assert self.n is not None and self.d is not None, "Specify n and d"
            noise_model = getattr(adaptive, self.noise_model)
            kwargs = dict(
                module=noise_model,
                module__n=self.n,
                module__d=self.d,
                optimizer=optim.Adadelta,
                max_epochs=self.max_epochs,
                shuffle=self.shuffle,
            )
            kwargs.update(self.kwargs)
            self.opt = OGD(**kwargs)
            # TODO: change defaults for Embedding and children
        self.opt.push(X_train)
        self._meta: Dict[str, Number] = {"pf_calls": 0}

        self.opt_ = self.opt
        self.history_ = []
        self.initialized_ = True

    def partial_fit(self, X_train):
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize(X_train)

        self._partial_fit(X_train)
        return self

    def fit(self, X_train, X_test):
        self.initialize(X_train)
        self._meta["pf_calls"] = 0
        _start = time()
        for k in itertools.count():
            self._partial_fit(X_train)
            if self.verbose and k == 0:
                print(self.opt_.optimizer, self.opt_.get_params())
            if self.opt_.meta_["num_grad_comps"] >= self.max_epochs * len(X_train):
                break

            if k % 20 == 0 or abs(self.max_epochs - k) <= 10 or k <= 100:
                datum = deepcopy(self._meta)
                datum.update(self.opt_.meta_)
                test_score, loss_test = self._score(X_test)
                datum["score_test"] = test_score
                datum["loss_test"] = loss_test
                keys = ["ident", "score_test", "train_data", "max_epochs", "_epochs"]
                datum["_elapsed_time"] = time() - _start
                show = {k: _print_fmt(datum[k]) for k in keys}
                self.history_.append(datum)
            if self.verbose and k % self.verbose == 0:
                print(show)

        test_score, loss_test = self._score(X_test)
        self.history_[-1]["score_test"] = test_score
        self.history_[-1]["loss_test"] = loss_test
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
        if len(self.history_):
            prev_time = self.history_[-1]["elapsed_time"]

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

    @property
    def embedding_(self):
        return self.opt_.embedding_

    def score(self, X):
        acc, loss = self._score(X)
        self._meta["score__acc"] = acc
        self._meta["score__loss"] = loss
        return acc
