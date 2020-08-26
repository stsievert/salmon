import numpy as np
import numpy.linalg as LA
from salmon.triplets.algs.adaptive import UncertaintyScorer


def test_uncertainty_sampling(random_state=42):
    n, d = 100, 2
    rng = np.random.RandomState(random_state)
    X = rng.uniform(size=(n, d))

    search = UncertaintyScorer(embedding=X, random_state=random_state,)
    queries, scores = search.score(num=100)
    distances = [
        abs(LA.norm(X[h] - X[l]) - LA.norm(X[h] - X[r])) for h, l, r in queries
    ]
    idx_best_score = np.argmax(scores)
    assert distances[idx_best_score] == min(distances)
