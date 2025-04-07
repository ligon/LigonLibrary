#!/usr/bin/env python3

"""Miscellany of tools for manipulating dataframes.
"""

from . import strings
import pandas as pd

def normalize_strings(df,**kwargs):
    """Normalize strings in a dataframe.
    """
    def normalize_string(s):
        if isinstance(s, str):
            return strings.normalized(s,**kwargs)
        return s  # If it's not a string, return it as-is


    return df.map(normalize_string)

import pandas as pd
from typing import Callable, Dict, Set

def find_similar_pairs(
    s1: pd.Series,
    s2: pd.Series,
    similar: Callable[[str, str], bool]=strings.similar
) -> Dict[str, str]:
    """
    Find pairs of similar strings between two pandas Series.

    For each string in s1, find all strings in s2 where the comparison function
    `similar` returns True. Each s1 string maps to at most one s2 string.

    Parameters:
    -----------
    s1 : pd.Series
        First series of strings to compare
    s2 : pd.Series
        Second series of strings to compare
    similar : Callable[[str, str], bool]
        Comparison function that takes two strings and returns True if they're
        considered similar

    Returns:
    --------
    Dict[str, str]
        Dictionary mapping strings from s1 to similar strings in s2.
        Only includes pairs where similar() returned True.
        Each s1 string appears at most once in the keys.
        Each s2 string appears at most once in the values.
    """
    result = {}
    used_s2 = set()  # Track s2 strings already matched

    # Convert series to sets for faster lookup and to avoid duplicates
    s1_strings = set(s1.dropna())
    s2_strings = set(s2.dropna())

    for str1 in s1_strings:
        if str1 in result:
            continue  # Already matched

        # Find first unmatched s2 string that's similar
        for str2 in s2_strings:
            if str2 not in used_s2 and similar(str1, str2):
                result[str1] = str2
                used_s2.add(str2)
                break  # Move to next s1 string after first match

    return result
