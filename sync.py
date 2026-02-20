from state import State

def sync_faders(osc, st: State, channels: int = 18):
    # pull mixer truth and overwrite local state
    for ch in range(1, channels+1):
        addr = f"/ch/{ch:02d}/mix/{st.bus:02d}/level"
        v = osc.query(addr, tries=2)
        if v is not None:
            st.ch_db[ch] = float(v)