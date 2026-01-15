#!/usr/bin/env python3

"""Miscellany of tools for manipulating dataframes."""
import struct
import warnings
from warnings import warn
from io import BytesIO
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import magic  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    magic = None
try:
    from pyarrow.lib import ArrowInvalid
except ImportError:  # pragma: no cover - optional dependency
    class ArrowInvalid(Exception):  # type: ignore
        """Fallback ArrowInvalid when pyarrow is unavailable."""

        pass
from functools import lru_cache

def df_to_orgtbl(
    df,
    tdf=None,
    sedf=None,
    conf_ints=None,
    float_fmt="%5.3f",
    bonus_stats=None,
    math_delimiters=True,
    print_heading=True,
):
    """
    Return a string that renders *df* as an org-table.

    Optional inputs include conf_ints, a pair (lowerdf, upperdf). If supplied,
    confidence intervals will be printed in brackets below the point estimate.

    If conf_ints is not supplied but sedf is, then standard errors will be
    in parentheses below the point estimate.

    If tdf is False and sedf is supplied then stars will decorate significant point estimates.
    If tdf is a df of t-statistics stars will decorate significant point estimates.
    """

    def is_missing(x):
        try:
            return pd.isna(x)
        except TypeError:
            return False

    def mypop(x, index=-1):
        """Pop like a list, but pop of non-iterables returns x."""
        if isinstance(x, str):
            return x
        try:
            return x.pop(index)
        except (IndexError, AttributeError):
            return x

    if isinstance(df, list):
        if len(df) == 0:
            return ""
        col0 = df[0].columns

        current = df_to_orgtbl(
            mypop(df, 0),
            mypop(tdf, 0),
            mypop(sedf, 0),
            conf_ints=mypop(conf_ints, 0),
            float_fmt=mypop(float_fmt, 0),
            bonus_stats=mypop(bonus_stats, 0),
            math_delimiters=mypop(math_delimiters, 0),
            print_heading=print_heading,
        )

        if len(df):
            if np.all(df[0].columns == col0):
                print_heading = False
            else:
                print_heading = True

            return (
                current
                + "|-\n"
                + df_to_orgtbl(
                    df,
                    tdf=tdf,
                    sedf=sedf,
                    conf_ints=conf_ints,
                    float_fmt=float_fmt,
                    bonus_stats=bonus_stats,
                    math_delimiters=math_delimiters,
                    print_heading=print_heading,
                )
            )
        else:
            return current

    if len(df.shape) == 1:  # We have a series?
        df = pd.DataFrame(df)

    # Test for duplicates in index
    if df.index.duplicated().sum() > 0:
        warn("Dataframe index contains duplicates.")

    # Test for duplicates in columns
    if df.columns.duplicated().sum() > 0:
        warn("Dataframe columns contain duplicates.")

    try:  # Look for a multiindex
        levels = len(df.index.levels)
        names = ["" if v is None else v for v in df.index.names]
    except AttributeError:  # Single index
        levels = 1
        names = [df.index.name if (df.index.name is not None) else ""]

    def column_heading(df):
        try:  # Look for multiindex columns
            collevels = len(df.columns.levels)
            colnames = ["" if v is None else v for v in df.columns.names]
        except AttributeError:  # Single index
            collevels = 1
            colnames = [df.columns.name if (df.columns.name is not None) else ""]

        if collevels == 1:
            s = "| " + " | ".join(names) + " | " + "|   ".join([str(s) for s in df.columns]) + "  |\n|-\n"
        else:
            colhead = np.array(df.columns.tolist()).T
            lastcol = [""] * collevels
            for l, j in enumerate(colhead.T.copy()):
                for k in range(collevels):
                    if lastcol[k] == j[k]:
                        colhead[k, l] = ""
                lastcol = j

            colhead = colhead.tolist()
            s = ""
            for k in range(collevels):
                if k < collevels - 1:
                    s += "| " * levels + " | "
                else:
                    s += "| " + " | ".join(names) + " | "
                s += " | ".join(colhead[k]) + "  |\n"
            s += "|-\n"

        return s

    def se_linestart(stats, i):
        if stats is None:
            return "|" * levels
        else:
            try:
                statline = stats.loc[i]
                assert levels >= len(statline), "Too many columns of bonus stats"
                line = [""] * (levels - len(statline) + 1)
                line += statline.tolist()
                return " | ".join(line)
            except (AttributeError, TypeError):  # stats a dict or series?
                return " | " + str(stats[i])

    def format_entry(x, stars="", se=False, float_fmt=float_fmt, math_delimiters=math_delimiters):
        try:
            fmt = float_fmt + stars
            if se:
                fmt = f"({fmt})"
            if math_delimiters:
                entry = "| \\(" + fmt + "\\) "
            else:
                entry = "| " + fmt + " "
            if is_missing(x):
                return "| --- "
            else:
                return entry % x
        except TypeError:
            return "| %s " % str(x)

    if print_heading:
        s = column_heading(df)
    else:
        s = ""

    if (tdf is None) and (sedf is None) and (conf_ints is None):
        lastidx = [""] * levels
        for i in df.index:
            if levels == 1:  # Normal index
                s += "| %s  " % i
            else:
                for k in range(levels):
                    if lastidx[k] != i[k]:
                        s += "| %s " % i[k]
                    else:
                        s += "| "
            lastidx = i

            for j in df.columns:  # Point estimates
                s += format_entry(df[j][i])
            s += "|\n"
        return s
    elif not (tdf is None) and (sedf is None) and (conf_ints is None):
        lastidx = [""] * levels
        for i in df.index:
            if levels == 1:  # Normal index
                s += "| %s  " % i
            else:
                for k in range(levels):
                    if lastidx[k] != i[k]:
                        s += "| %s " % i[k]
                    else:
                        s += "| "
            lastidx = i

            for j in df.columns:
                try:
                    stars = (np.abs(tdf[j][i]) > 1.65) + 0.0
                    stars += (np.abs(tdf[j][i]) > 1.96) + 0.0
                    stars += (np.abs(tdf[j][i]) > 2.577) + 0.0
                    stars = int(stars)
                    if stars > 0:
                        stars = "^{" + "*" * stars + "}"
                    else:
                        stars = ""
                except KeyError:
                    stars = ""
                s += format_entry(df[j][i], stars)

            s += "|\n"

        return s
    elif not (sedf is None) and (conf_ints is None):  # Print standard errors on alternate rows
        if tdf is not False:
            try:  # Passed in dataframe?
                tdf.shape
            except AttributeError:
                tdf = df[sedf.columns] / sedf

        lastidx = [""] * levels
        for i in df.index:
            if levels == 1:  # Normal index
                s += "| %s  " % i
            else:
                for k in range(levels):
                    if lastidx[k] != i[k]:
                        s += "| %s " % i[k]
                    else:
                        s += "| "
            lastidx = i

            for j in df.columns:  # Point estimates
                if tdf is not False:
                    try:
                        stars = (np.abs(tdf[j][i]) > 1.65) + 0.0
                        stars += (np.abs(tdf[j][i]) > 1.96) + 0.0
                        stars += (np.abs(tdf[j][i]) > 2.577) + 0.0
                        stars = int(stars)
                        if stars > 0:
                            stars = "^{" + "*" * stars + "}"
                        else:
                            stars = ""
                    except KeyError:
                        stars = ""
                else:
                    stars = ""
                s += format_entry(df[j][i], stars)

            s += "|\n" + se_linestart(bonus_stats, i)
            for j in df.columns:  # Now standard errors
                s += "  "
                try:
                    if is_missing(df[j][i]):  # Pt estimate miss
                        se = ""
                    elif is_missing(sedf[j][i]):
                        se = "(---)"
                    else:
                        se = format_entry(sedf[j][i], se=True)
                except KeyError:
                    se = "|  "
                s += se
            s += "|\n"
        return s
    elif not (conf_ints is None):  # Print confidence intervals on alternate rows
        if tdf is not False and sedf is not None:
            try:  # Passed in dataframe?
                tdf.shape
            except AttributeError:
                tdf = df[sedf.columns] / sedf
        lastidx = [""] * levels
        for i in df.index:
            if levels == 1:  # Normal index
                s += "| %s  " % i
            else:
                for k in range(levels):
                    if lastidx[k] != i[k]:
                        s += "| %s " % i[k]
                    else:
                        s += "| "
            lastidx = i

            for j in df.columns:  # Point estimates
                if tdf is not False and tdf is not None:
                    try:
                        stars = (np.abs(tdf[j][i]) > 1.65) + 0.0
                        stars += (np.abs(tdf[j][i]) > 1.96) + 0.0
                        stars += (np.abs(tdf[j][i]) > 2.577) + 0.0
                        stars = int(stars)
                        if stars > 0:
                            stars = "^{" + "*" * stars + "}"
                        else:
                            stars = ""
                    except KeyError:
                        stars = ""
                else:
                    stars = ""
                s += format_entry(df[j][i], stars)
            s += "|\n" + se_linestart(bonus_stats, i)

            for j in df.columns:  # Now confidence intervals
                s += "  "
                try:
                    lower = conf_ints[0][j][i]
                    upper = conf_ints[1][j][i]
                    if is_missing(lower) or is_missing(upper):
                        ci = "---"
                    else:
                        ci = "[" + float_fmt + "," + float_fmt + "]"
                        ci = ci % (lower, upper)
                except KeyError:
                    ci = ""
                entry = "| " + ci + "  "
                s += entry
            s += "|\n"
        return s



