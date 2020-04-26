from math import pi
from datetime import timedelta, datetime
import json

from bokeh.plotting import figure, show
from bokeh.embed import json_item
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import holoviews as hv
import hvplot.pandas

from .utils import get_logger


def _make_hist(title, xlabel, hist, edges):
    p = figure(title=title, background_fill_color="#fafafa", x_axis_type="datetime",
               width=600, height=200,  toolbar_location="above")
    p.quad(
        top=hist, bottom=0, left=edges[:-1], right=edges[1:],
        fill_color="blue", line_color="white", alpha=0.5,
    )

    p.y_range.start = 0
    p.legend.location = "center_right"
    p.legend.background_fill_color = "#fefefe"
    p.xaxis.axis_label = xlabel
    p.yaxis.axis_label = 'Frequency'
    p.grid.grid_line_color="white"
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

    _start = start.isoformat()[:10 + 6]
    xlabel = f"\nTime received"
    p = _make_hist(f"Time responses received", xlabel, bin_heights, edges)
    p.xaxis.major_label_orientation = pi/4
    return p

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

async def response_time(df: pd.DataFrame):
    col = "response_time"
    title = "Human respose time"
    label = "Response time (s)"
    p = df[col].hvplot(kind="hist", ylabel="Frequency", title=title,xlabel=label, width=300)
    return await hv_to_bokeh(p)

async def network_latency(df: pd.DataFrame):
    col = "network_latency"
    title = "Client side latency"
    label = "Delay (s)"
    p = df[col].hvplot(kind="hist", ylabel="Frequency", xlabel=label, title=title, width=300)
    return await hv_to_bokeh(p)

async def hv_to_bokeh(p):
    renderer = hv.renderer('bokeh')
    hvplot = renderer.get_plot(p)
    return hvplot.state
