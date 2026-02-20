# music-studio-control

Raspberry Pi endpoint for personal monitor control on Behringer XR18.

## Current architecture

- `main.py` loop: polls knob events, applies grouped fader deltas, updates displays.
- `osc.py`: UDP OSC client + query support + xremote keepalive.
- `state.py`: in-memory mixer state, channel names, group definitions, knob mapping.
- `knobs.py`: encoder backend adapter (`ENCODER_BACKEND`, currently `null`).
- `display.py`: display backend adapter (`DISPLAY_BACKEND`, `null` or `console`).

## Environment variables

- `XR18_IP` (required): mixer IP address.
- `XR18_BUS` (optional, default `2`): monitor bus 1..6.
- `LOCAL_PORT` (optional, default `9100`): local UDP port.
- `ENCODER_BACKEND` (optional, default `null`): encoder backend selection.
- `DISPLAY_BACKEND` (optional, default `null`): display backend selection (`console` for debug output).

## Notes

- Channel levels are stored as **linear 0.0..1.0** values (not dB).
- Knob mapping is in `State.knob_to_group` and currently maps 8 knobs to 8 groups.
- Hardware-specific encoder/OLED backends are intentionally stubbed for incremental bring-up.
