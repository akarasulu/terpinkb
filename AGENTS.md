# AGENTS

## Project Name

`terpinkb` - short for **ter**minal **pin** keyboard

## Purpose

Build a standalone Python project that provides an idiomatic Textual widget/screen for randomized PIN or secret-entry workflows using mixed-character on-screen entry.

The project must provide a reusable Textual `ModalScreen` that displays a randomized on-screen keyboard. Users can enter a PIN or secret using terminal mouse clicks or non-secret keyboard navigation such as Tab, Shift-Tab, arrow keys, Enter, Backspace, Escape, and optional Clear.

The on-screen keyboard must behave like a compact modern software keyboard, not a single numeric keypad and not a giant flat character grid. Even when the consuming application calls the value a PIN, this component must support mixed characters, punctuation, numbers, capitalization, Shift-modified characters, Caps Lock, and alternative symbol palettes.

By default, the keyboard should derive its character palettes from what the current Python process and locale can represent. Use the active locale as a best-effort signal for the default text palette, include common number and punctuation palettes, and keep the layout extensible so applications can provide explicit palettes later. Do not read physical keypresses to discover characters.

In this project, safe secret entry specifically means entering the secret value through the randomized on-screen keyboard rather than through physical character keys. This keeps the PIN or secret out of the keyboard input path, which is the channel this component is designed to avoid.

The primary goal is to avoid sending secret characters through the physical keyboard input path, reducing exposure to keyboard event loggers in a constrained local-terminal threat model.

This project is not a complete anti-compromise solution. It protects only against keyboard-channel capture. It does not protect against a compromised terminal emulator, compromised Textual process, screen scraper, memory inspector, hostile host, malicious shell, terminal escape injection, or malware observing mouse events or process memory.

---

## Core Design Goals

1. Implement the secret-entry UI as a native Textual `ModalScreen`.
2. Use Textual's normal composition model: `compose()`, containers, widgets, messages, bindings, and TCSS/CSS.
3. Keep the component reusable by other Textual applications.
4. Provide a minimal demo application.
5. Provide tests using Textual's testing facilities and `pytest`.
6. Avoid direct use of curses, raw terminal parsing, or ad-hoc ANSI escape handling.
7. Avoid custom global event loops.
8. Avoid storing secret values longer than necessary.
9. Do not use a normal Textual `Input` widget for secret entry.
10. Do not bind physical character keys to secret entry.

---

## Intended Usage

A parent Textual app should be able to do something like:

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
            # Verify immediately.
            # Then wipe application-side copies as soon as possible.
        finally:
            result.destroy()
````

---

## Deliverables

Create a complete standalone Python package with the following structure:

```text
terpinkb/
  AGENTS.md
  Readme.md
  pyproject.toml
  src/
    terpinkb/
      __init__.py
      modal.py
      result.py
      keypad.py
      policy.py
      messages.py
      css/
        randomized_pin_modal.tcss
  examples/
    demo.py
  tests/
    test_modal.py
    test_result.py
    test_keypad_layout.py
    test_policy.py
```

The project must be installable with:

```bash
pip install -e ".[dev]"
```

The demo must run with:

```bash
python examples/demo.py
```

The tests must run with:

```bash
pytest
```

---

## Dependencies

Use modern Python packaging.

Use `uv` for local project and dependency management. Keep the project metadata standard PEP 621 in `pyproject.toml` so the package remains installable with normal `pip` tooling.

Preferred local workflow:

```bash
uv venv
uv pip install -e ".[dev]"
uv run pytest
uv run ruff check .
uv run mypy src
```

Required runtime dependencies:

```toml
dependencies = [
  "textual>=0.86",
]
```

Development dependencies:

```toml
[project.optional-dependencies]
dev = [
  "pytest",
  "pytest-asyncio",
  "ruff",
  "mypy",
]
```

Prefer Python 3.11+.

```toml
requires-python = ">=3.11"
```

Do not add large dependencies for such a small component.

Use Python standard-library locale facilities for best-effort default palette selection. Do not add a keyboard-layout engine dependency for version 0.1.

---

## Public API

The package root must export:

