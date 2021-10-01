import itertools
from collections import defaultdict
from copy import deepcopy
from textwrap import dedent
from time import time
from typing import Any, Dict, List, Optional, Tuple, TypeVar

import numpy as np
import numpy.linalg as LA
import pandas as pd
import torch.optim

import salmon.triplets.samplers.adaptive as adaptive
from ...backend.sampler import Sampler
from salmon.triplets.samplers._random_sampling import _get_query as _random_query
from salmon.triplets.samplers.adaptive import InfoGainScorer, UncertaintyScorer
from salmon.utils import get_logger

logger = get_logger(__name__)

Query = TypeVar("Query")
Answer = TypeVar("Answer")


class Adaptive(Sampler):
    """
    The sampler that runs adaptive algorithms.
    """

    def __init__(
        self,
        *,
        n: int,
        d: int = 2,
        ident: str = "",
        module: str = "TSTE",
        optimizer: str = "Embedding",
        R: float = 10,
        scorer: str = "infogain",
        random_state: Optional[int] = None,
        **kwargs,
    ):
        """
        Parameters
        ----------
        n : int
            The number of items to embed.
        d : int (optional, default: ``2``)
            Embedding dimension.
        ident : str (optional, default: ``""``).
            The identity of this runner. Must be unique among all adaptive algorithms.
        optimizer : str (optional, default: ``Embedding``).
            The optimizer underlying the embedding. This method specifies how to
            change the batch size. Choices are
            ``["Embedding", "PadaDampG", "GeoDamp"]``.
        R : int (optional, default: ``1``)
            Adaptive sampling after ``R * n`` responses have been received.
        scorer : str (optional, default: ``"infogain"``)
            How queries should be scored. Scoring with ``scorer='infogain'``
            tries to link query score and "embedding improvement," and
            ``scorer='uncertainty'`` looks at the query that's closest to the
            decision boundary (or 50% probability).
        random_state : int, None, optional (default: ``None``)
            The random state to be used for initialization.
        kwargs : dict, optional
            Keyword arguments to pass to :class:`~salmon.triplets.samplers.adaptive.Embedding`.
        """
        super().__init__(ident=ident)

        self.n = n
        self.d = d
        self.R = R

        self.n_search = kwargs.pop("n_search", 0)

        Opt = getattr(adaptive, optimizer)
        Module = getattr(adaptive, module)

        logger.info("Module = %s", Module)
        logger.info("opt = %s", Opt)

        self.opt = Opt(
            module=Module,
            module__n=n,
            module__d=d,
            module__random_state=random_state,
            optimizer=torch.optim.Adadelta,
            warm_start=True,
            max_epochs=200,
            **kwargs,
        )
        self.opt.initialize()

        probs = self.opt.net_.module_.probs
        if scorer == "infogain":
            search = InfoGainScorer(embedding=self.opt.embedding(), probs=probs)
        elif scorer == "uncertainty":
            search = UncertaintyScorer(embedding=self.opt.embedding(), probs=probs)
        else:
            raise ValueError(f"scorer={scorer} not in ['uncertainty', 'infogain']")

        self.search = search
        self.search.push([])
        self.meta = {
            "num_ans": 0,
            "model_updates": 0,
            "process_answers_calls": 0,
            "empty_pa_calls": 0,
        }
        self.params = {
            "n": n,
            "d": d,
            "R": R,
            "optimizer": optimizer,
            **kwargs,
        }

    def get_query(self) -> Tuple[Optional[Dict[str, int]], Optional[float]]:
        """Randomly select a query where there are few responses"""
        if self.meta["num_ans"] <= self.R * self.n:
            head, left, right = _random_query(self.n)
            return {"head": int(head), "left": int(left), "right": int(right)}, -9999
        return None, -9999

    def get_queries(self, num=None, stop=None) -> Tuple[List[Query], List[float], dict]:
        """Get and score many queries."""
        ret_queries = []
        ret_scores = []
        n_searched = 0
        for pwr in range(12, 40 + 1):
            # I think there's a memory leak in search.score -- Dask workers
            # kept on dying on get_queries. min(pwr, 16) to fix that (and
            # verified too).
            #
            # pwr in range(12, 41) => about 1.7 million queries searched
            pwr = min(pwr, 16)
            queries, scores = self.search.score(num=2 ** pwr)
            n_searched += len(queries)
            ret_queries.append(queries)
            ret_scores.append(scores)

            # returned object is about (n_searched/1e6) * 16 MB in size
            # let's limit it to be 32MB in size
            if (n_searched >= 2e6) or (stop is not None and stop.is_set()):
                break
            if num or self.n_search:
                n_ret = int(num or self.n_search)
                if n_searched >= 3 * n_ret:
                    break

        queries = np.concatenate(ret_queries).astype(int)
        scores = np.concatenate(ret_scores)
        queries = self._sort_query_order(queries)

        ## Rest of this function takes about 450ms
        df = pd.DataFrame(queries)
        hashes = pd.util.hash_pandas_object(df, index=False)
        _, idx = np.unique(hashes.to_numpy(), return_index=True)
        queries = queries[idx]
        scores = scores[idx]
        if num or self.n_search:
            n_ret = int(num or self.n_search)
            queries = queries[:n_ret]
            scores = scores[:n_ret]
        return queries, scores, {}

    @staticmethod
    def _sort_query_order(queries: np.ndarray) -> np.ndarray:
        mins = np.minimum(queries[:, 1], queries[:, 2])
        maxs = np.maximum(queries[:, 1], queries[:, 2])
        queries[:, 1], queries[:, 2] = mins, maxs
        return queries

    def process_answers(self, answers: List[Answer]):
        """Process answers from the database.

        This function requires pulling from the database, and feeding those
        answers to the underlying optimization algorithm.
        """
        if not len(answers):
            self.meta["empty_pa_calls"] += 1
            if self.meta["empty_pa_calls"] >= 20:
                self.meta["empty_pa_calls"] = 0
                return self, True

        self.meta["num_ans"] += len(answers)
        self.meta["process_answers_calls"] += 1
        logger.debug("self.meta = %s", self.meta)
        logger.debug("self.R, self.n = %s, %s", self.R, self.n)

        # fmt: off
        alg_ans = [
            (a["head"], a["winner"],
             a["left"] if a["winner"] == a["right"] else a["right"])
            for a in answers
        ]
        # fmt: on
        self.search.push(alg_ans)
        self.search.embedding = self.opt.embedding()
        self.opt.push(alg_ans)
        if self.meta["num_ans"] < (self.R * self.n) / 10:
            return self, True

        # Make sure only valid answers are passed to partial_fit;
        # self.opt.answers_ has a bunch of extra space for new answers
        n_ans = self.opt.meta_["num_answers"]

        difficulty = np.log(self.params["n"]) * self.params["d"] * self.params["n"]
        if n_ans / difficulty <= 1:
            max_epochs = 200
        elif n_ans / difficulty <= 3:
            max_epochs = 120
        else:
            max_epochs = 50

        # max_epochs above for completely random initializations
        self.opt.set_params(max_epochs=max_epochs)

        valid_ans = self.opt.answers_[:n_ans]
        self.opt.fit(valid_ans)
        self.meta["model_updates"] += 1
        return self, True

    def get_model(self) -> Dict[str, Any]:
        """
        Get the embedding alongside other related information.
        """
        return {
            "embedding": self.search.embedding.tolist(),
            **self.meta,
            **self.params,
        }

    def predict(self, X, embedding=None):
        """
        Predict the answers of queries from the current embedding.

        Parameters
        ----------
        X : array-like
            Each row is ``[head, left, right]``. Each element in ``X`` or
            ``X[i, j]`` is an index of the current embedding.

        Returns
        -------
        y : array-like
            The winner of each query. An element of ``y`` is 0 if the left
            item is the predicted winner, and 1 if the right element is the
            predicted winner.

        """
        head_idx = X[:, 0].flatten()
        left_idx = X[:, 1].flatten()
        right_idx = X[:, 2].flatten()

        if embedding is None:
            embedding = self.opt.embedding()
        head = embedding[head_idx]
        left = embedding[left_idx]
        right = embedding[right_idx]

        ldiff = LA.norm(head - left, axis=1)
        rdiff = LA.norm(head - right, axis=1)

        # 1 if right closer; 0 if left closer
        # (which matches the labeling scheme)
        right_closer = rdiff < ldiff
        return right_closer.astype("uint8")

    def score(self, X, y, embedding=None):
        """
        Evaluate to see if current embedding agrees with the provided queries.

        Parameters
        ----------
        X : array-like, shape (n, 3)
            The columns should be aranged
        y : array-like, shape (n, )
            The answers to specific queries. The ``i``th value should be 0 if
            ``X[i, 1]`` won the query and 1 if ``X[i, 2]`` won the query.
        embedding : array-like, optional
            The embedding to use instead of the current embedding.
            The values in ``X`` will be treated as indices to this array.

        Returns
        -------
        acc : float
            The percentage of queries that agree with the current embedding.

        """
        y_hat = self.predict(X, embedding=embedding)
        return (y_hat == y).mean()


