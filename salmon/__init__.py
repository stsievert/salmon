from .frontend import app as app
from .backend import app as app_algs

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

app.version = app_algs.version = __version__