```python
from terpinkb.modal import RandomizedPinModal
from terpinkb.result import PinResult
from terpinkb.keypad import KeypadLayout, KeypadKey, KeypadPalette
from terpinkb.policy import SecretPolicy

__all__ = [
    "RandomizedPinModal",
    "PinResult",
    "KeypadLayout",
    "KeypadKey",
    "KeypadPalette",
    "SecretPolicy",
]
```

---

## Main Components

### 1. `RandomizedPinModal`

File:

```text
src/terpinkb/modal.py
```

Implement:

```python
class RandomizedPinModal(ModalScreen[PinResult | None]):
    ...
```

This must be a Textual `ModalScreen`, not a plain widget.

The modal must:

1. Dim or visually separate the underlying application using normal Textual modal behavior and CSS.
2. Render a dialog centered on the screen.
3. Show a masked secret display.
4. Render randomized character buttons for the active palette.
5. Support mouse clicks.
6. Support focus traversal.
7. Support arrow-key movement over the keypad grid.
8. Support Enter/Space to activate the focused button.
9. Support Escape to cancel.
10. Support Backspace to delete the last entered character.
11. Support Clear.
12. Support Shift as a temporary modifier for capitalization and shifted alternatives.
13. Support Caps Lock for persistent capitalization on letter palettes.
14. Support switching between text, numbers, punctuation, and alternative symbol palettes.
15. Optionally support Shuffle.
16. Optionally auto-submit when `secret_length` characters are entered.
17. Return `PinResult` on success.
18. Return `None` on cancel.
19. Never return a normal Python `str` secret from the public modal API.

Constructor:

```python
def __init__(
    self,
    secret_length: int = 6,
    *,
    title: str = "Enter Secret",
    palettes: tuple[KeypadPalette, ...] | None = None,
    policy: SecretPolicy | None = None,
    show_strength_indicator: bool = False,
    auto_submit: bool = True,
    shuffle_on_open: bool = True,
    shuffle_after_each_character: bool = False,
    show_shuffle_button: bool = True,
    show_clear_button: bool = True,
    mask_character: str = "•",
    submit_label: str = "OK",
    cancel_label: str = "Cancel",
) -> None:
    ...
```

Validation:

1. `secret_length` must be greater than zero.
2. `mask_character` must be non-empty.
3. `palettes`, if provided, must contain at least one palette with at least one character key.
4. If `palettes` is omitted, create default palettes from the active locale plus common numbers, punctuation, and symbol alternatives.
5. `policy`, if provided, must be valid for `secret_length`; for example, a minimum length greater than `secret_length` is invalid while fixed-length entry is used.
6. If `shuffle_after_each_character` is true, the active palette layout must reshuffle after each character press without losing the already-entered secret.
7. Physical character keys must not be accepted for secret entry.

Expected public behavior:

```python
self.dismiss(PinResult(...))
```

on successful entry.

```python
self.dismiss(None)
```

on cancel.

Do not call parent application callbacks manually. Use Textual's `push_screen(..., callback)` and `dismiss(...)` mechanism.

---

### 2. `PinResult`

File:

```text
src/terpinkb/result.py
```

Implement a small class that avoids exposing the PIN or secret as a normal string.

Suggested API:

```python
class PinResult:
    def __init__(self, value: bytearray) -> None:
        ...

    def consume(self) -> bytes:
        """
        Return an immutable bytes copy of the secret.

        The caller should verify it immediately and then drop references.
        This method does not destroy the internal bytearray automatically
        because callers may need controlled lifecycle behavior.
        """

    def destroy(self) -> None:
        """
        Overwrite the internal bytearray in place.
        After destroy(), consume() must raise RuntimeError.
        """

    @property
    def destroyed(self) -> bool:
        ...
```

Rules:

1. Do not expose `__str__` returning the PIN or secret.
2. Do not expose `repr` containing the PIN or secret.
3. `repr(result)` must show only metadata, such as length and destroyed state.
4. `consume()` returns `bytes`, not `str`.
5. `destroy()` must overwrite the internal `bytearray` with zeroes.
6. Calling `consume()` after `destroy()` must raise `RuntimeError`.

