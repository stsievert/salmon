import itertools
import math
from time import time
from typing import Tuple, Union

import numpy as np
import numpy.linalg as LA
import torch

try:
    from . import gram_utils
except:
    import gram_utils

Array = Union[np.ndarray, torch.Tensor]


def random_query(n):
    rng = np.random.RandomState()
    while True:
        a = rng.choice(n)
        b = rng.choice(n)
        c = rng.choice(n)
        if a != b and b != c and c != a:
            break
    return [a, b, c]


def embedding_matches(ans, D):
    """
    Parameters
    ----------
    ans = List[int], [head, winner, loser].
        Indices of the head/winner/loser
    D : np.ndarray
        Distance matrix

    Returns
    -------
    ans : int
        1 if agrees with D, 0 if doesn't
    """
    head, winner, loser = ans
    return D[head, winner] < D[head, loser]


def decide(D, head, winner, loser, distance=False, random=True):
    """
    Inputs
    ------
    D : np.ndarray
        Distance or embedding matrix.
        If embedding, n points in d dimensions. D.shape == (n, d)
        If distance, D[a, b] is distance between objects a and b.
    head, winner, loser: int
        Indices of head, winner and loser

    Returns
    -------
    prob : float
        The probability the triplet is satisfied
    """
    if distance:
        gram_utils.assert_distance(D)
        d_winner = D[head, winner]
        d_loser = D[head, loser]
    else:
        gram_utils.assert_embedding(D)
        d_winner = LA.norm(D[head] - D[winner]) ** 2
        d_loser = LA.norm(D[head] - D[loser]) ** 2
    if not random:
        q = [head, winner, loser] if d_winner < d_loser else [head, loser, winner]
        return q, {}

    # 0 < dist: agrees with embedding (d_loser > d_winner)
    dist = d_loser - d_winner  # >0: agrees with embedding. <0: does not agree.
    try:
        prob = 1 / (1 + np.exp(-dist))
    except FloatingPointError:
        prob = 0
    # d1 = d_winner, d2 = d_loser
    # = 1 / (1 + exp(-d2 + d1))
    # = 1 / (1 + exp(-d2 / -d1))
    # = exp(-d1) / (exp(-d1) + exp(d2))

    meta = {"prob": prob, "dist": dist}
    if np.random.rand() < prob:
        return [head, winner, loser], meta
    return [head, loser, winner], meta


def STE_probs(d1, d2, alpha=1):
    """
    Returns the probability that triplet wins
    """
    c = -(alpha + 1.0) / 2
    t1 = (1 + d1 / alpha) ** c
    t2 = (1 + d2 / alpha) ** c
    return t1 / (t1 + t2)


def exp_STE_probs(d2_winner, d2_loser):
    # dist>0: agrees with embedding. <0: does not agree.
    # d1 = d2_winner, d2 = d2_loser
    # 1 / (1 + exp(d1 - d2))
    # = 1 / (1 + exp(-d2 + d1))
    # = 1 / (1 + exp(-d2 / -d1))
    # = exp(-d1) / (exp(-d1) + exp(d2))
    # = prob of winning by STE
    return 1 / (1 + np.exp(d2_winner - d2_loser))


def entropy(x):
    if x.ndim == 1:
        i = x > 0
        y = x[i].copy()
        return (-1 * y * np.log(y)).sum()
    elif x.ndim == 2:
        i = np.argwhere(x > 0)
        y = x.copy()
        idx = (i[:, 0], i[:, 1])
        ret = -1 * y[idx] * np.log(y[idx])
        y[idx] = ret
        return np.sum(y, axis=1)
    else:
        raise ValueError("Invalid number of dimensions in input ``x``")


def posterior(D, S, alpha=1):
    gram_utils.assert_distance(D)
    n = D.shape[0]
    tau = np.zeros((n, n))
    for head, w, l in S:
        tau[head] += np.log(STE_probs(D[w], D[l], alpha=alpha))

    tau = np.exp(tau)
    s = tau.sum(axis=1)  # the sum of each row
    tau = (tau.T / s).T
    return tau


