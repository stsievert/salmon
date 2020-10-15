import itertools
import sys
import zipfile
from functools import lru_cache
from typing import Dict, Any
from time import time
from pathlib import Path

import msgpack
from sklearn.utils import check_random_state
import dask.array as da

DIR = Path(__file__).absolute().parent
sys.path.append(str(DIR.parent))

from datasets import strange_fruit


class NoData(Exception):
    pass


class OfflineSearch:
    def __init__(
        self,
        alg,
        n_search=50,
        n_partial_fit=10,
        answers_per_search=4,
        queries_per_search=1,
        random_state=42,
        dataset="strange_fruit",
    ):
        self.alg = alg
        self.n_search = n_search
        self.n_partial_fit = n_partial_fit
        self.answers_per_search = answers_per_search
        self.queries_per_search = queries_per_search
        self.random_state = random_state
        self.dataset = dataset

        self.pf_calls_ = 0
        self.random_state_ = check_random_state(self.random_state)

    def _answer(self, query: Dict[str, Any]) -> Dict[str, Any]:
        assert "winner" not in query
        dataset = self.dataset
        if dataset == "strange_fruit":
            ans = strange_fruit(
                query["head"],
                query["left"],
                query["right"],
                random_state=self.random_state_,
            )
            winner = query["left"] if ans == 0 else query["right"]
            response = {"winner": winner, **query}
            show = {
                "d_left": abs(response["head"] - response["left"]),
                "d_right": abs(response["head"] - response["right"]),
            }
            if response["left"] == response["winner"]:
                show["winner"] = "left"
            elif response["right"] == response["winner"]:
                show["winner"] = "right"
            else:
                raise ValueError(show)
            return response
        elif dataset == "zappos":
            freqs = self._get_zappos_train_freqs()
            h, o1, o2 = query["head"], query["left"], query["right"]
            #  key = bytes(f"{h}-{o1}-{o2}", "ascii")
            key = f"{h}-{o1}-{o2}"
            if key not in freqs:
                raise NoData()
            o1_wins, o2_wins = freqs[key]
            if not o1_wins or not o2_wins:
                raise NoData()
            answers = ([o1] * o1_wins) + ([o2] * o2_wins)
            winner = self.random_state_.choice(answers)
            return {"winner": winner, **query}

        raise ValueError(f"dataset={dataset} not recognized")

    @lru_cache()
    def _get_zappos_train_freqs(self):
        data_dir = DIR.parent / "datasets"
        zappos_data = data_dir / "zappos" / "freqs.msgpack.zip"
        with zipfile.ZipFile(str(zappos_data), "r") as myzip:
            with myzip.open("freqs.msgpack", "r") as f:
                freqs = msgpack.load(f)
        return freqs

    def _partial_fit(self):
        self.pf_calls_ += 1

        # Run this loop if a single query is returned
        # Do one process_answers call
        for k in itertools.count():
            #  if k == 90:
                #  breakpoint()
            if k >= 100:
                raise ValueError("infinite loop?")
            query, score = self.alg.get_query()
            if query is None:
                break
            else:
                try:
                    response = self._answer(query)
                except NoData:
                    continue
                else:
                    self.alg.process_answers([response])
                    return True

        # Run this loop if multiple queries are returned
        # Call process_answers once
        for k in itertools.count():
            if k >= 100:
                raise ValueError("infinite loop?")
            queries, scores = self.alg.get_queries(num=self.n_search)
            assert len(queries) == self.n_search
            responses = []
            N = self.queries_per_search
            #  scores += self.random_state_.uniform(low=0, high=0.1, size=len(scores))
            _scores = da.from_array(scores, chunks=-1)
            top_N_idx = da.argtopk(_scores, k=N).compute()
            top_N_queries = queries[top_N_idx]
            for idx, (h, a, b) in zip(top_N_idx, top_N_queries):
                query = {"head": h, "left": a, "right": b, "score": scores[idx]}
                try:
                    ans = self._answer(query)
                except NoData:
                    pass
                else:
                    responses.append(ans)
            if len(responses):
                break
        self.alg.process_answers(responses)
        return True

    def partial_fit(self, *args, **kwargs):
        for _ in range(self.n_partial_fit):
            _start = time()
            success = self._partial_fit()
            self.pf_time_ = time() - _start
            assert success
        return self

    def score(self, X, y):
        return float(self.alg.score(X, y))
