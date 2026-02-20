import os
from typing import Any, Dict

from app.core.state import State


def _ensure_int_list(values):
    out = []
    for v in values:
        iv = int(v)
        if iv < 1 or iv > 18:
            raise ValueError(f"channel out of range: {iv}")
        out.append(iv)
    return out


def _load_yaml(path: str) -> Dict[str, Any]:
    try:
        import yaml  # PyYAML
    except Exception as exc:
        raise RuntimeError("PyYAML is required for controls.yaml") from exc

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_controls(path: str = "controls.yaml") -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    return _load_yaml(path)


def get_controls_value(key: str, default=None, path: str = "controls.yaml"):
    try:
        data = load_controls(path)
    except Exception:
        return default

    cur = data
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def apply_controls_config(st: State, path: str = "controls.yaml"):
    if not os.path.exists(path):
        return

    data = _load_yaml(path)

    groups = data.get("groups")
    if isinstance(groups, dict):
        st.groups = {
            str(name): _ensure_int_list(chans)
            for name, chans in groups.items()
            if isinstance(chans, list) and chans
        }

    knob_to_group = data.get("knob_to_group")
    if isinstance(knob_to_group, dict):
        mapped = {}
        for knob_id, group_name in knob_to_group.items():
            g = str(group_name)
            if g in st.groups:
                mapped[str(knob_id)] = g
        if mapped:
            st.knob_to_group = mapped

    knob_step = data.get("knob_step")
    try:
        if knob_step is not None:
            sv = float(knob_step)
            if sv > 0:
                st.knob_step = sv
    except Exception:
        pass
