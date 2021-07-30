from typing import Union

import numpy as np
import numpy.linalg as LA
import scipy
import torch
from scipy.linalg import eigh
from scipy.spatial import procrustes

Array = Union[np.ndarray, torch.Tensor]


def decompose(G, d):
    """
    Arguments
    ---------
    G : ndarray
        Gram matrix; X @ X.T
    d : int
        Dimension of each vector in X; X.shape == (n, d)
        when G.shape == (n, n)

    Returns
    -------
    X : ndarray
        Points that make up gram matrix
    """
    assert_gram(G)
    n = G.shape[0]
    w, v = eigh(G)
    i = [idx for idx in range(n - d, n)]
    assert len(i) == d
    X_hat = np.diag(np.sqrt(w[i])) @ (v[:, i]).T
    return X_hat.T


def gram_matrix(X: Array) -> Array:
    """
    Get Gram matrix from embedding

    Arguments
    ---------
    X : Array
        Embedding. X.shape == (num_items, item_dim)

    Returns
    -------
    G : Array
        Gram matrix. G.shape == (n, n)
    """
    if isinstance(X, torch.Tensor):
        return X @ X.transpose(0, 1)
    return X @ X.T


def distances(G: Array) -> Array:
    """
    Get distance matrix from gram matrix

    Arguments
    ---------
    G : Array
        Gram matrix. G.shape == (n, n) for n objects

    Returns
    -------
    D : Array
        Distance matrix. D.shape == (n, n)
    """
    assert_gram(G)
    G1 = np.diag(G).reshape(1, -1)
    G2 = np.diag(G).reshape(-1, 1)

    D = -2 * G + G1 + G2
    return D


def dist2(G, a, b):
    # assert_gram(G)
    return G[a, a] + G[b, b] - 2 * G[a, b]


def is_psd(G, return_vals=False):
    s = eigh(G, eigvals_only=True)
    psd = 0 <= s.min() or s.min() > -3e-7
    return psd if not return_vals else (psd, s)


def onto_psd(G, one=True, out=None):
    """
    Project onto semi-positive definite cone
    """
    # assert_gram(G)
    if out is None:
        out = G.copy()
    s, v = eigh(out, eigvals=(0, 0))
    assert s.shape == (1,)
    assert v.shape[1] == 1
    v = v.flat[:]
    if s < 0:
        out -= s * np.outer(v, v)
    return out


def assert_embedding(X):
    n, d = X.shape
    assert n != d


def assert_gram(G):
    pass


#     if isinstance(G, torch.Tensor):
#         assert torch.allclose(G, G.transpose(0, 1))
#         m = torch.abs(torch.diag(G) / torch.norm(G))
#         assert not np.allclose(m.sum().item(), 0)
#     else:
#         assert np.allclose(G, G.T)
#         assert not np.allclose(np.diag(G) / LA.norm(G), 0)


def assert_distance(D):
    pass


#     assert np.abs(np.diag(D)).sum() < 1e-6
#     assert np.allclose(D, D.T)
