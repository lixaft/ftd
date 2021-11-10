"""Root package."""
import os

with open(os.path.join(os.path.dirname(__file__), "VERSION"), "r") as _stream:
    __version__ = _stream.read().strip()
    version_info = tuple(__version__.split("."))
del _stream
