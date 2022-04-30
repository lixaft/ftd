from maya import mel


def delete_unused():
    """Delete all the unused nodes in the scene.

    Examples:
        >>> from maya import cmds
        >>> _ = cmds.file(new=True, force=True)
        >>> a = cmds.createNode("addDoubleLinear", name="A")
        >>> delete_unused()
        >>> cmds.objExists(a)
        False
    """
    mel.eval("MLdeleteUnused")
