import time

from app.core.apply_logic import process_knob_event
from app.config.startup import StartupError, startup
from app.config.controls import get_controls_value
from app.io.display import (
    display_self_test,
    get_display_health,
    percent_from_value,
    set_screen_display,
    set_screen_text,
)
from app.core.error_handler import report_error
from app.core.error_policy import get_policy, sleep_backoff
from app.core.faders import add_group
from app.io.knobs import poll_knobs
from app.core.logutil import setup_logging
from app.core.sync import sync_faders

SYNC_EVERY_S = float(get_controls_value("runtime.sync_every_s", 1.0))
LOOP_SLEEP_S = 0.01
DEADMAN_TIMEOUT_S = float(get_controls_value("runtime.deadman_timeout_s", 3.0))


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


def _run_with_policy(where: str, fn, st=None):
    policy = get_policy(where)
    last_exc = None
    for attempt in range(policy.max_retries + 1):
        try:
            return True, fn(), attempt, policy
        except Exception as exc:
            last_exc = exc
            if attempt < policy.max_retries:
                sleep_backoff(policy, attempt)
                continue
            report_error(where, exc, st, meta={"attempt": attempt + 1, "severity": policy.severity, "mode": policy.mode})
            if policy.mode == "fatal":
                raise
            return False, None, attempt, policy
    return False, None, 0, policy


def main():
    setup_logging()
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
            ok, sync_result, attempts, _ = _run_with_policy("loop.sync", lambda: sync_faders(osc, st, 18), st)
            last_sync = now
            if ok and sync_result:
                if deadman_active:
                    print(f"[recovery] loop.sync recovered after {attempts + 1} attempt(s)")
                deadman_active = False
                ok_render, _, _, _ = _run_with_policy("loop.render", lambda: _render_levels(st), st)
                if not ok_render:
                    pass
            else:
                age = now - st.last_ok_sync_ts
                if age >= DEADMAN_TIMEOUT_S and not deadman_active:
                    deadman_active = True
                    print(f"[deadman] mixer sync stale for {age:.1f}s")
                    _render_error(st, "XR18 LINK")

        ok_poll, events, _, _ = _run_with_policy("loop.poll", poll_knobs, st)
        if not ok_poll:
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
            if display_degraded_announced:
                print("[recovery] display health recovered")
            display_degraded_announced = False

        time.sleep(LOOP_SLEEP_S)


if __name__ == "__main__":
    main()
