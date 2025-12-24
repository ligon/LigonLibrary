import os

import pytest
from googleapiclient.errors import HttpError

from ligonlibrary.email_from_ligon import (
    ENV_EMAIL_CREDENTIALS,
    EmailContent,
    _as_email_content,
    _format_addresses,
    _compose_message,
    _send_with_retry,
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


def test_compose_message_multipart_when_html_present():
    content = EmailContent("Subj", "Plain text", (), "<b>HTML</b>")

    msg = _compose_message("to@example.com", content, "from@example.com")

    assert msg.get_content_type() == "multipart/alternative"
    parts = msg.get_payload()
    assert len(parts) == 2
    assert parts[0].get_content_type() == "text/plain"
    assert parts[0].get_payload(decode=True).decode() == "Plain text"
    assert parts[1].get_content_type() == "text/html"
    assert parts[1].get_payload(decode=True).decode() == "<b>HTML</b>"


def test_compose_message_raises_on_mismatched_html():
    content = EmailContent("Subj", "Plain text", (), "<b>HTML")

    with pytest.raises(ValueError):
        _compose_message("to@example.com", content, "from@example.com")


def test_format_addresses_parses_display_names():
    formatted = _format_addresses(["Name <user@example.com>", "other@example.com"])
    assert formatted == "Name <user@example.com>, other@example.com"


def test_send_with_retry_backoff(monkeypatch):
    calls = []

    class FakeResp:
        status = 429
        reason = "Too Many Requests"

    class FakeSend:
        def __init__(self):
            self.count = 0

        def execute(self):
            self.count += 1
            if self.count < 3:
                exc = HttpError(FakeResp(), b"rate limit")
                raise exc
            return {"id": "ok"}

    class FakeService:
        _sender = FakeSend()

        def users(self):
            return self

        def messages(self):
            return self

        def send(self, userId, body):
            calls.append((userId, body))
            return self._sender

    # Make time.sleep a no-op to keep test fast
    monkeypatch.setattr("time.sleep", lambda *_: None)

    out = _send_with_retry(FakeService(), {"raw": "x"}, max_retries=3, base_sleep=0)
    assert out == {"id": "ok"}
    assert calls[0][0] == "me"


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
                html_body="<p>This is a <strong>test</strong> message triggered by RUN_EMAIL_FROM_LIGON_TEST=1.</p>",
            )
        },
        from_email="ligon@berkeley.edu",
    )
