from ._version import get_versions
from .backend import app as app_algs
from .frontend import app as app

__version__ = get_versions()["version"]
del get_versions

app.version = app_algs.version = __version__
