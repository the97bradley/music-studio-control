import json
import os
from typing import Any, Dict

from state import State


def _ensure_int_list(values):
    out = []
    for v in values:
        iv = int(v)
        if iv < 1 or iv > 18:
            raise ValueError(f"channel out of range: {iv}")
        out.append(iv)
    return out


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(path: str) -> Dict[str, Any]:
    try:
        import yaml  # PyYAML
    except Exception as exc:
        raise RuntimeError("PyYAML is required for .yaml controls files") from exc

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _load_controls(path: str) -> Dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".yaml", ".yml"):
        return _load_yaml(path)
    return _load_json(path)


def apply_controls_config(st: State, path: str):
    if not os.path.exists(path):
        return

    data = _load_controls(path)

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
    if isinstance(knob_step, dict):
        new_steps = {}
        for knob_id, step in knob_step.items():
            try:
                sv = float(step)
            except Exception:
                continue
            if sv <= 0:
                continue
            new_steps[str(knob_id)] = sv
        if new_steps:
            st.knob_step.update(new_steps)
