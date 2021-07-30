import numpy as np
import numpy.linalg as LA
import pytest
import scipy.spatial
import torch
from sklearn.utils import check_random_state

from .. import gram_utils


@pytest.mark.parametrize("n", [10, 20, 40])
@pytest.mark.parametrize("d", [2, 3])
def test_decompose_gram(n, d, seed=None):
    rng = check_random_state(seed)
    X = rng.randn(n, d)
    G = X @ X.T

    X_hat = gram_utils.decompose(G, d)

    assert not np.allclose(X, X_hat)
    Y1, Y2, m = scipy.spatial.procrustes(X, X_hat)
    assert m < 1e-15
    assert np.allclose(Y1, Y2)
    G_hat = X_hat @ X_hat.T
    assert np.allclose(G, G_hat)


@pytest.mark.parametrize("n", [10, 20, 40])
@pytest.mark.parametrize("d", [1, 2, 3])
def test_project_and_is_psd(n, d, seed=None):
    rng = check_random_state(seed)
    X = rng.randn(n, d)
    G = gram_utils.gram_matrix(X)
    assert gram_utils.is_psd(G)
    lamduhs, vecs = LA.eigh(G)
    lamduhs[0] = -1
    G = vecs.T @ np.diag(lamduhs) @ vecs
    assert not gram_utils.is_psd(G)

    F = gram_utils.onto_psd(G)
    assert not np.allclose(F, G)

    l2, _ = LA.eigh(F)
    assert np.allclose(min(l2), 0)


def test_project_changes_torch():
    n, d, seed = 20, 2, None
    rng = check_random_state(seed)
    X = torch.randn(n, d)

    G = gram_utils.gram_matrix(X.numpy())
    lamduhs, vecs = LA.eigh(G)
    lamduhs[0] = -1
    G = vecs.T @ np.diag(lamduhs) @ vecs
    G = torch.from_numpy(G)
    e, v = torch.symeig(G)
    assert e.min().item() < -0.5

    before = G.numpy().copy()
    after = gram_utils.onto_psd(G.numpy(), out=G.numpy())

    assert not np.allclose(before, after)
    assert not torch.allclose(torch.from_numpy(before), G)
    e, v = torch.symeig(G)
    assert e.min() > -0.25


def test_project_no_change_with_pos_eig(n=20, d=2, seed=None):
    rng = check_random_state(seed)
    X = rng.randn(n, d)
    G = gram_utils.gram_matrix(X)
    lamduhs, vecs = LA.eigh(G)
    lamduhs += lamduhs.min() + 1
    G = vecs.T @ np.diag(lamduhs) @ vecs

    F = gram_utils.onto_psd(G)
    assert np.allclose(F, G)


def test_gram_generation(seed=None, n=20, d=2):
    rng = check_random_state(seed)
    X = rng.randn(n, d)
    G_star = X @ X.T
    G_hat = gram_utils.gram_matrix(X)
    assert np.allclose(G_star, G_hat)
    assert np.allclose(G_hat, G_hat.T)

    for i, g_star in enumerate(G_star):
        for j, g_hat in enumerate(G_hat):
            assert np.allclose(G_hat[i, j], np.inner(X[i], X[j]))


def test_distances(seed=None, n=20, d=4):
    rng = check_random_state(seed)
    X = rng.randn(n, d)
    G = X @ X.T

    D = gram_utils.distances(G)

    D_star = scipy.spatial.distance.pdist(X) ** 2
    D_star = scipy.spatial.distance.squareform(D_star)
    assert np.allclose(D, D_star)


def test_dist2(seed=None):
    rng = check_random_state(seed)
    n, d = 10, 2
    X = rng.randn(n, d)
    G = X @ X.T

    inds = [rng.choice(n, size=2, replace=False) for _ in range(100)]
    dists = [LA.norm(X[i[0]] - X[i[1]]) ** 2 for i in inds]
    gram_dists1 = [gram_utils.dist2(G, i[0], i[1]) for i in inds]
    gram_dists2 = [gram_utils.dist2(G, i[1], i[0]) for i in inds]
    assert np.allclose(dists, gram_dists1)
    assert np.allclose(dists, gram_dists2)