def orgtbl_to_df(table, col_name_size=1, format_string=None, index=None, dtype=None):
    """
    Convert an org-table (list of lists) into a pandas DataFrame.

    Requires the use of the header `:colnames no` for preservation of original column names.

    Parameters
    ----------
    table : list[list]
        Parsed org table rows.
    col_name_size : int
        Number of rows that make up the column names.
    format_string : str, optional
        Format string applied to column names.
    index : str | list[str], optional
        Column(s) to set as the index.
    dtype : type, optional
        Optional dtype for the DataFrame.
    """
    if col_name_size == 0:
        return pd.DataFrame(table, dtype=dtype)

    colnames = table[:col_name_size]

    if col_name_size == 1:
        if format_string:
            new_colnames = [format_string % x for x in colnames[0]]
        else:
            new_colnames = colnames[0]
    else:
        new_colnames = []
        for colnum in range(len(colnames[0])):
            curr_tuple = tuple([x[colnum] for x in colnames])
            if format_string:
                new_colnames.append(format_string % curr_tuple)
            else:
                new_colnames.append(str(curr_tuple))

    df = pd.DataFrame(table[col_name_size:], columns=new_colnames, dtype=dtype)

    if index:
        df.set_index(index, inplace=True)

    return df
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


def _looks_like_pgp(header: bytes, path_hint=None) -> bool:
    """Heuristically determine if the content looks like PGP-encrypted data."""
    if path_hint:
        suffix = str(path_hint).lower()
        if suffix.endswith((".gpg", ".pgp", ".asc")):
            return True

    stripped = header.lstrip()
    if stripped.startswith(b"-----BEGIN PGP MESSAGE-----"):
        return True

    if magic is not None:
        try:
            mime = magic.from_buffer(header, mime=True)
        except Exception:
            mime = None
        try:
            desc = magic.from_buffer(header)
        except Exception:
            desc = None

        for candidate in (mime, desc):
            if candidate and "pgp" in str(candidate).lower():
                return True

    # Fallback heuristic for binary packets: look for "PGP" marker in the first bytes.
    return b"PGP" in header[:32]


