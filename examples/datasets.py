from pathlib import Path

import numpy as np
import pandas as pd


def strange_fruit(head, left, right, rng=None):
    """
    Parameters
    ----------
    head, left, right : int, int, int
        Number of spikes on the various objects

    Returns
    -------
    winner : str
        Either "left" or "right"

    Notes
    -----
    This is determined from human data.
    See datasets/strange-fruit-triplet/noise-model.ipynb for details.
    """
    ldiff = np.abs(head - left)
    rdiff = np.abs(head - right)

    r = np.maximum(ldiff, rdiff) / (ldiff + rdiff)
    rate = 19.5269746
    final = 0.9567
    p_correct = final / (1 + np.exp(-rate * (r - 0.5)))

    winner = 0 if ldiff < rdiff else 1
    if not rng:
        rng = np.random.RandomState()
    if rng.uniform() <= p_correct:
        return winner
    return 1 - winner
