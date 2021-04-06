from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.utils import check_random_state


def _sigmoid(x, err, rate):
    noiseless = 1 / (1 + np.exp(-rate * (x - 0.5)))
    p_correct = (1 - err * 2) * (noiseless - 0.5) + 0.5
    return p_correct


def alien_egg(h, l, r, random_state=None, err=0.07074231, rate=17.55473809) -> int:
    """
    Parameters
    ----------
    h, l, r : int, int, int
        Number of spikes on the various objects

    Returns
    -------
    winner : int
        0 if left wins, 1 if right wins

    Notes
    -----
    This is determined from human data.
    See datasets/alien-egg/alien-eggs-noise-model-n=30/Noise-model.ipynb for details.
    """
    ldiff = np.abs(h - l)
    rdiff = np.abs(h - r)

    r = np.maximum(ldiff, rdiff) / (ldiff + rdiff)
    p_correct = _sigmoid(r, err, rate)

    winner = 0 if ldiff < rdiff else 1
    random_state = check_random_state(random_state)
    if random_state.uniform() <= p_correct:
        return winner
    return 1 - winner
