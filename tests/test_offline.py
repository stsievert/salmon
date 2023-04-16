from pathlib import Path
import yaml
import random
from typing import Dict

import numpy as np
import numpy.linalg as LA
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

from salmon.triplets.offline import OfflineEmbedding
from salmon.triplets.samplers import TSTE
import salmon.triplets.offline

ArrayLike = np.ndarray

def test_salmon_import():
    """This test makes sure that no errors are raised on import
    (non-existant directories, etc)"""
    import salmon

    return True


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
    for head, left, right in X:
        ldist = LA.norm(embed[head] - embed[left])
        rdist = LA.norm(embed[head] - embed[right])

        left_wins = ldist <= rdist
        y_hat2.append(0 if left_wins else 1)

    assert y_hat.tolist() == y_hat2


def test_offline_embedding():
    n, d = 85, 2
    max_epochs = 20

    X = np.random.choice(n, size=(10_000, 3))
    X_train, X_test = train_test_split(X, random_state=0, test_size=0.2)

    model = OfflineEmbedding(n=n, d=d, max_epochs=max_epochs)
    model.fit(X_train, X_test)
    assert isinstance(model.embedding_, np.ndarray)
    assert model.embedding_.shape == (n, d)

    assert isinstance(model.history_, list)
    assert all(isinstance(h, dict) for h in model.history_)
    epochs = model.history_[-1]["num_grad_comps"] / len(X_train)
    eps = 0.75
    assert max_epochs - eps <= epochs <= max_epochs + eps


def test_offline_embedding_random_state():
    n, d = 85, 2
    max_epochs = 20
    random_state = 20

    X = np.random.choice(n, size=(10_000, 3))
    X_train, X_test = train_test_split(X, random_state=0, test_size=0.2)

    m1 = OfflineEmbedding(
        n=n, d=d, max_epochs=max_epochs, random_state=random_state
    ).initialize(X_train)
    m2 = OfflineEmbedding(
        n=n, d=d, max_epochs=max_epochs, random_state=random_state
    ).initialize(X_train)
    assert np.allclose(m1.embedding_, m2.embedding_)


def test_offline_init():
    n, d = 20, 2

    X = np.random.choice(n, size=(100, 3))
    em = np.random.uniform(size=(n, d))
    est = OfflineEmbedding(n=n, d=d)
    est.initialize(X, embedding=em)

    assert np.allclose(est.embedding_, em)
    est.partial_fit(X)
    assert not np.allclose(est.embedding_, em), "Embedding didn't change"


def test_offline_names_correct():
    DIR = Path(__file__).absolute().parent
    _f = DIR / "data" / "active.yaml"
    config = yaml.load(_f.read_text(), Loader=yaml.SafeLoader)
    n = len(config["targets"])
    d = config["sampling"]["common"]["d"]

    X = np.random.choice(n, size=(100, 3))
    est = OfflineEmbedding(n=n, d=d)
    est.partial_fit(X)

    import salmon.triplets.offline as offline

    em = offline.join(est.embedding_, config["targets"])
    assert isinstance(em, pd.DataFrame)
    assert len(em) == len(config["targets"])
    assert set(em.columns) == {"x", "y", "target"}
    assert (em["target"] == config["targets"]).all()


def _answer(q: Dict[str, int], X: ArrayLike) -> int:
    h = X[q["head"]]
    l = X[q["left"]]
    r = X[q["right"]]
    if LA.norm(h - l) < LA.norm(h - r):
        return q["left"]
    return q["right"]

def test_offline_adaptive(n=10, d=1):
    rng = np.random.RandomState(42)
    X = rng.uniform(size=(n, d))
    val_queries = np.asarray([rng.choice(n, size=3, replace=False) for _ in range(5000)])
    val_ans = np.asarray([0 if LA.norm(X[h] - X[l]) < LA.norm(X[h] - X[r]) else 1 for h, l, r in val_queries])

    sampler = TSTE(n=n, d=d, alpha=1, R=1)
    score0 = sampler.score(val_queries, val_ans)
    for t in range(20):
        queries, scores, _ = sampler.get_queries()
        _good_queries = queries[np.argsort(scores)[-4:]]
        good_queries = [{"head": h, "left": o1, "right": o2} for h, o1, o2 in _good_queries]
        answers = [{"winner": _answer(q, X), **q} for q in good_queries]
        sampler.process_answers(answers)

    scorem1 = sampler.score(val_queries, val_ans)
    assert 0 <= score0 <= scorem1 <= 1
    assert score0 + 0.08 < scorem1, "Improves by at least 8% after 200 answers"


if __name__ == "__main__":
    test_offline_init()
    test_offline_embedding_random_state()
    test_offline_embedding()
