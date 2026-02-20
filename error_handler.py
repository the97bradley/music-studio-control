import traceback
from datetime import datetime

from display import fallback_alert, set_screen_text

ERROR_CODES = {
    # startup path
    "startup.load_env": "E111",
    "startup.osc_client": "E112",
    "startup.controls": "E113",
    "startup.wait_xr18": "E114",
    "startup.initial_sync": "E115",
    "startup.channel_names": "E116",
    # display/bootstrap
    "display.init": "E121",
    "display.selftest": "E122",
    # runtime loop
    "loop.sync": "E211",
    "loop.render": "E212",
    "loop.poll": "E213",
    "loop.apply": "E214",
    "loop.apply.mapping": "E214A",
    "loop.apply.write": "E214B",
    "loop.apply.display": "E214C",
    "loop.display_health": "E215",
    # compatibility with earlier labels
    "startup": "E101",
    "display_init": "E102",
    "main_loop": "E201",
}


def _first_screen(st=None) -> str:
    if st is not None and getattr(st, "knob_to_group", None):
        try:
            return next(iter(st.knob_to_group.keys()))
        except Exception:
            pass
    return "knob1"


def _code_for(where: str) -> str:
    return ERROR_CODES.get(where, "E999")


def _second_screen(st=None) -> str:
    if st is not None and getattr(st, "knob_to_group", None):
        try:
            keys = list(st.knob_to_group.keys())
            if len(keys) >= 2:
                return keys[1]
            if len(keys) == 1:
                return keys[0]
        except Exception:
            pass
    return "knob2"


def report_error(where: str, exc: Exception, st=None):
    err_type = type(exc).__name__
    msg = str(exc).strip() or "no details"
    code = _code_for(where)

    print(f"[error] {code} {where}: {err_type}: {msg}")
    print(traceback.format_exc())

    screen1 = _first_screen(st)
    screen2 = _second_screen(st)
    ts = datetime.now().strftime("%H:%M:%S")

    try:
        ok1 = set_screen_text(screen1, code, "ERROR")
        ok2 = set_screen_text(screen2, "LOG TS", ts)
        if not (ok1 and ok2):
            fallback_alert("E311", f"{code}:{err_type}@{ts}")
    except Exception:
        fallback_alert("E311", f"{code}:{err_type}@{ts}")
