# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2026-09-07

### Fixed
- `from_dta(..., encoding=...)` no longer deletes characters from value
  labels.  `_coerce_label` passed `errors="ignore"` on both ends of its
  round trip, so every character the target codec could not represent
  was dropped without a word: `Boîte de tomate` came back as
  `Bote de tomate`.  Failures are now caught and the value returned
  unchanged — text that was never double-encoded is the normal case,
  not an error — and raw bytes use `errors="replace"` so a genuine loss
  stays visible.
- `_coerce_label` now reverses the decode that actually mangled the
  label.  pandas reads a `.dta` as latin-1 — by declaration below Stata
  format 118, as the fallback above it — so latin-1's inverse is what
  recovers the file's bytes.  Taking the caller's declared `encoding`
  there made the repair a silent no-op for any other declaration: one
  file holding the UTF-8 bytes of `Côte d’Ivoire` was repaired under
  `encoding="iso-8859-1"` and returned still broken under
  `encoding="cp1252"`.

  Only callers passing `encoding=` are affected; the parameter still
  selects the codec for raw `bytes` input and still gates the repair.

### Changed
- Regenerated `poetry.lock`, which had drifted from `pyproject.toml`
  since the 0.2.1 packaging changes.  `poetry install` had aborted on
  every CI run since May, so no test had actually executed on `master`
  or on any pull request in that window.  No dependency versions moved.
- `.coder-session/` is now ignored.

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

[Unreleased]: https://github.com/ligon/LigonLibrary/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/ligon/LigonLibrary/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/ligon/LigonLibrary/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ligon/LigonLibrary/releases/tag/v0.2.0
