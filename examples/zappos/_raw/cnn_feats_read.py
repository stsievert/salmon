import numpy as np
from zipfile import ZipFile

def _divide(n):
    div = len(n) // 2
    idx = n.find(".", 2)
    return n[:idx - 1], n[idx + 1:]


def _reduce(x):
    out = []
    for xi in x:
        if isinstance(xi, tuple):
            for _ in xi:
                out.append(float(_))
        else:
            out.append(float(xi))
    return out

def _get_features(filename: str = "cnn_feats.csv.zip"):
    with ZipFile(filename) as zf:
        with zf.open("cnn_feats.csv") as f:
            lines = f.readlines()
    assert len(lines) == 1
    txt = lines[0].decode("ascii")
    raw = txt.split(",")
    newlines = [i for i, n in enumerate(raw) if n.count(".") == 2]
    mrare = [(n, ) if i not in newlines else _divide(n) for i, n in enumerate(raw)]
    medium = _reduce(mrare)

    mwell = [medium[k * 4096 : (k + 1) * 4096] for k in range(n)]
    well_done = np.array(mwell)
    return well_done

if __name__ == "__main__":
    n = 85
    X = _get_features()
    import pandas as pd
    responses = pd.read_csv("all_triplets.csv.zip")
    responses.columns = ["worker_id", "head", "close", "far"]
