import os
import time

from controls import apply_controls_config
from osc import OscClient
from state import State
from sync import sync_faders


class StartupError(RuntimeError):
    def __init__(self, where: str, cause: Exception):
        super().__init__(f"{where}: {cause}")
        self.where = where
        self.cause = cause


def wait_for_xr18(osc: OscClient, bus: int):
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
    for ch in range(1, channels + 1):
        addr = f"/ch/{ch:02d}/config/name"
        v = osc.query(addr, tries=2)
        if isinstance(v, str) and v.strip():
            st.ch_name[ch] = v.strip()


def startup():
    try:
        ip, bus, local_port = load_bus_and_ip()
    except Exception as exc:
        raise StartupError("startup.load_env", exc)

    try:
        osc = OscClient(ip, local_port=local_port, timeout_s=2.0)
    except Exception as exc:
        raise StartupError("startup.osc_client", exc)

    st = State(bus=bus)
    st.ensure_channels(18)

    try:
        controls_path = os.environ.get("CONTROLS_CONFIG", "controls.yaml")
        apply_controls_config(st, controls_path)
    except Exception as exc:
        raise StartupError("startup.controls", exc)

    try:
        wait_for_xr18(osc, bus)
        osc.start_keepalive(5.0)
    except Exception as exc:
        raise StartupError("startup.wait_xr18", exc)

    try:
        sync_faders(osc, st, 18)
    except Exception as exc:
        raise StartupError("startup.initial_sync", exc)

    try:
        fetch_channel_names(osc, st, 18)
    except Exception as exc:
        raise StartupError("startup.channel_names", exc)

    return osc, st
