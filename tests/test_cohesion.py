import random
import sys
from pathlib import Path

from backend.backend.algs.utils import deserialize_query, serialize_query

from .utils import server


def test_query_serialization():
    q1 = (1, (2, 3))
    h, (a, b) = q1
    q2 = deserialize_query(serialize_query(q1))
    assert q2["head"] == h
    assert q2["left"] == a
    assert q2["right"] == b