class TSTE(Adaptive):
    """The t-Distributed STE (t-STE) embedding algorithm [1]_.

    Notes
    -----
    This algorithm is proposed for the following reason:

    .. epigraph::

        In STE the value of the corresponding probability rapidly becomes
        infinitesimal when a triplet constraint is violated.  As a result,
        stronger violations of a constraint do not lead to significantly
        larger penalties, which reduces the tendency to correct triplet
        constraints that violate the consensus. This is illustrated by the
        STE gradient depicted in Figure 1:  the STE gradient is nearly zero
        when a constraint is strongly violated or satisfied. However, it
        appears that the gradient decays too rapidly, making it hard for
        STE to fix errors made early in the optimization later on.

        To address this problem, we propose to use a heavy-tailed kernel to
        measure local similarities between data points instead

        -- Section 4 of [1]_.


    References
    ----------
    .. [1] "Stochastic Triplet Embedding". 2012.
           http://www.cs.cornell.edu/~kilian/papers/stochastictriplet.pdf
           van der Maaten, Weinberger.
    """

    def __init__(self, alpha=1, **kwargs):
        """
        Parameters
        ----------
        alpha : float, default=1
            The parameter that controls how heavily the tails of the probability
            distribution are.
        kwargs : dict
            Keyword arguments to pass to :class:`~salmon.triplets.samplers.Adaptive`.
        """
        super().__init__(module="TSTE", module__alpha=alpha, **kwargs)


