from .frontend import app as frontend
from .backend import app as backend

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

frontend.version = backend.version = __version__
