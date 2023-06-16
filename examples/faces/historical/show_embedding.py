from pathlib import Path

import pandas as pd
from bokeh.io import curdoc, show
from bokeh.models import ColumnDataSource, Grid, ImageURL, LinearAxis, Plot, Range1d


if __name__ == "__main__":
    DIR = Path(__file__).absolute().parent
    df: pd.DataFrame = pd.read_csv(DIR / "embedding.csv")
    df.columns = ["fname", "x", "y"]
    df = df.set_index("fname")

    df["x"] *= 1000
    df["y"] *= 1000

    urls = {
        f.name.replace(".png", ""): f"file://{f.absolute()}"
        for f in (DIR.parent / "faces").glob("*.png")
    }
    df["url"] = pd.Series(urls)
    df = df.reset_index().sample(frac=1, replace=False)
    # 167 x 206
    df["w"] = int(167 * 1.2)
    df["h"] = int(206 * 1.2)

    source = ColumnDataSource(df)

    xdr = Range1d(start=int(df.x.min()) - 1, end=int(df.x.max()) + 1)
    ydr = Range1d(start=int(df.y.min()) - 1, end=int(df.y.max()) + 1)

    plot = Plot(
        title=None, x_range=xdr, y_range=ydr, width=800, height=500,
        min_border=0, toolbar_location=None)

    image1 = ImageURL(url="url", x="x", y="y", w="w", h="h", anchor="center")
    plot.add_glyph(source, image1)

    xaxis = LinearAxis()
    plot.add_layout(xaxis, 'below')

    yaxis = LinearAxis()
    plot.add_layout(yaxis,'left')

    plot.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
    plot.add_layout(Grid(dimension=1, ticker=yaxis.ticker))

    curdoc().add_root(plot)
    show(plot)
