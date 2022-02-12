"""Test main."""
import importlib
import pkgutil

import pytest

import ftd

MODULES = [
    x[1] for x in pkgutil.walk_packages(ftd.__path__, ftd.__name__ + ".")
]


@pytest.mark.parametrize("module", MODULES)
def test_import_modules(module):
    """Test that all the modules can be imported."""
    importlib.import_module(module)
