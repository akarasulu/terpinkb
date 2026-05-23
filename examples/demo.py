from __future__ import annotations

from pathlib import Path
import sys

from textual.app import App, ComposeResult
from textual.containers import Center, Middle
from textual.widgets import Button, Static

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from terpinkb import RandomizedPinModal, SecretPolicy  # noqa: E402


class DemoApp(App[None]):
    CSS = """
    Screen {
        align: center middle;
    }

    #status {
        margin-top: 1;
        content-align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                yield Button("Enter Secret", id="enter-secret", variant="primary")
                yield Static("No secret received", id="status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "enter-secret":
            self.push_screen(
                RandomizedPinModal(
                    secret_length=6,
                    policy=SecretPolicy(min_length=6),
                    show_strength_indicator=True,
                ),
                self.handle_secret_result,
            )

    def handle_secret_result(self, result: object) -> None:
        status = self.query_one("#status", Static)
        if result is None:
            self.notify("Secret entry canceled")
            status.update("Canceled")
            return

        assert hasattr(result, "consume")
        assert hasattr(result, "destroy")
        try:
            secret_bytes = result.consume()
            status.update(f"Secret received: {'•' * len(secret_bytes)}")
            self.notify("Secret received")
        finally:
            result.destroy()


if __name__ == "__main__":
    DemoApp().run()
