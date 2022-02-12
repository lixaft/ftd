"""Manage the package version."""
import logging

LOG = logging.getLogger(__name__)
MAJOR = 0
MINOR = 1
PATCH = 0

INFO = (MAJOR, MINOR, PATCH)
STR = "{}{}{}".format(*INFO)


def require_maya(minimum=None, maximum=None):
    """Require a version of maya to be executed."""
    raise RuntimeError()


def deprecated():
    """Deprecate a function."""
