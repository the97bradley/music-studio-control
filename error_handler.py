import traceback

from display import set_screen_text

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
    # runtime loop
    "loop.sync": "E211",
    "loop.render": "E212",
    "loop.poll": "E213",
    "loop.apply": "E214",
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


def report_error(where: str, exc: Exception, st=None):
    err_type = type(exc).__name__
    msg = str(exc).strip() or "no details"
    code = _code_for(where)

    print(f"[error] {code} {where}: {err_type}: {msg}")
    print(traceback.format_exc())

    screen = _first_screen(st)
    line1 = code
    line2 = err_type[:10]
    try:
        set_screen_text(screen, line1, line2)
    except Exception:
        pass
