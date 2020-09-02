"""
This script runs a simulation with the Salmon server launched at SALMON.

It does the following:

* Uses the strange fruit dataset
* Pings the API to get query, answers, then sends the answer
* Every $n$ targets, it gets the embedding and computed the accuracy/etc.

Stats to record include accuracy and distances to nearest neighbor (median, mean, etc).
"""

import asyncio
from pathlib import Path
import sys
import httpx
from sklearn.base import BaseEstimator
from sklearn.utils import check_random_state
import yaml
import httpx

DIR = Path(__file__).absolute().parent
sys.path.append(str(DIR.parent))
import datasets


SALMON = "http://localhost:8421"


class SalmonExperiment(BaseEstimator):
    def __init__(self, salmon=SALMON, dataset="strange_fruit", n=200, d=2, random_state=None):
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
            httpx.post(self.salmon + "/init_exp", data={"exp": yaml.dump(init)}, auth=("username", "password"))
        else:
            raise ValueError(f"dataset={dataset} not recognized")
        return self


class User(BaseEstimator):
    def __init__(self, salmon=SALMON, n_responses=100, response_time=1, random_state=None, http=None):
        self.salmon = salmon
        self.response_time = response_time
        self.n_responses = n_responses
        self.random_state = random_state
        self.http = http

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
            _ans = datasets.strange_fruit(query["head"], query["left"], query["right"], random_state=self.random_state_)
            winner = query["left"] if _ans == 0 else query["right"]
            answer = {"winner": winner, **query}
            # print(answer)
            sleep_time = self.random_state_.normal(loc=self.response_time, scale=0.25)
            sleep_time = max(0.75, sleep_time)
            print(sleep_time)
            await asyncio.sleep(self.response_time)
            await self.http.post(self.salmon + "/answer", data=answer)
        return self

    def partial_fit(self, X=None, y=None):
        return self._partial_fit(X=X, y=y)



async def main(**config):
    kwargs = {k: config[k] for k in ["random_state", "dataset", "n", "d"]}
    exp = SalmonExperiment(**kwargs).init()

    async with httpx.AsyncClient() as client:
        users = [User(http=client, random_state=i) for i in range(config["n_users"])]
        responses = [user.partial_fit() for user in users]
        await asyncio.gather(*responses)

if __name__ == "__main__":
    config = {"n_users": 20, "n": 200, "d": 2, "dataset": "strange_fruit", "random_state": 42}
    asyncio.run(main(**config))

