"""Manage the package version."""
import logging

import packaging.version

from maya import cmds

import ftd

__all__ = [
    "MAJOR",
    "MINOR",
    "MICRO",
    "RELEASE",
    "require_maya",
    "deprecated",
]

LOG = logging.getLogger(__name__)

VERSION = packaging.version.parse(ftd.__version__)
MAJOR = VERSION.major
MINOR = VERSION.minor
MICRO = VERSION.micro
RELEASE = VERSION.release

MAYA = int(cmds.about(version=True))


def require_maya(minimum=None, maximum=None):
    """Require a version of maya to be executed."""
    raise NotImplementedError()


def deprecated():
    """Deprecate a function."""
    raise NotImplementedError()
