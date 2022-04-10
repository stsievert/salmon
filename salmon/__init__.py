from salmon._version import get_versions
from salmon.backend import app as app_algs
from salmon.frontend import app as app

__version__ = app.version = app_algs.version = get_versions()["version"]
del get_versions
