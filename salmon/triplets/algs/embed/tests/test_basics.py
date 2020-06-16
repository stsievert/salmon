import numpy as np
from sklearn.utils import check_random_state

import salmon.triplets.algs.embed as embed
from torch.optim import SGD


def test_random_state():
    n, d = 20, 2
    random_state = 10

    rng = check_random_state(random_state)
    answers = rng.choice(n, size=(4 * n, 3))

    kwargs = dict(
        module=embed.STE,
        module_kwargs={"n": n, "d": 2},
        optimizer=SGD,
        optimizer_kwargs={"nesterov": True, "lr": 0.1, "momentum": 0.9},
        random_state=random_state,
    )

    est1 = embed.Embedding(**kwargs)
    est2 = embed.Embedding(**kwargs)

    est1.partial_fit(answers)
    est2.partial_fit(answers)
    assert np.allclose(est1.embedding, est2.embedding)

    s1 = est1.score(answers)
    s2 = est2.score(answers)
    assert np.allclose(s1, s2)
