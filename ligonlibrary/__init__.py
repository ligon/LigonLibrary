"""Top-level helpers exposed by ligonlibrary."""

from importlib.metadata import PackageNotFoundError, version

from .dataframes import df_to_orgtbl, from_dta, orgtbl_to_df  # noqa: F401
from .sheets import (  # noqa: F401
    delete_sheet,
    get_credentials,
    read_public_sheet,
    read_sheets,
    write_sheet,
)

from .email_from_ligon import email_from_ligon

try:  # pragma: no cover - fallback during editable installs
    __version__ = version("ligonlibrary")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    "delete_sheet",
    "df_to_orgtbl",
    "from_dta",
    "orgtbl_to_df",
    "get_credentials",
    "read_public_sheet",
    "read_sheets",
    "write_sheet",
    "email_from_ligon",
    "__version__",
]