Example:

```python
result = PinResult(bytearray(b"123456"))
secret = result.consume()
result.destroy()
```

Security note: Python cannot guarantee complete memory secrecy. The goal is only to reduce accidental long-lived string copies.

---

### 3. `SecretPolicy`

File:

```text
src/terpinkb/policy.py
```

Implement optional policy metadata for embedding applications that want to guide or enforce length and character-class requirements.

```python
@dataclass(frozen=True)
class SecretPolicy:
    min_length: int = 0
    require_lowercase: bool = False
    require_uppercase: bool = False
    require_digit: bool = False
    require_punctuation: bool = False
    require_symbol: bool = False
```

Rules:

1. Do not enable composition requirements by default.
2. Do not claim that composition rules make a PIN or secret secure.
3. Prefer length and application-specific policy over generic "must include uppercase, punctuation, and number" rules.
4. Track policy satisfaction using metadata collected at character-entry time, such as length and palette/key category. Do not store the entered secret as `str` to evaluate policy.
5. If a policy is configured, OK and auto-submit must submit only when both `secret_length` and policy requirements are satisfied.
6. If `show_strength_indicator=True`, display only a coarse advisory label or meter such as `Too short`, `Weak`, `Fair`, or `Meets policy`. Never display entered characters or detailed guesses that could leak useful information.
7. The strength indicator must be framed as guidance, not a cryptographic guarantee. For short fixed PINs, a strength indicator is often less useful than clear length and retry/lockout policy.
8. Do not add a large password-strength dependency for version 0.1.

---

### 4. `KeypadLayout`, `KeypadPalette`, and `KeypadKey`

File:

```text
src/terpinkb/keypad.py
```

Implement layout logic independent from Textual rendering so it can be unit tested.

```python
@dataclass(frozen=True)
class KeypadKey:
    label: str
    value: str | None
    role: str


@dataclass(frozen=True)
class KeypadPalette:
    name: str
    label: str
    keys: tuple[KeypadKey, ...]
    shifted_keys: tuple[KeypadKey, ...] = ()
```

Roles:

```text
character
shift
caps
palette
backspace
clear
shuffle
submit
cancel
spacer
```

Implement:

```python
class KeypadLayout:
    @classmethod
    def default(
        cls,
        *,
        locale_name: str | None = None,
        rng: random.Random | None = None,
    ) -> "KeypadLayout":
        ...

    @classmethod
    def from_palettes(
        cls,
        palettes: tuple[KeypadPalette, ...],
        *,
        rng: random.Random | None = None,
    ) -> "KeypadLayout":
        ...

    @property
    def palettes(self) -> tuple[KeypadPalette, ...]:
        ...

    def keys(
        self,
        palette: str = "letters",
        *,
        shifted: bool = False,
        caps: bool = False,
    ) -> tuple[KeypadKey, ...]:
        ...

    def rows(
        self,
        palette: str = "letters",
        *,
        shifted: bool = False,
        caps: bool = False,
        width: int = 10,
    ) -> tuple[tuple[KeypadKey, ...], ...]:
        ...
```

Rules:

1. Use `secrets.SystemRandom()` by default for shuffling.
2. Allow injecting a deterministic `random.Random` in tests.
3. The default layout must provide separate palettes for letters, numbers, punctuation, and alternative symbols.
4. Use the active locale as a best-effort source for the letters palette. At minimum, the fallback locale-independent layout must include ASCII `a-z`, shifted `A-Z`, digits `0-9`, and common ASCII punctuation and symbols.
5. Shift must select `shifted_keys` for the active palette when present. For the letters palette, Shift must produce capitalization. For the number and punctuation palettes, Shift should expose the usual shifted alternatives where they are known.
6. Caps Lock must persist capitalization for letter keys without affecting number and punctuation palettes.
7. Palette switching must not clear or mutate the entered secret.
8. The visible order of character keys in the active palette must be randomized.
9. Control keys such as Shift, Caps, palette switchers, Backspace, Clear, Shuffle, Submit, and Cancel should keep stable positions where practical so the keyboard remains usable.
10. De-duplicate repeated characters within each palette while preserving the first occurrence before shuffling.
11. Unit tests must verify that deterministic RNG produces stable layouts.
12. Unit tests must verify that default layouts contain expected fallback letters, digits, punctuation, shifted letters, and symbol alternatives.

