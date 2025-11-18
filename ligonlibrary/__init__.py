"""Top-level helpers exposed by ligonlibrary."""

from importlib.metadata import PackageNotFoundError, version

from .dataframes import from_dta  # noqa: F401

try:  # pragma: no cover - fallback during editable installs
    __version__ = version("ligonlibrary")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = ["from_dta", "__version__"]
