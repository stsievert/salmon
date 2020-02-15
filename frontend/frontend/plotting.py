import numpy as np
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from .utils import get_logger


async def time_histogram(seconds):
    logger = get_logger(__name__)
    mpl_data = mdates.epoch2num(seconds)
    w = 3
    fig, ax = plt.subplots(figsize=(1.5 * w, w))
    ax.hist(mpl_data, bins="auto")
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.AutoDateFormatter(locator))
    ax.set_xlabel("Time since start")
    ax.set_ylabel("Number of responses")
    ax.grid(alpha=0.6)
    try:
        fig.autofmt_xdate()
    except ValueError:
        logger.error("Matplotlib failed on fig.autofmt_xdate.")
    return fig, ax


def _any_outliers(x, low=True, high=True):
    _high = np.mean(x) + 3 * np.std(x) <= np.max(x)
    _low = np.min(x) <= np.mean(x) - 3 * np.std(x)
    if low and not high:
        return _low
    elif high and not low:
        return _high
    elif high and low:
        return _high or _low
    else:
        raise ValueError(f"high={high}, low={low}")
