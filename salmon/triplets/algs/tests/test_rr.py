import cloudpickle
import numpy as np

from salmon.triplets.algs import RoundRobin

def test_rr():
    alg = RoundRobin(n=10, random_state=42)
    ir = cloudpickle.dumps(alg)
    alg2 = cloudpickle.loads(ir)
    assert type(alg2) == RoundRobin
    assert alg2.n == 10
    assert np.allclose(alg2.random_state.randint(10, size=10), alg.random_state.randint(10, size=10))
