import itertools
import pandas as pd
import numpy as np
from time import time
from copy import deepcopy

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
        max_epochs=1_000_000,
        opt=None,
        verbose=20,
        ident="",
        noise_model="CKL",
        shuffle=False,
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
                random_state=42 ** 3,
                optimizer=optim.SGD,
                optimizer__lr=0.02,
                optimizer__momentum=0.2,
                max_epochs=self.max_epochs,
                shuffle=self.shuffle,
                optimizer__weight_decay=1e-8,
            )
            kwargs.update(self.kwargs)
            self.opt = OGD(**kwargs)
            # TODO: change defaults for Embedding and children
        self.opt.push(X_train)

        self.opt_ = self.opt
        self.history_ = []
        self.initialized_ = True

    def fit(self, X_train, X_test):
        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize(X_train)

        _start = time()
        _print_deadline = time() + self.verbose
        _n_ans = len(X_train)
        for k in itertools.count():
            train_score = self.opt_.score(X_train)
            module_ = self.opt_.module_
            loss_train = module_.losses(*module_._get_dists(X_train)).mean().item()
            datum = {
                "score_train": train_score,
                "loss_train": loss_train,
                "k": k,
                "elapsed_time": time() - _start,
                "train_data": len(X_train),
                "test_data": len(X_test),
                "n": self.n,
                "d": self.d,
                "max_epochs": self.max_epochs,
                "verbose": self.verbose,
                "ident": self.ident,
                **deepcopy(self.opt_.meta_),
            }
            datum["_epochs"] = datum["num_grad_comps"] / _n_ans
            if k % 20 == 0 or k <= 100:
                with torch.no_grad():
                    test_score = self.opt_.score(X_test)
                    loss_test = module_.losses(*module_._get_dists(X_test))

                datum["score_test"] = test_score
                datum["loss_test"] = loss_test.mean().item()

                self.history_.append(datum)

            if self.opt_.meta_["num_grad_comps"] >= self.max_epochs * len(X_train):
                break
            if time() >= _print_deadline:
                show = {k: _print_fmt(v) for k, v in self.history_[-1].items()}
                print(show)
                _print_deadline = time() + self.verbose
            self.opt_.partial_fit(X_train)

        test_score = self.opt_.score(X_test)
        self.history_[-1]["score_test"] = test_score
        module_ = self.opt_.module_
        loss_test = module_.losses(*module_._get_dists(X_test))
        self.history_[-1]["loss_test"] = loss_test.mean().item()
        return self

    @property
    def embedding_(self):
        return self.opt_.embedding_

    def score(self):
        return self.history_[-1]["score_test"]
