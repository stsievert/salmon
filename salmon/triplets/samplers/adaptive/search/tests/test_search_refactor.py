import numpy as np
import numpy.linalg as LA
import pandas as pd
import pytest
from sklearn.utils import check_random_state

from salmon.triplets.samplers.adaptive import STE, TSTE, InfoGainScorer

from .. import _search as search
from .. import gram_utils
from . import utilsSTE


def test_probs():
    rng = check_random_state(0)
    n, d = 10, 2
    X = rng.randn(n, d)

    N = 100
    queries = [search.random_query(10) for _ in range(N)]
    p1 = [
        utilsSTE.getSTETripletProbability(X[o1], X[o2], X[h]) for h, o1, o2 in queries
    ]
    p1 = np.array(p1)

    d1 = np.array([LA.norm(X[h] - X[o1]) ** 2 for h, o1, o2 in queries])
    d2 = np.array([LA.norm(X[h] - X[o2]) ** 2 for h, o1, o2 in queries])
    p2 = search.STE_probs(d1, d2)
    assert np.allclose(p1, p2)

    p3 = search.exp_STE_probs(d1, d2)

    i = p2 > 0.5
    assert N / 3 <= i.sum() <= N * (1 - 1 / 3)
    assert (p3[i] > 0.5).all()


# @pytest.mark.xfail(reason="unknown bug (but negative scores provide adaptive gains)")
def test_score_refactor(seed=None):
    n, d = 40, 2
    rng = check_random_state(seed)
    X = rng.randn(n, d)
    G = X @ X.T
    D = gram_utils.distances(G)
    tau = rng.rand(n, n)
    for i in range(n):
        tau[i] /= tau[i].sum()

    queries = [search.random_query(n) for _ in range(100)]
    # old_score has been refactored to take in [h, w, l]
    old_scores = [_score_next([w, l, h], tau, X) for h, w, l in queries]

    Q = np.asarray(queries)
    H, W, L = Q[:, 0].flatten(), Q[:, 1].flatten(), Q[:, 2].flatten()
    new_scores = search.score(H, W, L, tau, D)

    old = np.array(old_scores)
    new = np.array(new_scores)
    assert np.allclose(old, new)


def test_probs_vector(seed=None):
    rng = check_random_state(seed)
    X = rng.randn(20, 2)
    n = X.shape[0]
    G = X @ X.T
    D = gram_utils.distances(G)

    for w, l in [(3, 5), (5, 3), (1, 4), (4, 1), (10, 15), (15, 10)]:
        p1 = [utilsSTE.getSTETripletProbability(X[w], X[l], X[i]) for i in range(n)]
        p2 = search.STE_probs(D[w], D[l])
        assert np.allclose(p1, p2)


def test_posterior(seed=None):
    """
    The two searches have different orderings for their queries.

    This depends on that ordering being correct. To resolve any differences,
    switch the ordering here. [[w, l, h] for h, w, l in S_D]
    """
    rng = check_random_state(seed)
    n, d = 40, 2
    X = rng.randn(n, d)
    G = X @ X.T
    D = gram_utils.distances(G)

    S_D = [search.random_query(n) for _ in range(200)]
    S_X = [[w, l, h] for h, w, l in S_D]

    new = search.posterior(D, S_D)
    old = utilsSTE.getSTETauDistribution(X, S_X)
    assert np.allclose(new, old)
    assert (new > 0).all()
    assert np.allclose(new.sum(axis=1), 1)


def test_posterior_v2(seed=None):
    """
    The two searches have different orderings for their queries.

    This depends on that ordering being correct. To resolve any differences,
    switch the ordering here. [[w, l, h] for h, w, l in S_D]
    """
    rng = check_random_state(seed)
    n, d = 40, 2
    X = rng.randn(n, d)
    G = X @ X.T
    D = gram_utils.distances(G)

    S_new = [search.random_query(n) for _ in range(200)]
    S_old = [[w, l, h] for h, w, l in S_new]

    new = search.posterior_embed(X, S_new)
    old = utilsSTE.getSTETauDistribution(X, S_old)
    assert np.allclose(new, old)
    assert (new > 0).all()
    assert np.allclose(new.sum(axis=1), 1)


def test_decide_distance(seed=None):
    rng = check_random_state(seed)
    n, d = 40, 2
    X = rng.randn(n, d)
    G = X @ X.T
    D = gram_utils.distances(G)

    queries = [search.random_query(n) for _ in range(50)]
    info1 = [search.decide(D, *q, distance=True, random=False) for q in queries]
    info2 = [search.decide(X, *q, distance=False, random=False) for q in queries]

    queries1 = [info[0] for info in info1]
    queries2 = [info[0] for info in info2]
    assert queries1 == queries2


def test_correct_prob(seed=None):
    rng = check_random_state(seed)
    n, d = 40, 2
    X = rng.randn(n, d)
    G = X @ X.T
    D = gram_utils.distances(G)

    queries = [search.random_query(n) for _ in range(10)]
    meta = [search.decide(X, *q)[1] for q in queries]
    queries = [search.decide(X, *q)[0] for q in queries]
    df = pd.DataFrame(meta)

    # cases where agrees with embedding X (distance more than 0)
    agrees = 0 < df.dist
    assert (0.5 < df["prob"][agrees]).all()

    # cases where disagrees with embedding (distance is less than 0)
    disagrees = df.dist < 0
    assert (df["prob"][disagrees] < 0.5).all()


