"""
Utilities for dealing with the nastiness that is LS_COLORS.

"""

from os import environ


def to_colorizer(ls_colors=None):
    if ls_colors is None:
        ls_colors = environ.get("LS_COLORS", "")
        print sorted(dict(
            thing.split("=", 1) for thing in ls_colors.split(":") if thing
        ))


to_colorizer()
