from __future__ import annotations

import pytest

from terpinkb import SecretPolicy


def test_default_policy_imposes_no_requirements() -> None:
    policy = SecretPolicy()
    assert policy.satisfied_by(set(), 0)
    assert policy.missing_requirements(set(), 0) == ()


def test_invalid_policy_values_raise() -> None:
    with pytest.raises(ValueError):
        SecretPolicy(min_length=-1)


def test_policy_satisfaction_uses_metadata() -> None:
    policy = SecretPolicy(
        min_length=4,
        require_lowercase=True,
        require_uppercase=True,
        require_digit=True,
        require_punctuation=True,
    )
    categories = {"lowercase", "uppercase", "digit", "punctuation"}
    assert policy.satisfied_by(categories, 4)
    assert not policy.satisfied_by({"lowercase", "digit"}, 4)
    symbol_policy = SecretPolicy(require_symbol=True)
    assert symbol_policy.missing_requirements(set(), 1) == ("symbol",)


def test_strength_labels_are_coarse() -> None:
    policy = SecretPolicy(min_length=4, require_digit=True)
    assert policy.strength_label({"lowercase"}, 2) == "Too short"
    assert policy.strength_label({"lowercase"}, 4) == "Weak"
    label = policy.strength_label({"lowercase", "digit"}, 4)
    assert label in {"Meets policy", "Fair", "Strong"}
    assert "a1bc" not in label
    assert policy.strength_label({"lowercase", "uppercase", "digit"}, 12) == "Strong"
    assert policy.strength_label({"lowercase", "digit"}, 8) == "Fair"
