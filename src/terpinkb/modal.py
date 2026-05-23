from __future__ import annotations

from dataclasses import dataclass

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from terpinkb.keypad import KeypadKey, KeypadLayout, KeypadPalette
from terpinkb.policy import SecretPolicy
from terpinkb.result import PinResult


@dataclass(frozen=True)
class _EnteredCategory:
    byte_length: int
    category: str


class RandomizedPinModal(ModalScreen[PinResult | None]):
    CSS_PATH = "css/randomized_pin_modal.tcss"
    AUTO_FOCUS = "#char-0"

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("backspace", "backspace", "Backspace", show=False),
        Binding("delete", "clear", "Clear", show=False),
        Binding("left", "focus_left", "Left", show=False),
        Binding("right", "focus_right", "Right", show=False),
        Binding("up", "focus_up", "Up", show=False),
        Binding("down", "focus_down", "Down", show=False),
    ]

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
        super().__init__()
        if secret_length <= 0:
            raise ValueError("secret_length must be greater than zero")
        if not mask_character:
            raise ValueError("mask_character must be non-empty")
        if len(mask_character) != 1:
            raise ValueError("mask_character must be exactly one character")
        if policy is not None and policy.min_length > secret_length:
            raise ValueError("policy min_length cannot exceed secret_length")
        if not title.isprintable():
            raise ValueError("title must be printable")
        if not submit_label or not submit_label.isprintable():
            raise ValueError("submit_label must be non-empty and printable")
        if not cancel_label or not cancel_label.isprintable():
            raise ValueError("cancel_label must be non-empty and printable")

        self.secret_length = secret_length
        self._modal_title = title
        self.policy = policy
        self.show_strength_indicator = show_strength_indicator
        self.auto_submit = auto_submit
        self.shuffle_after_each_character = shuffle_after_each_character
        self.show_shuffle_button = show_shuffle_button
        self.show_clear_button = show_clear_button
        self.mask_character = mask_character
        self.submit_label = submit_label
        self.cancel_label = cancel_label

        self._layout = (
            KeypadLayout.default()
            if palettes is None
            else KeypadLayout.from_palettes(palettes)
        )
        self._active_palette = self._layout.palettes[0].name
        self._shifted = False
        self._caps = False
        self._secret = bytearray()
        self._entered: list[_EnteredCategory] = []
        self._button_keys: dict[str, KeypadKey] = {}
        self._key_cache: dict[tuple[str, bool, bool], tuple[KeypadKey, ...]] = {}
        self._focus_ids: list[str] = []
        self._mounted = False
        self._shuffle_on_open = shuffle_on_open

    def compose(self) -> ComposeResult:
        with Container(id="pin-dialog"):
            with Vertical():
                yield Static(self._modal_title, id="pin-title")
                yield Static("", id="pin-display")
                if self.show_strength_indicator:
                    yield Static("", id="pin-strength")
                with Grid(id="pin-keypad"):
                    pass
                with Grid(id="pin-modifiers"):
                    yield Button("Shift", id="pin-shift", classes="pin-control")
                    yield Button("Caps", id="pin-caps", classes="pin-control")
                    yield Button("Space", id="pin-space", classes="pin-control")
                    for palette in self._layout.palettes:
                        yield Button(
                            palette.label,
                            id=f"pin-palette-{palette.name}",
                            classes="pin-control",
                        )
                with Grid(id="pin-actions"):
                    if self.show_clear_button:
                        yield Button("Clear", id="pin-clear", classes="pin-control")
                    if self.show_shuffle_button:
                        yield Button("Shuffle", id="pin-shuffle", classes="pin-control")
                    yield Button(self.submit_label, id="pin-submit", classes="pin-control")
                    yield Button(self.cancel_label, id="pin-cancel", classes="pin-control")

    async def on_mount(self) -> None:
        self._mounted = True
        await self._render_keypad(force_shuffle=self._shuffle_on_open)
        self._update_display()

    def on_unmount(self) -> None:
        self._wipe_secret()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id is None:
            return
        if button_id.startswith("char-"):
            await self._append_character_by_button_id(button_id)
        elif button_id == "pin-space":
            await self._append_character(" ", "symbol")
        elif button_id == "pin-shift":
            await self.action_shift()
        elif button_id == "pin-caps":
            await self.action_caps()
        elif button_id.startswith("pin-palette-"):
            await self.action_switch_palette(button_id.removeprefix("pin-palette-"))
        elif button_id == "pin-backspace":
            self.action_backspace()
        elif button_id == "pin-clear":
            self.action_clear()
        elif button_id == "pin-shuffle":
            await self.action_shuffle()
        elif button_id == "pin-submit":
            self.action_submit()
        elif button_id == "pin-cancel":
            self.action_cancel()
        event.stop()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.action_cancel()
            event.stop()
            return
        if event.key == "backspace":
            self.action_backspace()
            event.stop()
            return
        if event.key == "delete":
            self.action_clear()
            event.stop()
            return
        if event.character:
            event.stop()

    async def action_shift(self) -> None:
        self._shifted = not self._shifted
        await self._render_keypad()
        self._update_display()

    async def action_caps(self) -> None:
        self._caps = not self._caps
        await self._render_keypad()
        self._update_display()

    async def action_switch_palette(self, palette: str) -> None:
        if palette not in {item.name for item in self._layout.palettes}:
            return
        self._active_palette = palette
        self._shifted = False
        await self._render_keypad()
        self._update_display()

    def action_backspace(self) -> None:
        if self._entered:
            entered = self._entered.pop()
            for _ in range(entered.byte_length):
                self._secret[-1] = 0
                del self._secret[-1]
        self._update_display()

    def action_clear(self) -> None:
        self._wipe_secret()
        self._update_display()

    async def action_shuffle(self) -> None:
        await self._render_keypad(force_shuffle=True)

    def action_submit(self) -> None:
        if not self._can_submit():
            self._update_display()
            return
        result = PinResult(bytearray(self._secret))
        self._wipe_secret()
        self.dismiss(result)

    def action_cancel(self) -> None:
        self._wipe_secret()
        self.dismiss(None)

    async def action_focus_left(self) -> None:
        self._move_key_focus(-1, 0)

    async def action_focus_right(self) -> None:
        self._move_key_focus(1, 0)

    async def action_focus_up(self) -> None:
        self._move_key_focus(0, -1)

    async def action_focus_down(self) -> None:
        self._move_key_focus(0, 1)

    async def _append_character_by_button_id(self, button_id: str) -> None:
        key = self._button_keys.get(button_id)
        if key is None or key.value is None:
            return
        await self._append_character(key.value, key.category)

    async def _append_character(self, value: str, category: str) -> None:
        if len(value) != 1:
            return
        if len(self._entered) >= self.secret_length:
            return
        encoded = value.encode("utf-8")
        self._secret.extend(encoded)
        self._entered.append(_EnteredCategory(len(encoded), category))
        if self._shifted and not self._caps:
            self._shifted = False
            await self._render_keypad()
        self._update_display()
        if self.auto_submit and self._can_submit():
            self.action_submit()
        elif self.shuffle_after_each_character:
            await self._render_keypad(force_shuffle=True)

    def _can_submit(self) -> bool:
        if len(self._entered) != self.secret_length:
            return False
        if self.policy is None:
            return True
        return self.policy.satisfied_by(self._categories(), len(self._entered))

    def _categories(self) -> set[str]:
        return {entered.category for entered in self._entered if entered.category}

    def _update_display(self) -> None:
        if not self._mounted:
            return
        filled = [self.mask_character] * len(self._entered)
        empty = ["_"] * (self.secret_length - len(self._entered))
        self.query_one("#pin-display", Static).update(" ".join(filled + empty))
        if self.show_strength_indicator:
            self.query_one("#pin-strength", Static).update(self._strength_text())
        submit = self.query_one("#pin-submit", Button)
        submit.disabled = not self._can_submit()

    def _strength_text(self) -> str:
        if self.policy is None:
            if not self._entered:
                return "Too short"
            if len(self._entered) < self.secret_length:
                return "Weak"
            return "Meets policy"
        return self.policy.strength_label(self._categories(), len(self._entered))

    async def _render_keypad(self, *, force_shuffle: bool = False) -> None:
        if not self._mounted:
            return
        grid = self.query_one("#pin-keypad", Grid)
        await grid.remove_children()
        self._button_keys.clear()
        rows = self._rows_for_active_palette(force_shuffle=force_shuffle)
        buttons: list[Button] = []
        index = 0
        for row in rows:
            for key in row:
                button_id = f"char-{index}"
                self._button_keys[button_id] = key
                label = "Space" if key.value == " " else key.label
                buttons.append(Button(label, id=button_id, classes="pin-key"))
                index += 1
        buttons.append(Button("<-", id="pin-backspace", classes="pin-key"))
        await grid.mount(*buttons)
        self._refresh_focus_ids()

    def _rows_for_active_palette(self, *, force_shuffle: bool) -> tuple[tuple[KeypadKey, ...], ...]:
        cache_key = (self._active_palette, self._shifted, self._caps)
        if force_shuffle or cache_key not in self._key_cache:
            self._key_cache[cache_key] = self._active_keys(
                shuffled=force_shuffle or self._shuffle_on_open
            )
        keys = self._key_cache[cache_key]
        return tuple(tuple(keys[index : index + 10]) for index in range(0, len(keys), 10))

    def _active_keys(self, *, shuffled: bool) -> tuple[KeypadKey, ...]:
        if shuffled:
            return self._layout.keys(
                self._active_palette,
                shifted=self._shifted,
                caps=self._caps,
            )
        for palette in self._layout.palettes:
            if palette.name == self._active_palette:
                use_shifted = (self._shifted or self._caps) and bool(palette.shifted_keys)
                return palette.shifted_keys if use_shifted else palette.keys
        return ()

    def _refresh_focus_ids(self) -> None:
        self._focus_ids = [
            button.id
            for button in self.query(Button)
            if button.id is not None and not button.disabled
        ]

    def _move_key_focus(self, x_delta: int, y_delta: int) -> None:
        self._refresh_focus_ids()
        if not self._focus_ids:
            return
        focused = self.app.focused
        current_id = focused.id if focused is not None else None
        if current_id not in self._focus_ids:
            self.query_one(f"#{self._focus_ids[0]}", Button).focus()
            return
        current_index = self._focus_ids.index(current_id)
        width = 10
        if x_delta:
            next_index = (current_index + x_delta) % len(self._focus_ids)
        else:
            next_index = current_index + (y_delta * width)
            next_index %= len(self._focus_ids)
        self.query_one(f"#{self._focus_ids[next_index]}", Button).focus()

    def _wipe_secret(self) -> None:
        for index in range(len(self._secret)):
            self._secret[index] = 0
        self._secret.clear()
        self._entered.clear()
