import time
from config import startup
from faders import add_group
from sync import sync_faders
from display import set_screen_display, percent_from_value
from knobs import poll_knobs

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

        events = poll_knobs()

        for (knob_id, direction) in events:
            group_name = st.knob_to_group.get(knob_id)
            if not group_name:
                continue

            add_group(osc, st, group_name, direction * DELTA_PER_TICK)

            # update display using representative channel of target group
            rep_ch = st.groups[group_name][0]
            pct = percent_from_value(st.ch_db[rep_ch])
            label = group_name.upper()
            set_screen_display(knob_id, label, pct)

        time.sleep(LOOP_SLEEP_S)

if __name__ == "__main__":
    main()
    