import os

import pytest

from ligonlibrary.email_from_ligon import (
    ENV_EMAIL_CREDENTIALS,
    EmailContent,
    _as_email_content,
    _resolve_credentials_path,
    email_from_ligon,
)


def test_as_email_content_accepts_legacy_tuple():
    content = _as_email_content(("Subject", "Body"))

    assert content.subject == "Subject"
    assert content.body == "Body"
    assert content.cc == ()


def test_resolve_credentials_prefers_env(monkeypatch, tmp_path):
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}")
    monkeypatch.setenv(ENV_EMAIL_CREDENTIALS, str(cred_file))

    assert _resolve_credentials_path() == cred_file


def test_resolve_credentials_falls_back_to_home(monkeypatch, tmp_path):
    home_dir = tmp_path / "home"
    creds_dir = home_dir / ".ligonlibrary"
    creds_dir.mkdir(parents=True)
    cred_file = creds_dir / "email_secret.json"
    cred_file.write_text("{}")
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.delenv(ENV_EMAIL_CREDENTIALS, raising=False)

    assert _resolve_credentials_path() == cred_file


@pytest.mark.skipif(
    os.getenv("RUN_EMAIL_FROM_LIGON_TEST") != "1",
    reason="Integration test sends a real email; set RUN_EMAIL_FROM_LIGON_TEST=1 to run.",
)
def test_email_from_ligon_with_cc():
    email_from_ligon(
        {
            "test@ligon.org": EmailContent(
                subject="Test message from automated test",
                body="This is a test message triggered by RUN_EMAIL_FROM_LIGON_TEST=1.",
                cc=("cc@ligon.org",),
            )
        },
        from_email="ligon@berkeley.edu",
    )
