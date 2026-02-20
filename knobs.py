from typing import List, Tuple
from hardware import create_encoder_backend

_encoder = create_encoder_backend()


def poll_knobs() -> List[Tuple[str, int]]:
    """
    Returns list of events like:
      ("knob6", +1) or ("knob1", -1)
    where +/- means one detent movement.
    """
    return _encoder.read_events()
