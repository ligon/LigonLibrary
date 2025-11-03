#!/usr/bin/env python3

"""Miscellany of tools for manipulating dataframes.
"""
import pandas as pd
import dvc.api
from . import strings
from pyarrow.lib import ArrowInvalid
from functools import lru_cache
from pathlib import Path
from cfe.df_utils import df_to_orgtbl
from importlib.resources import files
from dvc.api import DVCFileSystem
from lsms import from_dta
import pyreadstat

@lru_cache(maxsize=3)
def get_dataframe(fn,convert_categoricals=True,encoding=None,categories_only=False,sheet=None):
    """From a file named fn, try to return a dataframe.

    Hope is that caller can be agnostic about file type,
    or if file is local or on a dvc remote.
    """

    def local_file(fn):
    # Is the file local?
        try:
            with open(fn) as f:
                pass
            return True
        except FileNotFoundError:
            return False

    def read_file(f,convert_categoricals=convert_categoricals,encoding=encoding,sheet=sheet):
        if isinstance(f,str):
            try:
                return pd.read_spss(f,convert_categoricals=convert_categoricals)
            except (pd.errors.ParserError, UnicodeDecodeError):
                pass

        try:
            return pd.read_parquet(f, engine='pyarrow')
        except (ArrowInvalid,):
            pass

        try:
            f.seek(0)
            return from_dta(f,convert_categoricals=convert_categoricals,encoding=encoding,categories_only=categories_only)
        except ValueError:
            pass

        try:
            f.seek(0)
            return pd.read_csv(f,encoding=encoding)
        except (pd.errors.ParserError, UnicodeDecodeError):
            pass

        try:
            f.seek(0)
            return pd.read_excel(f,sheet_name=sheet)
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError):
            pass

        try:
            f.seek(0)
            return pd.read_feather(f)
        except (pd.errors.ParserError, UnicodeDecodeError,ArrowInvalid) as e:
            pass

        try:
            f.seek(0)
            return pd.read_fwf(f)
        except (pd.errors.ParserError, UnicodeDecodeError):
            pass


        raise ValueError(f"Unknown file type for {fn}.")

    try:
        with open(fn,mode='rb') as f:
            df = read_file(f,convert_categoricals=convert_categoricals,encoding=encoding)
    except (TypeError,ValueError): # Needs filename?
        df = read_file(fn,convert_categoricals=convert_categoricals,encoding=encoding)

    return df

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
    similarity_threshold=85,
    verbose=False) -> Dict[str, str]:

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
    similarity_threshold : How demanding is match?

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
    if isinstance(s1,(list,tuple,set)):
        s1_strings = set(s1)
    else:
        s1_strings = set(s1.dropna())

    if isinstance(s2,(list,tuple,set)):
        s2_strings = set(s2)
    else:
        s2_strings = set(s2.dropna())

    for str1 in s1_strings:
        if str1 in result:
            continue  # Already matched

        out = strings.most_similar(str1,s2_strings,similarity_threshold=similarity_threshold,verbose=verbose,return_similarity=True)

        if out is not None:
            name, score = out
            result[str1] = name

    return result
