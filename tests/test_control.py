"""test the constraint module."""
import pytest

import ftd.control


@pytest.mark.parametrize("shape", ftd.control.SHAPES.keys())
def test_create(shape):
    """Test to create a control."""
    ftd.control.create(shape)
