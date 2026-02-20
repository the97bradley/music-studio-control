import time
from dataclasses import dataclass, field
from typing import Dict, List

MIN_LEVEL = 0.0
MAX_LEVEL = 1.0

# XR18 fader scale reference (for display/conversion helpers)
MIN_DB = -90.0
MAX_DB = 10.0


@dataclass
class State:
    bus: int
    last_ok_sync_ts: float = field(default_factory=time.time)
    # channel -> linear level 0.0..1.0 (authoritative local cache)
    ch_level: Dict[int, float] = field(default_factory=dict)
    # channel -> name
    ch_name: Dict[int, str] = field(default_factory=dict)

    # logical group -> channels
    groups: Dict[str, List[int]] = field(default_factory=lambda: {
        "vocal": [1],
        "keys": [2],
        "gtr1": [3],
        "gtr2": [4],
        "bass": [5],
        "drums": [6, 7, 8, 9, 10, 11],
        "click": [17],
        "playback": [18],
    })

    # 8 physical knobs -> logical groups
    knob_to_group: Dict[str, str] = field(default_factory=lambda: {
        "knob1": "vocal",
        "knob2": "keys",
        "knob3": "gtr1",
        "knob4": "gtr2",
        "knob5": "bass",
        "knob6": "drums",
        "knob7": "click",
        "knob8": "playback",
    })

    # global knob sensitivity in linear mixer level units (0..1)
    knob_step: float = 0.01

    def ensure_channels(self, n: int = 18):
        for ch in range(1, n + 1):
            self.ch_level.setdefault(ch, MIN_LEVEL)
            self.ch_name.setdefault(ch, f"CH{ch:02d}")
