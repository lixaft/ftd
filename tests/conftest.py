"""Configure pytest environement."""
import pytest

from maya import cmds


@pytest.fixture
def newscene():
    """Create a new scene."""
    cmds.file(new=True, force=True)