---

### 5. Optional Internal Messages

File:

```text
src/terpinkb/messages.py
```

Prefer native Textual messages where possible, especially `Button.Pressed`.

Only add custom messages if they simplify clean separation between a lower-level widget and the modal.

Potential messages:

```python
class CharacterPressed(Message):
    ...
```

However, do not over-engineer this. A single modal class handling `Button.Pressed` is acceptable for the first version.

---

## UI Layout Requirements

The modal should have this conceptual layout. The exact character placement is randomized per palette, but modifier and palette controls should remain predictable:

```text
╭────────────────────────────────────────╮
│ Enter Secret                           │
│                                        │
│          •  •  •  _  _  _             │
│                                        │
│   w    j    a    f    r    k    l     │
│   s    z    q    h    e    y    u     │
│   ⇧    p    d    x    c    v    ⌫     │
│   123  @#+  Caps Space OK   Cancel     │
│                                        │
│ Clear           Shuffle                │
╰────────────────────────────────────────╯
```

The exact visual appearance may differ, but the modal must be compact, centered, and usable on small terminals.

Minimum target size:

```text
80x24
```

It should degrade reasonably on smaller terminals.

---

## Textual Idioms to Use

Use these Textual mechanisms:

1. `ModalScreen[PinResult | None]`
2. `compose() -> ComposeResult`
3. `Button`
4. `Static` or `Label` for masked display
5. `Grid`, `Horizontal`, `Vertical`, or `Container` for layout
6. TCSS/CSS via either `CSS_PATH` or class-level `CSS`
7. `BINDINGS`
8. `action_*` methods
9. `on_button_pressed`
10. `AUTO_FOCUS`
11. `self.dismiss(...)`
12. `self.query_one(...)` or stored widget references where appropriate
13. Textual test pilot for tests

Avoid:

1. Raw terminal reads.
2. `curses`.
3. Manually emitting ANSI mouse-tracking escape sequences.
4. Private Textual internals.
5. Background threads.
6. Async complexity unless Textual requires it.
7. Normal `Input` widgets for the secret.
8. Physical character-key bindings.

---

## Focus and Navigation Behavior

Mouse behavior:

1. Clicking a character button appends that character.
2. Clicking Backspace removes the last character.
3. Clicking Clear clears the current entry.
4. Clicking Shuffle reshuffles visible character positions.
5. Clicking Shift toggles a one-shot shifted view of the active palette.
6. Clicking Caps toggles persistent capitalization for letter palettes.
7. Clicking a palette button switches to that palette without changing the entered secret.
8. Clicking OK submits only if enough characters are entered.
9. Clicking Cancel dismisses with `None`.

Keyboard behavior:

1. Tab moves focus forward.
2. Shift-Tab moves focus backward.
3. Arrow keys should move focus spatially where practical.
4. Enter activates the focused button.
5. Space activates the focused button if Textual already supports that for focused buttons.
6. Escape cancels.
7. Backspace removes the last entered character.
8. Delete may clear the full entry if implemented.
9. Physical character keys must not enter secret characters.

Important: keyboard navigation is allowed because it does not reveal the secret value. Keyboard character entry is disabled because it reintroduces the keylogger channel.

Shift behavior:

1. Pressing the on-screen Shift key affects the next character key and then returns to the unshifted palette unless Caps is active.
2. Pressing on-screen Caps keeps letter palettes capitalized until Caps is turned off.
3. Shift and Caps must not reveal entered secret characters.
4. Shift, Caps, and palette switching must use on-screen buttons and non-secret keyboard navigation only; do not bind physical Shift plus character combinations to secret entry.

---

## Secret Entry State

Internally maintain entered characters as UTF-8 bytes in:

```python
bytearray
```

Do not maintain them as:

```python
str
list[str]
```

If supporting multi-byte UTF-8 characters, maintain only byte-count metadata needed for deletion, such as `list[int]` of encoded character lengths. Do not store entered secret characters as Python strings.

