"""Build the documentation."""
import os
import sys

import sphinx.cmd.build


def main():
    """Entry point."""

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    argv = ["docs/source", "docs/build", "-E"]
    argv.extend(sys.argv[1:])
    status = sphinx.cmd.build.main(argv)

    return status


if __name__ == "__main__":
    sys.exit(main())
