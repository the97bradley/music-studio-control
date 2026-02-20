import os
from typing import Dict, List, Tuple


class EncoderBackend:
    """Interface for encoder hardware backends."""

    def read_events(self) -> List[Tuple[str, int]]:
        """
        Return list of (knob_id, direction) events.
        direction: +1 clockwise, -1 counter-clockwise.
        """
        return []


class NullEncoderBackend(EncoderBackend):
    """No-op backend used by default until hardware wiring is enabled."""

    pass


class DisplayBackend:
    """Interface for display hardware backends."""

    def render(self, knob_id: str, label: str, percent: int):
        pass

    def render_text(self, knob_id: str, line1: str, line2: str):
        pass


class NullDisplayBackend(DisplayBackend):
    """No-op backend used by default until OLED wiring is enabled."""

    pass


class ConsoleDisplayBackend(DisplayBackend):
    """Simple debug backend for bring-up/testing over SSH."""

    def __init__(self):
        self._last: Dict[str, Tuple[str, str]] = {}

    def render(self, knob_id: str, label: str, percent: int):
        self.render_text(knob_id, label, f"{percent}%")

    def render_text(self, knob_id: str, line1: str, line2: str):
        prev = self._last.get(knob_id)
        curr = (line1, line2)
        if prev != curr:
            self._last[knob_id] = curr
            print(f"[display] {knob_id}: {line1} | {line2}")


def create_encoder_backend() -> EncoderBackend:
    kind = os.environ.get("ENCODER_BACKEND", "null").lower().strip()

    # Placeholder for future hardware backends.
    if kind == "null":
        return NullEncoderBackend()

    # Unknown => fail safe to null.
    return NullEncoderBackend()


def create_display_backend() -> DisplayBackend:
    kind = os.environ.get("DISPLAY_BACKEND", "null").lower().strip()

    if kind == "console":
        return ConsoleDisplayBackend()
    if kind == "null":
        return NullDisplayBackend()

    # Unknown => fail safe to null.
    return NullDisplayBackend()
