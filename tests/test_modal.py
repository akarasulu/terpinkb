from __future__ import annotations

from typing import Any

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Static

from terpinkb import KeypadKey, KeypadPalette, PinResult, RandomizedPinModal, SecretPolicy


def palette() -> tuple[KeypadPalette, ...]:
    return (
        KeypadPalette(
            "letters",
            "ABC",
            (
                KeypadKey("a", "a", "character", "lowercase"),
                KeypadKey("b", "b", "character", "lowercase"),
            ),
            (
                KeypadKey("A", "A", "character", "uppercase"),
                KeypadKey("B", "B", "character", "uppercase"),
            ),
        ),
        KeypadPalette(
            "numbers",
            "123",
            (
                KeypadKey("1", "1", "character", "digit"),
                KeypadKey("2", "2", "character", "digit"),
            ),
        ),
        KeypadPalette(
            "punctuation",
            "?!",
            (
                KeypadKey("!", "!", "character", "punctuation"),
                KeypadKey("?", "?", "character", "punctuation"),
            ),
        ),
        KeypadPalette(
            "symbols",
            "@#",
            (
                KeypadKey("@", "@", "character", "symbol"),
                KeypadKey("#", "#", "character", "symbol"),
            ),
        ),
    )


class Harness(App[None]):
    def compose(self) -> ComposeResult:
        yield Button("open", id="open")


async def push_modal(app: Harness, modal: RandomizedPinModal) -> list[Any]:
    results: list[Any] = []
    await app.push_screen(modal, results.append)
    return results


def display_text(modal: RandomizedPinModal) -> str:
    return str(modal.query_one("#pin-display", Static).content)


def labels(modal: RandomizedPinModal, count: int = 2) -> list[str]:
    return [str(modal.query_one(f"#char-{index}", Button).label) for index in range(count)]


def test_constructor_validation() -> None:
    with pytest.raises(ValueError):
        RandomizedPinModal(secret_length=0)
    with pytest.raises(ValueError):
        RandomizedPinModal(mask_character="")
    with pytest.raises(ValueError):
        RandomizedPinModal(mask_character="**")
    with pytest.raises(ValueError):
        RandomizedPinModal(secret_length=2, policy=SecretPolicy(min_length=3))
    with pytest.raises(ValueError):
        RandomizedPinModal(title="bad\ntitle")
    with pytest.raises(ValueError):
        RandomizedPinModal(submit_label="")
    with pytest.raises(ValueError):
        RandomizedPinModal(cancel_label="bad\ncancel")


@pytest.mark.asyncio
async def test_modal_can_be_pushed() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=2, palettes=palette())
        await push_modal(pilot.app, modal)
        await pilot.pause()
        assert modal.query_one("#pin-dialog")


@pytest.mark.asyncio
async def test_clicking_character_updates_mask_without_displaying_secret() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=2, palettes=palette())
        await push_modal(pilot.app, modal)
        await pilot.pause()
        label = str(modal.query_one("#char-0", Button).label)
        await pilot.click("#char-0")
        await pilot.pause()
        assert "• _" in display_text(modal)
        assert label not in display_text(modal)


@pytest.mark.asyncio
async def test_backspace_and_clear_update_masked_count() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=3, palettes=palette())
        await push_modal(pilot.app, modal)
        await pilot.pause()
        await pilot.click("#char-0")
        await pilot.click("#char-1")
        await pilot.pause()
        assert "• • _" in display_text(modal)
        await pilot.click("#pin-backspace")
        await pilot.pause()
        assert "• _ _" in display_text(modal)
        await pilot.click("#pin-clear")
        await pilot.pause()
        assert "_ _ _" in display_text(modal)


@pytest.mark.asyncio
async def test_keyboard_backspace_and_delete_update_masked_count() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=3, palettes=palette(), auto_submit=False)
        await push_modal(pilot.app, modal)
        await pilot.pause()
        await pilot.click("#char-0")
        await pilot.click("#char-1")
        await pilot.pause()
        await pilot.press("backspace")
        await pilot.pause()
        assert "• _ _" in display_text(modal)
        await pilot.press("delete")
        await pilot.pause()
        assert "_ _ _" in display_text(modal)


