import numpy as np
import numpy.linalg as LA

from salmon.triplets.samplers.adaptive import UncertaintyScorer


def test_uncertainty_sampling(random_state=42):
    n, d = 100, 2
    rng = np.random.RandomState(random_state)
    X = rng.uniform(size=(n, d))

    search = UncertaintyScorer(embedding=X)
    queries, scores = search.score(num=100)
    distances = [
        abs(LA.norm(X[h] - X[l]) ** 2 - LA.norm(X[h] - X[r]) ** 2)
        for h, l, r in queries
    ]
    idx_best_score = np.argmax(scores)
    assert np.allclose(distances[idx_best_score], min(distances))
