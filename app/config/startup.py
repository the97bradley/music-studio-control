import time

from app.config.controls import apply_controls_config, load_controls
from app.io.osc import OscClient
from app.core.state import State
from app.core.sync import sync_faders


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


def load_bus_and_ip(controls_path: str):
    controls = load_controls(controls_path)
    xr18_cfg = controls.get("xr18") if isinstance(controls.get("xr18"), dict) else {}

    ip = xr18_cfg.get("ip") or controls.get("xr18_ip")
    if not ip:
        raise RuntimeError("Missing xr18.ip in controls.yaml")

    bus = int(xr18_cfg.get("bus", controls.get("xr18_bus", 0)))
    if bus < 1 or bus > 6:
        raise RuntimeError("xr18.bus must be 1-6 in controls.yaml")

    local_port = int(xr18_cfg.get("local_port", controls.get("local_port", 9100)))
    return ip, bus, local_port


def fetch_channel_names(osc: OscClient, st: State, channels: int = 18):
    for ch in range(1, channels + 1):
        addr = f"/ch/{ch:02d}/config/name"
        v = osc.query(addr, tries=2)
        if isinstance(v, str) and v.strip():
            st.ch_name[ch] = v.strip()


def startup():
    controls_path = "controls.yaml"

    try:
        ip, bus, local_port = load_bus_and_ip(controls_path)
    except Exception as exc:
        raise StartupError("startup.load_env", exc)

    try:
        osc = OscClient(ip, local_port=local_port, timeout_s=2.0)
    except Exception as exc:
        raise StartupError("startup.osc_client", exc)

    st = State(bus=bus)
    st.ensure_channels(18)

    try:
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