def getSTETripletProbability(i, j, k, alpha=1):
    """
    Return the probability of triplet [i,l,j] where a is closer to b than c.

    Namely:
    pabc = (1 + || c - a||^2/alpha)**(-(alpha+1)/2)/(2*alpha + || b - a ||^2+|| c - a ||^2)

    Inputs:
        (numpy.ndarray) a : numpy array
        (numpy.ndarray) b : numpy array
    (numpy.ndarray) c : numpy array
        (float) alpha : regularization parameter
    """
    ki = LA.norm(k - i)
    kj = LA.norm(k - j)
    c = -(alpha + 1.0) / 2
    return (1 + ki * ki / alpha) ** c / (
        (1 + ki * ki / alpha) ** c + (1 + kj * kj / alpha) ** c
    )


def posterior_orig(X, S, alpha=1):
    n = X.shape[0]
    tau = np.zeros((n, n))
    # Loop over each query
    for h, w, l in S:
        # Multiply by the amount the query contributes to each tau
        for i in range(n):
            tau[h, i] = tau[h, i] + math.log(
                getSTETripletProbability(X[w], X[l], X[i], alpha=alpha)
            )

    # Normalize -- make each row a PDF
    for a in range(n):
        tau[a] = np.exp(tau[a])
        s = sum(tau[a])
        tau[a] = tau[a] / s

    return tau


def posterior_embed(X, S, alpha=1):
    n = X.shape[0]
    tau = np.zeros((n, n))
    # Loop over each query
    for h, w, l in S:
        # Multiply by the amount the query contributes to each tau
        for i in range(n):
            tau[h, i] = tau[h, i] + math.log(
                getSTETripletProbability(X[w], X[l], X[i], alpha=alpha)
            )

    # Normalize -- make each row a PDF
    for i, a in enumerate(range(n)):
        ex = np.exp(tau[a])
        tau[a] = ex / ex.sum()

    return tau


def _score_v1(q: Tuple[int, int, int], tau: np.ndarray, D: np.ndarray) -> float:
    gram_utils.assert_distance(D)
    # head, o1, o2 = q
    head, w, l = q

    probs = STE_probs(D[w], D[l])  # probs.shape == (n, )
    eps = 1e-16
    # mask = (eps < np.abs(probs)) & (eps < np.abs(tau[head]))
    # mask = -1 < np.abs(probs)  # all probs

    p = (probs * tau[head]).sum()  # tau[head].shape == (n, )

    taub = tau[head] * probs
    taub /= taub.sum()

    tauc = tau[head] * (1 - probs)
    tauc /= tauc.sum()

    _entropy = -p * entropy(taub) - (1 - p) * entropy(tauc)
    return _entropy


def score(H: Array, W: Array, L: Array, tau: Array, D: Array, probs=STE_probs) -> Array:
    """
    Find the information gain for each query.

    Arguments
    ---------
    H, W, L : Array, Array, Array
        1D arrays describing the head and two choices respectively.
        If there are ``q`` questions, each array is of shape ``(q, )``.
    tau : Array
        Posterior, of shape ``(n, n)`` with ``n`` objects.
    D : Array
        Array of distances. Also of shape ``(n, n)``.

    Returns
    -------
    ig : Array of shape ``(q, )``
        The information gain of the queries (minus a constant).

    Notes
    -----

    The information gain of a query is given by the following expression:

    .. math::

       H(\tau) - pH(\tau_b) - (1 - p)H(\tau_a)

    where :math:`H` is the entropy. This

    References
    ----------
    [1] "Adaptively learning the crowd kernel" O. Tamuz, C. Liu,
         S. Belongie, O. Shamir, and A. Kalai. 2011.
         https://arxiv.org/abs/1105.1033

    """
    gram_utils.assert_distance(D)
    assert all(x.dtype.kind == "i" for x in (H, W, L))
    head, w, l = H, W, L
    q = len(head)

    probs = probs(D[l], D[w])  # (q, n)
    # probs = 1 - probs
    probs[np.isnan(probs)] = 0
    assert probs.min() >= 0
    eps = 0e-20
    # probs[probs < 1e-15] = 0

    p = (probs * tau[head]).sum(axis=1)  # (q, )

    _taub = tau[head] * probs  # (q, n)
    _taub[np.isnan(_taub)] = eps
    taub = _taub / (_taub.sum(axis=1).reshape(q, 1) + eps)

    _tauc = tau[head] * (1 - probs)  # (q, n)
    _tauc[np.isnan(_tauc)] = eps
    tauc = _tauc / (_tauc.sum(axis=1).reshape(q, 1) + eps)

    score = -p * entropy(taub) - (1 - p) * entropy(tauc)
    return score