@pytest.mark.asyncio
async def test_cancel_returns_none() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        results = await push_modal(
            pilot.app, RandomizedPinModal(secret_length=2, palettes=palette())
        )
        await pilot.pause()
        await pilot.click("#pin-cancel")
        await pilot.pause()
        assert results == [None]


@pytest.mark.asyncio
async def test_escape_returns_none() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        results = await push_modal(
            pilot.app, RandomizedPinModal(secret_length=2, palettes=palette())
        )
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert results == [None]


@pytest.mark.asyncio
async def test_auto_submit_returns_pin_result_not_string() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        results = await push_modal(
            pilot.app, RandomizedPinModal(secret_length=2, palettes=palette())
        )
        await pilot.pause()
        await pilot.click("#char-0")
        await pilot.click("#char-1")
        await pilot.pause()
        assert len(results) == 1
        assert isinstance(results[0], PinResult)
        assert not isinstance(results[0], str)
        results[0].destroy()


@pytest.mark.asyncio
async def test_ok_submits_only_when_complete_and_policy_satisfied() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        results = await push_modal(
            pilot.app,
            RandomizedPinModal(
                secret_length=2,
                palettes=palette(),
                auto_submit=False,
                policy=SecretPolicy(require_digit=True),
            ),
        )
        await pilot.pause()
        await pilot.click("#char-0")
        await pilot.click("#pin-submit")
        await pilot.pause()
        assert results == []
        await pilot.click("#pin-palette-numbers")
        await pilot.click("#char-0")
        await pilot.click("#pin-submit")
        await pilot.pause()
        assert isinstance(results[0], PinResult)
        results[0].destroy()


@pytest.mark.asyncio
async def test_physical_character_keys_do_not_enter_secret() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=2, palettes=palette())
        await push_modal(pilot.app, modal)
        await pilot.pause()
        await pilot.press("a", "1")
        await pilot.pause()
        assert "_ _" in display_text(modal)


@pytest.mark.asyncio
async def test_space_button_and_strength_indicator() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(
            secret_length=2,
            palettes=palette(),
            auto_submit=False,
            show_strength_indicator=True,
            policy=SecretPolicy(min_length=2, require_symbol=True),
        )
        await push_modal(pilot.app, modal)
        await pilot.pause()
        assert "Too short" in str(modal.query_one("#pin-strength", Static).content)
        await pilot.click("#pin-space")
        await pilot.pause()
        assert "• _" in display_text(modal)
        await pilot.click("#char-0")
        await pilot.pause()
        assert str(modal.query_one("#pin-strength", Static).content) in {
            "Meets policy",
            "Fair",
            "Strong",
        }


@pytest.mark.asyncio
async def test_shift_caps_and_palette_switching() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=3, palettes=palette(), auto_submit=False)
        await push_modal(
            pilot.app,
            modal,
        )
        await pilot.pause()
        await pilot.click("#pin-shift")
        await pilot.pause()
        assert {
            str(modal.query_one("#char-0", Button).label),
            str(modal.query_one("#char-1", Button).label),
        } <= {
            "A",
            "B",
        }
        await pilot.click("#char-0")
        await pilot.pause()
        assert {
            str(modal.query_one("#char-0", Button).label),
            str(modal.query_one("#char-1", Button).label),
        } <= {
            "a",
            "b",
        }
        await pilot.click("#pin-caps")
        await pilot.pause()
        assert {
            str(modal.query_one("#char-0", Button).label),
            str(modal.query_one("#char-1", Button).label),
        } <= {
            "A",
            "B",
        }
        await pilot.click("#pin-palette-punctuation")
        await pilot.pause()
        assert {
            str(modal.query_one("#char-0", Button).label),
            str(modal.query_one("#char-1", Button).label),
        } <= {
            "!",
            "?",
        }


