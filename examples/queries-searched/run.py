import collections
import itertools
import pickle
import sys
import zipfile
from copy import copy
from pprint import pprint
from functools import partial
from typing import Any, Dict, Union, List
from toolz.dicttoolz import merge
from joblib import Parallel, delayed
from typing import List
from pathlib import Path
from pprint import pprint

import numpy as np
import pandas as pd
from dask.distributed import Client, as_completed
from sklearn.base import BaseEstimator
from sklearn.model_selection import train_test_split

import salmon.triplets.algs as algs
from salmon.triplets.algs.adaptive._embed import gram_utils
from offline import OfflineSearch

DIR = Path(__file__).absolute().parent
sys.path.append(str(DIR.parent))
from datasets import alien_egg


def _test_dataset(n, n_test, seed=42):
    rng = np.random.RandomState(seed)
    X = rng.choice(n, size=(n_test, 3)).astype("int16")
    repeats = (X[:, 0] == X[:, 1]) | (X[:, 0] == X[:, 2]) | (X[:, 1] == X[:, 2])
    X = X[~repeats]
    # assert len(X) >= 9500
    y = np.array([alien_egg(h, l, r, random_state=38) for (h, l, r) in X])
    return X, y


class Test(BaseEstimator):
    def __init__(
        self,
        noise_model: str = "TSTE",
        n_search: int = None,
        n: int = 600,
        d: int = 1,
        R: int = 10,
        max_queries: int = 60_000,
        n_test: int = 10_000,
        n_partial_fit: int = 100,
        random_state=42,
        dataset: str = "alien_egg",
        write: bool = False,
        queries_per_search: int = 1,
        verbose: Union[int, bool, float] = True,
        noise: bool = False,
        score_factor: int = 1,
    ):
        self.n_search = n_search
        self.n = n
        self.d = d
        self.R = R
        self.max_queries = max_queries
        self.n_test = n_test
        self.n_partial_fit = n_partial_fit
        self.random_state = random_state
        self.dataset = dataset
        self.write = write
        self.queries_per_search = queries_per_search
        self.noise_model = noise_model
        self.verbose = verbose
        self.noise = noise
        self.score_factor = score_factor
        super().__init__()

    def init(self):
        params = {
            "optimizer": "Embedding",
            "optimizer__lr": 0.05,
            "optimizer__momentum": 0.75,
            "random_state": self.random_state,
        }

        Alg = getattr(algs, self.noise_model)
        alg = Alg(n=self.n, d=self.d, R=self.R, **params)
        search = OfflineSearch(
            alg,
            n_search=self.n_search,
            n_partial_fit=self.n_partial_fit,
            dataset=self.dataset,
            queries_per_search=self.queries_per_search,
            noise=self.noise,
            score_factor=self.score_factor,
        )

        static = {
            "n": search.alg.n,
            "d": search.alg.d,
            "R": search.alg.R,
            **self.get_params(deep=False),
            **search.alg.params,
        }

        self.alg_ = alg
        self.search_ = search
        self.static_ = static
        self.params_ = params
        self.initialized_ = True
        self.data_ = []
        return self

    def inited(self):
        inited = hasattr(self, "initialized_") and self.initialized_
        return inited

    def partial_fit(self, X=None, y=None):
        if X is not None and y is not None:
            raise ValueError("Expected X and y to be None")
        if not self.inited():
            self.init()

        self.search_ = self.search_.partial_fit()

    def fit(self, X=None, y=None):
        if X is not None and y is not None:
            raise ValueError("Expected X and y to be None")
        if (
            self.dataset == "zappos"
            and (self.n != 85 or self.n is not None)
            and self.d != 2
        ):
            raise ValueError("Incorrect parameters for self.dataset=zappos")

        if self.dataset == "alien_egg":
            X_test, y_test = _test_dataset(self.n, self.n_test, seed=self.random_state)
        elif self.dataset == "zappos":
            X_test, y_test = self._get_zappos_test_set(), None
        else:
            raise ValueError(f"dataset={self.dataset} not recognized")

        for k in itertools.count():
            self.partial_fit()
            self.score(X_test, y_test)
            iters = (
                int(1 / self.verbose)
                if isinstance(self.verbose, float)
                else int(self.verbose)
            )
            if k % iters == 0:
                pprint(self.data_[-1])
            if self.write:
                df = pd.DataFrame(self.data_)
                fparams = {**self.params_, **self.static_}
                ident = "-".join(
                    [f"{k[:5]}={v}" for k, v in sorted(tuple(fparams.items()))]
                )
                df.to_parquet(f"data/{ident}.parquet")
            if self.search_.alg.meta["num_ans"] >= self.max_queries:
                break

        return self

    def _get_zappos_test_set(self):
        data_dir = DIR.parent / "datasets"
        zappos_data = data_dir / "zappos" / "zappos.csv.zip"
        with zipfile.ZipFile(str(zappos_data), "r") as myzip:
            with myzip.open("zappos.csv", "r") as f:
                responses = pd.read_csv(f, usecols=["head", "b", "c"])
        responses.columns = ["head", "winner", "loser"]

        N = responses["head"].nunique()

        train, test = train_test_split(responses, random_state=42, test_size=0.2)
        #  train_ans = train.to_numpy()
        test_ans = test.to_numpy()
        return test_ans

    def score(self, X, y=None):
        if self.dataset == "alien_egg":
            return self._score_fruit(X, y)
        elif self.dataset == "zappos":
            return self._score_zappos(X)
        raise ValueError(f"dataset={self.dataset} not recognized")

    def _score_zappos(self, queries):
        """
        queries : List[Answer]
            Organized head, winner, loser
        """
        embedding = self.alg_.opt.embedding()
        gram_matrix = gram_utils.gram_matrix(embedding)
        dists = gram_utils.distances(gram_matrix)
        # queries is organized as ["head", "winner", "loser"]
        winner_dists = dists[queries[:, 0], queries[:, 1]]
        loser_dists = dists[queries[:, 0], queries[:, 2]]
        acc = (winner_dists <= loser_dists).mean()

        datum = {
            "acc": acc,
            "embedding_max": embedding.max(),
            "pf_time": self.search_.pf_time_,
            **self.static_,
            **self.search_.alg.meta,
            **self.search_.meta_,
        }
        self.data_.append(datum)
        return acc

    def _score_fruit(self, X, y):
        acc = self.search_.score(X, y)
        e = self.search_.alg.opt.embedding().flatten()
        datum = {
            "acc": acc,
            "embedding_max": e.max(),
            "pf_time": self.search_.pf_time_,
            **self.static_,
            **self.search_.alg.meta,
            **self.search_.meta_,
        }
        if self.d == 1:
            P = [1, 2, 5] + list(range(10, 100, 10)) + [95, 98, 99]
            for factor, name in [(1, ""), (-1, "m1")]:
                ranks = (factor * e).argsort()
                rank_diff = np.abs(ranks - np.arange(len(ranks)))
                rank_data = {
                    f"rank{name}_diff_min": rank_diff.min(),
                    f"rank{name}_diff_median": np.median(rank_diff),
                    f"rank{name}_diff_mean": rank_diff.mean(),
                    f"rank{name}_diff_max": rank_diff.max(),
                    f"rank{name}_incorrect": (rank_diff > 0).sum(),
                }
                percentiles = {
                    f"rank_diff{name}_p{p}": np.percentile(rank_diff, p) for p in P
                }
                datum.update(rank_data)
                datum.update(percentiles)
        assert all(
            isinstance(v, (int, str, float, np.int64, np.int32, np.float32, np.float64))
            for v in datum.values()
        )
        self.data_.append(datum)
        return acc


