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


class Adaptive(Runner):
    def __init__(
        self,
        n: int,
        d: int = 2,
        ident: str = "",
        module: str = "TSTE",
        optimizer: str = "PadaDampG",
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, module="TSTE", **kwargs)


class STE(Adaptive):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, module="STE", **kwargs)


class GNMDS(Adaptive):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, module="GNMDS", **kwargs)


class CKL(Adaptive):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, module="CKL", **kwargs)
