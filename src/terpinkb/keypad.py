from __future__ import annotations

import locale
import random
import re
import secrets
import string
from dataclasses import dataclass


CHARACTER = "character"
SHIFT = "shift"
CAPS = "caps"
PALETTE = "palette"
BACKSPACE = "backspace"
CLEAR = "clear"
SHUFFLE = "shuffle"
SUBMIT = "submit"
CANCEL = "cancel"
SPACER = "spacer"

VALID_ROLES = {
    CHARACTER,
    SHIFT,
    CAPS,
    PALETTE,
    BACKSPACE,
    CLEAR,
    SHUFFLE,
    SUBMIT,
    CANCEL,
    SPACER,
}

_SAFE_PALETTE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class KeypadKey:
    label: str
    value: str | None
    role: str
    category: str = ""

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("label must be non-empty")
        if not self.label.isprintable():
            raise ValueError("label must be printable")
        if self.role not in VALID_ROLES:
            raise ValueError(f"unsupported key role: {self.role}")
        if self.role == CHARACTER and not self.value:
            raise ValueError("character keys require a value")
        if self.role == CHARACTER and self.value is not None and len(self.value) != 1:
            raise ValueError("character key values must be exactly one character")
        if self.role == CHARACTER and self.value is not None and not self.value.isprintable():
            raise ValueError("character key values must be printable")
        if self.role != CHARACTER and self.value is not None:
            raise ValueError("only character keys may have values")


@dataclass(frozen=True)
class KeypadPalette:
    name: str
    label: str
    keys: tuple[KeypadKey, ...]
    shifted_keys: tuple[KeypadKey, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("palette name must be non-empty")
        if _SAFE_PALETTE_NAME.fullmatch(self.name) is None:
            raise ValueError("palette name must be a safe identifier")
        if not self.label:
            raise ValueError("palette label must be non-empty")
        if not self.label.isprintable():
            raise ValueError("palette label must be printable")
        if not any(key.role == CHARACTER for key in self.keys):
            raise ValueError("palette must contain at least one character key")


class KeypadLayout:
    def __init__(
        self,
        palettes: tuple[KeypadPalette, ...],
        *,
        rng: random.Random | None = None,
    ) -> None:
        if not palettes:
            raise ValueError("at least one palette is required")
        self._rng = rng if rng is not None else secrets.SystemRandom()
        self._palettes = tuple(self._dedupe_palette(palette) for palette in palettes)
        self._palette_by_name = {palette.name: palette for palette in self._palettes}
        if len(self._palette_by_name) != len(self._palettes):
            raise ValueError("palette names must be unique")

    @classmethod
    def default(
        cls,
        *,
        locale_name: str | None = None,
        rng: random.Random | None = None,
    ) -> KeypadLayout:
        letters = _locale_letters(locale_name)
        lower_letters = "".join(char for char in letters if char.lower() == char)
        shifted_letters = "".join(char.upper() for char in lower_letters)
        if not lower_letters:
            lower_letters = string.ascii_lowercase
            shifted_letters = string.ascii_uppercase

        return cls.from_palettes(
            (
                _palette("letters", "ABC", lower_letters, shifted_letters, "lowercase"),
                _palette("numbers", "123", string.digits, '!@#$%^&*()', "digit"),
                _palette("punctuation", ".,?", ".,;:?!'\"`", "<>[]{}()_-", "punctuation"),
                _palette("symbols", "@#+", "@#$/\\|+=~*&%^", "€£¥¢§©®™°±×÷", "symbol"),
            ),
            rng=rng,
        )

    @classmethod
    def from_palettes(
        cls,
        palettes: tuple[KeypadPalette, ...],
        *,
        rng: random.Random | None = None,
    ) -> KeypadLayout:
        return cls(palettes, rng=rng)

    @property
    def palettes(self) -> tuple[KeypadPalette, ...]:
        return self._palettes

    def keys(
        self,
        palette: str = "letters",
        *,
        shifted: bool = False,
        caps: bool = False,
    ) -> tuple[KeypadKey, ...]:
        selected = self._palette_by_name[palette]
        use_shifted = (shifted or caps) and bool(selected.shifted_keys)
        keys = selected.shifted_keys if use_shifted else selected.keys
        character_keys = [key for key in keys if key.role == CHARACTER]
        self._rng.shuffle(character_keys)
        return tuple(character_keys)

    def rows(
        self,
        palette: str = "letters",
        *,
        shifted: bool = False,
        caps: bool = False,
        width: int = 10,
    ) -> tuple[tuple[KeypadKey, ...], ...]:
        if width <= 0:
            raise ValueError("width must be greater than zero")
        keys = self.keys(palette, shifted=shifted, caps=caps)
        return tuple(tuple(keys[index : index + width]) for index in range(0, len(keys), width))

    def _dedupe_palette(self, palette: KeypadPalette) -> KeypadPalette:
        return KeypadPalette(
            name=palette.name,
            label=palette.label,
            keys=_dedupe_keys(palette.keys),
            shifted_keys=_dedupe_keys(palette.shifted_keys),
        )


def _palette(
    name: str,
    label: str,
    characters: str,
    shifted: str,
    category: str,
) -> KeypadPalette:
    shifted_category = "uppercase" if category == "lowercase" else category
    return KeypadPalette(
        name=name,
        label=label,
        keys=tuple(KeypadKey(char, char, CHARACTER, category) for char in characters),
        shifted_keys=tuple(KeypadKey(char, char, CHARACTER, shifted_category) for char in shifted),
    )


def _dedupe_keys(keys: tuple[KeypadKey, ...]) -> tuple[KeypadKey, ...]:
    seen_values: set[str] = set()
    deduped: list[KeypadKey] = []
    for key in keys:
        if key.role != CHARACTER:
            deduped.append(key)
            continue
        assert key.value is not None
        if key.value in seen_values:
            continue
        seen_values.add(key.value)
        deduped.append(key)
    return tuple(deduped)


def _locale_letters(locale_name: str | None) -> str:
    name = locale_name or locale.getlocale()[0] or ""
    language = name.split("_", maxsplit=1)[0].lower()
    extras = {
        "cs": "áčďéěíňóřšťúůýž",
        "da": "æøå",
        "de": "äöüß",
        "es": "ñáéíóúü",
        "fi": "åäö",
        "fr": "àâæçéèêëîïôœùûüÿ",
        "is": "áéíóúýþæöð",
        "it": "àèéìíîòóùú",
        "nl": "áéíóúàèëïöü",
        "no": "æøå",
        "pl": "ąćęłńóśźż",
        "pt": "áâãàçéêíóôõúü",
        "sv": "åäö",
        "tr": "çğıöşü",
    }.get(language, "")
    return _dedupe_text(string.ascii_lowercase + extras)


def _dedupe_text(value: str) -> str:
    seen: set[str] = set()
    chars: list[str] = []
    for char in value:
        if char in seen:
            continue
        seen.add(char)
        chars.append(char)
    return "".join(chars)
