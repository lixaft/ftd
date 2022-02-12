# pylint: disable=import-outside-toplevel
"""Run unit test suite."""
import os
import sys

from maya import standalone


def main():
    """Entry point."""
    standalone.initialize()
    import pytest

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    argv = [
        "src",
        "tests",
        "--doctest-modules",
        "--cov=src",
        "--cov-report=term",
        "--cov-report=html",
        "--showlocals",
    ]
    argv.extend(sys.argv[1:])
    status = pytest.main(argv)

    standalone.uninitialize()
    return status


if __name__ == "__main__":
    sys.exit(main())
