import collections
from copy import copy
import itertools
import pickle
import sys
from pprint import pprint
from functools import partial
from typing import Any, Dict
from toolz.dicttoolz import merge
from joblib import Parallel, delayed

import numpy as np
import pandas as pd
from dask.distributed import Client, as_completed

from salmon.triplets.algs import TSTE
from offline import OfflineSearch
from datasets import strange_fruit


def _test_dataset(n, n_test, seed=42):
    rng = np.random.RandomState(seed)
    X = rng.choice(n, size=(n_test, 3)).astype("int16")
    repeats = (X[:, 0] == X[:, 1]) | (X[:, 0] == X[:, 2]) | (X[:, 1] == X[:, 2])
    X = X[~repeats]
    # assert len(X) >= 9500
    y = np.array([strange_fruit(h, l, r) for (h, l, r) in X])
    return X, y


def run(n_search, *, n=600, d=1, max_queries=60_000, n_test=10_000, n_partial_fit=100):
    params = {
        "optimizer": "Embedding",
        "optimizer__lr": 0.10,
        "optimizer__momentum": 0.75,
        "random_state": 10023,
    }

    alg = TSTE(n=n, d=d, **params)
    search = OfflineSearch(alg, n_search=n_search, n_partial_fit=n_partial_fit)

    static = {
        "n": search.alg.n,
        "d": search.alg.d,
        "R": search.alg.R,
        "n_search": n_search,
        "max_queries": max_queries,
        "n_test": n_test,
        "n_partial_fit": n_partial_fit,
        **search.alg.params,
    }

    X, y = _test_dataset(static["n"], static["n_test"], seed=42)
    data = []
    for k in itertools.count():
        search = search.partial_fit()
        acc = search.score(X, y)
        e = search.alg.opt.embedding().flatten()
        ranks = e.argsort()
        rank_diff = np.abs(ranks - np.arange(len(ranks)))
        datum = {
            "acc": acc,
            "embedding_max": e.max(),
            "pf_time": search.pf_time_,
            "rank_diff_mean": rank_diff.mean(),
            "rank_diff_median": np.median(rank_diff),
            "rank_diff_max": rank_diff.max(),
            "rank_diff_p95": np.percentile(rank_diff, 95),
            "rank_diff_p90": np.percentile(rank_diff, 90),
            "rank_diff_p80": np.percentile(rank_diff, 80),
            "rank_diff_p70": np.percentile(rank_diff, 70),
            "rank_diff_p60": np.percentile(rank_diff, 60),
            **static,
            **search.alg.meta,
        }
        assert all(
            isinstance(v, (int, str, float, np.int64, np.int32, np.float32, np.float64))
            for v in datum.values()
        )
        data.append(datum)
        if k % 1 == 0:
            pprint({k: v for k, v in data[-1].items() if k != "sizeof"})
            df = pd.DataFrame(data)
            fparams = {**params, **static}
            ident = "-".join([f"{k}={v}" for k, v in sorted(tuple(fparams.items()))])
            df.to_parquet(f"data/{ident}.parquet")
        if search.alg.meta["num_ans"] >= max_queries:
            break

    return data, {**params, **static}


if __name__ == "__main__":

    config = {"max_queries": 50_000, "n": 600, "d": 1, "n_test": 10_000}
    assert "n_search" not in config

    searches = [[1 * 10 ** i, 2 * 10 ** i, 5 * 10 ** i] for i in range(1, 6 + 1)]
    search = sum(searches, [])
    results = Parallel(n_jobs=-1, backend="loky")(
        delayed(run)(s, **config) for s in search
    )
