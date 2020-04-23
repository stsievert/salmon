from typing import Tuple, List, Dict
from dataclasses import dataclass
from rejson import Path
import logging
from time import sleep

Query = Tuple[int, Tuple[int, int]]  # head, (obj1, obj2)

logger = logging.getLogger(__name__)


@dataclass
class Answer:
    head: int
    left: int
    right: int


def _clear_queries(name, rj) -> bool:
    rj.delete(f"alg-{name}.queries")
    return True


def _post_queries(name, queries, scores, rj) -> bool:
    q2 = {f"{h}-{a}-{b}": score for (h, (a, b)), score in zip(queries, scores)}
    key = f"alg-{name}-queries"
    rj.zadd(key, q2)
    return True


def _get_and_clear_answers(name, rj):
    pipe = rj.pipeline()
    pipe.jsonget(f"alg-{name}-answers", Path("."))
    pipe.jsonset(f"alg-{name}-answers", Path("."), [])
    answers, success = pipe.execute()
    return answers


def run(name, alg, client, rj):
    answers: List = []
    while True:
        # TODO: integrate Dask
        #  f1 = client.submit(alg.get_queries)
        #  f2 = client.submit(alg.process_answers, answers)
        #  (queries, scores, clear), _ = await client.compute((f1, f2))
        #  logger.info("Getting queries...")
        queries, scores = alg.get_queries()
        if answers:
            logger.info(f"Processing {len(answers)} answers...")
            alg.process_answers(answers)
            answers = []
        if alg.clear:
            _clear_queries(name, rj)
        if queries:
            _post_queries(name, queries, scores, rj)
        answers = _get_and_clear_answers(name, rj)
        if "reset" in rj.keys() and rj.jsonget("reset"):
            reset = rj.jsonget("reset")
            logger.info("reset=%s for %s", reset, name)
            rj.jsonset(f"stopped-{name}", Path("."), True)
            return