Acceptable internal storage:

```python
self._secret = bytearray()
```

Appending a character:

```python
self._secret.extend(character.encode("utf-8"))
```

Backspace:

```python
if self._character_byte_lengths:
    byte_count = self._character_byte_lengths.pop()
    for _ in range(byte_count):
        self._secret[-1] = 0
        del self._secret[-1]
```

Clear:

```python
for i in range(len(self._secret)):
    self._secret[i] = 0
self._secret.clear()
self._character_byte_lengths.clear()
```

Submit:

```python
result = PinResult(bytearray(self._secret))
self._wipe_secret()
self.dismiss(result)
```

Cancel:

```python
self._wipe_secret()
self.dismiss(None)
```

---

## Masked Display

The masked display must show progress but not the PIN or secret.

For `secret_length=6`, after three characters:

```text
• • • _ _ _
```

Requirements:

1. Never render actual secret characters.
2. Do not include the PIN or secret in logs.
3. Do not include the PIN or secret in notifications.
4. Do not include the PIN or secret in exception messages.
5. Do not include the PIN or secret in `repr`.
6. Do not expose a debug mode that prints the PIN or secret.

---

## Strength and Policy UI

A strength indicator can be worthwhile for general mixed-character secrets, but it should be optional and modest. It is less useful for short fixed-length PIN workflows, HSM PINs with device-enforced retry limits, or applications where the secret format is dictated by an external system.

Requirements:

1. Default behavior should not enforce punctuation, capitalization, or mixed-character composition rules.
2. Embedding applications may configure `SecretPolicy` when they need specific length or character-class requirements.
3. If policy requirements are shown, present them as a compact checklist or status line, never as text that includes the secret.
4. If a strength indicator is shown, base it on length and category metadata only.
5. The strength indicator must not log, print, expose, or retain the entered secret.
6. The UI must make incomplete policy state clear without trapping the user; Cancel and Escape must still work.
7. The Readme must explain that strength meters and composition rules are usability guidance, not a substitute for server-side or device-side policy, rate limits, retry counters, and lockouts.

---

## Randomization

Use:

```python
secrets.SystemRandom()
```

by default.

Do not use:

```python
random.shuffle(...)
```

with the global default PRNG for production behavior.

Support deterministic RNG injection for tests only.

Randomization modes:

1. `shuffle_on_open=True`: layout randomized when modal opens.
2. `shuffle_after_each_character=False`: default stable layout after opening.
3. `shuffle_after_each_character=True`: reshuffle after each character press.

Default:

```python
shuffle_on_open=True
shuffle_after_each_character=False
```

Rationale:

1. Randomized per open prevents users from relying on fixed character positions.
2. Not reshuffling after each character is less hostile to users.
3. Reshuffling after every character can be offered for higher shoulder-surfing resistance but is slower and more error-prone.

---

## Accessibility and Usability

The widget must remain usable without a mouse.

Required:

1. Focusable buttons.
2. Clear title.
3. Clear masked progress indicator.
4. Clear cancel path.
5. Clear backspace path.
6. Optional instructions line, such as:

```text
Use mouse or Tab/arrow keys. Number keys are disabled.
```

Do not make mouse mandatory.

Do not trap the user without Escape or Cancel.

---

## Styling

Prefer a separate TCSS file:

```text
src/terpinkb/css/randomized_pin_modal.tcss
```

Example style target:

```css
RandomizedPinModal {
    align: center middle;
}

#pin-dialog {
    width: 72;
    height: auto;
    border: round $accent;
    background: $surface;
    padding: 1 2;
}

#pin-title {
    text-style: bold;
    content-align: center middle;
    margin-bottom: 1;
}

#pin-display {
    height: 3;
    content-align: center middle;
    border: round $primary;
    margin-bottom: 1;
    text-style: bold;
}

#pin-keypad {
    grid-size: 10;
    grid-gutter: 1 1;
    height: auto;
}

#pin-controls {
    grid-size: 3;
    grid-gutter: 1 1;
    margin-top: 1;
}

.pin-key {
    width: 5;
}
```

