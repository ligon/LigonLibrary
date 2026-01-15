import io
import os
import shutil
import subprocess

import pandas as pd
import pytest

from ligonlibrary.dataframes import get_dataframe


def test_get_dataframe_uses_excel_sheet(tmp_path, monkeypatch):
    excel_file = tmp_path / "sample.xlsx"
    first = pd.DataFrame({"first": [1]})
    second = pd.DataFrame({"second": [2]})

    with pd.ExcelWriter(excel_file) as writer:
        first.to_excel(writer, sheet_name="one", index=False)
        second.to_excel(writer, sheet_name="two", index=False)

    def raise_import_error(*args, **kwargs):
        raise ImportError("pyarrow missing")

    monkeypatch.setattr(pd, "read_parquet", raise_import_error)

    get_dataframe.cache_clear()
    df = get_dataframe(excel_file, sheet="two")

    assert list(df.columns) == ["second"]
    assert df.iloc[0, 0] == 2


def test_sheet_name_is_passed_to_read_excel_for_path(tmp_path, monkeypatch):
    excel_file = tmp_path / "sample.xlsx"
    pd.DataFrame({"col": [1]}).to_excel(excel_file, index=False, sheet_name="sheety")

    # Force all earlier readers to fail so read_excel is reached.
    monkeypatch.setattr(pd, "read_spss", lambda *_, **__: (_ for _ in ()).throw(ValueError("no spss")))
    monkeypatch.setattr(pd, "read_parquet", lambda *_, **__: (_ for _ in ()).throw(ImportError("no pyarrow")))
    monkeypatch.setattr("ligonlibrary.dataframes.from_dta", lambda *_, **__: (_ for _ in ()).throw(ValueError("no dta")))
    monkeypatch.setattr(pd, "read_csv", lambda *_, **__: (_ for _ in ()).throw(pd.errors.ParserError("bad csv")))
    monkeypatch.setattr(pd, "read_feather", lambda *_, **__: (_ for _ in ()).throw(ImportError("no feather")))
    monkeypatch.setattr(pd, "read_fwf", lambda *_, **__: (_ for _ in ()).throw(pd.errors.ParserError("bad fwf")))

    called = {}

    def fake_read_excel(file, sheet_name=None, **kwargs):
        called["sheet_name"] = sheet_name
        return pd.DataFrame({"ok": [1]})

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    get_dataframe.cache_clear()
    df = get_dataframe(excel_file, sheet="sheety")

    assert called["sheet_name"] == "sheety"
    assert list(df.columns) == ["ok"]


def test_sheet_name_is_passed_to_read_excel_for_buffer(tmp_path, monkeypatch):
    excel_file = tmp_path / "sample.xlsx"
    pd.DataFrame({"col": [1]}).to_excel(excel_file, index=False, sheet_name="sheety")

    with open(excel_file, "rb") as f:
        excel_bytes = f.read()

    # Disable upstream readers
    monkeypatch.setattr(pd, "read_parquet", lambda *_, **__: (_ for _ in ()).throw(ImportError("no pyarrow")))
    monkeypatch.setattr("ligonlibrary.dataframes.from_dta", lambda *_, **__: (_ for _ in ()).throw(ValueError("no dta")))
    monkeypatch.setattr(pd, "read_csv", lambda *_, **__: (_ for _ in ()).throw(pd.errors.ParserError("bad csv")))
    monkeypatch.setattr(pd, "read_feather", lambda *_, **__: (_ for _ in ()).throw(ImportError("no feather")))
    monkeypatch.setattr(pd, "read_fwf", lambda *_, **__: (_ for _ in ()).throw(pd.errors.ParserError("bad fwf")))

    called = {}

    def fake_read_excel(file, sheet_name=None, **kwargs):
        called["sheet_name"] = sheet_name
        return pd.DataFrame({"ok": [2]})

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    buffer = pd.io.common.BytesIO(excel_bytes)
    get_dataframe.cache_clear()
    df = get_dataframe(buffer, sheet="sheety")

    assert called["sheet_name"] == "sheety"
    assert list(df.columns) == ["ok"]
    assert df.iloc[0, 0] == 2


def test_non_seekable_stream_is_buffered(monkeypatch):
    csv_bytes = b"col\n3\n"

    class NonSeekable(io.BytesIO):
        def seekable(self):
            return False

        def seek(self, *_, **__):
            raise OSError("no seek")

    buffer = NonSeekable(csv_bytes)

    # Force fallthrough to CSV reader.
    monkeypatch.setattr(pd, "read_parquet", lambda *_, **__: (_ for _ in ()).throw(ImportError("no pyarrow")))
    monkeypatch.setattr("ligonlibrary.dataframes.from_dta", lambda *_, **__: (_ for _ in ()).throw(ValueError("no dta")))
    monkeypatch.setattr(pd, "read_excel", lambda *_, **__: (_ for _ in ()).throw(ValueError("no excel")))
    monkeypatch.setattr(pd, "read_feather", lambda *_, **__: (_ for _ in ()).throw(ImportError("no feather")))
    monkeypatch.setattr(pd, "read_fwf", lambda *_, **__: (_ for _ in ()).throw(pd.errors.ParserError("bad fwf")))

    get_dataframe.cache_clear()
    df = get_dataframe(buffer)

    assert list(df.columns) == ["col"]
    assert df.iloc[0, 0] == 3


def test_get_dataframe_decrypts_pgp_file(tmp_path, monkeypatch):
    gpg = shutil.which("gpg")
    if gpg is None:
        pytest.skip("gpg not installed")

    gnupg_home = tmp_path / "gnupg"
    gnupg_home.mkdir()
    env = os.environ.copy()
    env["GNUPGHOME"] = str(gnupg_home)

    # Create a key without a passphrase for non-interactive decrypt.
    subprocess.run(
        [
            gpg,
            "--batch",
            "--yes",
            "--homedir",
            str(gnupg_home),
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            "",
            "--quick-gen-key",
            "test@example.com",
            "default",
            "default",
            "0",
        ],
        check=True,
        env=env,
    )

    plaintext = tmp_path / "data.csv"
    plaintext.write_text("col\n4\n", encoding="utf-8")
    ciphertext = tmp_path / "data.csv.gpg"

    subprocess.run(
        [
            gpg,
            "--batch",
            "--yes",
            "--homedir",
            str(gnupg_home),
            "--trust-model",
            "always",
            "--recipient",
            "test@example.com",
            "--output",
            str(ciphertext),
            "--encrypt",
            str(plaintext),
        ],
        check=True,
        env=env,
    )

    monkeypatch.setenv("GNUPGHOME", str(gnupg_home))
    get_dataframe.cache_clear()
    df = get_dataframe(ciphertext)

    assert list(df.columns) == ["col"]
    assert df.iloc[0, 0] == 4
