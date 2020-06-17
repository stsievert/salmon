import numpy as np
import numpy.linalg as LA
import pandas as pd
import pytest

from .. import gram_utils
from .. import _utilsSTE as utilsSTE
from .. import _search as search

def old_score(q, tau, X):
    """
    copy/pasted from STE/myApp.py's getQuery
    (slightly modified)
    """
    n = X.shape[0]
    a, b, c = q
    # q = random_query(n) == [head, winner, loser]
    # utilsSTE.getRandomQuery == [winner, loser, head]
    # this is from utilsSTE.py#getRandomQuery and myAlg.py#get_query (which calls utilsSTE#getRandomQuery)
    # from myAlg.py#getQuery: b, c, a = q
    #                   (winner, loser, head)
    a, b, c = q
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


def test_probs():
    X = np.random.randn(10, 2)
    h, o1, o2 = [1, 2, 3]
    p1 = utilsSTE.getSTETripletProbability(X[o1], X[o2], X[h])

    d1 = LA.norm(X[h] - X[o1]) ** 2
    d2 = LA.norm(X[h] - X[o2]) ** 2
    p2 = search.STE_probs(d1, d2)
    assert np.allclose(p1, p2)


def test_score_refactor():
    n, d = 40, 2
    X = np.random.randn(n, d)
    G = X @ X.T
    D = gram_utils.distances(G)
    tau = np.random.rand(n, n)

    queries = [search.random_query(n) for _ in range(100)]
    old_scores = [old_score(q, tau, X) for q in queries]
    new_scores = [search.score(q, tau, D) for q in queries]

    old = np.array(old_scores)
    new = np.array(new_scores)
    assert np.allclose(old, new)


def test_probs_vector():
    X = np.random.randn(20, 2)
    n = X.shape[0]
    G = X @ X.T
    D = gram_utils.distances(G)

    for w, l in [(3, 5), (5, 3), (1, 4), (4, 1), (10, 15), (15, 10)]:
        p1 = [utilsSTE.getSTETripletProbability(X[w], X[l], X[i]) for i in range(n)]
        p2 = search.STE_probs(D[w], D[l])
        assert np.allclose(p1, p2)


def test_posterior():
    """
    The two searches have different orderings for their queries.

    This depends on that ordering being correct. To resolve any differences,
    switch the ordering here. [[w, l, h] for h, w, l in S_D]
    """
    np.random.seed(42)
    n, d = 40, 2
    X = np.random.randn(n, d)
    G = X @ X.T
    D = gram_utils.distances(G)

    S_D = [search.random_query(n) for _ in range(200)]
    S_X = [[w, l, h] for h, w, l in S_D]

    new = search.posterior(D, S_D)
    old = utilsSTE.getSTETauDistribution(X, S_X)
    assert np.allclose(new, old)


def test_decide_distance():
    np.random.seed(42)
    n, d = 40, 2
    X = np.random.randn(n, d)
    G = X @ X.T
    D = gram_utils.distances(G)

    queries = [search.random_query(n) for _ in range(50)]
    info1 = [search.decide(D, *q, distance=True, random=False) for q in queries]
    info2 = [search.decide(X, *q, distance=False, random=False) for q in queries]

    queries1 = [info[0] for info in info1]
    queries2 = [info[0] for info in info2]
    assert queries1 == queries2


def test_correct_prob():
    np.random.seed(42)
    n, d = 40, 2
    X = np.random.randn(n, d)
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


def test_agrees_with_embedding():
    np.random.seed(42)
    n, d = 40, 2
    X = np.random.randn(n, d)
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
