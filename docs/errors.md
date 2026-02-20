# Error Code Troubleshooting

This project is designed for headless Raspberry Pi use.

When something fails, screen 1 (`knob1`) shows a short error code (for example `E114`) plus exception type.
This doc maps each code to likely causes and first fixes.

---

## Startup codes (`E1xx`)

### `E111` — `startup.load_env`
**What it means:** Required env/config values are missing or invalid.

**Likely causes**
- `XR18_IP` not set
- `XR18_BUS` outside 1..6
- bad/non-numeric `LOCAL_PORT`

**Try first**
1. Check service env values (`systemctl cat xr18pm` or env file).
2. Confirm `XR18_IP` is the actual mixer IP.
3. Set `XR18_BUS` to a valid bus number (1–6).

---

### `E112` — `startup.osc_client`
**What it means:** OSC UDP socket could not be created or bound.

**Likely causes**
- `LOCAL_PORT` already in use
- insufficient permissions
- networking stack issue

**Try first**
1. Change `LOCAL_PORT` (e.g. 9101) and retry.
2. Check what owns the port (`sudo lsof -iUDP:9100`).
3. Restart service/network.

---

### `E113` — `startup.controls`
**What it means:** `controls.json` failed to load/validate.

**Likely causes**
- invalid JSON syntax
- channel numbers outside 1..18
- malformed keys/values

**Try first**
1. Validate JSON (`python -m json.tool controls.json`).
2. Ensure channels are 1..18.
3. Ensure `knob_to_group` points to existing group names.

---

### `E114` — `startup.wait_xr18`
**What it means:** Could not establish stable comms with XR18 during startup.

**Likely causes**
- Pi and XR18 not on same network/VLAN
- wrong `XR18_IP`
- mixer powered off or rebooting

**Try first**
1. Ping mixer IP from Pi.
2. Verify XR18 is powered and network link is up.
3. Confirm IP didn’t change (DHCP reservation recommended).

---

### `E115` — `startup.initial_sync`
**What it means:** Initial fader readback failed.

**Likely causes**
- intermittent network packet loss
- OSC response timeout too short for current network

**Try first**
1. Retry service start.
2. Check network stability (switch/AP cabling).
3. Consider slightly longer OSC timeout in code if persistent.

---

### `E116` — `startup.channel_names`
**What it means:** Failed reading channel names from mixer.

**Likely causes**
- temporary XR18 response loss
- channel-name query path not responding reliably

**Try first**
1. Restart service and observe if intermittent.
2. Treat as non-fatal if levels still work.

---

## Init/display code

### `E121` — `display.init`
**What it means:** Failed while drawing startup screens.

**Likely causes**
- display backend misconfigured
- OLED bus/address mismatch
- I2C not enabled on Pi

**Try first**
1. Verify `DISPLAY_BACKEND` setting.
2. Run `i2cdetect -y 1` and confirm expected device addresses.
3. Ensure I2C is enabled (`raspi-config`).

---

## Runtime codes (`E2xx`)

### `E211` — `loop.sync`
**What it means:** Periodic mixer sync failed.

**Likely causes**
- temporary XR18 comms drop
- socket/network instability

**Try first**
1. Watch if it self-recovers in a few seconds.
2. If sustained, inspect network and mixer health.

---

### `E212` — `loop.render`
**What it means:** Failed refreshing displays during normal operation.

**Likely causes**
- OLED backend exception
- I2C hiccup

**Try first**
1. Check I2C bus/device presence.
2. Restart service.

---

### `E213` — `loop.poll`
**What it means:** Encoder polling backend crashed or threw.

**Likely causes**
- GPIO/I2C read errors
- backend bug in encoder driver

**Try first**
1. Check encoder wiring.
2. Reboot Pi and retest.
3. Run with debug logs on backend path.

---

### `E214` — `loop.apply`
**What it means:** Failed applying a knob change (group lookup/write/display update path).

**Likely causes**
- bad knob mapping
- malformed step config
- OSC write failure during apply

**Try first**
1. Verify `controls.json` mapping and steps.
2. Check for unknown knob IDs from hardware backend.
3. Confirm mixer comms are healthy.

---

## Fallback

### `E999` — Unknown
**What it means:** Error context wasn’t mapped.

**Try first**
1. Check service logs for full traceback.
2. Add/assign a specific code for that context in `error_handler.py`.

---

## Log commands (Pi)

```bash
sudo systemctl status xr18pm
sudo journalctl -u xr18pm -n 200 --no-pager
sudo journalctl -u xr18pm -f
```
