import logging
from dataclasses import dataclass
from time import sleep
from typing import Any, Dict, List, Tuple

import rejson
from pydantic import BaseModel
from rejson import Client as RedisClient
from rejson import Path

Query = Tuple[int, Tuple[int, int]]  # head, (choice 1, choice 2)

logger = logging.getLogger(__name__)


class Answer(BaseModel):
    head: int
    left: int
    right: int
    winner: int


def clear_queries(name, rj: RedisClient) -> bool:
    rj.delete(f"alg-{name}.queries")
    return True


def post_queries(
    name, queries: List[Query], scores: List[float], rj: RedisClient
) -> bool:
    q2 = {serialize_query(q): score for q, score in zip(queries, scores)}
    key = f"alg-{name}-queries"
    rj.zadd(key, q2)
    return True


def get_answers(name: str, rj: RedisClient, clear: bool = True) -> List[Answer]:
    if not clear:
        raise NotImplementedError
    pipe = rj.pipeline()
    pipe.jsonget(f"alg-{name}-answers", Path("."))
    pipe.jsonset(f"alg-{name}-answers", Path("."), [])
    answers, success = pipe.execute()
    return answers


def serialize_query(q: Query) -> str:
    h, (a, b) = q
    return f"{h}-{a}-{b}"


def deserialize_query(serialized_query: str) -> Dict[str, int]:
    h, l, r = serialized_query.split("-")
    return {
        "head": int(h),
        "left": int(l),
        "right": int(r),
    }


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
                logger.info(f"Done processing answers.")
                answers = []
            if self.clear:
                clear_queries(name, rj)
            if queries:
                post_queries(name, queries, scores, rj)
            answers = get_answers(name, rj, clear=True)
            if "reset" in rj.keys() and rj.jsonget("reset"):
                self.reset(name, client, rj)
                return

    def reset(self, name, client, rj):
        reset = rj.jsonget("reset")
        logger.info("reset=%s for %s", reset, name)
        rj.jsonset(f"stopped-{name}", Path("."), True)
        return True

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
