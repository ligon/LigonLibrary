import base64
import os
from email.headerregistry import Address
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, NamedTuple

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from requests import HTTPError


class EmailContent(NamedTuple):
    subject: str
    body: str
    cc: tuple[str, ...] = ()
    html_body: str | None = None


def is_html(s):
    return bool(s) and s.lstrip().startswith('<')


_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class _LooseHTMLValidator(HTMLParser):
    """Lightweight check for obvious mismatched/unclosed tags."""

    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in _VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        # Self-closing; nothing to track
        return

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"Unexpected </{tag}>; open stack={self.stack!r}")
        else:
            self.stack.pop()


def _validate_html_body(html_body: str):
    parser = _LooseHTMLValidator()
    parser.feed(html_body)
    if parser.stack:
        parser.errors.append(f"Unclosed tags: {parser.stack!r}")
    if parser.errors:
        raise ValueError("; ".join(parser.errors))


def _format_addresses(addresses: Iterable[str] | str) -> str:
    """Ensure addresses are RFC-compliant and dedented of display names."""
    if isinstance(addresses, str):
        addresses = (addresses,)

    formatted = []
    for raw in addresses:
        name, addr_spec = parseaddr(raw)
        if not addr_spec:
            raise ValueError(f"Invalid email address: {raw!r}")
        formatted.append(str(Address(display_name=name or "", addr_spec=addr_spec)))
    return ", ".join(formatted)


def _coerce_cc(cc):
    """Normalize CC input into a tuple of addresses."""
    if cc is None:
        return ()
    if isinstance(cc, str):
        return (cc,)
    if isinstance(cc, Iterable):
        return tuple(cc)
    raise TypeError(f"cc must be a string or iterable of strings, got {type(cc).__name__}")


def _as_email_content(value):
    """Accept legacy (subject, body) tuples or EmailContent with optional cc."""
    if isinstance(value, EmailContent):
        return value
    if isinstance(value, tuple):
        if len(value) == 2:
            subject, body = value
            return EmailContent(subject, body)
        if len(value) == 3:
            subject, body, cc = value
            return EmailContent(subject, body, _coerce_cc(cc))
        if len(value) == 4:
            subject, body, cc, html_body = value
            return EmailContent(subject, body, _coerce_cc(cc), html_body)
    raise TypeError("Expected EmailContent or tuple of length 2, 3, or 4 for email content.")


ENV_EMAIL_CREDENTIALS = "LIGONLIBRARY_EMAIL_CREDENTIALS"


def _resolve_credentials_path() -> Path:
    """Locate OAuth client secrets used for sending mail."""
    candidates = []

    env_path = os.environ.get(ENV_EMAIL_CREDENTIALS)
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists():
            return candidate
        candidates.append(candidate)

    home_default = Path.home() / ".ligonlibrary" / "email_secret.json"
    if home_default.exists():
        return home_default
    candidates.append(home_default)

    legacy = Path("./.credentials/email_secret.json")
    if legacy.exists():
        return legacy
    candidates.append(legacy)

    raise FileNotFoundError(
        f"No email credentials found. Checked: {', '.join(str(c) for c in candidates)}. "
        f"Set {ENV_EMAIL_CREDENTIALS} to point at your OAuth client secrets."
    )


def _compose_message(to: str, content: EmailContent, from_email: str):
    """Build the MIME message, using multipart/alternative when HTML provided."""
    if content.html_body is not None:
        _validate_html_body(content.html_body)
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(content.body, "plain"))
        message.attach(MIMEText(content.html_body, "html"))
    else:
        subtype = "html" if is_html(content.body) else "plain"
        message = MIMEText(content.body, subtype)

    message["Subject"] = content.subject
    message["From"] = _format_addresses((from_email,))
    message["To"] = _format_addresses((to,))
    if content.cc:
        message["Cc"] = _format_addresses(content.cc)

    return message


def email_from_ligon(emails,from_email='ligon@berkeley.edu'):
    """Create and send email from ligon@berkeley.edu.

       - emails : A dictionary with keys which are "to" email addresses, and
                  values which are either (subject, body), (subject, body, cc),
                  (subject, body, cc, html_body), or EmailContent(subject, body, cc, html_body).
       - If html_body is provided, send multipart/alternative with both plain and HTML parts.
    """
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.send"
    ]
    credential_path = _resolve_credentials_path()
    flow = InstalledAppFlow.from_client_secrets_file(credential_path, SCOPES)
    creds = flow.run_local_server(port=0)

    try:
        # create gmail api client
        service = build("gmail", "v1", credentials=creds)

        for to,body in emails.items():
            content = _as_email_content(body)

            message = _compose_message(to, content, from_email)

            create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

            msg = (service.users().messages().send(userId="me", body=create_message).execute())
            print(f"Sent message to {message['To']} Message Id: {msg['id']}.")
    except HTTPError as error:
        print(F'An error occurred: {error}')
