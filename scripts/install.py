"""Install the package."""
import argparse
import logging
import os
import sys

LOG = logging.getLogger(__name__)
ROOT = os.path.dirname(os.path.abspath(__file__))


def main(version=None):
    """Add to the MAYA_MODULE_PATH variable the root of the directory.

    For more information on modules, please consult the official documentation:
    https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2020/ENU/Maya-EnvVar/files/GUID-8EFB1AC1-ED7D-4099-9EEE-624097872C04-htm.html

    Arguments:
        version (int, optional): The version of maya on which the package needs
            to be installed.
    """
    LOG.info("Running the installation of ftd package...")

    # - Find the maya application directory ---
    LOG.info("Finding the maya application directory.")

    # If ther user decides to change the default location of the application
    # directory, maya will create an environement variable that point to this
    # new directory.
    app_dir = os.getenv("MAYA_APP_DIR", None)

    # Otherwise, let's find the application directory depending on the user's
    # operating system.
    if app_dir is None:
        if sys.platform == "win32":
            path = ("~", "Documents", "maya")
        elif sys.platform == "darwin":
            path = ("~", "Library", "Preferences", "Autodesk", "maya")
        elif sys.platform == "linux":
            path = ("~", "maya")
        else:
            msg = "Sorry, the plateform '%s' is not keep in charge for this"
            msg += "installation. Please do a manual install and/or let me"
            msg += " know the problem so I can take care of your case."
            LOG.error(msg, sys.platform)

        app_dir = os.path.expanduser(os.path.join(*path))
        assert os.path.exists(app_dir)

    # add the version of maya if the user has provided one
    if version is not None:
        app_dir = os.path.join(app_dir, str(version))
    if not os.path.exists(app_dir):
        msg = "The specified version of maya is not installed on the system."
        LOG.error(msg)
        return

    # - Add the package to the MAYA_MODULE_PATH environement variable ---
    LOG.info("Appening the module to maya environement.")

    # store path variables
    env_file = os.path.join(app_dir, "Maya.env")

    # get existing variables
    lines = []
    if os.path.exists(env_file):
        with open(env_file, "r") as stream:
            lines = stream.readlines()

    # add the package to the variable
    for index, line in enumerate(lines):
        if "MAYA_MODULE_PATH" in line:
            if ROOT not in line:
                line = line.strip()
                sep = "" if line.endswith(";") else ";"
                lines[index] = "{}{}{}\n".format(line, sep, ROOT)
            break
    else:
        lines.append("MAYA_MODULE_PATH={}\n".format(ROOT))

    # edit the Maya.env file
    with open(env_file, "w") as stream:
        stream.writelines(lines)
    LOG.info("Module add to the file '%s'", env_file)

    LOG.info("Installation completed!")


def onMayaDroppedPythonFile(_):
    # pylint: disable=invalid-name, import-outside-toplevel
    """Function runned by maya on dropped action."""
    from maya import cmds
    from maya.app.startup import basic

    main(cmds.about(version=True))
    basic.executeUserSetup()

    # The best thing would be to find a way to add the whole module at runtime,
    # but for now it is enough to add the src directory to the PYTHON_PATH.
    sys.path.append(os.path.join(ROOT, "src"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.description = main.__doc__.splitlines()[0]
    parser.add_argument(
        "-m",
        "--maya-version",
        help="The version of maya on which the package should be installed.",
    )
    args = parser.parse_args()
    main(args.maya_version)
