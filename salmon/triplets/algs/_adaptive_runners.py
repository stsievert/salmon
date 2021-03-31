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

import salmon.triplets.algs.adaptive as adaptive
from salmon.triplets.algs.adaptive import InfoGainScorer, UncertaintyScorer
from salmon.backend import Runner
from salmon.utils import get_logger
from salmon.triplets.algs._random_sampling import _get_query as _random_query

logger = get_logger(__name__)

Query = TypeVar("Query")
Answer = TypeVar("Answer")

PARAMS = dedent(
    """
    d : int
        Embedding dimension.
    optimizer : str
        The optimizer underlying the embedding. This method specifies how to
        change the batch size. Choices are
        ``["Embedding", "PadaDampG", "GeoDamp"]``.
    sampling : str
        "adaptive" by default. Use ``sampling="random"`` to perform random
        sampling with the same optimization method and noise model.
    """
)


class Adaptive(Runner):
    def __init__(
        self,
        n: int,
        d: int = 2,
        ident: str = "",
        module: str = "TSTE",
        optimizer: str = "Embedding",
        R: float = 10,
        sampling: str = "adaptive",
        scorer: str = "infogain",
        random_state: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(ident=ident)

        self.n = n
        self.d = d
        self.R = R
        self.sampling = sampling
        if sampling not in ["adaptive", "random"]:
            raise ValueError(
                "Must pass sampling='adaptive' or sampling='random', not "
                "sampling={sampling}"
            )

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

        if scorer == "infogain":
            search = InfoGainScorer(
                embedding=self.opt.embedding(), probs=self.opt.net_.module_.probs,
            )
        elif scorer == "uncertainty":
            search = UncertaintyScorer(embedding=self.opt.embedding(),)
        else:
            raise ValueError(f"scorer={scorer} not in ['uncertainty', 'infogain']")

        self.search = search
        self.search.push([])
        self.meta = {"num_ans": 0, "model_updates": 0, "process_answers_calls": 0}
        self.params = {
            "n": n,
            "d": d,
            "R": R,
            "sampling": sampling,
            "optimizer": optimizer,
            **kwargs,
        }

    def get_query(self) -> Tuple[Optional[Dict[str, int]], Optional[float]]:
        if (self.meta["num_ans"] <= self.R * self.n) or self.sampling == "random":
            head, left, right = _random_query(self.n)
            return {"head": int(head), "left": int(left), "right": int(right)}, -9999
        return None, -9999

    def get_queries(self, num=None, stop=None) -> Tuple[List[Query], List[float], dict]:
        if num:
            queries, scores = self.search.score(num=num)
            return queries[:num], scores[:num]
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
        queries = np.concatenate(ret_queries).astype(int)
        scores = np.concatenate(ret_scores)

        ## Rest of this function takes about 450ms
        df = pd.DataFrame(queries)
        hashes = pd.util.hash_pandas_object(df, index=False)
        _, idx = np.unique(hashes.to_numpy(), return_index=True)
        return queries[idx], scores[idx], {}

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
        # Use max_epochs // 2 because online and will already be
        # partially fit
        self.opt.set_params(max_epochs=max_epochs)

        valid_ans = self.opt.answers_[:n_ans]
        self.opt.fit(valid_ans)
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

    def score(self, X, y, embedding=None):
        y_hat = self.predict(X, embedding=embedding)
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
        sampling="adaptive",
        scorer="infogain",
        alpha=1,
        random_state=None,
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            module__alpha=alpha,
            module="TSTE",
            sampling=sampling,
            scorer=scorer,
            random_state=random_state,
            **kwargs,
        )


class RR(Adaptive):
    """
    A randomized round robin algorithm.

    Parameters
    ----------
    d : int
        Embedding dimension.
    R: int = 1
        Adaptive sampling starts are ``R * n`` response have been received.
    optimizer : str
        The optimizer underlying the embedding. This method specifies how to
        change the batch size. Choices are
        ``["Embedding", "PadaDampG", "GeoDamp"]``.
    scorer : str, (default ``"infogain"``)
        The scoring method to use.
    module : str, optional (default ``"TSTE"``).
        The noise model to use.
    kwargs : dict
        Arguments to pass to :ref:`~Adaptive`.


    Notes
    -----
    This algorithm is proposed in [1]_. They propose this algorithm because
    "scoring every triplet is prohibitvely expensive." It's also useful because it adds some randomness to the queries. This presents itself in a couple use cases:

    * When models don't update instantly (common). In that case, the user will
      query the database for multiple queries, and queries with the same head
      object may be returned.
    * When the noise model does not precisely model the human responses. In
      this case, the most informative query will

    References
    ----------
    .. [1] Heim, Eric, et al. "Active perceptual similarity modeling withi
           auxiliary information." arXiv preprint arXiv:1511.02254 (2015). https://arxiv.org/abs/1511.02254

    """

    def __init__(
        self,
        n: int,
        d: int = 2,
        R: int = 1,
        ident: str = "",
        optimizer: str = "Embedding",
        sampling="adaptive",
        scorer="infogain",
        module="TSTE",
        random_state=None,
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            R=R,
            ident=ident,
            optimizer=optimizer,
            module=module,
            sampling=sampling,
            scorer=scorer,
            random_state=random_state,
            **kwargs,
        )

    def get_queries(self, *args, **kwargs):
        queries, scores, meta = super().get_queries(*args, **kwargs)

        # (dataframe useful for manipulation below)
        df = pd.DataFrame(queries, columns=["h", "l", "r"])
        df["score"] = scores

        # Find the top scores per head
        top_scores_by_head = df.groupby(by="h")["score"].nlargest(n=3)
        top_idx = top_scores_by_head.index.droplevel(0)

        top_queries = df.loc[top_idx]
        top_scores = top_queries["score"].to_numpy()

        posted = top_queries[["h", "l", "r"]].to_numpy().astype("int64")
        r_scores = np.random.uniform(low=10, high=11, size=len(posted))

        meta.update({"n_queries_scored_(complete)": len(df)})
        return posted, r_scores, meta

    def process_answers(self, *args, **kwargs):
        new_self, updated = super().process_answers(*args, **kwargs)
        # Always return True to clear queries from the database (limits
        # randomness)
        return new_self, True


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
        sampling="adaptive",
        scorer="infogain",
        random_state=None,
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            module="STE",
            sampling=sampling,
            scorer=scorer,
            random_state=random_state,
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
        sampling="adaptive",
        scorer="uncertainty",
        random_state=None,
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            module="GNMDS",
            sampling=sampling,
            random_state=random_state,
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
        mu=1,
        sampling="adaptive",
        random_state=None,
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            module__mu=mu,
            module="CKL",
            sampling=sampling,
            random_state=random_state,
            **kwargs,
        )


class SOE(Adaptive):
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
        sampling="adaptive",
        random_state=None,
        **kwargs,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            module="SOE",
            sampling=sampling,
            random_state=random_state,
            **kwargs,
        )
