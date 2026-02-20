from hardware import create_display_backend

_display = create_display_backend()


def set_screen_display(knob_name: str, label: str, percent: int):
    _display.render(knob_name, label, percent)


def percent_from_value(v: float) -> int:
    # v is 0..1
    return max(0, min(100, int(round(v * 100))))