def _decrypt_with_gpg(stream, path_hint=None):
    """Attempt to decrypt the supplied stream/path with gpg, returning BytesIO on success."""
    cmd = ["gpg", "--batch", "--yes", "--quiet", "--pinentry-mode", "loopback", "--decrypt"]
    try:
        if isinstance(stream, (str, Path)):
            completed = subprocess.run(cmd + [str(stream)], capture_output=True, check=False, timeout=15)
        else:
            payload = stream.read()
            completed = subprocess.run(cmd, input=payload, capture_output=True, check=False, timeout=15)
        if completed.returncode != 0 or not completed.stdout:
            if not isinstance(stream, (str, Path)) and hasattr(stream, "seek"):
                try:
                    stream.seek(0)
                except Exception:
                    pass
            return None
        return BytesIO(completed.stdout)
    except FileNotFoundError:  # gpg missing
        return None
    except subprocess.TimeoutExpired:
        return None


@lru_cache(maxsize=3)
def get_dataframe(fn,convert_categoricals=True,encoding=None,categories_only=False,sheet=None):
    """From a file named fn, try to return a dataframe.

    Hope is that caller can be agnostic about file type.
    """

    def read_file(f,convert_categoricals=convert_categoricals,encoding=encoding,sheet=sheet):
        stream = f
        if not isinstance(stream, (str, Path)):
            if (not hasattr(stream, "seek")) or (hasattr(stream, "seekable") and not stream.seekable()):
                stream = BytesIO(stream.read())
            else:
                stream.seek(0)

        path_hint = stream if isinstance(stream, (str, Path)) else None

        def peek_header():
            try:
                if isinstance(stream, (str, Path)):
                    with open(stream, "rb") as handle:
                        return handle.read(1024)
                pos = None
                if hasattr(stream, "tell"):
                    try:
                        pos = stream.tell()
                    except Exception:
                        pos = None
                data = stream.read(1024)
                if pos is not None and hasattr(stream, "seek"):
                    stream.seek(pos)
                elif hasattr(stream, "seek"):
                    stream.seek(0)
                return data
            except OSError:
                return b""

        header = peek_header()
        if header and _looks_like_pgp(header, path_hint=path_hint):
            decrypted = _decrypt_with_gpg(stream, path_hint=path_hint)
            if decrypted is not None:
                stream = decrypted
            elif not isinstance(stream, (str, Path)) and hasattr(stream, "seek"):
                try:
                    stream.seek(0)
                except Exception:
                    pass

        def reset():
            if hasattr(stream, "seek"):
                stream.seek(0)

        if isinstance(stream,(str, Path)):
            try:
                return pd.read_spss(stream,convert_categoricals=convert_categoricals)
            except (pd.errors.ParserError, UnicodeDecodeError, ValueError, ImportError):
                pass

        try:
            return pd.read_parquet(stream, engine='pyarrow')
        except (ArrowInvalid, ImportError):
            pass

        try:
            reset()
            return from_dta(stream,convert_categoricals=convert_categoricals,encoding=encoding,categories_only=categories_only)
        except ValueError:
            pass

        try:
            reset()
            return pd.read_csv(stream,encoding=encoding)
        except (pd.errors.ParserError, UnicodeDecodeError):
            pass

        try:
            reset()
            return pd.read_excel(stream,sheet_name=sheet)
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError):
            pass

        try:
            reset()
            return pd.read_feather(stream)
        except (pd.errors.ParserError, UnicodeDecodeError, ArrowInvalid, ImportError):
            pass

        try:
            reset()
            return pd.read_fwf(stream)
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
