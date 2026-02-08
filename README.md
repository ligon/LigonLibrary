# LigonLibrary

A Python utility library for working with DataFrames, Google Sheets,
fuzzy string matching, and more.

## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/ligon/LigonLibrary.git
```

Or add to your project's dependencies (e.g. in `pyproject.toml`):

```toml
dependencies = [
    "ligonlibrary @ git+https://github.com/ligon/LigonLibrary.git",
]
```

Requires Python 3.11+.

## What's included

### DataFrame utilities

- **`get_dataframe(f)`** — Read a DataFrame from nearly any file: CSV, Excel,
  Parquet, Feather, Stata (.dta), SPSS, fixed-width, org-tables, and
  GPG-encrypted variants of all of the above.
- **`df_to_orgtbl(df)`** — Render a DataFrame as an Emacs org-mode table,
  with optional standard errors, confidence intervals, and significance stars.
- **`orgtbl_to_df(table)`** — Parse an org-mode table back into a DataFrame.
- **`df_from_orgfile(path)`** — Read named tables from `.org` files.
- **`from_dta(fn)`** — Read Stata `.dta` files with automatic label decoding.
- **`normalize_strings(df, ...)`** — Normalize string columns in a DataFrame.
- **`find_similar_pairs(s1, s2)`** — Find fuzzy-matching pairs between two Series.

### Google Sheets

- **`read_sheets(key, ...)`** / **`read_public_sheet(key)`** — Read a Google Sheet into a DataFrame.
- **`write_sheet(df, key, ...)`** — Write a DataFrame to a Google Sheet.
- **`delete_sheet(key)`** — Delete a Google Sheet.
- **`get_credentials(...)`** — Load Google service-account credentials (supports GPG-encrypted JSON).

### String matching

- **`normalized(s)`** — Normalize a string (case, whitespace, hyphens).
- **`similar(a, b)`** — Check whether two strings are fuzzy-similar.
- **`most_similar(s, candidates)`** — Find the best fuzzy match from a list.

### Other

- **`email_from_ligon(...)`** — Send email via the Gmail API.
- **`get_password_for_machine(host)`** — Look up a password in a GPG-encrypted `~/.authinfo.gpg` file.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
