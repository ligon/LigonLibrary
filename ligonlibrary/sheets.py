"""Utilities for interacting with Google Sheets."""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Optional
from urllib.error import HTTPError

import gnupg
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from gspread_pandas import Spread
from gspread_pandas.client import SpreadsheetNotFound

ENV_SERVICE_ACCOUNT_DIR = "LIGONLIBRARY_SERVICE_ACCOUNTS"
SERVICE_ACCOUNT_EMAIL_FIELD = "client_email"


def _default_key_destination() -> Path:
    return Path(
        os.environ.get(
            ENV_SERVICE_ACCOUNT_DIR, Path.home() / ".ligonlibrary" / "service_accounts"
        )
    )


def decrypt_credentials(
    encrypted_key_file: str,
    destination: Optional[os.PathLike[str] | str] = None,
) -> Path:
    """
    Decrypt a GPG-wrapped service account key into *destination*.

    Parameters
    ----------
    encrypted_key_file:
        Path to the encrypted credentials bundle (e.g. ``students.json.gpg``).
    destination:
        Directory where the decrypted JSON credentials should be stored.
        Each decrypted file is saved under the service account's email.
    """
    destination_path = Path(destination) if destination is not None else _default_key_destination()
    destination_path.mkdir(parents=True, exist_ok=True)

    gpg = gnupg.GPG()
    passphrase = input(
        f"Input secret passphrase for {encrypted_key_file} to create google drive credentials: "
    )
    with open(encrypted_key_file, "rb") as encrypted_file:
        status = gpg.decrypt_file(encrypted_file, passphrase=passphrase)

    if not status.ok:
        if "decryption failed" in status.status:
            raise ValueError("Decryption failed. Check passphrase?")
        if "gpg: error" in status.stderr:
            raise IOError("Unable to write key file.")
        raise RuntimeError(f"Unable to create decrypted file: {status.status}")

    account_data = json.loads(status.data)
    credential_path = destination_path / account_data[SERVICE_ACCOUNT_EMAIL_FIELD]
    with credential_path.open("w") as output_file:
        json.dump(account_data, output_file)

    return credential_path


def _load_credentials_from_path(
    path: Path, *, verbose: bool = False
) -> Dict[str, MutableMapping[str, str]]:
    with path.open() as credential_file:
        service_account_info = json.load(credential_file)
    if verbose:
        print(f"Key available for {service_account_info[SERVICE_ACCOUNT_EMAIL_FIELD]}.")
    return {
        service_account_info[SERVICE_ACCOUNT_EMAIL_FIELD]: service_account_info,
    }


def get_credentials(
    fn: Optional[os.PathLike[str] | str] = None,
    encrypted_key_file: str = "students.json.gpg",
    verbose: bool = False,
) -> Dict[str, MutableMapping[str, str]]:
    """
    Load service-account credentials from *fn*.

    If *fn* points to a directory, load every JSON file inside.  When credentials
    are missing, this routine attempts to decrypt *encrypted_key_file* into the
    destination directory and then retry.
    """
    path = Path(fn) if fn is not None else _default_key_destination()
    credentials: Dict[str, MutableMapping[str, str]] = {}

    try:
        if path.is_dir():
            files: Iterable[Path] = list(path.iterdir())
            if not files:
                raise IOError
            for entry in files:
                if entry.is_dir():
                    continue
                credentials.update(
                    get_credentials(
                        entry,
                        encrypted_key_file=encrypted_key_file,
                        verbose=verbose,
                    )
                )
        else:
            credentials.update(_load_credentials_from_path(path, verbose=verbose))
        return credentials
    except IOError:
        decrypt_credentials(encrypted_key_file, destination=path)
        return get_credentials(
            fn=path, encrypted_key_file=encrypted_key_file, verbose=verbose
        )


def to_numeric(value):
    try:
        return pd.to_numeric(value)
    except (ValueError, TypeError):
        return value


def read_public_sheet(key: str, sheet: Optional[str | int] = None) -> pd.DataFrame:
    """
    Read a public Google Sheet and return a :class:`pandas.DataFrame`.
    """
    if key.startswith("https://"):
        parts = key.split("/")
        try:
            key = parts[parts.index("d") + 1]
        except (ValueError, IndexError) as exc:
            raise ValueError("Unrecognized sheet URL format.") from exc

    url = f"https://docs.google.com/spreadsheets/d/{key}/export?format=csv"
    if sheet is not None:
        url += f"&gid={str(sheet).replace(' ', '%20')}"

    try:
        df = pd.read_csv(url)
    except HTTPError as exc:
        raise HTTPError(f"Not found. Check permissions? {exc}") from exc

    return df.drop([col for col in df.columns if col.startswith("Unnamed")], axis=1)


def _raw_sheet_to_df(data, nheaders: int):
    headers = data[:nheaders]
    body = data[nheaders:]

    if nheaders > 1:
        clean_headers = [header_row[:] for header_row in headers]
        forward_header = [s.strip() for s in clean_headers[0]]
        forward_header.reverse()
        idxn = len(forward_header) - forward_header.index("")
        idxnames = headers[-1][:idxn]

        columns = pd.MultiIndex.from_arrays([h[idxn:] for h in headers])
        if len(columns.levels) == 1:
            columns = columns.get_level_values(0)

        index = [row[:idxn] for row in body]
        values = [row[idxn:] for row in body]
        index = pd.MultiIndex.from_tuples(index, names=idxnames)
        if len(index.levels) == 1:
            index = index.get_level_values(0)
        return pd.DataFrame(values, index=index, columns=columns)

    columns = pd.Index(headers[0])
    return pd.DataFrame(body, columns=columns)


