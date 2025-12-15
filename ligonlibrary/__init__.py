"""Top-level helpers exposed by ligonlibrary."""

from importlib.metadata import PackageNotFoundError, version

from .dataframes import from_dta  # noqa: F401
from .sheets import (  # noqa: F401
    delete_sheet,
    get_credentials,
    read_public_sheet,
    read_sheets,
    write_sheet,
)

try:  # pragma: no cover - fallback during editable installs
    __version__ = version("ligonlibrary")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    "delete_sheet",
    "from_dta",
    "get_credentials",
    "read_public_sheet",
    "read_sheets",
    "write_sheet",
    "__version__",
]
