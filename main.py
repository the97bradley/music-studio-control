import os
import time

from apply_logic import process_knob_event
from config import StartupError, startup
from display import (
    display_self_test,
    get_display_health,
    percent_from_value,
    set_screen_display,
    set_screen_text,
)
from error_handler import report_error
from faders import add_group
from knobs import poll_knobs
from sync import sync_faders

SYNC_EVERY_S = float(os.environ.get("SYNC_EVERY_S", "1.0"))
LOOP_SLEEP_S = 0.01
DEADMAN_TIMEOUT_S = float(os.environ.get("DEADMAN_TIMEOUT_S", "3.0"))


def _render_startup(st):
    for knob_id, group_name in st.knob_to_group.items():
        set_screen_text(knob_id, "BOOT", group_name.upper())


def _render_error(st, text: str):
    for knob_id in st.knob_to_group.keys():
        set_screen_text(knob_id, "ERROR", text[:10])


def _render_levels(st):
    for knob_id, group_name in st.knob_to_group.items():
        chans = st.groups.get(group_name)
        if not chans:
            set_screen_text(knob_id, "CONFIG", "NO GROUP")
            continue
        rep_ch = chans[0]
        pct = percent_from_value(st.ch_level[rep_ch])
        set_screen_display(knob_id, group_name.upper(), pct)


def main():
    try:
        osc, st = startup()
    except StartupError as exc:
        report_error(exc.where, exc.cause)
        raise
    except Exception as exc:
        report_error("startup", exc)
        raise

    print("[startup] XR18 connected; entering control loop")
    print(f"[startup] bus={st.bus} knobs={len(st.knob_to_group)} sync={SYNC_EVERY_S}s deadman={DEADMAN_TIMEOUT_S}s")

    try:
        _render_startup(st)
        failed = display_self_test(st.knob_to_group.keys())
        if failed:
            report_error("display.selftest", RuntimeError(",".join(failed)), st)
        _render_levels(st)
    except Exception as exc:
        report_error("display.init", exc, st)

    last_sync = 0.0
    deadman_active = False
    display_degraded_announced = False

    while True:
        now = time.time()

        if now - last_sync >= SYNC_EVERY_S:
            try:
                ok = sync_faders(osc, st, 18)
                last_sync = now
                if ok:
                    if deadman_active:
                        print("[sync] recovered from stale state")
                    deadman_active = False
                    try:
                        _render_levels(st)
                    except Exception as exc:
                        report_error("loop.render", exc, st)
                else:
                    age = now - st.last_ok_sync_ts
                    if age >= DEADMAN_TIMEOUT_S and not deadman_active:
                        deadman_active = True
                        print(f"[deadman] mixer sync stale for {age:.1f}s")
                        _render_error(st, "XR18 LINK")
            except Exception as exc:
                report_error("loop.sync", exc, st)

        try:
            events = poll_knobs()
        except Exception as exc:
            report_error("loop.poll", exc, st)
            events = []

        if deadman_active and events:
            time.sleep(LOOP_SLEEP_S)
            continue

        for knob_id, direction in events:
            process_knob_event(
                osc,
                st,
                knob_id,
                direction,
                add_group_fn=add_group,
                set_screen_display_fn=set_screen_display,
                report_error_fn=report_error,
            )

        health = get_display_health()
        if any(health["unhealthy"].values()):
            if not display_degraded_announced:
                bad = [k for k, v in health["unhealthy"].items() if v]
                report_error("loop.display_health", RuntimeError(",".join(bad)), st)
                display_degraded_announced = True
        else:
            display_degraded_announced = False

        time.sleep(LOOP_SLEEP_S)


if __name__ == "__main__":
    main()
