import numpy as np
import numpy.linalg as LA

from salmon.triplets.algs import TSTE


def test_score_predict_basic():
    """Test the interface for score/predict"""
    n = 10
    n_ans = 40
    X = np.random.choice(n, size=(n_ans, 3)).astype("uint8")
    alg = TSTE(n=n, d=2)

    # Test expected interface
    y = np.random.choice(2, size=n_ans).astype("uint8")
    y_hat = alg.predict(X)
    assert y_hat.shape == (n_ans,)
    assert np.unique(y_hat).tolist() == [0, 1]

    acc = alg.score(X, y)
    assert isinstance(acc, float)
    assert 0 <= acc <= 1


def test_score_accurate():
    n = 10
    n_ans = 40
    X = np.random.choice(n, size=(n_ans, 3)).astype("uint8")
    alg = TSTE(n=n, d=2)
    y_hat = alg.predict(X)

    # Make sure perfect accuracy if the output aligns with the embedding
    assert np.allclose(alg.score(X, y_hat), 1)

    # Make sure the score has the expected value (winner has minimum distance)
    embed = alg.opt.embedding() * 1e3
    y_hat2 = []
    for (head, left, right) in X:
        ldist = LA.norm(embed[head] - embed[left])
        rdist = LA.norm(embed[head] - embed[right])

        left_wins = ldist <= rdist
        y_hat2.append(0 if left_wins else 1)

    assert y_hat.tolist() == y_hat2
