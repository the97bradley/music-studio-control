from typing import List
from app.core.state import State


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def set_faders_abs(osc, st: State, channels: List[int], new_value: float):
    new_value = clamp(new_value)
    for ch in channels:
        addr = f"/ch/{ch:02d}/mix/{st.bus:02d}/level"
        osc.send(addr, float(new_value))
        st.ch_level[ch] = new_value


def add_faders_linear(osc, st: State, channels: List[int], delta: float):
    base = st.ch_level[channels[0]]
    new_value = clamp(base + delta)
    set_faders_abs(osc, st, channels, new_value)


def set_group(osc, st: State, group_name: str, new_value: float):
    chans = st.groups[group_name]
    set_faders_abs(osc, st, chans, new_value)


def add_group(osc, st: State, group_name: str, delta: float):
    chans = st.groups[group_name]
    add_faders_linear(osc, st, chans, delta)
