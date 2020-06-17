import numpy as np
import scipy
from scipy.linalg import eigh
import numpy.linalg as LA
from scipy.spatial import procrustes
from scipy.linalg import eigh

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
    n = G.shape[0]
    w, v = eigh(G)
    i = [idx for idx in range(n - d, n)]
    assert len(i) == d
    X_hat = np.diag(np.sqrt(w[i])) @ (v[:, i]).T
    return X_hat.T


def distances(G):
    G1 = np.diag(G).reshape(1, -1)
    G2 = np.diag(G).reshape(-1, 1)

    D = -2 * G + G1 + G2
    return D


def dist2(G, a, b):
    return G[a, a] + G[b, b] - 2 * G[a, b]


def project(G, one=True, out=None):
    """
    Project onto semi-positive definite cone
    """
    if out is None:
        out = G.copy()
        s, v = eigh(out, eigvals=(0, 0))
    assert s.shape == (1,)
    assert v.shape[1] == 1
    v = v.flat[:]
    if s < 0:
        out -= s * np.outer(v, v)
    return out
