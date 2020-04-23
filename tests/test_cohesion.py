import random
import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.append(str(root / "backend"))
sys.path.append(str(root / "frontend"))

from backend.algs.utils import Answer as BackAnswer
from backend.algs.utils import deserialize_query, serialize_query
from frontend.manager import Answer as FrontAnswer

from .utils import server


def test_answer(server):
    server.authorize()
    exp = Path(__file__).parent / "data" / "exp-active.yaml"
    server.post("/init_exp", data={"exp": exp.read_bytes()})
    query = server.get("/query").json()
    answer = {
        "puid": "foo",
        "winner": random.choice([query["left"], query["right"]]),
        "response_time": 10e-3,
        "network_latency": 1e-3,
        **query,
    }

    a1 = FrontAnswer(**answer).dict()
    a2 = BackAnswer(**answer).dict()
    assert set(a2).issubset(set(a2))


def test_query_serialization():
    q1 = (1, (2, 3))
    h, (a, b) = q1
    q2 = deserialize_query(serialize_query(q1))
    assert q2["head"] == h
    assert q2["left"] == a
    assert q2["right"] == b