def _authorize_clients(
    json_creds: Optional[str],
) -> Dict[str, gspread.Client]:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    clients: Dict[str, gspread.Client] = {}

    if json_creds is not None:
        creds = Credentials.from_service_account_file(json_creds, scopes=scope)
        clients[creds.service_account_email] = gspread.authorize(creds)
        return clients

    try:
        json_info = get_credentials()
        for account_email, service_account_info in json_info.items():
            creds = Credentials.from_service_account_info(
                service_account_info, scopes=scope
            )
            clients[account_email] = gspread.authorize(creds)
    except Exception:
        warnings.warn("Unable to access credentials. Trying without...")

    return clients


def read_sheets(
    key: str | Mapping[str, str],
    json_creds: Optional[str] = None,
    sheet: Optional[str | int] = None,
    force_numeric: bool = True,
    nheaders: int = 1,
):
    """
    Read a Google Sheet via key or URL, optionally using service-account credentials.

    Parameters mirror the historical interface used in course material.
    """
    clients = _authorize_clients(json_creds)

    if not clients:
        if json_creds is not None:
            raise RuntimeError("No valid credentials found.")
        return read_public_sheet(key, sheet)

    try:
        key = key[sheet]  # type: ignore[index]
    except (TypeError, KeyError):
        pass

    warnings_raised = []
    workbook = None
    active_client = None

    for service_account, client in clients.items():
        try:
            if isinstance(key, str) and key.startswith("https://"):
                workbook = client.open_by_url(key)
            else:
                workbook = client.open_by_key(key)  # type: ignore[arg-type]
            workbook.worksheets()
            active_client = client
            break
        except (APIError, PermissionError):
            warnings_raised.append(
                f"Unable to open {key} using credentials for {service_account}."
            )

    for message in warnings_raised:
        warnings.warn(message)

    if workbook is None or active_client is None:
        raise RuntimeError(f"Unable to open {key} with available credentials.")

    if sheet is None:
        dataframes = {}
        for worksheet in workbook.worksheets():
            data = worksheet.get_all_values()
            df = _raw_sheet_to_df(data, nheaders)
            dataframes[worksheet.title] = df.apply(to_numeric) if force_numeric else df
        return dataframes

    try:
        sheet_index = int(sheet)
    except (TypeError, ValueError):
        worksheet = workbook.worksheet(sheet)  # type: ignore[arg-type]
    else:
        worksheet = workbook.get_worksheet(sheet_index)

    data = worksheet.get_all_values()
    df = _raw_sheet_to_df(data, nheaders)
    return df.apply(to_numeric) if force_numeric else df


def _select_service_account_info(
    creds: Dict[str, MutableMapping[str, str]]
) -> MutableMapping[str, str]:
    if not creds:
        raise RuntimeError("No valid credentials found.")
    return next(iter(creds.values()))


def write_sheet(
    df: pd.DataFrame,
    user_email: str,
    user_role: str = "reader",
    json_creds: Optional[str] = None,
    key: str = "",
    sheet: str = "My Sheet",
) -> str:
    """
    Write ``df`` to Google Sheets, creating the sheet if necessary.

    Returns the spreadsheet key.
    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    if "http" in key and "/" in key:
        parts = key.split("/")
        try:
            key = parts[parts.index("d") + 1]
        except (ValueError, IndexError) as exc:
            raise ValueError("Unrecognized sheet URL format.") from exc

    if json_creds is not None:
        credential_obj = Credentials.from_service_account_file(json_creds, scopes=scope)
        gc = gspread.authorize(credential_obj)
        service_credentials = credential_obj
    else:
        json_info = get_credentials()
        service_account_info = _select_service_account_info(json_info)
        service_credentials = Credentials.from_service_account_info(
            service_account_info, scopes=scope
        )
        gc = gspread.authorize(service_credentials)

    try:
        spread = Spread(key, creds=service_credentials)
        spreadsheet_id = spread.url.split("/")[-1]
    except SpreadsheetNotFound:
        spreadsheet = gc.create(key or "EEP153 Sheet")
        spreadsheet_id = spreadsheet.id
        spread = Spread(spreadsheet_id, creds=gc.auth)  # type: ignore[arg-type]
        try:
            worksheet = spreadsheet.sheet1
        except AttributeError:
            worksheet = None
        if worksheet is not None:
            spreadsheet.del_worksheet(worksheet)

    gc.insert_permission(spreadsheet_id, user_email, perm_type="user", role=user_role)
    spread.df_to_sheet(df, sheet=sheet)

    return spreadsheet_id


def delete_sheet(
    key: str,
    json_creds: Optional[str] = None,
) -> None:
    """
    Delete a Google Sheet identified by *key* (or URL).
    """
    clients = _authorize_clients(json_creds)

    if not clients:
        raise RuntimeError("No valid credentials found.")

    warnings_raised = []
    workbook_key = key
    gc_client: Optional[gspread.Client] = None

    for service_account, client in clients.items():
        try:
            if workbook_key.startswith("https://"):
                parts = workbook_key.split("/")
                workbook_key = parts[parts.index("d") + 1]
            workbook = client.open_by_key(workbook_key)
            workbook.worksheets()
            gc_client = client
            break
        except (APIError, PermissionError):
            warnings_raised.append(
                f"Unable to open {key} using credentials for {service_account}."
            )

    for message in warnings_raised:
        warnings.warn(message)

    if gc_client is None:
        raise RuntimeError(f"Unable to open {key} with available credentials.")

    print(f"Deleting {workbook_key}.")
    gc_client.del_spreadsheet(workbook_key)
