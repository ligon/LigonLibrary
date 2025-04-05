#!/usr/bin/env python3

"""Miscellany of tools for manipulating dataframes.
"""

from . import strings

def normalize_strings(df,**kwargs):
    """Normalize strings in a dataframe.
    """
    def normalize_string(s):
        if isinstance(s, str):
            return strings.normalized(s,**kwargs)
        return s  # If it's not a string, return it as-is


    return df.map(normalize_string)
