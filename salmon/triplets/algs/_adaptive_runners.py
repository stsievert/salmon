import itertools
from collections import defaultdict
from time import time, sleep
from textwrap import dedent
from typing import List, TypeVar, Tuple, Dict, Any, Optional
from copy import deepcopy

import torch.optim
import numpy as np
import numpy.linalg as LA
import pandas as pd
from sklearn.utils import check_random_state

import salmon.triplets.algs.adaptive as adaptive
from salmon.triplets.algs.adaptive import InfoGainScorer, UncertaintyScorer
from salmon.backend import Runner
from salmon.utils import get_logger
from salmon.triplets.algs._random_sampling import _get_query as _random_query

logger = get_logger(__name__)

Query = TypeVar("Query")
Answer = TypeVar("Answer")

PARAMS = """
    d : int
        Embedding dimension.
    optimizer : str
        The optimizer underlying the embedding. This method specifies how to
        change the batch size. Choices are
        ``["Embedding", "PadaDampG", "GeoDamp"]``.
    optimizer__lr : float
        Which learning rate to use with the optimizer. The learning rate must
        be positive.
    optimizer__momentum : float
        The momentum to use with the optimizer.
    random_state : int, None, np.random.RandomState
        The seed used to generate psuedo-random numbers.
    sampling : str
        "adaptive" by default. Use ``sampling="random"`` to perform random
        sampling with the same optimization method and noise model.
    """


class Adaptive(Runner):
    def __init__(
        self,
        n: int,
        d: int = 2,
        ident: str = "",
        module: str = "TSTE",
        optimizer: str = "Embedding",
        optimizer__lr=0.050,
        optimizer__momentum=0.9,
        random_state=None,
        R: float = 10,
        sampling: str = "adaptive",
        scorer: str = "infogain",
        **kwargs,
    ):
        super().__init__(ident=ident)

        self.n = n
        self.d = d
        self.R = R
        self.sampling = sampling
        if sampling not in ["adaptive", "random"]:
            raise ValueError(
                "Must pass sampling='adaptive' or sampling='random', not sampling={sampling}"
            )

        Opt = getattr(adaptive, optimizer)
        Module = getattr(adaptive, module)

        logger.info("Module = %s", Module)
        logger.info("opt = %s", Opt)
        self.opt = Opt(
            module=Module,
            module__n=n,
            module__d=d,
            optimizer=torch.optim.SGD,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            random_state=random_state,
            warm_start=True,
            max_epochs=1,
            **kwargs,
        )
        self.opt.initialize()

        if scorer == "infogain":
            search = InfoGainScorer(
                embedding=self.opt.embedding(),
                probs=self.opt.module_.probs,
                random_state=random_state,
            )
        elif scorer == "uncertainty":
            search = UncertaintyScorer(
                embedding=self.opt.embedding(), random_state=random_state,
            )
        else:
            raise ValueError(f"scorer={scorer} not in ['uncertainty', 'infogain']")

        self.random_state_ = check_random_state(random_state)
        self.search = search
        self.search.push([])
        self.meta = {"num_ans": 0, "model_updates": 0, "process_answers_calls": 0}
        self.params = {
            "n": n,
            "d": d,
            "R": R,
            "sampling": sampling,
            "random_state": random_state,
            "optimizer": optimizer,
            "optimizer__lr": optimizer__lr,
            "optimizer__momentum": optimizer__momentum,
            **kwargs,
        }

    def get_query(self) -> Tuple[Optional[Dict[str, int]], Optional[float]]:
        if (self.meta["num_ans"] <= self.R * self.n) or self.sampling == "random":
            head, left, right = _random_query(self.n, random_state=self.random_state_)
            return {"head": int(head), "left": int(left), "right": int(right)}, -9999
        return None, -9999

    def get_queries(
        self, num=10_000, stop=None, random_state=None
    ) -> Tuple[List[Query], List[float]]:
        if num:
            queries, scores = self.search.score(num=num, random_state=random_state)
            return queries[:num], scores[:num]
        ret_queries = []
        ret_scores = []
        rng = None
        if random_state:
            rng = check_random_state(random_state)
        deadline = time() + self.min_search_length()
        for pwr in itertools.count(start=12):
            queries, scores = self.search.score(
                num=2 ** pwr, trim=False, random_state=rng
            )
            ret_queries.append(queries)
            ret_scores.append(scores)
            if time() >= deadline and stop.is_set():
                break
        return np.concenate(ret_queries), np.concatenate(ret_scores)

    def process_answers(self, answers: List[Answer]):
        if not len(answers):
            return self, False

        self.meta["num_ans"] += len(answers)
        self.meta["process_answers_calls"] += 1
        logger.debug("self.meta = %s", self.meta)
        logger.debug("self.R, self.n = %s, %s", self.R, self.n)

        alg_ans = [
            (
                a["head"],
                a["winner"],
                a["left"] if a["winner"] == a["right"] else a["right"],
            )
            for a in answers
        ]
        self.search.push(alg_ans)
        self.search.embedding = self.opt.embedding()
        self.opt.push(alg_ans)

        # Make sure only valid answers are passed to partial_fit;
        # self.opt.answers_ has a bunch of extra space for new answers
        n_ans = self.opt.meta_["num_answers"]
        valid_ans = self.opt.answers_[:n_ans]

        self.opt.partial_fit(valid_ans, time_limit=10)
        self.meta["model_updates"] += 1
        return self, True

    def get_model(self) -> Dict[str, Any]:
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

    def score(self, X, y):
        y_hat = self.predict(X)
        return (y_hat == y).mean()


