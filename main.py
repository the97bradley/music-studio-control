import os
import time

from config import startup
from display import percent_from_value, set_screen_display, set_screen_text
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
    osc, st = startup()
    print("[startup] XR18 connected; entering control loop")
    print(f"[startup] bus={st.bus} knobs={len(st.knob_to_group)} sync={SYNC_EVERY_S}s deadman={DEADMAN_TIMEOUT_S}s")

    _render_startup(st)
    _render_levels(st)

    last_sync = 0.0
    deadman_active = False

    while True:
        now = time.time()

        if now - last_sync >= SYNC_EVERY_S:
            ok = sync_faders(osc, st, 18)
            last_sync = now
            if ok:
                if deadman_active:
                    print("[sync] recovered from stale state")
                deadman_active = False
                _render_levels(st)
            else:
                age = now - st.last_ok_sync_ts
                if age >= DEADMAN_TIMEOUT_S and not deadman_active:
                    deadman_active = True
                    print(f"[deadman] mixer sync stale for {age:.1f}s")
                    _render_error(st, "XR18 LINK")

        events = poll_knobs()
        if deadman_active and events:
            # fail-safe: ignore writes while stale link is active
            continue

        for knob_id, direction in events:
            group_name = st.knob_to_group.get(knob_id)
            if not group_name:
                continue

            step = st.knob_step.get(knob_id, 0.03)
            add_group(osc, st, group_name, direction * step)

            chans = st.groups[group_name]
            rep_ch = chans[0]
            pct = percent_from_value(st.ch_level[rep_ch])
            set_screen_display(knob_id, group_name.upper(), pct)

        time.sleep(LOOP_SLEEP_S)


if __name__ == "__main__":
    main()
