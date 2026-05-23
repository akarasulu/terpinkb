from __future__ import annotations

import pytest

from terpinkb import PinResult


def test_consume_returns_bytes() -> None:
    result = PinResult(bytearray(b"abc123"))
    assert result.consume() == b"abc123"
    assert isinstance(result.consume(), bytes)


def test_destroy_wipes_and_marks_destroyed() -> None:
    value = bytearray(b"abc123")
    result = PinResult(value)
    result.destroy()
    assert result.destroyed is True
    assert value == bytearray(b"\x00" * 6)
    value[:] = b"abc123"
    result.destroy()
    assert value == bytearray(b"\x00" * 6)


def test_consume_after_destroy_raises() -> None:
    result = PinResult(bytearray(b"abc123"))
    result.destroy()
    with pytest.raises(RuntimeError):
        result.consume()


def test_repr_and_str_do_not_contain_secret() -> None:
    result = PinResult(bytearray(b"abc123"))
    assert "abc123" not in repr(result)
    assert "abc123" not in str(result)
