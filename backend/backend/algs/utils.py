from typing import Tuple, List, Dict, Any
from dataclasses import dataclass
from rejson import Client as RedisClient, Path
import rejson
import logging

Query = Tuple[int, Tuple[int, int]]  # head, (obj1, obj2)

logger = logging.getLogger(__name__)


@dataclass
class Answer:
    head: int
    left: int
    right: int
    winner: int

def clear_queries(name, rj: RedisClient) -> bool:
    rj.delete(f"alg-{name}.queries")
    return True


def post_queries(name, queries: List[Query], scores: List[float], rj: RedisClient) -> bool:
    q2 = {f"{h}-{a}-{b}": score for (h, (a, b)), score in zip(queries, scores)}
    key = f"alg-{name}-queries"
    rj.zadd(key, q2)
    return True


def get_answers(name: str, rj: RedisClient, clear: bool=True) -> List[Answer]:
    if not clear:
        raise NotImplementedError
    pipe = rj.pipeline()
    pipe.jsonget(f"alg-{name}-answers", Path("."))
    pipe.jsonset(f"alg-{name}-answers", Path("."), [])
    answers, success = pipe.execute()
    return answers

class Runner:
    def run(self, name: str, client, rj: RedisClient):
        """
        Run the algorithm.

        Parameters
        ----------
        name : str
        client : DaskClient
        rj : RedisClient

        """
        answers: List = []
        while True:
            # TODO: integrate Dask
            queries, scores = self.get_queries()
            if answers:
                logger.info(f"Processing {len(answers)} answers...")
                self.process_answers(answers)
                answers = []
            if self.clear:
                clear_queries(name, rj)
            if queries:
                post_queries(name, queries, scores, rj)
            answers = get_answers(name, rj, clear=True)
            if "reset" in rj.keys() and rj.jsonget("reset"):
                reset = rj.jsonget("reset")
                logger.info("reset=%s for %s", reset, name)
                rj.jsonset(f"stopped-{name}", Path("."), True)
                return

    @property
    def clear(self):
        return True

    def process_answers(self, answers: List[Answer]):
        """
        Process answers.

        Parameters
        ----------
        answers : List[Answers]
            Each answer is a dictionary. Each answer certainly has the keys
            "head", "left", "right" and "winner", and may have the key
            "puid" for participant UID.
        """
        raise NotImplementedError

    def get_queries(self) -> Tuple[List[Query], List[float]]:
        """
        Get queries.

        Returns
        -------
        queries : List[Query]
            The list of queries
        scores : List[float]
            The scores for each query. Higher scores are sampled more
            often.

        Notes
        -----
        The scores have to be unique. The underlying implementation does
        not sample queries of the same score unbiased.

        """
        raise NotImplementedError

    def get_model(self) -> Dict[str, Any]:
        raise NotImplementedError
