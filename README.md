# music-studio-control

Raspberry Pi endpoint for personal monitor control on Behringer XR18.

## Current architecture

- `main.py` loop: polls knob events, applies grouped fader deltas, syncs mixer state, updates displays.
- `osc.py`: UDP OSC client + query support + xremote keepalive.
- `state.py`: in-memory mixer state, channel names, group definitions, knob mapping, per-knob step.
- `controls.py` + `controls.json`: externalized group/mapping/sensitivity config.
- `knobs.py`: encoder backend adapter (`ENCODER_BACKEND`, currently `null`).
- `display.py`: display backend adapter (`DISPLAY_BACKEND`, `null` or `console`).

## Environment variables

- `XR18_IP` (required): mixer IP address.
- `XR18_BUS` (optional, default `2`): monitor bus 1..6.
- `LOCAL_PORT` (optional, default `9100`): local UDP port.
- `CONTROLS_CONFIG` (optional, default `controls.json`): path to controls config.
- `ENCODER_BACKEND` (optional, default `null`): encoder backend selection.
- `DISPLAY_BACKEND` (optional, default `null`): display backend selection (`console` for debug output).
- `SYNC_EVERY_S` (optional, default `1.0`): mixer sync interval.
- `DEADMAN_TIMEOUT_S` (optional, default `3.0`): stale-link timeout before lockout + error display.

## Runtime behavior

- Channel levels are stored as **linear 0.0..1.0** values in `State.ch_level`.
- dB reference constants in `state.py` use XR18 range `-90.0 .. +10.0`.
- Startup writes `BOOT` info to displays, then switches to live levels.
- On stale mixer link, displays show `ERROR | XR18 LINK` and knob writes are blocked until recovery.
- Exceptions are centralized via `error_handler.py` and routed to the first screen (`knob1` by default) for headless troubleshooting.
- Error codes: `E101` startup, `E102` display init, `E201` main loop, `E999` unknown.
- Displays refresh during periodic sync, so external mixer/app changes are reflected.
