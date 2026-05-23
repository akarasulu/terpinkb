from __future__ import annotations

import random

import pytest

from terpinkb import KeypadKey, KeypadLayout, KeypadPalette


def _values(keys: tuple[KeypadKey, ...]) -> set[str]:
    return {key.value for key in keys if key.value is not None}


def test_default_layout_contains_expected_palettes() -> None:
    layout = KeypadLayout.default(rng=random.Random(1))
    assert {palette.name for palette in layout.palettes} == {
        "letters",
        "numbers",
        "punctuation",
        "symbols",
    }
    assert set("abcxyz") <= _values(layout.keys("letters"))
    assert set("ABCXYZ") <= _values(layout.keys("letters", shifted=True))
    assert set("0123456789") == _values(layout.keys("numbers"))
    assert {"!", "?", "."} <= _values(layout.keys("punctuation")) | _values(
        layout.keys("punctuation", shifted=True)
    )
    assert {"@", "#", "$"} <= _values(layout.keys("symbols"))


def test_deterministic_rng_produces_deterministic_order() -> None:
    first = KeypadLayout.default(rng=random.Random(42))
    second = KeypadLayout.default(rng=random.Random(42))
    assert [key.value for key in first.keys("letters")] == [
        key.value for key in second.keys("letters")
    ]


def test_rows_use_requested_width() -> None:
    layout = KeypadLayout.default(rng=random.Random(1))
    rows = layout.rows("numbers", width=3)
    assert [len(row) for row in rows] == [3, 3, 3, 1]
    with pytest.raises(ValueError):
        layout.rows("numbers", width=0)


def test_roles_are_validated() -> None:
    with pytest.raises(ValueError):
        KeypadKey("X", "x", "unknown")
    with pytest.raises(ValueError):
        KeypadKey("", "x", "character")
    with pytest.raises(ValueError):
        KeypadKey("bad\nlabel", "x", "character")
    with pytest.raises(ValueError):
        KeypadKey("X", None, "character")
    with pytest.raises(ValueError):
        KeypadKey("AB", "ab", "character")
    with pytest.raises(ValueError):
        KeypadKey("ESC", "\x1b", "character")
    with pytest.raises(ValueError):
        KeypadKey("Clear", "x", "clear")


def test_palette_and_layout_validation() -> None:
    with pytest.raises(ValueError):
        KeypadPalette("", "ABC", (KeypadKey("a", "a", "character"),))
    with pytest.raises(ValueError):
        KeypadPalette("bad name", "ABC", (KeypadKey("a", "a", "character"),))
    with pytest.raises(ValueError):
        KeypadPalette("1bad", "ABC", (KeypadKey("a", "a", "character"),))
    with pytest.raises(ValueError):
        KeypadPalette("letters", "", (KeypadKey("a", "a", "character"),))
    with pytest.raises(ValueError):
        KeypadPalette("letters", "bad\nlabel", (KeypadKey("a", "a", "character"),))
    with pytest.raises(ValueError):
        KeypadPalette("letters", "ABC", (KeypadKey("Clear", None, "clear"),))
    with pytest.raises(ValueError):
        KeypadLayout.from_palettes(())
    palette = KeypadPalette("letters", "ABC", (KeypadKey("a", "a", "character"),))
    with pytest.raises(ValueError):
        KeypadLayout.from_palettes((palette, palette))


def test_no_duplicate_character_keys_in_palette() -> None:
    palette = KeypadPalette(
        "letters",
        "ABC",
        (
            KeypadKey("a", "a", "character", "lowercase"),
            KeypadKey("a", "a", "character", "lowercase"),
            KeypadKey("b", "b", "character", "lowercase"),
        ),
    )
    layout = KeypadLayout.from_palettes((palette,), rng=random.Random(1))
    assert _values(layout.keys("letters")) == {"a", "b"}


def test_locale_extras_and_control_key_dedupe() -> None:
    layout = KeypadLayout.default(locale_name="tr_TR", rng=random.Random(1))
    assert {"ç", "ğ", "ı", "ö", "ş", "ü"} <= _values(layout.keys("letters"))

    palette = KeypadPalette(
        "letters",
        "ABC",
        (
            KeypadKey("Clear", None, "clear"),
            KeypadKey("a", "a", "character", "lowercase"),
        ),
    )
    layout = KeypadLayout.from_palettes((palette,), rng=random.Random(1))
    assert len(layout.palettes[0].keys) == 2


def test_caps_uses_shifted_letters() -> None:
    layout = KeypadLayout.default(rng=random.Random(1))
    assert set("ABC") <= _values(layout.keys("letters", caps=True))
