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
- `ALERT_BACKEND=console` — fallback alert channel when display writes fail
- `DISPLAY_MAX_RETRIES=3` — per-write display retry count
- `DISPLAY_BACKOFF_MS=40` — retry backoff base in ms
- `DISPLAY_FAIL_THRESHOLD=3` — failures before a screen is marked unhealthy
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
- On boot, screens show `BOOT`, run a per-screen self-test, then switch to live values.
- Display writes are isolated per screen with retry + backoff; one bad screen should not break the full loop.
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
- `E122` — `display.selftest` (one or more screens failed startup self-test)

**Runtime loop**
- `E211` — `loop.sync` (periodic mixer sync failure)
- `E212` — `loop.render` (display refresh failure)
- `E213` — `loop.poll` (encoder polling failure)
- `E214` — `loop.apply` (legacy generic apply failure)
- `E214A` — `loop.apply.mapping` (unknown knob/group mapping)
- `E214B` — `loop.apply.write` (mixer write path failure)
- `E214C` — `loop.apply.display` (display update failed after apply)
- `E215` — `loop.display_health` (one or more screens marked unhealthy)

**Fallback channel**
- `E311` — display-error fallback alert path triggered

**Fallback**
- `E999` — unknown/unmapped context

This makes it possible to diagnose failures from the device itself without SSH.

For likely causes and quick fixes per code, see **`docs/errors.md`**.

---

## Unit tests

A lightweight unit test suite is included under `tests/`.

Run all tests:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Current test coverage includes:
- controls config loading/validation
- mixer sync behavior (success + partial failure)
- error-code mapping and fallback alert path
- granular apply-path error routing

### Live XR18 integration tests

There is also a live integration test runner with **one flag per test** (short + long forms).

Base args:
- `--xr18-ip <ip>` (required)
- `--local-port <port>` (optional)

Test selectors:
- `-a`, `--connectivity`
- `-b`, `--linear <detents> <duration_s>`
- `-c`, `--backforth <detents> <duration_s>`
- `-d`, `--boundary`
- `-e`, `--group <csv_channels>`
- `-f`, `--buscheck`
- `-g`, `--latency <queries> <max_ms>`
- `-i`, `--idempotent`
- `-j`, `--timeout <ip> <max_s>`

Example:

```bash
python3 tests/run_xr18_integration.py \
  --xr18-ip 192.168.x.x \
  -a \
  -b -12 2.0 \
  -c 12 2.0 \
  -d \
  -e 6,7,8 \
  -f \
  -g 10 350 \
  -i \
  -j 192.0.2.1 6
```

What it validates:
- OSC connectivity/query works
- simulated linear motion changes mixer level (`--sim-detents` supports signed + / -, default step size 0.01)
- simulated back-and-forth motion returns near baseline
- detent simulation can be spread over time with `--sim-duration-s`
- boundary clamping at low/high limits
- multi-step monotonic trajectory behavior
- group consistency (when `--group-channels` has 2+ channels)
- bus correctness (target bus changes, alternate bus stays stable)
- query latency budget (`--latency-queries`, `--latency-max-ms`)
- timeout behavior against unreachable peer (`--drop-test-ip`, `--drop-test-max-s`)
- idempotent restore behavior across repeated cycles
- level restore works after test

The suite prints progress lines while running so you can see each bus/channel step.

Safety notes:
- runs sequentially (not concurrent) across configured buses/channels
- run when no critical recording take is in progress
- tests restore channel values after motion checks

---

## Next recommended steps

1. Implement real encoder backend (GPIO or I2C expander).
2. Implement real OLED backend (SSD1306/SH1106, whichever your screens are).
3. Add a tiny installer note for Pi OS + systemd environment file.
4. Add a simple hardware self-test mode (`--self-test`) for bench validation.
