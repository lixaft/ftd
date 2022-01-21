"""Test the version of the package."""
import os

import ftd


def test_version():
    """Test the version."""
    with open(os.path.join(ftd.__path__[0], "VERSION"), "r") as stream:
        assert ftd.__version__ == stream.read().strip()
