from typing import List, TypeVar, Tuple, Dict, Any

from sklearn.utils import check_random_state

import salmon.triplets.algs.adaptive._embed as embed
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
        ident: str = "",
        module: str = "TSTE",
        optimizer: str = "PadaDampG",
        d: int = 2,
        random_state=None,
        **kwargs,
    ):
        super().__init__(ident=ident)
        Opt = getattr(embed, optimizer)
        random_state = check_random_state(random_state)
        self.opt = Opt(random_state=random_state, **kwargs)

        self.opt.initialize()
        search = InfoGainScorer(
            embedding=self.opt.embedding(),
            probs=self.opt.est_.module_.probs,
            random_state=random_state,
        )
        search.push([])

    def get_queries(self, num=10_000) -> Tuple[List[Query], List[float]]:
        queries, scores = self.search.score(num=int(num * 1.1))
        return queries, scores

    def process_answers(self, answers: List[Answer]):
        self.search.push(answers)
        self.search.embedding = self.opt.embedding()

        self.opt.push(answers)
        self.opt.partial_fit(answers)

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
