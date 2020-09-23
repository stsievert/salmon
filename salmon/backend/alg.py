import itertools
from pprint import pprint
from time import time
from typing import List, TypeVar, Tuple, Dict, Any, Optional

import cloudpickle
import numpy as np
import dask.distributed as distributed
from redis.exceptions import ResponseError
from rejson import Client as RedisClient, Path
from dask.distributed import Client as DaskClient

from ..utils import get_logger

logger = get_logger(__name__)

Query = TypeVar("Query")
Answer = TypeVar("Answer")
root = Path.rootPath()


class Runner:
    """
    Run a sampling algorithm. Provides hooks to connect with the database and
    the Dask cluster.

    Parameters
    ----------
    ident : str
        The algorithm idenfifier. This value is used to identify the algorithm
        in the database.
    """

    def __init__(self, ident: str = ""):
        self.ident = ident
        self.meta_ = []

    def redis_client(self, decode_responses=True) -> RedisClient:
        return RedisClient(host="redis", port=6379, decode_responses=decode_responses)

    def run(self, client: DaskClient):
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
        rj = self.redis_client()

        answers: List = []
        logger.info(f"Staring {self.ident}")

        def submit(fn: str, *args, **kwargs):
            return client.submit(getattr(type(self), fn), *args, **kwargs)

        update = False
        queries = np.array([])
        scores = np.array([])
        n_model_updates = 0
        rj.jsonset(f"alg-perf-{self.ident}", root, [])
        save_deadline = 0  # right away
        for k in itertools.count():
            try:
                loop_start = time()
                datum = {"iteration": k, "ident": self.ident}

                answers = self.get_answers(rj, clear=True)
                datum["num_answers"] = len(answers)
                self_future = client.scatter(self)

                _start = time()
                queries_f = client.scatter(queries)
                scores_f = client.scatter(scores)
                if update:
                    datum["cleared_queries"] = True
                    self.clear_queries(rj)
                done = distributed.Event(name="pa_finished")
                done.clear()
                f_post = submit(
                    "post_queries", self_future, queries_f, scores_f, done=done
                )
                f_model = submit("process_answers", self_future, answers)

                if hasattr(self, "get_queries"):
                    f_search = submit(
                        "get_queries", self_future, random_state=k, stop=done
                    )
                else:
                    f_search = client.submit(lambda x: x, 1)

                time_model = 0
                time_post = 0
                time_search = 0

                def _model_done(_):
                    nonlocal time_model
                    done.set()
                    time_model += time() - _start

                def _post_done(_):
                    nonlocal time_post
                    time_post += time() - _start

                def _search_done(_):
                    nonlocal time_search
                    time_search += time() - _start

                f_model.add_done_callback(_model_done)
                f_post.add_done_callback(_post_done)
                f_search.add_done_callback(_search_done)

                # Future.result raises errors automatically
                posted = f_post.result()
                new_self, update = f_model.result()
                queries, scores = f_search.result()

                _datum_update = {
                    "n_queries_posted": posted,
                    "update": update,
                    "n_db_queries": rj.zcard(f"alg-{self.ident}-queries"),
                    "n_model_updates": n_model_updates,
                    "time_posting_queries": time_post,
                    "time_model_update": time_model,
                    "time_search": time_search,
                    "time": time(),
                }
                datum.update(_datum_update)
                if update:
                    _s = time()
                    self.__dict__.update(new_self.__dict__)
                    datum["time_update"] = time() - _s
                    n_model_updates += 1

            except Exception as e:
                logger.exception(e)

            _s = time()
            if time() >= save_deadline:
                minute = 60
                save_deadline = time() + 10 * minute
                self.save()
            datum["time_save"] = time() - _s
            datum["time_loop"] = time() - loop_start
            rj.jsonarrappend(f"alg-perf-{self.ident}", root, datum)
            logger.info(datum)
            from pprint import pprint

            pprint(datum)
            if "reset" in rj.keys() and rj.jsonget("reset"):
                self.reset(client, rj)
                break
            logger.info(datum)
            pprint(datum)
        return True

    def min_search_length(self):
        return 0

    def save(self) -> bool:
        rj2 = self.redis_client(decode_responses=False)

        out = cloudpickle.dumps(self)
        rj2.set(f"state-{self.ident}", out)

        try:
            out = cloudpickle.dumps(self.get_model())
        except NotImplementedError:
            pass
        else:
            rj2.set(f"model-{self.ident}", out)
        return True

    def reset(self, client, rj):
        """
        Stop the algorithm. The algorithm will be deleted shortly after
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

        Returns
        -------
        data : dict
            An update to self.__dict__.
        """
        raise NotImplementedError

        #  def get_queries(self) -> Tuple[List[Query], List[float]]:
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
        rj.delete(f"alg-{name}-queries")
        return True

    def post_queries(
        self,
        queries: List[Query],
        scores: List[float],
        rj: Optional[RedisClient] = None,
        done=None,
    ) -> int:
        if rj is None:
            rj = self.redis_client()

        if isinstance(queries, np.ndarray) and isinstance(scores, np.ndarray):
            idx = np.argsort(-scores)
            scores = scores[idx]  # high to low scores
            queries = queries[idx]

        if not len(queries):
            return 0

        n_chunks = len(queries) // 500
        split_queries = np.array_split(queries, max(n_chunks, 1))
        split_scores = np.array_split(scores, max(n_chunks, 1))

        n_queries = 0
        for _queries, _scores in zip(split_queries, split_scores):
            queries2 = {
                self.serialize_query(q): float(score)
                for q, score in zip(_queries, _scores)
                if not np.isnan(score)
            }
            name = self.ident
            key = f"alg-{name}-queries"
            if len(queries2):
                rj.zadd(key, queries2)
            n_queries += len(queries2)
            if done is not None and done.is_set():
                break

        return n_queries

    def serialize_query(self, q: Query) -> str:
        # TODO: use ast.literal_eval or json.loads
        h, a, b = q
        return f"{h}-{a}-{b}"

    def get_answers(self, rj: RedisClient, clear: bool = True) -> List[Answer]:
        if not clear:
            raise NotImplementedError
        key = f"alg-{self.ident}-answers"
        if key in rj.keys():
            pipe = rj.pipeline()
            pipe.jsonget(key, Path("."))
            pipe.jsonset(key, Path("."), [])
            answers, success = pipe.execute()
            return answers
        return []
