# music-studio-control

A Raspberry Pi box for **personal monitor mixing** on a Behringer XR18.

Think of it like a DIY Hearback-style controller for recording sessions:
- 8 knobs
- 8 mini OLED screens
- one monitor bus per musician/station

---

## What this project does

This service runs on a Pi and talks to the XR18 over OSC.

It:
- reads knob movements,
- adjusts grouped channel levels,
- keeps local state in sync with the mixer,
- updates little screens so the user sees what changed.

It is built for **headless operation** (no keyboard/monitor attached), so error/status info is shown on-screen and printed to logs.

---

## Current status (important)

Core control logic is in place.

Hardware-specific drivers are still stubs right now:
- `ENCODER_BACKEND` defaults to `null`
- `DISPLAY_BACKEND` defaults to `null` (or `console` for SSH/debug)

So the architecture is ready, and now we can plug in real GPIO/I2C backends.

---

## File map (quick)

- `main.py` — main control loop
- `osc.py` — OSC transport + query + keepalive
- `state.py` — runtime state (`ch_level`, names, mappings, per-knob step)
- `controls.json` — editable mappings/sensitivity
- `controls.py` — loads/validates controls config
- `faders.py` — group-level mixer writes
- `sync.py` — periodic readback from mixer
- `knobs.py` — encoder backend adapter
- `display.py` — display backend adapter
- `error_handler.py` — centralized exception handling + on-screen error codes

---

## Configuration

### Required
- `XR18_IP` — mixer IP address

### Optional (with defaults)
- `XR18_BUS=2` — monitor bus (1..6)
- `LOCAL_PORT=9100` — local UDP port
- `CONTROLS_CONFIG=controls.json` — path to controls mapping file
- `ENCODER_BACKEND=null` — encoder backend selector
- `DISPLAY_BACKEND=null` — display backend selector (`console` is useful for testing)
- `SYNC_EVERY_S=1.0` — sync interval in seconds
- `DEADMAN_TIMEOUT_S=3.0` — stale-link timeout before lockout/error

---

## controls.json

This is where you customize behavior without editing Python.

You can define:
- `groups` (which channels each logical control affects)
- `knob_to_group` (which physical knob controls which group)
- `knob_step` (sensitivity per knob)

Example:

```json
{
  "groups": {
    "vocal": [1],
    "drums": [6, 7, 8, 9, 10, 11]
  },
  "knob_to_group": {
    "knob1": "vocal",
    "knob6": "drums"
  },
  "knob_step": {
    "knob1": 0.03,
    "knob6": 0.02
  }
}
```

---

## Runtime behavior

- Internal channel values are stored as **linear 0.0..1.0** in `State.ch_level`.
- XR18 dB reference constants are in `state.py` (`-90.0 .. +10.0`).
- On boot, screens show `BOOT`, then switch to live values.
- Sync runs every second by default, so external mixer/app changes appear on displays quickly.
- If mixer comms go stale past timeout, writes are blocked and screens show link error.

---

## Error handling (headless-friendly)

All major exceptions flow through a centralized handler and are routed to screen 1 (`knob1` by default).

### Granular error codes

**Startup**
- `E111` — `startup.load_env` (bad/missing env like `XR18_IP`, invalid bus)
- `E112` — `startup.osc_client` (socket create/bind failures)
- `E113` — `startup.controls` (invalid controls config)
- `E114` — `startup.wait_xr18` (mixer link probe/keepalive startup issues)
- `E115` — `startup.initial_sync` (initial fader sync failure)
- `E116` — `startup.channel_names` (channel name fetch failure)

**Display / init**
- `E121` — `display.init` (startup screen rendering failure)

**Runtime loop**
- `E211` — `loop.sync` (periodic mixer sync failure)
- `E212` — `loop.render` (display refresh failure)
- `E213` — `loop.poll` (encoder polling failure)
- `E214` — `loop.apply` (apply knob movement/write failure)

**Fallback**
- `E999` — unknown/unmapped context

This makes it possible to diagnose failures from the device itself without SSH.

For likely causes and quick fixes per code, see **`docs/errors.md`**.

---

## Next recommended steps

1. Implement real encoder backend (GPIO or I2C expander).
2. Implement real OLED backend (SSD1306/SH1106, whichever your screens are).
3. Add a tiny installer note for Pi OS + systemd environment file.
4. Add a simple hardware self-test mode (`--self-test`) for bench validation.