def test_agrees_with_embedding(seed=None):
    rng = check_random_state(seed)
    n, d = 40, 2
    X = rng.randn(n, d)
    G = X @ X.T
    D = gram_utils.distances(G)

    # Make sure positive distance means query fits embedding
    queries = [search.random_query(n) for _ in range(10)]
    queries = [search.decide(X, *q, random=False)[0] for q in queries]
    meta = [search.decide(X, *q)[1] for q in queries]
    df = pd.DataFrame(meta)
    agrees = 0 < df.dist

    assert agrees.all()
    for head, winner, loser in queries:
        assert LA.norm(X[head] - X[winner]) < LA.norm(X[head] - X[loser])


def test_internal_search_refactor():
    """ Test to make sure Salmon search v1 and v2 produce the same results """
    n, d = 85, 2
    X = np.random.randn(n, d).astype("float32")
    G = gram_utils.gram_matrix(X)
    D = gram_utils.distances(G)
    tau = np.random.uniform(size=(n, n))

    Q = [
        (h, o1, o2)
        for h in range(n)
        for o1 in set(range(n)) - {h}
        for o2 in set(range(n)) - {h, o1}
    ]
    Q = Q[:30_000]
    s_old = [search._score_v1((h, o2, o1), tau, D) for h, o1, o2 in Q]

    Q = np.array(Q).astype(int)
    s_new = search.score(Q[:, 0], Q[:, 1], Q[:, 2], tau, D)
    assert np.allclose(s_new, np.array(s_old))


def _simple_triplet(n, rng, p_flip=0.1):
    h, a, b = rng.choice(n, size=3, replace=False)
    if abs(h - a) < abs(h - b):
        ret = [h, a, b]
    ret = [h, b, a]

    flip = rng.uniform(0, 1)
    if flip < p_flip:
        return [ret[0], ret[1], ret[0]]
    return ret


def test_salmon_integration():
    import warnings

    warnings.filterwarnings("error")
    n, d = 10, 2
    rng = np.random.RandomState(42)
    X = rng.randn(n, d).astype("float32")
    est = TSTE(n)
    search = InfoGainScorer(embedding=X, probs=est.probs)
    history = [_simple_triplet(n, rng) for _ in range(1000)]
    search.push(history)
    queries, scores = search.score()

    # This is the right order: queries are stored in next as (w, l, h). See myApp.py#L93.
    next_history = [[w, l, h] for h, w, l in history]
    tau = utilsSTE.getSTETauDistribution(X, next_history)

    rel_error = LA.norm(tau - search.posterior_) / LA.norm(tau)
    post = search.posterior_
    err = np.abs(search.posterior_ / tau)
    assert rel_error < 0.01

    # Making sure posterior approximately correct
    eps = 3e-3
    assert np.allclose(np.median(err), 1)
    assert 1 - eps <= np.percentile(err, 1) <= np.percentile(err, 99) <= 1 + eps

    # Make sure scores are all negative (because only negative entropy
    # part of information gain)
    next_scores = np.array([_score_next(q, tau, X) for q in next_history])
    _, salmon_scores = search.score(queries=history)
    assert (salmon_scores <= 0).all()

    # Make sure scores are close to each other
    rel_err = LA.norm(next_scores - salmon_scores) / LA.norm(next_scores)
    assert rel_err <= 1e-5

    diff = np.abs(next_scores - salmon_scores)
    assert 0 <= diff.min() <= diff.max() <= 2e-5
    assert diff.mean() <= 1e-5
    assert np.median(diff) <= 1e-5


def test_salmon_posterior_refactor(n=30, d=2):
    rng = np.random.RandomState(42)
    X = rng.randn(n, d).astype("float32")
    est = TSTE(n)
    search = InfoGainScorer(embedding=X, probs=est.probs)
    history = [_simple_triplet(n, rng) for _ in range(2000)]
    search.push(history)
    queries, scores = search.score()

    next_history = [[w, l, h] for h, w, l in history]
    tau = utilsSTE.getSTETauDistribution(X, next_history)

    rel_error = LA.norm(tau - search.posterior_) / LA.norm(tau)
    assert rel_error < 10e-6

    ratio = np.abs(search.posterior_ / tau)
    assert ratio.max() - ratio.min() < 0.1e-3
    assert pytest.approx(ratio.mean()) == 1


def _score_next(q: [int, int, int], tau, X):
    """
    copy/pasted from STE/myApp.py's getQuery
    (slightly modified)
    """
    n = X.shape[0]
    #  a, b, c = q
    # q = random_query(n) == [head, winner, loser]
    # utilsSTE.getRandomQuery == [winner, loser, head]
    # this is from utilsSTE.py#getRandomQuery and myAlg.py#get_query (which calls utilsSTE#getRandomQuery)
    # from myAlg.py#getQuery: b, c, a = q
    #                   (winner, loser, head)
    #  a, b, c = q
    b, c, a = q
    p = 0
    for i in range(n):
        p += utilsSTE.getSTETripletProbability(X[b], X[c], X[i]) * tau[a, i]

    taub = list(tau[a])
    for i in range(n):
        taub[i] = taub[i] * utilsSTE.getSTETripletProbability(X[b], X[c], X[i])
    taub = taub / sum(taub)

    tauc = list(tau[a])
    for i in range(n):
        tauc[i] = tauc[i] * utilsSTE.getSTETripletProbability(X[c], X[b], X[i])
    tauc = tauc / sum(tauc)

    entropy = -p * utilsSTE.getEntropy(taub) - (1 - p) * utilsSTE.getEntropy(tauc)
    return entropy
