import cloudpickle
import numpy as np

from salmon.triplets.samplers import RoundRobin


def test_rr():
    alg = RoundRobin(n=10)
    alg.foo = "bar"
    ir = cloudpickle.dumps(alg)
    alg2 = cloudpickle.loads(ir)
    assert type(alg2) == RoundRobin
    assert alg2.n == 10
    assert alg.foo == alg2.foo
    assert alg.meta_ == alg2.meta_
