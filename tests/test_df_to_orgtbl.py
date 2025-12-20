import numpy as np
import pandas as pd

from ligonlibrary.dataframes import df_to_orgtbl, orgtbl_to_df


def test_df_to_orgtbl_basic_plain(show_tables):
    df = pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 4.0]}, index=["row1", "row2"])

    out = df_to_orgtbl(df, float_fmt="%.1f", math_delimiters=False)

    assert out.startswith("|  | A")
    assert "| row1" in out and "1.0" in out and "3.0" in out
    assert "| row2" in out and "2.0" in out and "4.0" in out
    if show_tables:
        print("\nBasic table:\n", out)


def test_df_to_orgtbl_with_standard_errors(show_tables):
    df = pd.DataFrame({"A": [1.0, 2.0]}, index=["row1", "row2"])
    sedf = pd.DataFrame({"A": [0.1, 0.2]}, index=df.index)

    out = df_to_orgtbl(df, sedf=sedf, tdf=False, float_fmt="%.1f", math_delimiters=False)

    assert "(0.1)" in out
    assert "(0.2)" in out
    if show_tables:
        print("\nSE table:\n", out)


def test_orgtbl_to_df_basic():
    table = [
        ["A", "B"],
        ["1", "2"],
        ["3", "4"],
    ]

    df = orgtbl_to_df(table, col_name_size=1)

    assert list(df.columns) == ["A", "B"]
    assert df.iloc[0, 0] == "1"
    assert df.iloc[1, 1] == "4"


def test_orgtbl_to_df_multirow_headers_and_index():
    table = [
        ["A1", "A2"],
        ["B1", "B2"],
        ["x", "1"],
        ["y", "2"],
    ]

    df = orgtbl_to_df(table, col_name_size=2, index="('A1', 'A2')")

    assert list(df.columns) == ["('B1', 'B2')"]
    assert df.index.name == "('A1', 'A2')"
    assert "y" in df.index


def test_df_to_orgtbl_missing_values_render_as_dashes(show_tables):
    df = pd.DataFrame(
        {
            "A": [1.0, None, pd.NA],
            "B": [np.nan, 2.0, 3.0],
        },
        index=["r1", "r2", "r3"],
    )

    out = df_to_orgtbl(df, float_fmt="%.1f", math_delimiters=False)

    # Expect three missing slots rendered as ---
    assert out.count("---") >= 3
    if show_tables:
        print("\nMissing table:\n", out)


def test_df_to_orgtbl_with_stars_from_tstats(show_tables):
    df = pd.DataFrame({"beta": [2.0]}, index=["x"])
    tdf = pd.DataFrame({"beta": [2.0]}, index=df.index)  # two stars (>1.96)
    sedf = pd.DataFrame({"beta": [0.5]}, index=df.index)

    out = df_to_orgtbl(df, sedf=sedf, tdf=tdf, float_fmt="%.2f", math_delimiters=False)

    assert "2.00^{**}" in out
    assert "(0.50)" in out
    if show_tables:
        print("\nStars table:\n", out)


def test_df_to_orgtbl_conf_intervals(show_tables):
    df = pd.DataFrame({"beta": [1.0]}, index=["x"])
    lower = pd.DataFrame({"beta": [0.8]}, index=df.index)
    upper = pd.DataFrame({"beta": [1.2]}, index=df.index)

    out = df_to_orgtbl(
        df,
        conf_ints=(lower, upper),
        tdf=False,
        float_fmt="%.2f",
        math_delimiters=False,
    )

    assert "[0.80,0.80]" not in out  # ensure not duplicated
    assert "[0.80,1.20]" in out
    if show_tables:
        print("\nCI table:\n", out)
