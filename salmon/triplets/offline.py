import itertools
import pandas as pd
import numpy as np
from time import time

from sklearn.model_selection import train_test_split
from sklearn.base import BaseEstimator
import torch.optim as optim

from salmon.triplets.algs.adaptive import GD, OGD
from salmon.triplets.algs.adaptive import TSTE


def _get_params(opt_):
    return {
        k: v
        for k, v in opt_.get_params().items()
        if k[-1] != "_"
        and all(ignore not in k for ignore in ["callback", "iterator"])
        and k not in ["optimizer", "module", "criterion", "dataset"]
    }


class OfflineEmbedding(BaseEstimator):
    def __init__(
        self, n=None, d=None, max_epochs=25, opt=None, verbose=10, ident="",
    ):
        self.opt = opt
        self.n = n
        self.d = d
        self.max_epochs = max_epochs
        self.verbose = verbose
        self.ident = ident

    def initialize(self, X_train):
        if self.opt is None:
            assert self.n is not None and self.d is not None, "Specify n and d"
            self.opt = OGD(
                module=TSTE,
                module__n=self.n,
                module__d=self.d,
                random_state=42,
                optimizer=optim.SGD,
                max_epochs=self.max_epochs,
            )
        # TODO: change defaults for Embedding and children
        self.opt.push(X_train)

        self.opt_ = self.opt
        self.history_ = []
        self.initialized_ = True

    def fit(self, X_train, X_test, sample_weight=None, scores=None):
        if sample_weight is not None and scores is not None:
            raise ValueError("Only one of sample_weight or scores can be specified")

        if not (hasattr(self, "initialized_") and self.initialized_):
            self.initialize(X_train)

        astart = self.n * 10
        if scores is not None and len(X_train) > astart:
            if len(scores) != len(X_train):
                msg = "length mismatch; len(scores)={}, len(X_train)={}"
                raise ValueError(msg.format(len(scores), len(X_train)))
            random = scores < -9990
            if random.sum() == 0:
                raise ValueError(
                    "Some random samples are needed to create embedding; "
                    f"got {len(random)} samples but 0 random samples"
                )
            n_active = len(X_train) - random.sum()

            # Larger rate -> later sample are less important
            # Smaller rate -> later samples are more important
            i = np.arange(0, n_active).astype("float32")

            # Number of queries required for random sampling
            required = 10 * self.n * self.d * np.log2(self.n)
            i /= required
            rate = 20

            sample_weight = np.zeros(len(X_train))
            sample_weight[~random] = 1 / (1 + rate * i)
            sample_weight[random] = 1

        _start = time()
        _print_deadline = time() + self.verbose
        for k in itertools.count():
            train_score = self.opt_.score(X_train)
            datum = {
                **self.opt_.meta_,
                "score_train": train_score,
                "k": k,
                "elapsed_time": time() - _start,
                "train_data": len(X_train),
                "test_data": len(X_test),
                "n": self.n,
                "d": self.d,
                "max_epochs": self.max_epochs,
                "verbose": self.verbose,
                "weight": scores is not None,
                "ident": self.ident,
            }
            self.history_.append(datum)
            if k % 5 == 0:
                test_score = self.opt_.score(X_test)
                self.history_[-1]["score_test"] = test_score
            if self.opt_.meta_["num_grad_comps"] >= self.max_epochs * len(X_train):
                break
            if time() >= _print_deadline:
                print(self.history_[-1])
                _print_deadline = time() + self.verbose
            self.opt_.partial_fit(X_train, sample_weight=sample_weight)
        test_score = self.opt_.score(X_test)
        self.history_[-1]["score_test"] = test_score
        return self

    @property
    def embedding_(self):
        return self.opt_.embedding_

    def score(self):
        return self.history_[-1]["score_test"]
