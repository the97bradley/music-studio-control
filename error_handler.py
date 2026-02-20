import traceback
from typing import Optional

from display import set_screen_text


def _first_screen(st=None) -> str:
    if st is not None and getattr(st, "knob_to_group", None):
        try:
            return next(iter(st.knob_to_group.keys()))
        except Exception:
            pass
    return "knob1"


def report_error(where: str, exc: Exception, st=None):
    err_type = type(exc).__name__
    msg = str(exc).strip() or "no details"
    print(f"[error] {where}: {err_type}: {msg}")
    print(traceback.format_exc())

    # Headless-first: route concise error to first screen.
    screen = _first_screen(st)
    code = where.upper()[:10]
    detail = f"{err_type}"[:10]
    try:
        set_screen_text(screen, code, detail)
    except Exception:
        # never let display failures crash error handling
        pass
