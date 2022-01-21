# pylint: disable=import-outside-toplevel
"""Unit test runner for mayapy."""
import sys

from maya import standalone


def main(argv):
    """Initialize maya and run the test suite."""
    standalone.initialize()
    import pytest

    status = pytest.main(argv)

    standalone.uninitialize()
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
