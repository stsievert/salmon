import logging
from time import sleep
from typing import List, Tuple

from sklearn.utils import check_random_state

from .utils import Answer, Query
from ...backend.alg import Runner

logger = logging.getLogger(__name__)


def _get_query(n, random_state=None) -> Tuple[int, int, int]:
    random_state = check_random_state(random_state)
    while True:
        a, b, c = random_state.choice(n, size=3)
        if a != b and b != c and c != a:
            break
    return a, b, c


class RandomSampling(Runner):
    """
    Choose the triplet queries randomly, only ensuring objects are not repeated.

    Parameters
    ----------
    n : int
        Number of objects
    random_state: Optional[int]
        Seed for random generateor
    ident : str
        Identifier of the algorithm

    """

    def __init__(self, n, d=2, random_state=None, ident=""):
        self.n = n
        self.d = d
        self.answers = []
        self.random_state = check_random_state(random_state)
        super().__init__(ident=ident)

    def get_query(self) -> Tuple[Query, float]:
        h, a, b = _get_query(self.n, random_state=self.random_state)
        query = {"head": int(h), "left": int(a), "right": int(b)}
        return query, 0.0

    def process_answers(self, ans: List[Answer]):
        self.answers.extend(ans)

    def run(self):
        rj = self.redis_client()
        client = self.dask_client()

        answers: List = []
        while True:
            if answers:
                self.process_answers(answers)
                answers = []
            answers = self.get_answers(rj, clear=True)
            if "reset" in rj.keys() and rj.jsonget("reset"):
                self.reset(client, rj)
                return
            sleep(1)
