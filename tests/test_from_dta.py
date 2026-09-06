import pandas as pd
import pytest

from ligonlibrary.dataframes import from_dta


def _write_sample_dta(path):
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "item": [1, 2],
            "quantity": [3.5, 4.25],
        }
    )
    value_labels = {"item": {1: "beans", 2: "rice"}}
    df.to_stata(path, write_index=False, value_labels=value_labels)
    return value_labels


def test_from_dta_maps_value_labels(tmp_path):
    path = tmp_path / "sample.dta"
    _write_sample_dta(path)

    out = from_dta(path)

    assert out["item"].tolist() == ["beans", "rice"]
    assert out["quantity"].tolist() == [3.5, 4.25]
    assert out["id"].tolist() == [1, 2]
    assert out["item"].dtype == object


def test_from_dta_categories_only(tmp_path):
    path = tmp_path / "sample.dta"
    labels = _write_sample_dta(path)

    cats = from_dta(path, categories_only=True)

    assert "item" in cats
    assert cats["item"] == labels["item"]


def test_from_dta_file_like(tmp_path):
    path = tmp_path / "sample.dta"
    _write_sample_dta(path)

    with open(path, "rb") as handle:
        out = from_dta(handle, convert_categoricals=False)

    assert out["item"].tolist() == [1, 2]


# Mojibake as it actually reaches us: the .dta holds the UTF-8 bytes of the
# true text, and pandas decodes them with latin-1 -- by declaration below
# format 118, as the fallback above it.
_TRUE_LABEL = "Côte d’Ivoire"


def _write_mojibake_dta(path):
    """A real format-117 file whose label bytes are UTF-8, not latin-1."""
    pd.DataFrame({"country": [1, 2]}).to_stata(
        path,
        write_index=False,
        version=117,
        # pandas writes format 117 as latin-1, so handing it the latin-1 view
        # puts the UTF-8 bytes into the file verbatim.
        value_labels={"country": {1: _TRUE_LABEL.encode("utf-8").decode("latin-1"),
                                  2: "Ok"}},
    )
    # Guard the fixture: if pandas ever changed how it writes these, the test
    # would otherwise keep passing while testing nothing.
    assert _TRUE_LABEL.encode("utf-8") in path.read_bytes()
    return path


@pytest.mark.parametrize("declared", ["iso-8859-1", "cp1252", "iso-8859-2"])
def test_mojibake_is_repaired_whatever_encoding_is_declared(tmp_path, declared):
    """The repair must not depend on the caller's declaration.

    latin-1 is what mis-decoded the label, so latin-1's inverse is what
    recovers the bytes.  Spelling that as `encoding` made the repair no-op
    for any other declaration: this same file came back as
    "CÃ´te dâ\\x80\\x99Ivoire" under `encoding="cp1252"`, because cp1252
    cannot encode U+0080 and the round trip raised.
    """
    path = _write_mojibake_dta(tmp_path / "cote.dta")

    cats = from_dta(path, encoding=declared, categories_only=True)

    assert cats["country"][1] == _TRUE_LABEL


def test_labels_are_untouched_without_an_encoding(tmp_path):
    """`encoding=None` still gates the whole thing; the mojibake stays."""
    path = _write_mojibake_dta(tmp_path / "cote.dta")

    cats = from_dta(path, categories_only=True)

    assert cats["country"][1] == _TRUE_LABEL.encode("utf-8").decode("latin-1")
