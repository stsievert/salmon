import random
from time import sleep

import pytest

from .utils import LogError, logs, server


def test_init_w_queries_valid_idx(server, logs):
    samplers = {"Validation": {"queries": [[0, 1, 4], [0, 1, 5]]}}
    exp = {"targets": [0, 1, 2, 3], "samplers": samplers}

    with pytest.raises(LogError), logs:
        server.authorize()
        server.get("/init")
        r = server.post("/init_exp", data={"exp": exp}, error=True)
        assert r.status_code == 500
        assert "the index 5 is included" in r.text.lower()
        assert "the n=4 targets" in r.text.lower()


def test_validation_sampling(server, logs):
    n_val = 4
    exp = {
        "targets": list(range(10)),
        "samplers": {"Validation": {"n_queries": n_val}},
    }
    data = []
    puid = "adsfjkl4awjklra"

    n_repeat = 4
    server.authorize()
    server.post("/init_exp", data={"exp": exp})
    Q = []
    for k in range(n_repeat * n_val):
        q = server.get("/query").json()
        _ans = random.choice([q["left"], q["right"]])
        ans = {"winner": _ans, "puid": k, **q}
        print([ans[k] for k in ["head", "left", "right"]])
        Q.append(ans)
        server.post("/answer", data=ans)
        data.append(ans)
        sleep(0.20)

    # Test the number of unique queries is specified by n_val
    queries = [(q["head"], (q["left"], q["right"])) for q in Q]
    uniq_queries = [(h, min(c), max(c)) for h, c in queries]
    assert len(set(uniq_queries)) == n_val, set(uniq_queries)

    # Test the order gets shuffled every iteration
    order = [hash(q) for q in queries]
    round_orders = [order[k * n_val : (k + 1) * n_val] for k in range(n_repeat)]
    for round_order in round_orders:
        assert len(set(round_order)) == n_val
    same_order = [round_orders[0] != order for order in round_orders[1:]]
    assert sum(same_order) in [len(same_order), len(same_order) - 1]
