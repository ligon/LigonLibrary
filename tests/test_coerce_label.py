"""`_coerce_label` must undo double-encoding without deleting anything.

The function exists to repair *mojibake*: UTF-8 text that some producer
decoded as `encoding`, so "Café" arrives as "CafÃ©".  The repair is to put the
bytes back and decode as UTF-8.  That direction is correct.

The bug was `errors="ignore"`, which made the same call LOSSY on text that was
never double-encoded: plain latin-1 "Boîte de tomate" encodes to b"Bo\xeete...",
0xEE is not a valid UTF-8 start byte, and ignoring the error DELETED the
character -- silently.
"""
import pytest

from ligonlibrary.dataframes import _coerce_label

DOUBLE_ENCODED = [                     # true text, before anything mangled it
    "Café",
    "bœuf",                            # the Niger _LOST_PREFIX_REPLACEMENTS case
    "Côte d’Ivoire",
]

PLAIN = [                              # correctly decoded already; leave alone
    ("iso-8859-1", "Boîte de tomate"),
    ("iso-8859-1", "Congé"),
    ("cp1252", "naïve"),
]


@pytest.mark.parametrize("declared", ["iso-8859-1", "cp1252", "iso-8859-2"])
@pytest.mark.parametrize("true_text", DOUBLE_ENCODED)
def test_double_encoding_is_undone(true_text, declared):
    """Build the mojibake the way pandas produces it, and vary what is declared.

    pandas decodes a .dta with latin-1 -- by declaration below format 118, as
    the fallback above it -- so the latin-1 view is the only string that ever
    reaches `_coerce_label`, and the repair must not depend on what the caller
    declared.  Decoding the fixture with `declared` instead would make the
    test invert its own construction: "Côte d’Ivoire" built via cp1252 gives
    "CÃ´te dâ€™Ivoire", which cp1252 re-encodes exactly, so the assertion
    passes on a string `from_dta` cannot produce.  What it really hands over
    is "CÃ´te dâ\x80\x99Ivoire", and cp1252 cannot encode U+0080 at all.
    """
    mojibake = true_text.encode("utf-8").decode("latin-1")
    assert _coerce_label(mojibake, declared) == true_text


@pytest.mark.parametrize("encoding,text", PLAIN)
def test_text_that_was_never_double_encoded_is_left_alone(encoding, text):
    """The old `errors="ignore"` deleted these characters instead."""
    assert _coerce_label(text, encoding) == text


@pytest.mark.parametrize("encoding,text", PLAIN)
def test_no_character_is_silently_dropped(encoding, text):
    """Guard the loss directly: the old failure was lossy, not merely wrong."""
    assert len(_coerce_label(text, encoding)) == len(text)


def test_none_is_a_passthrough():
    assert _coerce_label("Café", None) == "Café"
    assert _coerce_label(None, "cp1252") is None


def test_bytes_are_decoded_with_the_declared_encoding():
    assert _coerce_label("Café".encode("cp1252"), "cp1252") == "Café"


def test_undecodable_bytes_are_marked_not_dropped():
    """`errors="replace"` keeps a loss visible; `"ignore"` hid it."""
    assert _coerce_label(b"\xff\xfe", "utf-8") != ""
