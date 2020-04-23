import logging
from time import sleep
from typing import List, Tuple

import numpy as np
from sklearn.utils import check_random_state

from .utils import Answer, Query, Runner, get_answers

logger = logging.getLogger(__name__)

def _get_query(n, random_state=None) -> Tuple[int, Tuple[int, int]]:
    random_state = check_random_state(random_state)
    while True:
        a = random_state.choice(n)
        b = random_state.choice(n)
        c = random_state.choice(n)
        if a != b and b != c and c != a:
            break
    return a, (b, c)


class RandomSampling(Runner):
    def __init__(self, n, random_state=None):
        self.n = n
        self.answers = []
        self.random_state = check_random_state(random_state)

    def get_query(self) -> Tuple[Query, float]:
        h, (a, b) = _get_query(self.n, random_state=self.random_state)
        query = {"head": h, "left": a, "right": b}
        return query, 0.0

    def process_answers(self, ans: List[Answer]):
        self.answers.extend(ans)

    def run(self, name, client, rj):
        answers: List = []
        while True:
            if answers:
                self.process_answers(answers)
                answers = []
            answers = get_answers(name, rj, clear=True)
            if "reset" in rj.keys() and rj.jsonget("reset"):
                self.reset(name, client, rj)
                return
            sleep(1)
