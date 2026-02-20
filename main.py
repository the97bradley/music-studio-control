import time
from config import startup
from faders import add_group, set_group
from sync import sync_faders
from display import set_screen_display, percent_from_value

SYNC_EVERY_S = 60
LOOP_SLEEP_S = 0.01

# “down 10” meaning (not fancy): float-space step
# Example: 0.05 ~= 5% per detent. Tune later.
DELTA_PER_TICK = 0.05

def main():
    osc, st = startup()
    last_sync = time.time()

    while True:
        now = time.time()

        # periodic sync (optional)
        if now - last_sync >= SYNC_EVERY_S:
            sync_faders(osc, st, 18)
            last_sync = now

        # knob polling (stub)
        # events = poll_knobs()
        events = []

        for (knob, direction) in events:
            add_group(osc, st, knob, direction * DELTA_PER_TICK)

            # update display (stub)
            # show group name + percent from representative channel
            rep_ch = st.groups[knob][0]
            pct = percent_from_value(st.ch_db[rep_ch])
            label = knob if knob != "drums" else "DRUMS"
            set_screen_display(knob, label, pct)

        time.sleep(LOOP_SLEEP_S)

if __name__ == "__main__":
    main()
    