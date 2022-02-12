"""Configure pytest environement."""
import pytest

from maya import cmds


@pytest.fixture(autouse=True)
def newscene():
    """Create a new scene."""
    cmds.file(new=True, force=True)
