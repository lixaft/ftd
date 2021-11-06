"""Run the tests."""
import sys

import maya.standalone

if __name__ == "__main__":
    maya.standalone.initialize()
    import nose

    argv = sys.argv
    argv.extend(
        [
            "--verbose",
            "--with-doctest",
            "--with-coverage",
            "--cover-html",
            "--cover-package",
            "src/ftd",
            "--cover-erase",
            "--cover-tests",
            "tests",
            "src/ftd",
        ]
    )
    nose.run(argv=argv)

    maya.standalone.uninitialize()
