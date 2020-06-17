import numpy as np
import pytest
import scipy.spatial
import numpy.linalg as LA

from .. import gram_utils


@pytest.mark.parametrize("n", [20, 40, 80, 160])
@pytest.mark.parametrize("d", [2, 4, 8, 16])
def test_decompose_gram(n, d):
    X = np.random.randn(n, d)
    G = X @ X.T

    X_hat = gram_utils.decompose(G, d)

    assert not np.allclose(X, X_hat)
    Y1, Y2, m = scipy.spatial.procrustes(X, X_hat)
    assert m < 1e-15
    assert np.allclose(Y1, Y2)
    G_hat = X_hat @ X_hat.T
    assert np.allclose(G, G_hat)


@pytest.mark.parametrize("n", [20, 40, 80, 160])
@pytest.mark.parametrize("d", [1, 2, 3])
def test_project(n, d):
    X = np.random.randn(n, d)
    G = X @ X.T
    lamduhs, vecs = LA.eigh(G)
    lamduhs[0] = -1
    G = vecs.T @ np.diag(lamduhs) @ vecs

    F = gram_utils.project(G)
    assert not np.allclose(F, G)

    l2, _ = LA.eigh(F)
    assert np.allclose(min(l2), 0)


@pytest.mark.parametrize("n", [20, 40, 80, 160])
@pytest.mark.parametrize("d", [1, 2, 3])
def test_project_no_change(n, d):
    X = np.random.randn(n, d)
    G = X @ X.T
    lamduhs, vecs = LA.eigh(G)
    lamduhs += lamduhs.min() + 1
    G = vecs.T @ np.diag(lamduhs) @ vecs

    F = gram_utils.project(G)
    assert np.allclose(F, G)


@pytest.mark.parametrize("n", [20, 40, 80, 160])
@pytest.mark.parametrize("d", [2, 4, 8, 16])
def test_dist(n, d):
    X = np.random.randn(n, d)
    G = X @ X.T

    D = gram_utils.distances(G)

    D_star = scipy.spatial.distance.pdist(X) ** 2
    D_star = scipy.spatial.distance.squareform(D_star)
    assert np.allclose(D, D_star)


def test_dist2():
    n, d = 10, 2
    X = np.random.randn(n, d)
    G = X @ X.T

    inds = [np.random.choice(n, size=2, replace=False) for _ in range(100)]
    dists = [LA.norm(X[i[0]] - X[i[1]]) ** 2 for i in inds]
    gram_dists1 = [gram_utils.dist2(G, i[0], i[1]) for i in inds]
    gram_dists2 = [gram_utils.dist2(G, i[1], i[0]) for i in inds]
    assert np.allclose(dists, gram_dists1)
    assert np.allclose(dists, gram_dists2)
