from typing import List, TypeVar, Tuple, Dict, Any
from rejson import Client as RedisClient, Path
import cloudpickle

from ..utils import get_logger

logger = get_logger(__name__)

Query = TypeVar("Query")
Answer = TypeVar("Answer")


class Runner:
    """
    Run an adaptive algorithm.
    """

    def __init__(self, ident: str = ""):
        """
        ident : str
            The algorithm idenfifier. This value is used to identify the algorithm
            in the database.
        """
        self.ident = ident

    def run(self, client, rj: RedisClient):
        """
        Run the algorithm.

        Parameters
        ----------
        client : DaskClient
            A client to Dask.
        rj : RedisClient
            A Redist Client, a rejson.Client

        Notes
        -----
        This function runs the adaptive algorithm. Because it's asynchronous,
        this function should return if
        ``"reset" in rj.keys() and rj.jsonget("reset")``.

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
                self.clear_queries(rj)
            if len(queries):
                self.post_queries(queries, scores, rj)
            answers = self.get_answers(rj, clear=True)
            if "reset" in rj.keys() and rj.jsonget("reset"):
                self.reset(client, rj)
                return
            self.save()

    def save(self) -> bool:
        rj2 = RedisClient(host="redis", port=6379, decode_responses=False)
        out = cloudpickle.dumps(self)
        rj2.set(f"state-{self.ident}", out)
        return True

    def reset(self, client, rj):
        """
        Reset the algorithm. The algorithm will be deleted shortly after
        this function is called.
        """
        reset = rj.jsonget("reset")
        logger.info("reset=%s for %s", reset, self.ident)
        rj.jsonset(f"stopped-{self.ident}", Path("."), True)
        return True

    @property
    def clear(self):
        """
        Should the queries be cleared from the database?
        """
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
        """
        Get the model underlying the algorithm.

        Returns
        -------
        state : Dict[str, Any]
            The state of the algorithm. This can be used for display on the
            dashboard or with an HTTP get request.
        """
        raise NotImplementedError

    def clear_queries(self, rj: RedisClient) -> bool:
        name = self.ident
        rj.delete(f"alg-{name}.queries")
        return True

    def post_queries(
        self, queries: List[Query], scores: List[float], rj: RedisClient
    ) -> bool:
        q2 = {self.serialize_query(q): float(score) for q, score in zip(queries, scores)}
        name = self.ident
        key = f"alg-{name}-queries"
        rj.zadd(key, q2)
        return True

    def serialize_query(self, q: Query) -> str:
        # TODO: use ast.literal_eval or json.loads
        h, a, b = q
        return f"{h}-{a}-{b}"

    def get_answers(
        self, rj: RedisClient, clear: bool = True
    ) -> List[Answer]:
        if not clear:
            raise NotImplementedError
        pipe = rj.pipeline()
        name = self.ident
        pipe.jsonget(f"alg-{name}-answers", Path("."))
        pipe.jsonset(f"alg-{name}-answers", Path("."), [])
        answers, success = pipe.execute()
        return answers
