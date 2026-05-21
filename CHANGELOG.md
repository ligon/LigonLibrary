# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-05-21

### Changed
- Cleaned up `pyproject.toml`: removed redundant `[tool.poetry]` /
  `[tool.poetry.dependencies]` tables (Poetry 2.x reads PEP 621
  `[project]` natively), added PyPI classifiers, keywords, and project
  URLs.
- Fixed `make release` to bump the version before building so the
  resulting artifacts carry the new version.

### Added
- `CHANGELOG.md` (this file).
- GitHub Actions workflow that builds and publishes to PyPI on tag push
  using trusted publishing (OIDC).
- `README.org` mirror of `README.md` for Org-mode users.

## [0.2.0] - 2025-02-26

### Added
- `df_from_orgfile()` reads named tables from `.org` files; registered
  org-table reader inside `get_dataframe()`.
- GPG detection and decrypt fallback in `get_dataframe()`, with retry
  on agent failure.
- `python-magic`-based content sniffing so `get_dataframe()` orders
  parsers by detected file type rather than guessing from extension.
- `pass` (password-store) fallback in `get_password_for_machine()` for
  systems without `~/.authinfo.gpg`.
- Standard-error, confidence-interval, and significance-star options
  for `df_to_orgtbl()`.

### Changed
- `write_sheet()` now tries every available service account instead of
  only the first one.
- Non-seekable streams are buffered before reading in `get_dataframe()`.
- Packaging modernized for use as a pip-installable dependency.

### Removed
- Unused DVC handling from `get_dataframe()`.

[Unreleased]: https://github.com/ligon/LigonLibrary/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/ligon/LigonLibrary/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ligon/LigonLibrary/releases/tag/v0.2.0
