from dataclasses import dataclass, field
from typing import Dict, List

MIN_DB = -90.0
MAX_DB = 0.0   # keep simple for now; you can expand later

@dataclass
class State:
    bus: int
    # channel -> db (authoritative)
    ch_db: Dict[int, float] = field(default_factory=dict)
    # channel -> name
    ch_name: Dict[int, str] = field(default_factory=dict)

    # group knob -> channels
    groups: Dict[str, List[int]] = field(default_factory=lambda: {
        "vocal": [1],
        "keys": [2],
        "gtr1": [3],
        "gtr2": [4],
        "bass": [5],
        "drums": [6,7,8,9,10,11],
        "click": [17],
        "playback": [18],
    })

    def ensure_channels(self, n: int = 18):
        for ch in range(1, n+1):
            self.ch_db.setdefault(ch, MIN_DB)
            self.ch_name.setdefault(ch, f"CH{ch:02d}")