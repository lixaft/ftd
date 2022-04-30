# pylint: disable=import-outside-toplevel
"""Run unit test suite."""
import os
import re
import subprocess
import sys


def main():
    """CLI entry point."""
    # Parse the arguments in `sys.argv`.
    versions = [str(x) for x in sys.argv[1:] if x.isdigit()]
    argv = []

    command = (
        "import sys;"
        "sys.path.append('{}');"
        "import run_tests;"
        "exit_code = run_tests.run();"
        "sys.exit(exit_code);"
    ).format(os.path.dirname(__file__))
    exit_code = 0
    for version in versions or [None]:
        try:
            argv = [find_mayapy(version), "-c", command]
            exit_code = subprocess.check_call(argv)
        except subprocess.CalledProcessError:
            exit_code = 1
    return exit_code


def run():
    """Entry point."""
    from maya import standalone

    standalone.initialize()

    import pytest

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(os.path.join(root, "src"))
    os.chdir(root)

    argv = [
        "src",
        "tests",
        # "--doctest-modules",
        "--cov=src",
        "--cov-report=term",
        "--cov-report=html",
        "--showlocals",
        "-v",
    ]
    argv.extend(sys.argv[1:])
    status = pytest.main(argv)

    standalone.uninitialize()
    return status


def find_mayapy(version=None):
    """Find a mayapy executable path.

    Arguments:
        version (int, optional): Specify the version of the executable that
            will be searched. By default, it returns the most recent version
            present on the system.

    Returns:
        str: The path to the mayapy executable.
    """
    path = {
        "win32": os.path.normpath("C:/Program Files/Autodesk/"),
        "darwin": os.path.normpath("/Applications/Autodesk/"),
        "linux": os.path.normpath("/usr/autodesk/"),
    }.get(sys.platform)

    if version is None:
        # Search for the most recent version of maya.
        for each in os.listdir(path):
            if not re.match(r"(M|m)aya[0-9]{4}(-x64)?", each):
                continue
            number = int(each[4:].replace("-x64", ""))
            if number > (version or 0):
                version = number

    path = os.path.join(path, "maya{}".format(version))
    if sys.platform == "darwin":
        path = os.path.join(path, "Maya.app", "Contents")
    path = os.path.join(path, "bin", "mayapy")
    if sys.platform == "win32":
        path += ".exe"

    if not os.path.exists(path):
        return None
    return path


if __name__ == "__main__":
    sys.exit(main())