if __name__ == "__main__":
    import salmon

    assert salmon.__version__ == "v0.4.1+8.geafdca2.dirty"

    queries_per_search = 10
    #  _searches = [[1 * 10 ** i, 2 * 10 ** i, 5 * 10 ** i] for i in range(0, 5 + 1)]
    #  searches: List[int] = sum(_searches, [])
    searches = [1 * 10 ** i for i in range(0, 5 + 1)]
    #  _searches = [[1 * 10 ** i, 3 * 10 ** i] for i in range(0, 5 + 1)]
    #  searches: List[int] = sum(_searches, [])

    searches = [s for s in searches if s >= queries_per_search]
    datasets = ["zappos", "alien_egg"]
    D = [1, 2]
    noises = ["TSTE", "STE", "CKL"]
    factors = [1, -1]

    sddnf = list(itertools.product(searches, datasets, D, noises, factors))
    kwargs: List[Dict[str, Any]] = [
        {
            "n_search": s,
            "dataset": dset,
            "d": d,
            "noise_model": noise,
            "score_factor": sf,
        }
        for s, dset, d, noise, sf in sddnf
        if not (dset == "zappos" and d == 1)
    ]
    print(f"Total of launching {len(kwargs)} jobs")
    print("First 5 kwargs:")
    np.random.shuffle(kwargs)
    pprint(kwargs[:5])

    static = {
        "write": True,
        "queries_per_search": queries_per_search,
        "verbose": 0.10,
        "n_partial_fit": 1,
        "random_state": 139032,
        "noise": True,
        "max_queries": 20_000,
    }
    for kwarg in kwargs:
        if kwarg["dataset"] == "zappos":
            dynamic = {"n": 85}
        else:
            dynamic = {"n": 150}

        kwarg.update(**static, **dynamic)

    #  Test(**kwargs[0]).fit()
    results = Parallel(n_jobs=60, backend="multiprocessing")(
        delayed(Test(**kwarg).fit)() for kwarg in kwargs
    )
