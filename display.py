from state import State

def set_screen_display(knob_name: str, label: str, percent: int):
    # stub until LCD wiring exists
    # later: write to I2C LCD (or OLED)
    pass

def percent_from_value(v: float) -> int:
    # v is 0..1
    return max(0, min(100, int(round(v * 100))))