class ARR(Adaptive):
    """An asynchronous round robin algorithm.

    Notes
    -----
    This algorithms asks about "high scoring queries" uniformly at random. For
    each head, the top ``n_top`` queries are selected. The query shown to the
    user is a query selected uniformly at random from this set.

    If ``n_top > 1``, then in practice, this sampling algorithm randomly asks
    about high scoring queries for each head. Becaues it's asynchronous, it
    randomly selects a head (instead of doing it a round-robin fashion).

    .. note::

       We found this class to perform well in our experiments, some of which are detailed at https://docs.stsievert.com/salmon/benchmarks/active.html

    References
    ----------
    .. [1] Heim, Eric, et al. "Active perceptual similarity modeling with
           auxiliary information." arXiv preprint arXiv:1511.02254 (2015). https://arxiv.org/abs/1511.02254

    """

    def __init__(self, R: int = 1, n_top=1, module="TSTE", **kwargs):
        """
        Parameters
        ----------
        R : int (optional, default ``1``)
            Adaptive sampling starts after ``R * n`` responses have been received.
        module : str, optional (default ``"TSTE"``).
            The noise model to use.
        n_top : int (optional, default ``1``)
            For each head, the number of top-scoring queries to ask about.
        kwargs : dict
            Keyword arguments to pass to :class:`~salmon.triplets.samplers.Adaptive`.
        """
        self.n_top = n_top
        super().__init__(R=R, module=module, **kwargs)

    def get_queries(self, *args, **kwargs):
        queries, scores, meta = super().get_queries(*args, **kwargs)

        # (dataframe useful for manipulation below)
        df = pd.DataFrame(queries, columns=["h", "l", "r"])
        df["score"] = scores

        # Find the top scores per head
        top_scores_by_head = df.groupby(by="h")["score"].nlargest(n=self.n_top)
        top_idx = top_scores_by_head.index.droplevel(0)

        top_queries = df.loc[top_idx]
        top_scores = top_queries["score"].to_numpy()
        top_queries = top_queries.sample(frac=1, replace=False)

        posted = top_queries[["h", "l", "r"]].to_numpy().astype("int64")
        r_scores = np.random.uniform(low=10, high=11, size=len(posted))

        meta.update({"n_queries_scored_(complete)": len(df)})
        return posted, r_scores, meta

    def process_answers(self, *args, **kwargs):
        new_self, updated = super().process_answers(*args, **kwargs)
        # Always return True to clear queries from the database (limits
        # randomness)
        return new_self, True


