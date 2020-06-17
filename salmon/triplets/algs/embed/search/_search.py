import numpy as np
import numpy.linalg as LA


def random_query(n):
    return np.random.choice(n, replace=False, size=3)


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
        d_winner = D[head, winner]
        d_loser = D[head, loser]
    else:
        d_winner = LA.norm(D[head] - D[winner]) ** 2
        d_loser = LA.norm(D[head] - D[loser]) ** 2
    if not random:
        q = [head, winner, loser] if d_winner < d_loser else [head, loser, winner]
        return q, {}

    # 0 < dist: agrees with embedding (d_loser > d_winner)
    dist = d_loser - d_winner  # >0: agrees with embedding. <0: does not agree.
    prob = 1 / (1 + np.exp(-dist))
    # d1 = d_winner, d2 = d_loser
    # = 1 / (1 + exp(-d2 + d1))
    # = 1 / (1 + exp(-d2 / -d1))
    # = exp(-d1) / (exp(-d1) + exp(d2))

    meta = {"prob": prob, "dist": dist}
    if np.random.rand() < prob:
        return [head, winner, loser], meta
    return [head, loser, winner], meta


def score(q, tau, D):
    head, o1, o2 = q

    probs = STE_probs(D[o1], D[o2])
    eps = 1e-16
    #     mask = (eps < np.abs(probs)) & (eps < np.abs(tau[head]))
    mask = -1 < np.abs(probs)  # all probs

    p = (probs[mask] * tau[head, mask]).sum()

    taub = tau[head, mask] * probs[mask]
    taub /= taub.sum()

    tauc = tau[head, mask] * (1 - probs[mask])
    tauc /= tauc.sum()

    entropy = -p * _entropy(taub) - (1 - p) * _entropy(tauc)
    return entropy


def STE_probs(d1, d2, alpha=1):
    """
    Returns the probability that
    """
    c = -(alpha + 1.0) / 2
    top = (1 + d1 / alpha) ** c
    return top / (top + (1 + d2 / alpha) ** c)


def _entropy(x):
    i = x > 0
    y = x[i]
    return (-1 * y * np.log(y)).sum()


def posterior(D, S, alpha=1):
    n = D.shape[0]
    tau = np.zeros((n, n))
    for q in S:
        head, w, l = q
        tau[head] += np.log(STE_probs(D[w], D[l], alpha=alpha))

    #     tau = np.exp(tau)
    #     s = tau.sum(axis=1)  # the sum of each row
    #     tau = (tau.T / s).T

    tau = np.exp(tau)
    for a in range(n):
        s = sum(tau[a])
        mask = -1 < np.abs(tau[a])
        tau[a, mask] = tau[a, mask] / s
    return tau
