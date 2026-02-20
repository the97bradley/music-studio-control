from app.io.display import percent_from_value


def process_knob_event(osc, st, knob_id: str, direction: int, add_group_fn, set_screen_display_fn, report_error_fn):
    group_name = st.knob_to_group.get(knob_id)
    if not group_name:
        report_error_fn("loop.apply.mapping", RuntimeError(f"unknown knob: {knob_id}"), st)
        return

    step = float(getattr(st, "knob_step", 0.01))
    try:
        add_group_fn(osc, st, group_name, direction * step)
    except Exception as exc:
        report_error_fn("loop.apply.write", exc, st)
        return

    chans = st.groups.get(group_name)
    if not chans:
        report_error_fn("loop.apply.mapping", RuntimeError(f"missing group channels: {group_name}"), st)
        return

    rep_ch = chans[0]
    pct = percent_from_value(st.ch_level[rep_ch])
    ok = set_screen_display_fn(knob_id, group_name.upper(), pct)
    if not ok:
        report_error_fn("loop.apply.display", RuntimeError(f"display write failed: {knob_id}"), st)
