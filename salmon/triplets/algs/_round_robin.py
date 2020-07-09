import logging
from typing import List, Tuple

from sklearn.utils import check_random_state

from .utils import Answer, Query
from ...backend.alg import Runner


logger = logging.getLogger(__name__)


def _get_query(n, head, random_state=None) -> Tuple[int, int, int]:
    random_state = check_random_state(random_state)
    a = head
    while True:
        b, c = random_state.choice(n, size=2)
        if a != b and b != c and c != a:
            break
    return a, b, c


def _score_query(q: Tuple[int, int, int]) -> float:
    h, l, r = q
    score = max(abs(h - l), abs(h - r))
    return float(score)


class RoundRobin(Runner):
    """
    Let the head of the triplet query rotate through the available items while choosing the bottom two items randomly.

    Parameters
    ----------
    n : int
        Number of objects
    random_state: Optional[int]
        Seed for random generateor
    ident : str
        Identifier of the algorithm

    """

    def __init__(self, n, random_state=None, ident=""):
        self.n = n
        self.answers = []
        self.random_state = check_random_state(random_state)
        self.counter = 0
        super().__init__(ident=ident)

    def get_queries(self) -> Query:
        logger.info(f"get_queries, self.counter={self.counter}")
        num = 10
        queries = [
            _get_query(
                self.n, (self.counter + k) % self.n, random_state=self.random_state
            )
            for k in range(num)
        ]
        scores = [_score_query(q) for q in queries]
        return queries, scores

    def process_answers(self, ans: List[Answer]):
        logger.info(f"p_a, self.counter={self.counter}, len(ans)={len(ans)}")
        self.counter += len(ans)
        self.answers.extend(ans)
