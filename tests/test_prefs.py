# pylint: disable=all
"""Test prefs tools."""
import pytest
import yaml

import ftd.tools.prefs

with open(ftd.tools.prefs.LOCAL, "r") as stream:
    ftd.tools.prefs.load_commands(yaml.load(stream, Loader=yaml.FullLoader))


@pytest.mark.parametrize("command", ftd.tools.prefs.Command._registered.keys())
def test_run_pref_commands(command):
    cmd = ftd.tools.prefs.Command.get(command)
    if "skip_test" not in cmd.tags:
        exec(cmd.context)
        cmd.execute()
