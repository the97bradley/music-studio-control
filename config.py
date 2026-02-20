import os
import time

from controls import apply_controls_config
from osc import OscClient
from state import State
from sync import sync_faders


def wait_for_xr18(osc: OscClient, bus: int):
    # use OSC probe (not ping) — XR18 replies to requester port
    probe = f"/ch/01/mix/{bus:02d}/level"
    while True:
        osc.send("/xremote", 0)
        v = osc.query(probe, tries=1)
        if v is not None:
            return
        time.sleep(1)


def load_bus_and_ip():
    ip = os.environ.get("XR18_IP")
    if not ip:
        raise RuntimeError("XR18_IP is required")
    bus = int(os.environ.get("XR18_BUS", "0"))
    if bus < 1 or bus > 6:
        raise RuntimeError("XR18_BUS must be 1-6")
    local_port = int(os.environ.get("LOCAL_PORT", "9100"))
    return ip, bus, local_port


def fetch_channel_names(osc: OscClient, st: State, channels: int = 18):
    # /ch/xx/config/name is used by X32/X-Air family
    for ch in range(1, channels + 1):
        addr = f"/ch/{ch:02d}/config/name"
        v = osc.query(addr, tries=2)
        if isinstance(v, str) and v.strip():
            st.ch_name[ch] = v.strip()


def startup():
    ip, bus, local_port = load_bus_and_ip()
    osc = OscClient(ip, local_port=local_port, timeout_s=2.0)

    st = State(bus=bus)
    st.ensure_channels(18)
    controls_path = os.environ.get("CONTROLS_CONFIG", "controls.json")
    apply_controls_config(st, controls_path)

    wait_for_xr18(osc, bus)
    osc.start_keepalive(5.0)

    sync_faders(osc, st, 18)
    fetch_channel_names(osc, st, 18)

    return osc, st
