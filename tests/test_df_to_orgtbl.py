import pandas as pd

from ligonlibrary.dataframes import df_to_orgtbl


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
