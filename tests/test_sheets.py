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


class _FakeStatus:
    ok = True
    status = "decryption ok"
    stderr = ""

    def __init__(self, data):
        self.data = data


def _fake_decrypt(monkeypatch, sheets, payload, passphrase="pw"):
    import json as _json

    class _FakeGPG:
        def decrypt_file(self, fh, passphrase=None):
            return _FakeStatus(_json.dumps(payload).encode())

    monkeypatch.setattr(sheets.gnupg, "GPG", _FakeGPG)
    monkeypatch.setattr(sheets.getpass, "getpass", lambda prompt="": passphrase)
    monkeypatch.setattr(
        "builtins.input",
        lambda *a, **k: pytest.fail("passphrase must not be read with input()"),
    )


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_decrypt_credentials_writes_owner_only(monkeypatch, tmp_path):
    from ligonlibrary import sheets

    enc = tmp_path / "bundle.json.gpg"
    enc.write_bytes(b"ciphertext")
    dest = tmp_path / "keys"
    _fake_decrypt(monkeypatch, sheets, {"client_email": "svc@proj.iam.gserviceaccount.com"})

    out = sheets.decrypt_credentials(str(enc), destination=dest)

    assert out == dest / "svc@proj.iam.gserviceaccount.com"
    assert (out.stat().st_mode & 0o777) == 0o600
    assert (dest.stat().st_mode & 0o777) == 0o700


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_decrypt_credentials_tightens_existing_file(monkeypatch, tmp_path):
    from ligonlibrary import sheets

    enc = tmp_path / "bundle.json.gpg"
    enc.write_bytes(b"ciphertext")
    dest = tmp_path / "keys"
    dest.mkdir(mode=0o700)
    stale = dest / "svc@proj.iam.gserviceaccount.com"
    stale.write_text("{}")
    stale.chmod(0o644)
    _fake_decrypt(monkeypatch, sheets, {"client_email": stale.name})

    sheets.decrypt_credentials(str(enc), destination=dest)

    assert (stale.stat().st_mode & 0o777) == 0o600


@pytest.mark.parametrize("bad", ["../escape", "a/b", "..", ""])
def test_decrypt_credentials_rejects_unsafe_email(monkeypatch, tmp_path, bad):
    from ligonlibrary import sheets

    enc = tmp_path / "bundle.json.gpg"
    enc.write_bytes(b"ciphertext")
    _fake_decrypt(monkeypatch, sheets, {"client_email": bad})

    with pytest.raises(ValueError, match="Unsafe"):
        sheets.decrypt_credentials(str(enc), destination=tmp_path / "keys")
    assert not (tmp_path / "escape").exists()
