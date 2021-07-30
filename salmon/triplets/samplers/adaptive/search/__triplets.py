from time import time

import gram_utils
import numpy as np
import numpy.linalg as LA
import search
from gram_utils import dist2


def random_query(n):
    return np.random.choice(n, size=3, replace=False)


def update(G, head, winner, loser):
    """
    Perform the update mentioned in [1] (which also uses a Gram matrix)

    [1]:"Efficient online relative comparison kernel learning" by Eric Heim et. al.
    """
    D = gram_utils.distances(G)
    if D[head, winner] < D[head, loser]:
        pred_winner, pred_loser = winner, loser
    else:
        pred_winner, pred_loser = loser, winner

    # probability needs to use the estimated probability
    a = dist2(G, head, pred_winner)
    b = dist2(G, head, pred_loser)
    p_lose = 1 / (1 + np.exp(a - b))
    p_win = 1 - p_lose
    # 1 / (1 + exp(a - b)) = 1 / (1 + exp((-b) - (-a)))
    # = 1 / (1 + exp(-b) / exp(-a))
    # = exp(-a) / (exp(-a) + exp(-b))
    # and
    # a = ||h - w||^2_2
    # b = ||h - l||^2_2
    # p_win \probto exp(-||head - winner||^2) as in the STE paper

    # the amount of change should depend on the actual winner and loser
    # (and not change if it agrees)
    d2_win = dist2(G, head, winner)
    d2_loser = dist2(G, head, loser)
    P = np.log(np.e) / (1 + np.log(np.e))
    P = 0.8
    kappa = np.log(P) - np.log(1 - P)
    aggressive = d2_win - d2_loser + kappa
    step_size = max(0, aggressive)
    amount = step_size * (1 - p_win)

    # performing G = G - (amount * grad)
    # (grad given by 1/2 values)
    # - (x) given by G -= x
    G[head, winner] -= -2 * amount
    G[winner, head] -= -2 * amount
    G[head, loser] -= 2 * amount
    G[loser, head] -= 2 * amount
    G[winner, winner] -= 1 * amount
    G[loser, loser] -= -1 * amount

    start = time()
    G = gram_utils.project(G)
    # G_max_eig = LA.norm(G, ord=2)
    # if G_max_eig > 10:
    #    G *= 10 / G_max_eig
    svd_time = time() - start
    # if 10 < LA.norm(G):
    #   G /= LA.norm(G)

    # looking to see what vectors have 20 < norm(x)
    max_norm = 2
    too_large = np.argwhere(max_norm ** 2 < np.diag(G))
    norms = np.sqrt(G[too_large, too_large])

    # making sure those vectors x have norm(x) = 20
    for idx, norm in zip(too_large, norms):
        G[idx, :] *= max_norm / norm
        G[:, idx] *= max_norm / norm
    return G


class NoSearch:
    def __init__(self, n, d=2, **kwargs):
        self.n = n
        self.d = d

        self.X = np.random.randn(n, d) / 1000
        self.G = self.X @ self.X.T
        # self.G = np.eye(n)
        # self.X = gram_utils.decompose(self.G, d=self.d)

        self.data = []
        self.num_answers = 0
        self.answers = []

    def get_query(self):
        """
        Returns [head, predicted_winner, predicted_loser]
        """
        return random_query(self.n)

    def process_answer(self, head, winner, loser):
        self.num_answers = len(self.answers)
        num_ans = self.num_answers

        start = time()
        self.G = update(self.G, head, winner, loser)

        beta = self.n
        if num_ans > 2 * beta:
            for i in np.random.choice(num_ans, size=min(20, beta - 1),):
                self.G = update(self.G, *self.answers[i])
        self._times = {"update_time": time() - start}
        if len(self.answers) % self.n == 0:
            self.X = gram_utils.decompose(self.G, d=self.d)
        self.answers += [[head, winner, loser]]


class RandomSearch(NoSearch):
    def __init__(self, n, t_max=0.05, R=10, **kwargs):
        super().__init__(n, **kwargs)
        self.t_max = t_max
        self.tau = np.random.rand(n, n)
        self.n = n
        self.R = R
        self._summary = {"t_max": t_max, "name": type(self).__name__}

    def get_query(self):
        if (
            self.num_answers < self.R * self.n
            or self.t_max == 0
            or np.abs(self.t_max) < 0
            or np.allclose(self.t_max, 0)
        ):
            q = random_query(self.n)
            self._saved = {"query": q, "score": -np.inf, "searched": 0}
            return q

        n, tau, G = self.n, self.tau, self.G
        D = gram_utils.distances(G)

        best_score = -np.inf
        start = time()
        searched = 0
        best_q = random_query(n)
        while time() - start < self.t_max:
            searched += 10
            queries = [random_query(n) for _ in range(10)]
            scores = [search.score(q, tau, D) for q in queries]

            best_idx = np.argmax(scores)
            if best_score < scores[best_idx]:
                best_q = queries[best_idx]
                best_score = scores[best_idx]
        self._saved = {"query": best_q, "score": best_score, "searched": searched}
        return best_q

    def process_answer(self, head, winner, loser):
        super().process_answer(head, winner, loser)
        if self.num_answers % 10 == 0:
            D = gram_utils.distances(self.G)
            self.tau = search.posterior(D, self.answers)

        self.data += [
            {
                "num_answers": self.num_answers,
                "dist2[head, winner]": LA.norm(self.X[head] - self.X[winner]) ** 2,
                "dist2[head, loser]": LA.norm(self.X[head] - self.X[loser]) ** 2,
                **self._times,
                **search.decide(self.X, *self._saved["query"])[1],
                **self._saved,
                **self._summary,
            }
        ]