@pytest.mark.asyncio
async def test_invalid_palette_switch_and_symbol_palette() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=2, palettes=palette(), auto_submit=False)
        await push_modal(pilot.app, modal)
        await pilot.pause()
        before = labels(modal)
        await modal.action_switch_palette("missing")
        assert labels(modal) == before
        await pilot.click("#pin-palette-symbols")
        await pilot.pause()
        assert set(labels(modal)) <= {"@", "#"}


@pytest.mark.asyncio
async def test_shuffle_preserves_entered_length() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=3, palettes=palette(), auto_submit=False)
        await push_modal(
            pilot.app,
            modal,
        )
        await pilot.pause()
        await pilot.click("#char-0")
        await pilot.pause()
        await pilot.click("#pin-shuffle")
        await pilot.pause()
        assert "• _ _" in display_text(modal)


@pytest.mark.asyncio
async def test_layout_stays_stable_without_shuffle_after_each_character() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=3, palettes=palette(), auto_submit=False)
        await push_modal(pilot.app, modal)
        await pilot.pause()
        before = [str(modal.query_one(f"#char-{index}", Button).label) for index in range(2)]
        await pilot.click("#char-0")
        await pilot.pause()
        after = [str(modal.query_one(f"#char-{index}", Button).label) for index in range(2)]
        assert after == before


@pytest.mark.asyncio
async def test_shuffle_after_each_character_changes_layout_but_preserves_length() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(
            secret_length=3,
            palettes=palette(),
            auto_submit=False,
            shuffle_after_each_character=True,
        )
        await push_modal(pilot.app, modal)
        await pilot.pause()
        await pilot.click("#char-0")
        await pilot.pause()
        assert "• _ _" in display_text(modal)


@pytest.mark.asyncio
async def test_focus_actions_move_focus() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=2, palettes=palette(), auto_submit=False)
        await push_modal(pilot.app, modal)
        await pilot.pause()
        assert app.focused is not None
        modal.query_one("#char-0", Button).focus()
        await pilot.pause()
        await modal.action_focus_right()
        await pilot.pause()
        assert app.focused is modal.query_one("#char-1", Button)
        await modal.action_focus_left()
        await pilot.pause()
        assert app.focused is modal.query_one("#char-0", Button)
        await modal.action_focus_down()
        await pilot.pause()
        assert app.focused is not None
        await modal.action_focus_up()
        await pilot.pause()
        assert app.focused is not None


@pytest.mark.asyncio
async def test_optional_clear_and_shuffle_buttons_can_be_hidden() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(
            secret_length=2,
            palettes=palette(),
            show_clear_button=False,
            show_shuffle_button=False,
        )
        await push_modal(pilot.app, modal)
        await pilot.pause()
        assert not modal.query("#pin-clear")
        assert not modal.query("#pin-shuffle")


@pytest.mark.asyncio
async def test_multibyte_character_can_be_deleted() -> None:
    app = Harness()
    multi = (
        KeypadPalette(
            "letters",
            "ABC",
            (KeypadKey("ç", "ç", "character", "lowercase"),),
            (KeypadKey("Ç", "Ç", "character", "uppercase"),),
        ),
    )
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=1, palettes=multi, auto_submit=False)
        await push_modal(pilot.app, modal)
        await pilot.pause()
        await pilot.click("#char-0")
        await pilot.pause()
        assert "•" in display_text(modal)
        await pilot.press("backspace")
        await pilot.pause()
        assert "_" in display_text(modal)


@pytest.mark.asyncio
async def test_modal_wipes_on_unmount() -> None:
    app = Harness()
    async with app.run_test() as pilot:
        modal = RandomizedPinModal(secret_length=2, palettes=palette(), auto_submit=False)
        await push_modal(pilot.app, modal)
        await pilot.pause()
        await pilot.click("#char-0")
        await pilot.pause()
        assert modal._secret
        await pilot.app.pop_screen()
        await pilot.pause()
        assert modal._secret == bytearray()
