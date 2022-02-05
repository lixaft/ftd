# pylint: disable=unused-argument
"""test the constraint module."""
import pytest

import ftd.control


@pytest.mark.parametrize("shape", ftd.control.CONTROLS.keys())
def test_create(newscene, shape):
    """Test to create a control."""
    ftd.control.create(shape)
