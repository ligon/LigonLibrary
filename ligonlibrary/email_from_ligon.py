import base64
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Iterable, NamedTuple

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from requests import HTTPError


class EmailContent(NamedTuple):
    subject: str
    body: str
    cc: tuple[str, ...] = ()


def is_html(s):
    return bool(s) and s.lstrip().startswith('<')


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
    raise TypeError("Expected EmailContent or tuple of length 2 or 3 for email content.")


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


def email_from_ligon(emails,from_email='ligon@berkeley.edu'):
    """Create and send email from ligon@berkeley.edu.

       - emails : A dictionary with keys which are "to" email addresses, and
                  values which are either (subject, body) or EmailContent(subject, body, cc).
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

            if is_html(content.body):
                message = MIMEText(content.body, 'html')
            else:
                message = MIMEText(content.body, 'plain')

            message['Subject'] = content.subject
            message['From'] = from_email
            message['To'] = to
            if content.cc:
                message['Cc'] = ', '.join(content.cc)

            create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

            msg = (service.users().messages().send(userId="me", body=create_message).execute())
            print(f"Sent message to {message['To']} Message Id: {msg['id']}.")
    except HTTPError as error:
        print(F'An error occurred: {error}')
