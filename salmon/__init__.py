from salmon._version import get_versions
__version__ = get_versions()["version"]
del get_versions

try:
    from salmon.backend import app as app_algs
    from salmon.frontend import app as app

    app.version = app_algs.version = __version__
except (ModuleNotFoundError, ImportError):
    pass

from salmon.triplets.offline import OfflineEmbedding