If `CSS_PATH` is inconvenient for packaging, inline `CSS` on the modal is acceptable. Prefer package data if using a separate TCSS file.

---

## Packaging

Use `pyproject.toml`.

Suggested metadata:

```toml
[project]
name = "terpinkb"
version = "0.1.0"
description = "A randomized on-screen secret keyboard modal for Textual applications"
readme = "Readme.md"
requires-python = ">=3.11"
dependencies = [
  "textual>=0.86",
]

[project.optional-dependencies]
dev = [
  "pytest",
  "pytest-asyncio",
  "ruff",
  "mypy",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
```

Include package data if using TCSS:

```toml
[tool.setuptools.package-data]
"terpinkb" = ["css/*.tcss"]
```

---

## Readme Requirements

Create a `Readme.md` with:

1. Project summary.
2. Threat model.
3. Non-goals.
4. Installation.
5. Minimal usage example.
6. Demo instructions.
7. Testing instructions.
8. Security caveats.

The Readme must be explicit that this component avoids keyboard-channel secret entry but does not make secret entry safe on a compromised host or compromised terminal.

---

## Demo App

File:

```text
examples/demo.py
```

The demo app must:

1. Display a simple Textual application.
2. Have a button to open the modal.
3. Use `push_screen(RandomizedPinModal(...), callback)`.
4. Show a notification on cancel.
5. Show only masked output on success.
6. Immediately call `destroy()` on the result after demonstrating receipt.
7. Never print the actual PIN or secret.

Example behavior:

```text
Secret received: ••••••
```

Never:

```text
Secret received: aB3!x$
```

---

## Tests

Use `pytest`.

### `test_result.py`

Test:

1. `PinResult.consume()` returns bytes.
2. `PinResult.destroy()` wipes and marks destroyed.
3. `consume()` after destroy raises `RuntimeError`.
4. `repr(result)` does not contain the PIN or secret.
5. `str(result)` does not contain the PIN or secret.

### `test_keypad_layout.py`

Test:

1. Default layout contains locale-derived letters where available, ASCII fallback letters, digits, punctuation, shifted letters, and symbol alternatives.
2. Deterministic RNG produces deterministic order.
3. Layout rows are correct width.
4. Roles are valid.
5. No duplicate character keys.
6. Caller-provided repeated characters within a palette are de-duplicated before shuffling.
7. Shifted keys are exposed only when Shift or Caps rules require them.
8. Palette switching changes visible keys without mutating entered state.

### `test_policy.py`

Test:

1. Default `SecretPolicy` imposes no composition requirements.
2. Invalid policy values raise `ValueError`.
3. Policy satisfaction can be computed from length and character category metadata.
4. Policy checks do not require storing or exposing the entered secret as `str`.
5. Strength labels are coarse and do not include the secret.

### `test_modal.py`

Use Textual's testing tools.

Test:

1. Modal can be pushed.
2. Clicking character buttons updates masked display.
3. Actual secret characters are never displayed.
4. Backspace decreases masked count.
5. Clear removes masked count.
6. Cancel dismisses with `None`.
7. Entering `secret_length` characters auto-submits when `auto_submit=True`.
8. OK submits when `auto_submit=False` and enough characters are present.
9. OK does not submit early.
10. OK and auto-submit do not submit when configured policy requirements are incomplete.
11. Physical character keys do not enter secret characters.
12. Shift capitalizes the next letter and then resets when Caps is off.
13. Caps persists capitalization until toggled off.
14. Palette switching exposes numbers, punctuation, and alternative symbols.
15. Escape cancels.
16. Shuffle preserves entered secret length if reshuffling after partial entry.
17. `PinResult` is returned on success, not a string.

Do not assert exact visual snapshots unless snapshot testing is added deliberately.

---

## Security Requirements

The implementation must include a `SECURITY.md` or Readme section explaining:

### Protects Against

1. Simple physical keyboard event logging.
2. Accidental capture of secret-value keystrokes.
3. Workflows where keyboard input is considered untrusted but terminal mouse events are acceptable.

### Does Not Protect Against

