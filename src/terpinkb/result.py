class PinResult:
    """A bytearray-backed secret result with an explicit destroy lifecycle."""

    def __init__(self, value: bytearray) -> None:
        self._value = value
        self._destroyed = False
        self._length = len(value)

    def consume(self) -> bytes:
        """Return an immutable bytes copy of the secret."""
        if self._destroyed:
            raise RuntimeError("PinResult has been destroyed")
        return bytes(self._value)

    def destroy(self) -> None:
        """Overwrite the internal bytearray in place."""
        for index in range(len(self._value)):
            self._value[index] = 0
        self._destroyed = True

    @property
    def destroyed(self) -> bool:
        return self._destroyed

    def __repr__(self) -> str:
        return f"PinResult(length={self._length}, destroyed={self._destroyed})"

    __str__ = __repr__