class TSTE(Adaptive):
    """
    The t-Distributed STE (t-STE) embedding algorithm [1]_.

    Parameters
    ----------
    d : int
        Embedding dimension.
    alpha : float, default=1
        The parameter that controls how heavily the tails of the probability
        distribution are.
    optimizer : str
        The optimizer underlying the embedding. This method specifies how to
        change the batch size. Choices are
        ``["Embedding", "PadaDampG", "GeoDamp"]``.
    optimizer__lr : float
        Which learning rate to use with the optimizer. The learning rate must
        be positive.
    optimizer__momentum : float
        The momentum to use with the optimizer.
    random_state : int, None, np.random.RandomState
        The seed used to generate psuedo-random numbers.
    sampling : str
        "adaptive" by default. Use ``sampling="random"`` to perform random
        sampling with the same optimization method and noise model.
    kwargs : dict
        Arguments to pass to the optimization method.


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

    def __init__(
        self,
        n: int,
        d: int = 2,
        ident: str = "",
        optimizer: str = "Embedding",
        optimizer__lr=0.075,
        optimizer__momentum=0.9,
        random_state=None,
        sampling="adaptive",
        scorer="infogain",
        alpha=1,
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            random_state=random_state,
            module__alpha=alpha,
            module="TSTE",
            sampling=sampling,
            scorer=scorer,
            **kwargs,
        )


class RR(Adaptive):
    def __init__(
        self,
        n: int,
        d: int = 2,
        ident: str = "",
        optimizer: str = "Embedding",
        optimizer__lr=0.075,
        optimizer__momentum=0.9,
        random_state=None,
        sampling="adaptive",
        scorer="infogain",
        module="TSTE",
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            random_state=random_state,
            module=module,
            sampling=sampling,
            scorer=scorer,
            **kwargs,
        )

    def get_queries(self, *args, **kwargs):
        queries, scores = super().get_queries(*args, **kwargs)

        df = pd.DataFrame(queries, columns=["h", "l", "r"])
        df["score"] = scores

        top_scores_by_head = df.groupby(by="h")["score"].nlargest(n=5)
        top_idx = top_scores_by_head.index.droplevel(0)

        top_queries = df.loc[top_idx].sample(random_state=self.random_state_, frac=1)
        posted = top_queries[["h", "l", "r"]].values.astype("int64")
        scores = 10 + np.linspace(0, 1, num=len(posted))

        random = df.sample(random_state=self.random_state_, n=min(len(df), 1000))
        random_q = random[["h", "l", "r"]].values.astype("int64")
        random_scores = -9998 + self.random_state_.uniform(0, 1, size=len(random_q))

        ret_q = np.concatenate((posted, random_q))
        ret_score = np.concatenate((scores, random_scores))
        return ret_q, ret_score


class STE(Adaptive):
    """
    The Stochastic Triplet Embedding [1]_.

    Parameters
    ----------
    d : int
        Embedding dimension.
    optimizer : str
        The optimizer underlying the embedding. This method specifies how to
        change the batch size. Choices are
        ``["Embedding", "PadaDampG", "GeoDamp"]``.
    optimizer__lr : float
        Which learning rate to use with the optimizer. The learning rate must
        be positive.
    optimizer__momentum : float
        The momentum to use with the optimizer.
    random_state : int, None, np.random.RandomState
        The seed used to generate psuedo-random numbers.
    sampling : str
        "adaptive" by default. Use ``sampling="random"`` to perform random
        sampling with the same optimization method and noise model.

    References
    ----------
    .. [1] "Stochastic Triplet Embedding". 2012.
           http://www.cs.cornell.edu/~kilian/papers/stochastictriplet.pdf
           van der Maaten, Weinberger.
    """

    def __init__(
        self,
        n: int,
        d: int = 2,
        ident: str = "",
        optimizer: str = "Embedding",
        optimizer__lr=0.075,
        optimizer__momentum=0.9,
        random_state=None,
        sampling="adaptive",
        scorer="infogain",
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            random_state=random_state,
            module="STE",
            sampling=sampling,
            scorer=scorer,
            **kwargs,
        )


class GNMDS(Adaptive):
    """
    The Generalized Non-metric Multidimensional Scaling embedding [1]_.

    Parameters
    ----------
    d : int
        Embedding dimension.
    optimizer : str
        The optimizer underlying the embedding. This method specifies how to
        change the batch size. Choices are
        ``["Embedding", "PadaDampG", "GeoDamp"]``.
    optimizer__lr : float
        Which learning rate to use with the optimizer. The learning rate must
        be positive.
    optimizer__momentum : float
        The momentum to use with the optimizer.
    random_state : int, None, np.random.RandomState
        The seed used to generate psuedo-random numbers.
    sampling : str
        "adaptive" by default. Use ``sampling="random"`` to perform random
        sampling with the same optimization method and noise model.

    References
    ----------
    .. [1] "Generalized Non-metric Multidimensional Scaling". 2007.
           Agarwal, Wills, Cayton, Lanckriet, Kriegman, and Belongie.
           http://proceedings.mlr.press/v2/agarwal07a/agarwal07a.pdf
    """

    def __init__(
        self,
        n: int,
        d: int = 2,
        ident: str = "",
        optimizer: str = "Embedding",
        optimizer__lr=0.075,
        optimizer__momentum=0.9,
        random_state=None,
        sampling="adaptive",
        scorer="uncertainty",
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            random_state=random_state,
            module="GNMDS",
            sampling=sampling,
            **kwargs,
        )


class CKL(Adaptive):
    """
    The crowd kernel embedding.

    Parameters
    ----------
    d : int
        Embedding dimension.
    mu : float
        The mu or :math:`\\mu` used in the CKL embedding. This is typically small; the default is :math:`10^{-4}`.
    optimizer : str
        The optimizer underlying the embedding. This method specifies how to
        change the batch size. Choices are
        ``["Embedding", "PadaDampG", "GeoDamp"]``.
    optimizer__lr : float
        Which learning rate to use with the optimizer. The learning rate must
        be positive.
    optimizer__momentum : float
        The momentum to use with the optimizer.
    random_state : int, None, np.random.RandomState
        The seed used to generate psuedo-random numbers.
    sampling : str
        "adaptive" by default. Use ``sampling="random"`` to perform random
        sampling with the same optimization method and noise model.
    """

    def __init__(
        self,
        n: int,
        d: int = 2,
        ident: str = "",
        optimizer: str = "Embedding",
        optimizer__lr=0.075,
        optimizer__momentum=0.9,
        random_state=None,
        mu=1,
        sampling="adaptive",
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            random_state=random_state,
            module__mu=mu,
            module="CKL",
            sampling=sampling,
            **kwargs,
        )