1. Compromised application process.
2. Compromised Python runtime.
3. Compromised terminal emulator.
4. Compromised host OS.
5. Compromised guest OS if running inside the guest.
6. Screen capture.
7. Mouse event capture.
8. Memory scraping.
9. Terminal escape injection.
10. Shoulder surfing.
11. Malicious Textual dependencies.
12. Debug logs that the embedding app creates outside this component.

### Important Design Rule

This project must not claim to provide full secure PIN or secret entry. It provides keyboard-channel avoidance.

### HSM PIN Entry

This component may be used by an embedding application to collect an HSM, smart-card, token, or PKCS#11 PIN only when the embedding application can pass the returned `bytes` directly to the relevant HSM library or middleware without re-entering the secret through the physical keyboard path.

HSM usage requirements:

1. Do not shell out with the PIN in command-line arguments, such as `--pin ...`.
2. Do not put the PIN in environment variables, config files, logs, notifications, or exception messages.
3. Prefer direct library bindings that accept an in-memory PIN value.
4. Destroy `PinResult` immediately after the HSM login or verification attempt.
5. Respect device retry counters and lockout behavior; this component must not retry automatically.
6. Let the embedding application handle device-specific PIN formats. For example, some PKCS#11 modules require prefixes, key IDs, or other token-specific login material in addition to the user-entered secret.
7. Document that HSM middleware, drivers, agents, or vendor tools may still prompt for PINs through their own UI or terminal paths; this component cannot protect those external prompts.
8. Be explicit about encoding. `PinResult.consume()` returns bytes, and the embedding application is responsible for passing those bytes in the form expected by its HSM API.

---

## Implementation Notes

### Button IDs

Use structured IDs for character buttons based on their randomized index, not their value. Do not put the secret character itself in the widget ID, because punctuation may not be ID-safe and IDs may appear in debug output.

```text
char-0
char-1
...
char-N
```

Control IDs:

```text
pin-shift
pin-caps
pin-palette-letters
pin-palette-numbers
pin-palette-punctuation
pin-palette-symbols
pin-backspace
pin-clear
pin-shuffle
pin-submit
pin-cancel
```

### Handling Button Presses

Use `on_button_pressed`.

Pseudo-code:

```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    button_id = event.button.id

    if button_id and button_id.startswith("char-"):
        self._append_character_by_button_id(button_id)
    elif button_id == "pin-shift":
        self.action_shift()
    elif button_id == "pin-caps":
        self.action_caps()
    elif button_id and button_id.startswith("pin-palette-"):
        self.action_switch_palette(button_id.removeprefix("pin-palette-"))
    elif button_id == "pin-backspace":
        self.action_backspace()
    elif button_id == "pin-clear":
        self.action_clear()
    elif button_id == "pin-shuffle":
        self.action_shuffle()
    elif button_id == "pin-submit":
        self.action_submit()
    elif button_id == "pin-cancel":
        self.action_cancel()
```

### Bindings

Suggested bindings:

```python
BINDINGS = [
    Binding("escape", "cancel", "Cancel", show=True),
    Binding("backspace", "backspace", "Backspace", show=False),
    Binding("delete", "clear", "Clear", show=False),
    Binding("left", "focus_left", "Left", show=False),
    Binding("right", "focus_right", "Right", show=False),
    Binding("up", "focus_up", "Up", show=False),
    Binding("down", "focus_down", "Down", show=False),
]
```

Implement spatial focus movement cleanly. If Textual already provides acceptable focus traversal for Tab and Shift-Tab, do not reimplement those.

For arrow keys, maintain a list of focusable button IDs in row-major order and move within a virtual grid.

### Keyboard Character Handling

Physical character keys must not append secret characters. It is acceptable to stop character key events to prevent parent handlers from seeing them while the modal is open.

```python
def on_key(self, event: events.Key) -> None:
    if event.character:
        event.stop()
```

---

## Error Handling

1. Invalid constructor arguments should raise `ValueError`.
2. Submitting too early should not raise; it should do nothing or visually indicate incomplete entry.
3. Cancel should always work.
4. Clear should be idempotent.
5. Backspace on an empty secret should be idempotent.
6. Destroying a `PinResult` multiple times should be safe.

