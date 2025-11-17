import pandas as pd

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
