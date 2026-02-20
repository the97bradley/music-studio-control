import os
from typing import Dict, List, Tuple


class EncoderBackend:
    def read_events(self) -> List[Tuple[str, int]]:
        return []


class NullEncoderBackend(EncoderBackend):
    pass


class DisplayBackend:
    def render(self, knob_id: str, label: str, percent: int):
        pass

    def render_text(self, knob_id: str, line1: str, line2: str):
        pass


class NullDisplayBackend(DisplayBackend):
    pass


class ConsoleDisplayBackend(DisplayBackend):
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


class AlertBackend:
    def signal(self, code: str, detail: str = ""):
        pass


class NullAlertBackend(AlertBackend):
    pass


class ConsoleAlertBackend(AlertBackend):
    def signal(self, code: str, detail: str = ""):
        extra = f" {detail}" if detail else ""
        print(f"[alert] {code}{extra} (fallback)")


def create_encoder_backend() -> EncoderBackend:
    kind = os.environ.get("ENCODER_BACKEND", "null").lower().strip()
    if kind == "null":
        return NullEncoderBackend()
    return NullEncoderBackend()


def create_display_backend() -> DisplayBackend:
    kind = os.environ.get("DISPLAY_BACKEND", "null").lower().strip()
    if kind == "console":
        return ConsoleDisplayBackend()
    if kind == "null":
        return NullDisplayBackend()
    return NullDisplayBackend()


def create_alert_backend() -> AlertBackend:
    kind = os.environ.get("ALERT_BACKEND", "console").lower().strip()
    if kind == "console":
        return ConsoleAlertBackend()
    return NullAlertBackend()
