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

- `app/main.py` — main control loop
- `app/core/` — state, faders, sync, apply logic, error handling, logging
- `app/io/` — OSC, hardware/display/knob adapters
- `app/config/` — startup + controls loading
- `controls.yaml` — editable runtime + mapping config
- `tests/unit/` — fast unit tests
- `tests/integration/` — live XR18 integration tests + runner


---

## Configuration

Configuration is read from `controls.yaml`.

Key fields:
- `xr18.ip` (required)
- `xr18.bus` (required, 1..6)
- `xr18.local_port` (optional, default 9100)
- `runtime.sync_every_s`
- `runtime.deadman_timeout_s`
- `hardware.encoder_backend`
- `hardware.display_backend`
- `hardware.alert_backend`
- `display.max_retries`
- `display.backoff_ms`
- `display.fail_threshold`
- `logging.path`
- `logging.max_bytes`
- `logging.backup_count`
- `groups`
- `knob_to_group`
- `knob_step` (single global step)

---

## controls.yaml

This is where you customize behavior without editing Python.

You can define:
- `groups` (which channels each logical control affects)
- `knob_to_group` (which physical knob controls which group)
- `knob_step` (single global sensitivity for all knobs)

Example:

```yaml
xr18:
  bus: 2
  # ip: 192.168.50.62

groups:
  vocal: [1]
  drums: [6, 7, 8, 9, 10, 11]

knob_to_group:
  knob1: vocal
  knob6: drums

knob_step: 0.01
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

All major exceptions flow through a centralized handler:
- screen 1 (`knob1`): error code
- screen 2 (`knob2`): log timestamp (`HH:MM:SS`) to correlate with file logs

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
python3 -m unittest discover -s tests/unit -p "test_*.py" -v
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
- `--quiet` (optional, reduce verbose per-step logs)

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
- `-k`, `--reconnect`
- `-l`, `--burst <steps> <delta>`
- `-m`, `--drums`

Example:

```bash
python3 tests/integration/run_xr18_integration.py \
  --xr18-ip 192.168.x.x \
  -a \
  -b -12 2.0 \
  -c 12 2.0 \
  -d \
  -e 6,7,8 \
  -f \
  -g 10 350 \
  -i \
  -j 192.0.2.1 6 \
  -k \
  -l 40 0.01 \
  -m
```

What it validates:
- OSC connectivity/query works
- simulated linear motion changes mixer level (signed detents, default step size 0.01)
- simulated back-and-forth motion returns near baseline
- boundary clamping at low/high limits
- multi-step monotonic trajectory behavior
- group consistency (when group test is selected with CSV channels)
- bus correctness (target bus changes, alternate bus stays stable)
- query latency budget
- timeout behavior against unreachable peer
- reconnect/resume behavior after transport reset
- burst/hammer motion path behavior
- drums-group sweep test (6-channel profile)
- idempotent restore behavior across repeated cycles
- level restore works after test

The suite is verbose by default and prints per-step internals (bus/channel, before/after levels, deltas, restores, latency samples). Logs are line-buffered and flush immediately (no extra env var needed). Use `--quiet` to reduce output.

The runner also prints standard-style test lifecycle lines and summary:
- `[RUN ]` test start
- `[PASS]` success
- `[FAIL]` assertion failure
- `[ERR ]` runtime error
- `[SKIP]` skipped test

Safety notes:
- runs sequentially (not concurrent) across configured buses/channels
- run when no critical recording take is in progress
- tests restore channel values after motion checks

---

## Logging

The app writes timestamped logs to a rotating file configured in `controls.yaml`:

- `logging.path` (default `logs/endpoint.log`)
- `logging.max_bytes` (default `1073741824` = 1GB)
- `logging.backup_count` (default `1`)

Rotation keeps newest logs in `endpoint.log` and rolls older logs to `endpoint.log.1`.

---

## Next recommended steps

1. Implement real encoder backend (GPIO or I2C expander).
2. Implement real OLED backend (SSD1306/SH1106, whichever your screens are).
3. Add a tiny installer note for Pi OS + systemd environment file.
4. Add a simple hardware self-test mode (`--self-test`) for bench validation.
