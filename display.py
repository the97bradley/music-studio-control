import os
import time
from dataclasses import dataclass, field
from typing import Dict

from hardware import create_alert_backend, create_display_backend

_display = create_display_backend()
_alert = create_alert_backend()

DISPLAY_MAX_RETRIES = int(os.environ.get("DISPLAY_MAX_RETRIES", "3"))
DISPLAY_BACKOFF_MS = int(os.environ.get("DISPLAY_BACKOFF_MS", "40"))
DISPLAY_FAIL_THRESHOLD = int(os.environ.get("DISPLAY_FAIL_THRESHOLD", "3"))


@dataclass
class DisplayHealth:
    fail_count: Dict[str, int] = field(default_factory=dict)
    unhealthy: Dict[str, bool] = field(default_factory=dict)

    def mark_ok(self, knob_id: str):
        self.fail_count[knob_id] = 0
        self.unhealthy[knob_id] = False

    def mark_fail(self, knob_id: str):
        n = self.fail_count.get(knob_id, 0) + 1
        self.fail_count[knob_id] = n
        if n >= DISPLAY_FAIL_THRESHOLD:
            self.unhealthy[knob_id] = True


_health = DisplayHealth()


def _safe_write(knob_id: str, fn):
    for attempt in range(DISPLAY_MAX_RETRIES):
        try:
            fn()
            _health.mark_ok(knob_id)
            return True
        except Exception as exc:
            _health.mark_fail(knob_id)
            if attempt < DISPLAY_MAX_RETRIES - 1:
                time.sleep((DISPLAY_BACKOFF_MS / 1000.0) * (attempt + 1))
            else:
                _alert.signal("E31", f"{knob_id}:{type(exc).__name__}")
    return False


def set_screen_display(knob_name: str, label: str, percent: int):
    return _safe_write(knob_name, lambda: _display.render(knob_name, label, percent))


def set_screen_text(knob_name: str, line1: str, line2: str):
    return _safe_write(knob_name, lambda: _display.render_text(knob_name, line1, line2))


def display_self_test(knob_ids):
    failed = []
    for knob_id in knob_ids:
        ok = set_screen_text(knob_id, "SELFTEST", "OK")
        if not ok:
            failed.append(knob_id)
    return failed


def get_display_health():
    return {
        "fail_count": dict(_health.fail_count),
        "unhealthy": dict(_health.unhealthy),
    }


def fallback_alert(code: str, detail: str = ""):
    _alert.signal(code, detail)


def percent_from_value(v: float) -> int:
    return max(0, min(100, int(round(v * 100))))
