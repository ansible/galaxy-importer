"""Utils for manipulating strings"""


def removeprefix(target, prefix):
    """Remove a prefix from a string, based on 3.9 str.removeprefix()"""
    if target.startswith(prefix):
        return target[len(prefix) :]
    else:
        return target[:]
