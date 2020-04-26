from math import pi
from datetime import timedelta, datetime
import json

from bokeh.plotting import figure, show
from bokeh.embed import json_item
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .utils import get_logger


def _make_hist(
    title,
    xlabel,
    hist,
    edges,
    width=600,
    height=200,
    toolbar_location="right",
    **kwargs,
):
    p = figure(
        title=title,
        background_fill_color="#fafafa",
        width=width,
        height=height,
        toolbar_location=toolbar_location,
        **kwargs,
    )
    p.quad(
        top=hist,
        bottom=0,
        left=edges[:-1],
        right=edges[1:],
        fill_color="blue",
        line_color="white",
        alpha=0.5,
    )

    p.y_range.start = 0
    p.legend.location = "center_right"
    p.legend.background_fill_color = "#fefefe"
    p.xaxis.axis_label = xlabel
    p.yaxis.axis_label = "Frequency"
    p.grid.grid_line_color = "white"
    return p


async def _get_unique(series: pd.Series):
    assert series.nunique() == 1
    return series.iloc[0]


async def _get_nbins(x: np.array):
    total_days = (x.max() - x.min()) / (60 * 60 * 24)
    bins = max(10, total_days * 3)
    return bins


async def activity(df: pd.DataFrame, start_sec: float):
    x = df["time_received"].values.copy()
    try:
        bins = await _get_nbins(x)
    except ValueError:
        bins = 10
    bin_heights, edges = np.histogram(x, bins=bins)

    start = datetime(1970, 1, 1) + timedelta(seconds=start_sec)
    edges = [timedelta(seconds=e) + start for e in edges]

    _start = start.isoformat()[: 10 + 6]
    xlabel = f"\nTime received"
    p = _make_hist(
        f"Time responses received",
        xlabel,
        bin_heights,
        edges,
        toolbar_location="above",
        x_axis_type="datetime",
    )
    p.xaxis.major_label_orientation = pi / 4
    return p


async def _remove_outliers(x, low=True, high=True):
    _high = np.mean(x) + 3 * np.std(x) <= x
    _low = x <= np.mean(x) - 3 * np.std(x)
    bad = _high | _low
    return x[~bad]


async def response_time(df: pd.DataFrame):
    x = df["response_time"].values.copy()
    if len(x) >= 100:
        x = await _remove_outliers(x)
    try:
        bins = await _get_nbins(x)
    except ValueError:
        bins = 10
    bin_heights, edges = np.histogram(x, bins=bins)
    p = _make_hist(f"Response time", "Time (s)", bin_heights, edges, width=300)
    return p


async def network_latency(df: pd.DataFrame):
    x = df["network_latency"].values.copy()
    if len(x) >= 100:
        x = await _remove_outliers(x)
    try:
        bins = await _get_nbins(x)
    except ValueError:
        bins = 10
    bin_heights, edges = np.histogram(x, bins=bins)
    p = _make_hist(f"Client side latency", "Time (s)", bin_heights, edges, width=300)
    return p
