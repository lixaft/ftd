"""This module contains utility functions about plugins."""
import logging

from maya import cmds

LOG = logging.getLogger(__name__)


def remove_unknown():
    """Remove the unused plugin present in the current scene."""
    for plugin in cmds.unknownPlugin(query=True, list=True) or []:
        cmds.unknownPlugin(plugin, remove=True)
        LOG.info("Unloading unknown plugin: '%s'", plugin)
