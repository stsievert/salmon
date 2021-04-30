import itertools

import numpy as np
from sklearn.utils import check_random_state

from salmon.triplets.samplers import TSTE
from salmon.triplets.samplers.adaptive import InfoGainScorer

from .utils import alien_egg


def dataset(n, num_ans=1000, random_state=42):
    rng = check_random_state(random_state)
    X = rng.choice(n, size=(num_ans, 3)).astype(np.int16)
    repeats = (X[:, 0] == X[:, 1]) | (X[:, 1] == X[:, 2]) | (X[:, 0] == X[:, 2])
    X = X[~repeats]
    assert len(X) >= num_ans * 0.9
    y = [alien_egg(*x, random_state=rng) for x in X]
    return X, y


def answer(X, y):
    answers = [
        {"head": h, "left": l, "right": r, "winner": l if yi == 0 else r}
        for (h, l, r), yi in zip(X, y)
    ]
    alg_ans = [
        (a["head"], a["winner"], a["left"] if a["winner"] == a["right"] else a["right"])
        for a in answers
    ]
    return alg_ans


def test_same_salmon_next(n=40, d=2, num_ans=4000):
    X, y = dataset(n, num_ans=num_ans, random_state=42)
    ans = answer(X, y)

    est = TSTE(n=n, d=d)
    new_embedding = (np.arange(n * d) // d).reshape(n, d).astype("float32")

    for s1, s2 in [(30, 10)]:
        new_embedding[s1] = s2
        new_embedding[s2] = s1

    search = InfoGainScorer(embedding=new_embedding, probs=est.opt.module_.probs)
    search.push(ans)

    _, (useful, useless) = search.score(queries=[(29, 30, 10), (29, 11, 28)])
    assert useful > useless

    t = list(range(40))
    queries = [
        (h, o1, o2)
        for h, o1, o2 in itertools.product(t, t, t)
        if h != o1 != o2 and h != o2
    ]
    Q, scores = search.score(queries=queries)
    flipped = [30, 10]
    useful = (
        np.isin(Q[:, 0], flipped)
        | np.isin(Q[:, 1], flipped)
        | np.isin(Q[:, 2], flipped)
    )
    useful = np.isin(Q[:, 1], flipped) & np.isin(Q[:, 2], flipped)
    side_info = [29, 31, 9, 11]
    useful &= np.isin(Q[:, 0], side_info)
    assert scores[useful].mean() > scores[~useful].mean()
    assert np.median(scores[useful]) > np.median(scores[~useful])

    assert np.percentile(scores[~useful], 50) < np.percentile(scores[useful], 23)
    assert np.percentile(scores[~useful], 60) < np.percentile(scores[useful], 25)
    assert np.percentile(scores[~useful], 70) < np.percentile(scores[useful], 30)
    assert np.percentile(scores[~useful], 80) < np.percentile(scores[useful], 50)
    assert np.percentile(scores[~useful], 90) < np.percentile(scores[useful], 75)

    # Another test to make sure that "useless" queries have lower scores than
    # "useful" queries.
    all_queries = set(range(40))
    good_items = sum([list(range(q - 4, q + 4 + 1)) for q in side_info + flipped], [])
    useless = np.isin(Q[:, 0], list(all_queries - set(good_items)))
    useless |= np.isin(Q[:, 1], list(all_queries - set(good_items)))
    useless |= np.isin(Q[:, 2], list(all_queries - set(good_items)))

    assert -1.1 < np.median(scores[useless]) + 0.3 < np.median(scores[useful]) < -0.75
    assert -1.13 < scores[useless].mean() + 0.19 < scores[useful].mean() < -0.93
    assert -1.85 < scores[useless].min() < scores[useful].min() < -1.46

    p = np.percentile
    assert -1.29 < p(scores[useless], 30) < p(scores[useful], 19) < -1.23
    assert -1.17 < p(scores[useless], 40) < p(scores[useful], 23) < 1.04
    assert -1.10 < p(scores[useless], 50) < p(scores[useful], 24) < -0.98
    assert -1.05 < p(scores[useless], 60) < p(scores[useful], 25) < -0.94
    assert -0.93 < p(scores[useless], 70) < p(scores[useful], 26) < -0.90
    assert -0.80 < p(scores[useless], 85) < p(scores[useful], 30) < -0.77
    assert -0.76 < p(scores[useless], 90) < p(scores[useful], 80) < -0.74
