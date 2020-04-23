import numpy as np
from sklearn.utils import check_random_state
from typing import Tuple, List

from .utils import Query, Answer, Runner


def _get_query(n, random_state=None) -> Tuple[int, Tuple[int, int]]:
    random_state = check_random_state(random_state)
    while True:
        a = random_state.choice(n)
        b = random_state.choice(n)
        c = random_state.choice(n)
        if a != b and b != c and c != a:
            break
    return a, [b, c]


class RandomSampling(Runner):
    def __init__(self, n, random_state=None):
        self.n = n
        self.answers = []
        self.random_state = check_random_state(random_state)

    def get_queries(self) -> Tuple[Query, List[float]]:
        num = 10
        queries = [
            _get_query(self.n, random_state=self.random_state) for _ in range(num)
        ]
        scores = self.random_state.uniform(low=0, high=1, size=len(queries))
        return queries, scores.tolist()

    def process_answers(self, ans: List[Answer]):
        self.answers.extend(ans)
