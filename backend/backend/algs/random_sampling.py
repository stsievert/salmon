import numpy as np
from sklearn.utils import check_random_state

from .utils import Query, Answer


def _get_query(n, random_state=None):
    random_state = check_random_state(random_state)
    while True:
        a = random_state.choice(n)
        b = random_state.choice(n)
        c = random_state.choice(n)
        if a != b and b != c and c != a:
            break
    return a, [b, c]


class RandomSampling:
    def __init__(self, n, random_state=None):
        self.n = n
        self.answers = []
        self.random_state = check_random_state(random_state)

    def get_queries(self, num: int) -> Query:
        return [_get_query(self.n, random_state=self.random_state) for _ in range(num)]

    def process_answer(self, ans: Answer):
        self.answers.append(ans)
