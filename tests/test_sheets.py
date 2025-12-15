import importlib
import sys

import pandas as pd
import pytest


def test_default_destination_can_be_overridden(monkeypatch, tmp_path):
    monkeypatch.setenv("LIGONLIBRARY_SERVICE_ACCOUNTS", str(tmp_path))
    sys.modules.pop("ligonlibrary.sheets", None)
    sheets = importlib.import_module("ligonlibrary.sheets")

    assert sheets._default_key_destination() == tmp_path


def test_raw_sheet_to_df_multiindex():
    from ligonlibrary.sheets import _raw_sheet_to_df

    data = [
        ["", "", "metric", "metric"],
        ["country", "state", "value", "value2"],
        ["US", "CA", 1, 2],
        ["US", "NY", 3, 4],
    ]

    df = _raw_sheet_to_df(data, nheaders=2)

    assert isinstance(df.index, pd.MultiIndex)
    assert list(df.index.names) == ["country", "state"]
    assert isinstance(df.columns, pd.MultiIndex)
    assert list(df.columns.get_level_values(1)) == ["value", "value2"]
    assert df.loc[("US", "CA"), ("metric", "value")] == 1


def test_raw_sheet_to_df_single_header():
    from ligonlibrary.sheets import _raw_sheet_to_df

    data = [
        ["col_a", "col_b"],
        ["foo", "bar"],
    ]

    df = _raw_sheet_to_df(data, nheaders=1)

    assert list(df.columns) == ["col_a", "col_b"]
    assert df.iloc[0].tolist() == ["foo", "bar"]
