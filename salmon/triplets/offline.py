import itertools
import pandas as pd
import numpy as np
from time import time
from copy import deepcopy

from sklearn.model_selection import train_test_split
from sklearn.base import BaseEstimator
import torch.optim as optim

from salmon.triplets.algs.adaptive import GD, OGD
from salmon.triplets.algs.adaptive import TSTE, GNMDS
import salmon.triplets.algs.adaptive as adaptive


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
        self,
        n=None,
        d=None,
        max_epochs=25,
        opt=None,
        verbose=20,
        ident="",
        noise_model="GNMDS",
        shuffle=False,
    ):
        self.opt = opt
        self.n = n
        self.d = d
        self.max_epochs = max_epochs
        self.verbose = verbose
        self.ident = ident
        self.noise_model = noise_model
        self.shuffle = shuffle

    def initialize(self, X_train):
        if self.opt is None:
            assert self.n is not None and self.d is not None, "Specify n and d"
            noise_model = getattr(adaptive, self.noise_model)
            self.opt = OGD(
                module=noise_model,
                module__n=self.n,
                module__d=self.d,
                random_state=42 ** 2,
                optimizer=optim.SGD,
                optimizer__lr=0.1,
                optimizer__momentum=0.9,
                max_epochs=self.max_epochs,
                shuffle=self.shuffle,
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

            # divide by mean so 1 on average -> same step size in optimization
            sample_weight /= sample_weight.mean()

        _start = time()
        _print_deadline = time() + self.verbose
        for k in itertools.count():
            train_score = self.opt_.score(X_train)
            module_ = self.opt_.module_
            loss_train = module_.losses(*module_._get_dists(X_train)).mean().item()
            datum = {
                "score_train": train_score,
                "loss_train": loss_train,
                "k": k,
                #  "elapsed_time": time() - _start,
                #  "train_data": len(X_train),
                #  "test_data": len(X_test),
                #  "n": self.n,
                #  "d": self.d,
                #  "max_epochs": self.max_epochs,
                #  "verbose": self.verbose,
                "weight": scores is not None,
                "ident": self.ident,
                **deepcopy(self.opt_.meta_),
            }
            if k % 10 == 0 or k <= 100:
                self.history_.append(datum)
                test_score = self.opt_.score(X_test)
                self.history_[-1]["score_test"] = test_score
                loss_test = module_.losses(*module_._get_dists(X_test))
                self.history_[-1]["loss_test"] = loss_test.mean().item()
            if self.opt_.meta_["num_grad_comps"] >= self.max_epochs * len(X_train):
                break
            if time() >= _print_deadline:
                print(self.history_[-1])
                _print_deadline = time() + self.verbose
            self.opt_.partial_fit(X_train, sample_weight=sample_weight)

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
