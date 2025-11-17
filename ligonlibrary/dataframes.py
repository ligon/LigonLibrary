#!/usr/bin/env python3

"""Miscellany of tools for manipulating dataframes."""
import struct
import warnings

import pandas as pd

try:
    from pyarrow.lib import ArrowInvalid
except ImportError:  # pragma: no cover - optional dependency
    class ArrowInvalid(Exception):  # type: ignore
        """Fallback ArrowInvalid when pyarrow is unavailable."""

        pass
from functools import lru_cache

try:
    from cfe.df_utils import df_to_orgtbl  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    df_to_orgtbl = None  # type: ignore

try:
    import dvc.api  # noqa: F401  # pragma: no cover
    from dvc.api import DVCFileSystem  # noqa: F401  # pragma: no cover
except ImportError:  # pragma: no cover - optional dependency
    dvc = None  # noqa: F401
    DVCFileSystem = None  # type: ignore


def _coerce_label(value, encoding):
    """Return `value` recoded to UTF-8 using the supplied encoding."""
    if encoding is None or value is None:
        return value
    if isinstance(value, bytes):
        return value.decode(encoding, errors="ignore")
    return str(value).encode(encoding, errors="ignore").decode("utf-8", errors="ignore")


def from_dta(fn, convert_categoricals=True, encoding=None, categories_only=False):
    """Read a Stata .dta file into a pandas DataFrame.

    Parameters
    ----------
    fn : str | pathlib.Path | file-like
        Location of the Stata file or an open binary handle.
    convert_categoricals : bool, optional
        When true (default) map labelled columns to their string labels.
    encoding : str, optional
        Original character encoding for categorical labels, used to coerce
        values to UTF-8 when provided.
    categories_only : bool, optional
        When true, return the mapping of categorical metadata without
        materializing the DataFrame.
    """

    with pd.io.stata.StataReader(fn) as reader:
        try:
            df = reader.read(convert_dates=True, convert_categoricals=False)
        except struct.error as exc:
            raise ValueError("Not a Stata file?") from exc

        values = reader.value_labels()
        try:
            var_names = reader.varlist
            label_names = reader.lbllist
        except AttributeError:
            var_names = reader._varlist
            label_names = reader._lbllist

    var_to_label = dict(zip(var_names, label_names))
    cats = {}

    if convert_categoricals:
        for var in var_names:
            label_key = var_to_label.get(var)
            if not label_key:
                continue
            try:
                code_to_label = values[label_key]
            except KeyError:
                warnings.warn(f"Issue with categorical mapping: {var}", RuntimeWarning)
                continue
            if encoding:
                code_to_label = {
                    code: _coerce_label(label, encoding) for code, label in code_to_label.items()
                }
            df[var] = df[var].replace(code_to_label)
            cats[var] = code_to_label

    if categories_only:
        return cats

    return df

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
    from . import strings

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
    from . import strings

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
