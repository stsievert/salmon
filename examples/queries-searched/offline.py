import sys
from time import time
from pathlib import Path

from sklearn.utils import check_random_state

sys.path.append(str(Path(__file__).absolute().parent.parent))

from datasets import strange_fruit


class OfflineSearch:
    def __init__(
        self,
        alg,
        n_search=50,
        n_partial_fit=10,
        answers_per_search=4,
        queries_per_search=4,
        random_state=42,
    ):
        self.alg = alg
        self.n_search = n_search
        self.n_partial_fit = n_partial_fit
        self.answers_per_search = answers_per_search
        self.queries_per_search = queries_per_search
        self.random_state = random_state

        self.pf_calls_ = 0
        self.random_state_ = check_random_state(self.random_state)

    def _answer(self, query):
        ans = strange_fruit(
            query["head"], query["left"], query["right"], rng=self.random_state_
        )
        winner = query["left"] if ans == 0 else query["right"]
        response = {"winner": winner, **query}
        return response

    def _partial_fit(self):
        self.pf_calls_ += 1
        query, score = self.alg.get_query()
        if query is not None:
            response = self._answer(query)
            self.alg.process_answers([response])
            return True

        queries, scores = self.alg.get_queries(num=self.n_search)
        assert len(queries) == self.n_search
        responses = []
        N = self.queries_per_search
        top_N_idx = scores.argsort()
        top_N_queries = queries[top_N_idx[-N:]]
        for h, a, b in top_N_queries:
            query = {"head": h, "left": a, "right": b, "score": scores.max()}
            responses.append(self._answer(query))
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
