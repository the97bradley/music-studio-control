import time
from state import State


def sync_faders(osc, st: State, channels: int = 18) -> bool:
    """
    Pull mixer truth and overwrite local state.
    Returns True if all channel queries succeeded, else False.
    """
    ok = True
    for ch in range(1, channels + 1):
        addr = f"/ch/{ch:02d}/mix/{st.bus:02d}/level"
        v = osc.query(addr, tries=2)
        if v is None:
            ok = False
            continue
        st.ch_level[ch] = float(v)

    if ok:
        st.last_ok_sync_ts = time.time()
    return ok
