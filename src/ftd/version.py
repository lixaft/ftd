"""Manage the package version."""
import logging

__all__ = [
    "MAJOR",
    "MINOR",
    "PATCH",
    "TUPLE",
    "STR",
    "require_maya",
    "deprecated",
]

LOG = logging.getLogger(__name__)

MAJOR = 0
"""int: The major version of the package."""
MINOR = 1
"""int: The minor version of the package."""
PATCH = 0
"""int: The patch version of the package."""

TUPLE = (MAJOR, MINOR, PATCH)
"""tuple: The version as a tuple."""
STR = "{}.{}.{}".format(*TUPLE)
"""str: The version as a string."""


def require_maya(minimum=None, maximum=None):
    """Require a version of maya to be executed."""
    raise RuntimeError()


def deprecated():
    """Deprecate a function."""
