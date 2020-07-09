from textwrap import dedent
from typing import List, TypeVar, Tuple, Dict, Any

from sklearn.utils import check_random_state
import torch.optim

import salmon.triplets.algs.adaptive as adaptive
from salmon.triplets.algs.adaptive import InfoGainScorer
from salmon.backend import Runner
from salmon.utils import get_logger

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
    initial_batch_size : int
        The initial batch_size, the number of answers used to approximate the
        gradient.
    random_state : int, None, np.random.RandomState
        The seed used to generate psuedo-random numbers.
    """

class Adaptive(Runner):
    def __init__(
        self,
        n: int,
        d: int = 2,
        ident: str = "",
        module: str = "TSTE",
        optimizer: str = "Embedding",
        optimizer__lr=0.075,
        optimizer__momentum=0.9,
        initial_batch_size=4,
        random_state=None,
        **kwargs,
    ):

        super().__init__(ident=ident)
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
            initial_batch_size=initial_batch_size,
            random_state=random_state,
            warm_start=True,
            max_epochs=1,
            **kwargs,
        )
        self.opt.initialize()

        self.search = InfoGainScorer(
            embedding=self.opt.embedding(),
            probs=self.opt.est_.module_.probs,
            random_state=random_state,
        )
        self.search.push([])

    def get_queries(self, num=10_000) -> Tuple[List[Query], List[float]]:
        queries, scores = self.search.score(num=int(num * 1.1))
        return queries, scores

    def process_answers(self, answers: List[Answer]):
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
        self.opt.partial_fit(alg_ans)

    def get_model(self) -> Dict[str, Any]:
        pass


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
    initial_batch_size : int
        The initial batch_size, the number of answers used to approximate the
        gradient.
    random_state : int, None, np.random.RandomState
        The seed used to generate psuedo-random numbers.


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
        initial_batch_size=4,
        random_state=None,
        alpha=1,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            initial_batch_size=initial_batch_size,
            random_state=random_state,
            module__alpha=alpha,
            module="TSTE",
        )


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
    initial_batch_size : int
        The initial batch_size, the number of answers used to approximate the
        gradient.
    random_state : int, None, np.random.RandomState
        The seed used to generate psuedo-random numbers.

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
        initial_batch_size=4,
        random_state=None,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            initial_batch_size=initial_batch_size,
            random_state=random_state,
            module="STE",
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
    initial_batch_size : int
        The initial batch_size, the number of answers used to approximate the
        gradient.
    random_state : int, None, np.random.RandomState
        The seed used to generate psuedo-random numbers.

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
        initial_batch_size=4,
        random_state=None,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            initial_batch_size=initial_batch_size,
            random_state=random_state,
            module="GNMDS",
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
    initial_batch_size : int
        The initial batch_size, the number of answers used to approximate the
        gradient.
    random_state : int, None, np.random.RandomState
        The seed used to generate psuedo-random numbers.
    """
    def __init__(
        self,
        n: int,
        d: int = 2,
        ident: str = "",
        optimizer: str = "Embedding",
        optimizer__lr=0.075,
        optimizer__momentum=0.9,
        initial_batch_size=4,
        random_state=None,
        mu=1,
    ):
        super().__init__(
            n=n,
            d=d,
            ident=ident,
            optimizer=optimizer,
            optimizer__lr=optimizer__lr,
            optimizer__momentum=optimizer__momentum,
            initial_batch_size=initial_batch_size,
            random_state=random_state,
            module__mu=mu,
            module="CKL",
        )
