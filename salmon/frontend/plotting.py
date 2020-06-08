from math import pi
from datetime import timedelta, datetime
import json

from bokeh.plotting import figure, show
from bokeh.embed import json_item
from bokeh.models import ColumnDataSource
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from .utils import get_logger

logger = get_logger(__name__)


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


async def _get_nbins(x: np.array) -> int:
    if len(x) <= 10:
        return 10

    total_days = (np.nanmax(x) - np.nanmin(x)) / (60 * 60 * 24)
    bins = max(10, total_days * 4)
    return int(bins)


async def activity(df: pd.DataFrame, start_sec: float):
    x = df["time_received"].values.copy()
    bins = await _get_nbins(x)
    logger.info(f"bins = {bins}")
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
    # _high = np.mean(x) + 3 * np.std(x) <= x
    # _low = x <= np.mean(x) - 3 * np.std(x)
    _high = np.percentile(x, 95)
    _low = np.percentile(x, 5)
    good = (x >= _low) & (x <= _high)
    return x[good]


async def response_time(df: pd.DataFrame):
    x = df["response_time"].values.copy()
    limit = np.percentile(x, 95)
    x = x[x <= limit]
    bins = await _get_nbins(x)
    bin_heights, edges = np.histogram(x, bins=bins)
    p = _make_hist(
        f"Response time",
        "Time (s)",
        bin_heights,
        edges,
        width=300,
        toolbar_location="below",
    )
    return p


async def network_latency(df: pd.DataFrame):
    x = df["network_latency"].values.copy()
    if len(x) >= 100:
        x = await _remove_outliers(x)
    bins = await _get_nbins(x)
    bin_heights, edges = np.histogram(x, bins=bins)
    p = _make_hist(
        f"Client side latency",
        "Time (s)",
        bin_heights,
        edges,
        width=300,
        toolbar_location="below",
    )
    return p


async def _get_server_metrics():
    base = "http://prom:9090"
    start = datetime.now() - timedelta(days=1)
    end = datetime.now()
    data = {
        "query": "starlette_requests_processing_time_seconds_bucket",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "step": 0.1,
    }
    r = requests.post(base + "/api/v1/query", data=data)
    assert r.status_code == 200
    raw = r.json()
    assert raw["status"] == "success"
    rare = raw["data"]
    assert rare["resultType"] == "vector"
    med_rare = rare["result"]
    assert all(len(m["value"]) == 2 for m in med_rare)
    assert all(set(m.keys()) == {"value", "metric"} for m in med_rare)
    medium = [{"value": m["value"][1], **m["metric"]} for m in med_rare]
    df = pd.DataFrame(medium)
    df["value"] = df["value"].astype(float)
    df["le"] = df["le"].astype(float)

    cols = ["value", "le", "path_template"]
    proc = df[cols]
    proc.columns = ["count", "le", "endpoint"]

    bad_endpoints = ["/favicon.ico", "/metrics", "/metrics", "/api/v1/query", "/static", "/init_exp"]
    idx = proc.endpoint.isin(bad_endpoints)
    idx |= proc.endpoint.isin([e + "/" for e in bad_endpoints])
    proc = proc[~idx].copy()
    return proc

async def _process_endpoint_times(p, endpoint):
    e = endpoint
    base = pd.DataFrame([{"count": 0, "le": 0, "endpoint": e}])
    p = p.append(base)
    p = p.sort_values(by="le")

    between = p["count"].diff()
    limits = p["le"].values
    upper = limits
    idx = np.arange(len(p))
    lower = limits[idx - 1]
    df = pd.DataFrame({"between": between, "upper": upper, "lower": lower, "endpoint": e})
    df["prob"] = df["between"] / df["between"].sum()
    return df.copy()

async def get_endpoint_time_plots():
    proc = await _get_server_metrics()
    endpoints = proc.endpoint.unique()
    dfs = {e: await _process_endpoint_times(proc[proc.endpoint == e], e) for e in endpoints}
    out = {}
    for e, df in dfs.items():
        logger.info(df.columns)
        x = [
            str(xi) if xi >= 0.1 or xi <= 0 else "{}ms".format(int(xi * 1000))
            for xi in df.upper.unique()
        ]

        p = figure(x_range=x, plot_height=150, toolbar_location=None, title=f"{e} processing time",
                   width=500, tools="")

        _data = {k: df[k].values.tolist() for k in ["upper", "between"]}
        _data["upper"] = [str(k) for k in _data["upper"]]
        source = ColumnDataSource(_data)
        p.vbar(x=x, top=_data["between"], width=0.9, line_color="#" + "e" * 6)

        p.yaxis.axis_label = 'Frequency'
        p.xaxis.axis_label = 'Processing time (s)'
        p.yaxis.minor_tick_line_color = None  # turn off x-axis minor ticks
        out[e] = p
    return out
