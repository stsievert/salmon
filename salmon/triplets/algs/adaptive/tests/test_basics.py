import numpy as np
from sklearn.utils import check_random_state

from salmon.triplets.algs.adaptive import TSTE, Embedding
from torch.optim import SGD


def test_random_state():
    n, d = 20, 2
    random_state = 10

    rng = check_random_state(random_state)
    answers = rng.choice(n, size=(4 * n, 3))

    kwargs = dict(
        module=TSTE,
        module__n=n,
        module__d=2,
        optimizer=SGD,
        optimizer__lr=0.1,
        optimizer__momentum=0.9,
        random_state=random_state,
    )

    est1 = Embedding(**kwargs)
    est1.initialize()
    est1.partial_fit(answers)
    s1 = est1.score(answers)

    est2 = Embedding(**kwargs)
    est2.initialize()
    est2.partial_fit(answers)
    s2 = est2.score(answers)

    assert np.allclose(est1.embedding(), est2.embedding())
    assert np.allclose(s1, s2)
