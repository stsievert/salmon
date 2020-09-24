from math import pi
from datetime import timedelta, datetime
from typing import List
import json

from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource, Grid, LinearAxis, Plot, Text, ImageURL
from bokeh.palettes import brewer
from bokeh.embed import json_item

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from .utils import get_logger, image_url

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
        toolbar_location=None,
        x_axis_type="datetime",
    )
    p.xaxis.major_label_orientation = pi / 4
    return p


async def _remove_outliers(x, low=True, high=True, frac=0.10):
    """Remove outliers ``frac`` fraction of the data"""
    p = (frac * 100) / 2
    _high = np.percentile(x, 100 - p)
    _low = np.percentile(x, p)
    if low and high:
        good = (x >= _low) & (x <= _high)
    elif low:
        good = x >= _low
    elif high:
        good = x <= _high
    return x[good]


async def response_time(df: pd.DataFrame):
    x = df["response_time"].values.copy()
    if len(x) >= 100:
        x = await _remove_outliers(x, low=False, high=True)
    bins = await _get_nbins(x)
    bin_heights, edges = np.histogram(x, bins=bins)
    p = _make_hist(
        f"Response time",
        "Time (s)",
        bin_heights,
        edges,
        width=300,
        toolbar_location=None,
    )
    return p


async def network_latency(df: pd.DataFrame):
    x = df["network_latency"].values.copy()
    if len(x) >= 100:
        x = await _remove_outliers(x, low=False, high=True)
    bins = await _get_nbins(x)
    bin_heights, edges = np.histogram(x, bins=bins)
    p = _make_hist(
        f"Client side latency",
        "Time (s)",
        bin_heights,
        edges,
        width=300,
        toolbar_location=None,
    )
    return p


async def show_embedding(embedding: np.ndarray, targets: List[str], alg: str = ""):
    embedding = np.asarray(embedding)

    # scale each dimension between 0 and 1
    for dim in range(embedding.shape[1]):
        embedding[:, dim] = embedding[:, dim] - embedding[:, dim].min()
        embedding[:, dim] /= embedding[:, dim].max()
        embedding[:, dim] -= 0.5

    images = [
        k for k, target in enumerate(targets) if "img" in target or "video" in target
    ]
    image_urls = [image_url(target) for k, target in enumerate(targets) if k in images]

    data = {
        "x": embedding[images, 0],
        "y": embedding[images, 1] if len(embedding[0]) > 1 else embedding[images, 0],
        "image_url": image_urls,
    }
    source = ColumnDataSource(data=data)

    plot = figure(title=alg, plot_width=600, plot_height=500, toolbar_location="right",)
    #  glyph = Text(x="x", y="y", text="text", angle=0.3, text_color="#96deb3")
    w = h = {"units": "data", "value": 0.1}
    w = h = {"units": "screen", "value": 80}
    glyph = ImageURL(x="x", y="y", url="image_url", w=w, h=h)
    plot.add_glyph(source, glyph)

    text = [k for k in range(len(targets)) if k not in images]
    print(text)
    print(alg, embedding.shape)
    data = {
        "x": embedding[text, 0],
        "y": embedding[text, 1] if len(embedding[0]) > 1 else embedding[text, 0],
        "text": [target for k, target in enumerate(targets) if k in text],
    }
    glyph = Text(x="x", y="y", text="text")
    source = ColumnDataSource(data=data)
    plot.add_glyph(source, glyph)
    return plot


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

    bad_endpoints = [
        "/favicon.ico",
        "/metrics",
        "/metrics",
        "/api/v1/query",
        "/static",
        "/init_exp",
    ]
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
    df = pd.DataFrame(
        {"between": between, "upper": upper, "lower": lower, "endpoint": e}
    )
    df["prob"] = df["between"] / df["between"].sum()
    return df.copy()


async def get_endpoint_time_plots():
    proc = await _get_server_metrics()
    endpoints = proc.endpoint.unique()
    dfs = {
        e: await _process_endpoint_times(proc[proc.endpoint == e], e) for e in endpoints
    }
    out = {}
    for e, df in dfs.items():
        logger.info(df.columns)
        x = [
            str(xi) if xi >= 0.1 or xi <= 0 else "{}ms".format(int(xi * 1000))
            for xi in df.upper.unique()
        ]

        p = figure(
            x_range=x,
            plot_height=150,
            toolbar_location=None,
            title=f"{e} processing time",
            width=500,
            tools="",
        )

        _data = {k: df[k].values.tolist() for k in ["upper", "between"]}
        _data["upper"] = [str(k) for k in _data["upper"]]
        source = ColumnDataSource(_data)
        p.vbar(x=x, top=_data["between"], width=0.9, line_color="#" + "e" * 6)

        p.yaxis.axis_label = "Frequency"
        p.xaxis.axis_label = "Processing time (s)"
        p.yaxis.minor_tick_line_color = None  # turn off x-axis minor ticks
        out[e] = p
    return out


async def _get_alg_perf(df):
    cols = [c for c in df.columns if "time_" == c[:5] and c != "time_loop"]

    s = df[cols + ["time"]].copy()
    s["timedelta"] = pd.to_timedelta(s["time"] - s["time"].min(), unit="s")
    s = s.rolling(window="30s", on="timedelta").mean()

    source = ColumnDataSource(s)

    p = figure(
        title="Algorithm timing",
        x_axis_label="Time since start",
        y_axis_label="Time spent per task (s)",
        x_axis_type="datetime",
        width=600,
        height=300,
    )
    names = list(reversed(cols))
    p.varea_stack(
        x="timedelta",
        stackers=names,
        legend_label=names,
        color=brewer["Spectral"][len(names)],
        source=source,
    )
    p.legend.location = "top_left"
    return p
