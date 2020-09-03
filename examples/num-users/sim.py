"""
This script runs a simulation with the Salmon server launched at SALMON.

It does the following:

* Uses the strange fruit dataset
* Pings the API to get query, answers, then sends the answer
* Every $n$ targets, it gets the embedding and computed the accuracy/etc.

Stats to record include accuracy and distances to nearest neighbor (median, mean, etc).
"""

import asyncio
import sys
from pathlib import Path
from time import time
from typing import Optional, Tuple, Union

import httpx
import numpy as np
import pandas as pd
import yaml
from scipy.spatial import distance_matrix
from sklearn.base import BaseEstimator
from sklearn.utils import check_random_state

from salmon.triplets.algs import TSTE

DIR = Path(__file__).absolute().parent
sys.path.append(str(DIR.parent))
import datasets

sys.path.append(str(DIR.parent / "queries-searched"))
from run import _test_dataset

SALMON = "http://localhost:8421"


class SalmonExperiment(BaseEstimator):
    def __init__(
        self, salmon=SALMON, dataset="strange_fruit", n=200, d=2, random_state=None
    ):
        self.salmon = salmon
        self.dataset = dataset
        self.n = n
        self.d = d
        self.random_state = random_state

    def init(self):
        self.random_state_ = check_random_state(self.random_state)
        if self.dataset == "strange_fruit":
            init = {
                "d": self.d,
                "samplers": {"TSTE": {"alpha": 1, "random_state": self.random_state}},
                "targets": list(range(self.n)),
            }
            httpx.post(
                self.salmon + "/init_exp",
                data={"exp": yaml.dump(init)},
                auth=("username", "password"),
            )
        else:
            raise ValueError(f"dataset={self.dataset} not recognized")

        self.config = init
        return self


class User(BaseEstimator):
    def __init__(
        self,
        salmon=SALMON,
        n_responses=100,
        response_time=1,
        random_state=None,
        http=None,
        uid="",
    ):
        self.salmon = salmon
        self.response_time = response_time
        self.n_responses = n_responses
        self.random_state = random_state
        self.http = http
        self.uid = uid

    def init(self):
        self.initialized_ = True
        self.random_state_ = check_random_state(self.random_state)
        return self

    async def _partial_fit(self, X=None, y=None):
        if not hasattr(self, "initialized_") or not self.initialized_:
            self.init()

        for _ in range(self.n_responses):
            response = await self.http.get(self.salmon + "/query")
            query = response.json()
            _ans = datasets.strange_fruit(
                query["head"],
                query["left"],
                query["right"],
                random_state=self.random_state_,
            )
            winner = query["left"] if _ans == 0 else query["right"]
            sleep_time = self.random_state_.normal(loc=self.response_time, scale=0.25)
            sleep_time = max(0.75, sleep_time)
            answer = {
                "winner": winner,
                "puid": self.uid,
                "response_time": sleep_time,
                **query,
            }
            await asyncio.sleep(self.response_time)
            await self.http.post(self.salmon + "/answer", data=answer)
        return self

    def partial_fit(self, X=None, y=None):
        return self._partial_fit(X=X, y=y)


class Stats:
    def __init__(
        self,
        X,
        y,
        *,
        sampler,
        config=None,
        fname="stats.parquet",
        http=None,
        salmon=SALMON,
    ):
        self.sampler = sampler
        self.salmon = salmon
        self.http = http
        self.fname = fname
        self.history_ = []
        self.config = config
        self.X = X
        self.y = y

    async def collect(self):
        response = await self.http.get(self.salmon + f"/model/{self.sampler}")
        stats = response.json()
        stats["time"] = time()
        embedding = np.asarray(stats.pop("embedding"))
        accuracy = self._get_acc(embedding)
        nn_acc, nn_diffs = self._get_nn_diffs(embedding)

        diff_stats = {
            "nn_diff_p{k}": np.percentile(nn_diffs, k)
            for k in [99, 95, 90, 80, 70, 60, 50, 40, 30, 20, 10, 5, 1]
        }

        r = await self.http.get(self.salmon + f"/responses")
        responses = r.json()

        return {
            "accuracy": accuracy,
            "nn_diff_median": np.median(nn_diffs),
            "nn_diff_mean": nn_diffs.mean(),
            "nn_acc": nn_acc,
            "responses": responses,
            **diff_stats,
            **stats,
        }

    def _get_acc(self, embedding) -> float:
        alg = TSTE(self.config["n"], self.config["d"])
        y_hat = alg.predict(self.X, embedding=embedding)
        acc = (self.y == y_hat).mean()
        return acc

    def _get_nn_diffs(self, embedding) -> Tuple[float, np.ndarray]:
        dists = distance_matrix(embedding, embedding)
        dists[dists <= 0] = np.inf
        neighbors = dists.argmin(axis=1)
        neighbor_dists = np.abs(neighbors - np.arange(len(neighbors)))
        nn_acc = (neighbor_dists == 1).mean()
        return nn_acc, neighbor_dists

    async def run_until(self, event):
        while True:
            deadline = time() + 5
            datum = await self.collect()
            self.history_.append(datum)
            pd.DataFrame(self.history_).to_parquet(self.fname, index=False)
            if event.is_set():
                return self.history_
            while time() < deadline:
                await asyncio.sleep(0.1)


async def main(**config):
    kwargs = {k: config[k] for k in ["random_state", "dataset", "n", "d"]}
    exp = SalmonExperiment(**kwargs).init()

    X, y = _test_dataset(config["n"], config["n_test"])
    n_responses = (config["n_users"] // config["max_queries"]) + 1

    async with httpx.AsyncClient() as client:
        users = [
            User(http=client, random_state=i, uid=str(i), n_responses=n_responses)
            for i in range(config["n_users"])
        ]
        responses = [user.partial_fit() for user in users]
        completed = asyncio.Event()
        algs = list(exp.config["samplers"].keys())
        assert len(algs) == 1
        stats = Stats(X, y, config=config, sampler=algs[0], http=client)
        task = asyncio.create_task(stats.run_until(completed))
        await asyncio.gather(*responses)
        completed.set()
        while not task.done():
            await asyncio.sleep(0.1)
        history = task.result()
    return history


if __name__ == "__main__":
    config = {
        "n_users": 1,
        "max_queries": 4,
        "n": 200,
        "d": 2,
        "dataset": "strange_fruit",
        "random_state": 42,
        "n_test": 10_000,
    }
    asyncio.run(main(**config))
