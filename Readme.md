# terpinkb

`terpinkb` is a small Textual package for collecting PINs or short secrets with a
randomized on-screen keyboard. It is designed for applications that want to avoid
sending secret characters through the physical keyboard input path.

## Threat Model

This component helps with keyboard-channel avoidance. Users choose characters by
mouse or by non-secret keyboard navigation such as Tab, arrow keys, Enter,
Backspace, Escape, Shift, Caps, and palette switching.

It does not make secret entry safe on a compromised host, compromised terminal
emulator, compromised Python process, screen scraper, memory inspector, hostile
shell, terminal escape injection path, or malware that observes mouse events or
process memory.

## Features

- Native Textual `ModalScreen`.
- Randomized character buttons.
- Locale-aware default palettes with letters, numbers, punctuation, and symbols.
- On-screen Shift, Caps, Space, Backspace, Clear, Shuffle, OK, and Cancel.
- Optional coarse policy and strength/status display.
- `PinResult` returns bytes and supports explicit in-place destruction.

## Installation

```bash
pip install -e ".[dev]"
```

The preferred local workflow uses `uv`:

```bash
uv venv
uv pip install -e ".[dev]"
uv run pytest
uv run ruff check .
uv run mypy src
```

## Usage

```python
from textual.app import App, ComposeResult
from textual.widgets import Button

from terpinkb import RandomizedPinModal, PinResult


class DemoApp(App):
    def compose(self) -> ComposeResult:
        yield Button("Enter Secret", id="enter-secret")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "enter-secret":
            self.push_screen(
                RandomizedPinModal(secret_length=6),
                self.handle_secret_result,
            )

    def handle_secret_result(self, result: PinResult | None) -> None:
        if result is None:
            self.notify("Secret entry canceled")
            return

        try:
            secret_bytes = result.consume()
            # Verify immediately, then drop application-side references.
        finally:
            result.destroy()
```

## Demo

```bash
python examples/demo.py
```

The demo shows only masked receipt status. It never prints or displays the
secret itself.

## Testing

```bash
pytest
ruff check .
mypy src
```

## Release

Build and validate distribution artifacts locally:

```bash
python -m build
twine check dist/*
```

Publishing is configured through GitHub Actions and PyPI Trusted Publishing. To
publish a release, configure the `akarasulu/terpinkb` repository as a trusted
publisher for the `terpinkb` PyPI project, then publish a GitHub release. The
release workflow will test, build, validate, and upload the package to PyPI.

## Policy And Strength

`SecretPolicy` can enforce simple metadata-based requirements such as minimum
length or requiring a digit. These rules are optional and disabled by default.
Strength/status text is deliberately coarse and advisory. It is not a
cryptographic guarantee and is less useful for short fixed PIN workflows or HSM
PINs with device retry counters.

## HSM PINs

`terpinkb` may be used to collect an HSM, smart-card, token, or PKCS#11 PIN when
the embedding application can pass the returned bytes directly to its HSM library
or middleware. Do not pass the PIN in command-line arguments, environment
variables, config files, logs, or external prompts. Respect device retry counters
and lockout behavior, and let the embedding application handle vendor-specific
PIN formats.

## Security Caveats

Python cannot guarantee complete memory secrecy. `PinResult.destroy()` overwrites
the package-owned bytearray, but immutable bytes copies returned to the caller
cannot be wiped by this package. Verify immediately and drop references as soon
as possible.
