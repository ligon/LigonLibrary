"""Top-level helpers exposed by ligonlibrary."""

from importlib.metadata import PackageNotFoundError, version

from .dataframes import (  # noqa: F401
    df_from_orgfile,
    df_to_orgtbl,
    find_similar_pairs,
    from_dta,
    get_dataframe,
    normalize_strings,
    orgtbl_to_df,
)
from .sheets import (  # noqa: F401
    delete_sheet,
    get_credentials,
    read_public_sheet,
    read_sheets,
    write_sheet,
)
from .strings import most_similar, normalized, similar  # noqa: F401
from .authinfo import get_password_for_machine  # noqa: F401
from .email_from_ligon import email_from_ligon  # noqa: F401

try:  # pragma: no cover - fallback during editable installs
    __version__ = version("ligonlibrary")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    # dataframes
    "df_from_orgfile",
    "df_to_orgtbl",
    "find_similar_pairs",
    "from_dta",
    "get_dataframe",
    "normalize_strings",
    "orgtbl_to_df",
    # sheets
    "delete_sheet",
    "get_credentials",
    "read_public_sheet",
    "read_sheets",
    "write_sheet",
    # strings
    "most_similar",
    "normalized",
    "similar",
    # authinfo
    "get_password_for_machine",
    # email
    "email_from_ligon",
    # meta
    "__version__",
]
