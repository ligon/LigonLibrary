import pandas as pd

from ligonlibrary.dataframes import df_to_orgtbl, orgtbl_to_df


def test_df_to_orgtbl_basic_plain():
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]}, index=["row1", "row2"])

    out = df_to_orgtbl(df, float_fmt="%.0f", math_delimiters=False)

    assert "| A | B" in out
    assert "| row1  | 1 " in out
    assert "| row2  | 2 " in out


def test_df_to_orgtbl_with_standard_errors():
    df = pd.DataFrame({"A": [1.0, 2.0]}, index=["row1", "row2"])
    sedf = pd.DataFrame({"A": [0.1, 0.2]}, index=df.index)

    out = df_to_orgtbl(df, sedf=sedf, tdf=False, float_fmt="%.1f", math_delimiters=False)

    assert "(0.1)" in out
    assert "(0.2)" in out


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

    df = orgtbl_to_df(table, col_name_size=2, index="B1")

    assert list(df.columns) == ["('A1', 'A2')", "('B1', 'B2')"]
    assert df.index.name == "B1"
    assert "y" in df.index
