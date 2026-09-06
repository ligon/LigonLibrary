"""`_coerce_label` must recover mis-decoded Stata value labels, not delete them."""
import pytest

from ligonlibrary.dataframes import _coerce_label

# (declared encoding, the label as it exists in the file)
CASES = [
    ("iso-8859-2", "Đurđevdan"),      # Serbian/Croatian D-with-stroke
    ("cp1252", "Côte d’Ivoire"),      # curly apostrophe, cp1252 0x92
    ("iso-8859-1", "Café"),
    ("cp1252", "naïve — dash"),       # em dash, cp1252 0x97
]


@pytest.mark.parametrize("encoding,original", CASES)
def test_recovers_the_original_label(encoding, original):
    """pandas hands back a latin-1 *byte container*; reverse that, don't re-encode.

    `StataReader` has no `encoding` parameter (removed in pandas 2.0), so a
    .dta holding non-UTF-8 bytes is decoded as latin-1 with a UnicodeWarning.
    latin-1 maps bytes 0-255 onto codepoints 0-255 one-to-one, so the original
    bytes survive and `.encode("latin-1")` gets them back.

    The previous implementation encoded with the *caller's* encoding and
    decoded as UTF-8 -- the inverse of nothing -- and with `errors="ignore"`
    silently deleted every character the target codec could not represent:
    "Đurđevdan" -> "urevdan", "Café" -> "Caf".
    """
    as_pandas_returns_it = original.encode(encoding).decode("latin-1")
    assert _coerce_label(as_pandas_returns_it, encoding) == original


@pytest.mark.parametrize("encoding,original", CASES)
def test_no_character_is_silently_dropped(encoding, original):
    """The old failure was lossy, not merely wrong; guard the loss directly."""
    got = _coerce_label(original.encode(encoding).decode("latin-1"), encoding)
    assert len(got) == len(original)


def test_none_encoding_is_a_passthrough():
    assert _coerce_label("Café", None) == "Café"
    assert _coerce_label(None, "cp1252") is None


def test_an_already_correct_label_is_left_alone():
    """A value that never went through the fallback must not be round-tripped.

    `Đ` is not representable in latin-1, so the encode raises and the value is
    returned unchanged rather than mangled.
    """
    assert _coerce_label("Đurđevdan", "cp1252") == "Đurđevdan"


def test_bytes_input_is_decoded_with_the_declared_encoding():
    assert _coerce_label("Café".encode("cp1252"), "cp1252") == "Café"


def test_undecodable_bytes_are_marked_not_dropped():
    """`errors="replace"` keeps the loss visible; `"ignore"` hid it."""
    got = _coerce_label(b"\xff\xfe", "utf-8")
    assert got and got != ""
