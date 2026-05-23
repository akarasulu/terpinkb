from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecretPolicy:
    min_length: int = 0
    require_lowercase: bool = False
    require_uppercase: bool = False
    require_digit: bool = False
    require_punctuation: bool = False
    require_symbol: bool = False

    def __post_init__(self) -> None:
        if self.min_length < 0:
            raise ValueError("min_length must be non-negative")

    def satisfied_by(self, categories: set[str], length: int) -> bool:
        return not self.missing_requirements(categories, length)

    def missing_requirements(self, categories: set[str], length: int) -> tuple[str, ...]:
        missing: list[str] = []
        if length < self.min_length:
            missing.append("length")
        if self.require_lowercase and "lowercase" not in categories:
            missing.append("lowercase")
        if self.require_uppercase and "uppercase" not in categories:
            missing.append("uppercase")
        if self.require_digit and "digit" not in categories:
            missing.append("digit")
        if self.require_punctuation and "punctuation" not in categories:
            missing.append("punctuation")
        if self.require_symbol and "symbol" not in categories:
            missing.append("symbol")
        return tuple(missing)

    def strength_label(self, categories: set[str], length: int) -> str:
        if length < max(1, self.min_length):
            return "Too short"
        if self.missing_requirements(categories, length):
            return "Weak"
        variety = len(categories)
        if length >= 12 and variety >= 3:
            return "Strong"
        if length >= 8 and variety >= 2:
            return "Fair"
        return "Meets policy"
