import random
from pathlib import Path
from time import sleep

import pandas as pd
import pytest
import yaml

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


def test_round_robin(server, logs):

    exp = Path(__file__).parent / "data" / "round-robin.yaml"

    with open(exp, "r") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    n = len(config["targets"])
    n_repeat = 4

    with logs:
        server.authorize()
        server.post("/init_exp", data={"exp": exp.read_text()})
        for k in range(n_repeat * n):
            print(k)
            q = server.get("/query").json()

            ans = {"winner": random.choice([q["left"], q["right"]]), "puid": "foo", **q}
            server.post("/answer", json=ans)
            sleep(0.05)

        r = server.get("/responses")
        df = pd.DataFrame(r.json())
        assert set(df["head"].unique()) == set(range(n))
        heads = list(df["head"])
        rounds_heads = [heads[k * n : (k + 1) * n] for k in range(n_repeat)]

        # Make sure every head is asked in every round
        for heads in rounds_heads:
            assert len(set(heads)) == n

        # Make sure round order always shuffled
        orders = [hash(tuple(heads)) for heads in rounds_heads]
        assert len(set(orders)) == len(orders)


def test_round_robin_per_user(server):
    N = 5
    R = 2
    config = {"targets": N, "samplers": {"RoundRobin": {}}}
    server.authorize()
    server.post("/init_exp", data={"exp": config})

    # Ordering in this nested for loop is important
    # (users need to alternately request queries for valid test of per-user RR)
    for k in range(R * N):
        for puid in ["u1", "u2"]:
            q = server.get(f"/query?puid={puid}").json()
            winner = random.choice([q["left"], q["right"]])
            server.post("/answer", json={"winner": winner, "puid": puid, **q})
    r = server.get("/responses")
    df = pd.DataFrame(r.json())
    assert set(df["puid"].unique()) == {"u1", "u2"}
    df["test_user_responses"] = (1 + df["num_responses"]) // 2
    assert (df["puid_num_responses"] == df["test_user_responses"]).all()
    heads = df.pivot(values="head", columns="puid", index="puid_num_responses")

    for puid in heads.columns:
        for r in range(R):
            one_round = heads[puid].iloc[r * N : (r + 1) * N]
            assert set(one_round.values) == set(range(N))
