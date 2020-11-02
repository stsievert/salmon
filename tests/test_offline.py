import numpy as np
import numpy.linalg as LA
import pandas as pd
from sklearn.model_selection import train_test_split
from pathlib import Path
import pytest

from salmon.triplets.algs import TSTE
from salmon.triplets.offline import OfflineEmbedding


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


def test_offline_embedding():
    p = Path(__file__).absolute().parent / "data" / "responses.csv.zip"
    df = pd.read_csv(str(p))
    X = df[["head", "winner", "loser"]].to_numpy()

    n = int(X.max() + 1)
    d = 2  # embed into 2 dimensions

    X_train, X_test = train_test_split(X, random_state=0, test_size=0.2)
    model = OfflineEmbedding(n=n, d=d, max_epochs=3)
    model.fit(X_train, X_test)
    assert isinstance(model.embedding_, np.ndarray)
    assert model.embedding_.shape == (n, d)

    assert isinstance(model.history_, list)
    assert all(isinstance(h, dict) for h in model.history_)
    assert len(model.history_) == 3 + 1


def test_offline_embedding_adaptive():
    p = Path(__file__).absolute().parent / "data" / "responses.csv.zip"
    df = pd.read_csv(str(p))

    n = int(df["head"].max() + 1)
    d = 2

    adaptive = df.alg_ident == "TSTE"
    cols = ["head", "winner", "loser"]
    X_test = df.loc[~adaptive, cols].to_numpy()
    X_train = df.loc[adaptive, cols].to_numpy()

    model = OfflineEmbedding(n=n, d=d, max_epochs=4, weight=True)
    with pytest.raises(TypeError, match="`scores` is required"):
        model.fit(X_train, X_test)
    with pytest.raises(ValueError, match="length mismatch"):
        model.fit(X_train, X_test, scores=[1, 2, 3])

    model.fit(X_train, X_test, scores=df.loc[adaptive, "score"])
    assert isinstance(model.embedding_, np.ndarray)
    assert model.embedding_.shape == (n, d)

    assert isinstance(model.history_, list)
    assert all(isinstance(h, dict) for h in model.history_)
    assert len(model.history_) == 4 + 1