---

## Type Checking

Use type hints throughout.

Avoid `Any` unless necessary for Textual callback types.

Pass `mypy` in strict mode if practical. If Textual typing causes friction, document any necessary mypy exclusions narrowly.

---

## Code Style

1. Clear, small methods.
2. No clever abstractions.
3. No premature plugin architecture.
4. No global mutable state.
5. No logging of secret data.
6. No print debugging.
7. Prefer explicit IDs and constants.
8. Prefer dataclasses for value objects.
9. Keep the modal implementation understandable.

---

## Version 0.1 Scope

Implement mixed-character secret entry.

In scope:

1. Randomized mixed-character on-screen keyboard.
2. Locale-aware default palettes with fallback letters, numbers, punctuation, and alternatives.
3. Textual modal.
4. Mouse support through native Textual buttons.
5. Keyboard navigation.
6. On-screen Shift, Caps, and palette switching.
7. Optional policy and coarse strength/status indicator.
8. Masked display.
9. Result object with wipe support.
10. Demo app.
11. Tests.
12. Readme.
13. Security notes.

Out of scope:

1. OS-level secure input.
2. Hardware-backed secure input.
3. Exact emulation of every host OS keyboard layout engine.
4. Anti-screen-capture protections.
5. Clipboard support.
6. Networked verification.
7. Direct HSM, smart-card, token, or PKCS#11 integration.
8. PAM integration.
9. LUKS integration.
10. Serial-console mouse escape conversion.
11. Host/guest mouse relay daemons.

---

## Future Extensions

Possible later additions:

1. TOTP-style challenge input.
2. Additional preset keyboard profiles.
3. Optional per-click reshuffle animation.
4. Larger touch-friendly layout.
5. Custom key labels.
6. Custom verification callback.
7. Theme variants.
8. Integration examples for HSM, smart-card, token, or PKCS#11 PIN workflows.
9. Integration examples for LUKS unlock frontends.
10. Integration examples for quarantined VM workflows.
11. Snapshot tests with `pytest-textual-snapshot`.

Do not implement these in version 0.1 unless explicitly requested.

---

## Acceptance Criteria

The project is complete when:

1. `pip install -e ".[dev]"` succeeds.
2. `python examples/demo.py` launches a Textual app.
3. The demo opens a modal randomized secret keyboard.
4. The keyboard's active character palette is randomized each time by default.
5. Mouse clicks enter characters.
6. Keyboard navigation works.
7. On-screen Shift, Caps, and palette switching work.
8. Optional policy checks can prevent early submit without exposing the secret.
9. Physical character keys do not enter secret characters.
10. The displayed PIN or secret is always masked.
11. The modal returns `PinResult`, not `str`.
12. Cancel returns `None`.
13. `PinResult.destroy()` wipes its internal bytearray.
14. Tests pass with `pytest`.
15. Ruff passes.
16. Readme clearly explains the threat model and limitations.
17. No code path logs, prints, or renders the real PIN or secret.

---

## Suggested First Implementation Order

1. Create package skeleton.
2. Implement `PinResult`.
3. Implement `SecretPolicy`.
4. Implement `KeypadLayout`.
5. Implement minimal `RandomizedPinModal`.
6. Add demo app.
7. Add tests for `PinResult`.
8. Add tests for `SecretPolicy`.
9. Add tests for `KeypadLayout`.
10. Add modal interaction tests.
11. Add Readme and security notes.
12. Run formatting, linting, type checking, and tests.

---

## Do Not Do

1. Do not use curses.
2. Do not manually enable terminal mouse tracking.
3. Do not implement raw terminal escape parsing.
4. Do not use `Input` for the secret.
5. Do not return the PIN or secret as `str`.
6. Do not print the PIN or secret in the demo.
7. Do not log the PIN or secret.
8. Do not advertise this as complete secure input.
9. Do not make mouse the only usable path.
10. Do not make physical character keys active for secret entry.

```

::contentReference[oaicite:1]{index=1}
```

[1]: https://textual.textualize.io/guide/screens/?utm_source=chatgpt.com "Screens - Textual"