class SRR(ARR):
    """

    A synchronous round robin sampling strategy; it performs a search of
    ``n_search`` queries with a randomly selected head.

    .. note::

       "Round robin" is misnomer; this class actually selects a random head to mirror ARR.

    """

    def __init__(self, *args, n_search=400, **kwargs):
        """
        Parameters
        ----------
        n_search: int (optional, default ``400``)
            How many queries should be searched per user?
        kwargs : dict
            Keyword arguments to pass to :class:`~salmon.triplets.samplers.ARR`.
        """
        super().__init__(*args, **kwargs)
        self.n_search = n_search

    def get_queries(self, *args, **kwargs):
        return [], [], {}

    def get_query(self):
        q, score = super().get_query()
        if q is not None:
            return q, score

        head = int(np.random.choice(self.n))
        _choices = list(set(range(self.n)) - {head})
        choices = np.array(_choices)
        bottoms = [
            np.random.choice(choices, size=2, replace=False)
            for _ in range(self.n_search)
        ]

        _queries = [[head, l, r] for l, r in bottoms]
        queries, scores = self.search.score(queries=_queries)

        top_idx = np.argmax(scores)
        (h, l, r), score = queries[top_idx], float(scores[top_idx])
        return {"head": int(h), "left": int(l), "right": int(r)}, score


class STE(Adaptive):
    """The Stochastic Triplet Embedding [1]_.

    References
    ----------
    .. [1] "Stochastic Triplet Embedding". 2012.
           http://www.cs.cornell.edu/~kilian/papers/stochastictriplet.pdf
           van der Maaten, Weinberger.
    """

    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        kwargs : dict
            Keyword arguments to pass to :class:`~salmon.triplets.samplers.Adaptive`.
        """
        super().__init__(module="STE", **kwargs)


class GNMDS(Adaptive):
    """The Generalized Non-metric Multidimensional Scaling embedding [1]_.

    References
    ----------
    .. [1] "Generalized Non-metric Multidimensional Scaling". 2007.
           Agarwal, Wills, Cayton, Lanckriet, Kriegman, and Belongie.
           http://proceedings.mlr.press/v2/agarwal07a/agarwal07a.pdf
    """

    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        kwargs : dict
            Keyword arguments to pass to :class:`~salmon.triplets.samplers.Adaptive`.
        """
        super().__init__(module="GNMDS", **kwargs)


class CKL(Adaptive):
    """The crowd kernel embedding. Proposed in [1]_.

    References
    ----------
    .. [1] Tamuz, O., Liu, C., Belongie, S., Shamir, O., & Kalai, A. T. (2011).
           Adaptively learning the crowd kernel. https://arxiv.org/abs/1105.1033
    """

    def __init__(self, mu=1, **kwargs):
        """
        Parameters
        ----------
        mu : float
            The mu or :math:`\\mu` used in the CKL embedding. This is typically small; the default is :math:`10^{-4}`.
        kwargs : dict
            Keyword arguments to pass to :class:`~salmon.triplets.samplers.Adaptive`.
        """
        super().__init__(module__mu=mu, module="CKL", **kwargs)


class SOE(Adaptive):
    """The soft ordinal embedding detailed by Terada et al. [1]_

    This is evaluated as "SOE" by Vankadara et al., [2]_ in which they use the
    hinge loss on the distances (not squared distances).

    References
    ----------
    .. [1] Terada, Y. & Luxburg, U.. (2014). Local Ordinal Embedding.
           Proceedings of the 31st International Conference on Machine
           Learning, in PMLR 32(2):847-855.
           http://proceedings.mlr.press/v32/terada14.html

    .. [2] Vankadara, L. C., Haghiri, S., Lohaus, M., Wahab, F. U., &
           von Luxburg, U. (2019). Insights into Ordinal Embedding Algorithms:
           A Systematic Evaluation. https://arxiv.org/abs/1912.01666
    """

    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        kwargs : dict
            Keyword arguments to pass to :class:`~salmon.triplets.samplers.Adaptive`.
        """
        super().__init__(module="SOE", **kwargs)
