import time
import unittest

from faders import add_group, set_group
from state import State

XR18_IP = None
LOCAL_PORT = 9101
SIM_DETENTS = 1
STEP_SIZE = 0.01
SIM_DURATION_S = 0.0
GROUP_CHANNELS = None
LATENCY_QUERIES = 8
LATENCY_MAX_MS = 350.0
DROP_TEST_IP = "192.0.2.1"
DROP_TEST_MAX_S = 6.0
VERBOSE = True

# Fixed live coverage set (sequential, not concurrent)
TEST_BUSES = [1, 2]
TEST_CHANNELS = [1, 16]


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def _log(msg: str, level: str = "INFO"):
    if VERBOSE:
        # Intentionally indented so step logs sit under the active [RUN] test line.
        print(f"    [{level}] {msg}", flush=True)


class TestXR18Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not XR18_IP:
            _log("XR18 IP not provided", "WARN")
            raise unittest.SkipTest("XR18 IP not provided")

        from osc import OscClient

        cls.osc = OscClient(XR18_IP, local_port=int(LOCAL_PORT), timeout_s=2.0)
        cls.group_channels = cls._parse_group_channels(GROUP_CHANNELS)

        _log(f"XR18 target ip={XR18_IP} local_port={LOCAL_PORT}")
        _log(f"test buses={TEST_BUSES} channels={TEST_CHANNELS}")

        # preflight: at least one bus/channel query must succeed
        any_ok = False
        for bus in TEST_BUSES:
            for ch in TEST_CHANNELS:
                v = cls._query_level(ch, bus)
                _log(f"preflight query bus={bus} ch={ch} -> {v}")
                if v is not None:
                    any_ok = True
                    break
            if any_ok:
                break

        if not any_ok:
            _log("Could not query any configured bus/channel from XR18", "WARN")
            raise unittest.SkipTest("Could not query any configured bus/channel from XR18")

        _log("Preflight passed", "PASS")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.osc.close()
        except Exception:
            pass

    @staticmethod
    def _parse_group_channels(raw):
        if not raw:
            return []
        if isinstance(raw, list):
            chans = [int(x) for x in raw]
        else:
            chans = [int(x.strip()) for x in str(raw).split(",") if x.strip()]
        return [c for c in chans if 1 <= c <= 18]

    @classmethod
    def _query_level(cls, ch: int, bus: int):
        addr = f"/ch/{ch:02d}/mix/{bus:02d}/level"
        v = cls.osc.query(addr, tries=2)
        return None if v is None else float(v)

    @classmethod
    def _sync_channel(cls, st: State, ch: int):
        v = cls._query_level(ch, st.bus)
        if v is None:
            return None
        st.ch_level[ch] = float(v)
        return st.ch_level[ch]

    @classmethod
    def _state_for(cls, bus: int, ch: int):
        st = State(bus=bus)
        st.ensure_channels(18)
        st.groups = {"test": [ch]}
        st.knob_to_group = {"knob1": "test"}
        v = cls._query_level(ch, bus)
        if v is None:
            return None
        st.ch_level[ch] = float(v)
        return st

    @classmethod
    def _restore_channel(cls, st: State, ch: int, value: float):
        _log(f"restoring bus={st.bus} ch={ch} -> {value:.4f}")
        set_group(cls.osc, st, "test", value)
        time.sleep(0.1)
        restored = cls._sync_channel(st, ch)
        return restored

    def test_connectivity_query_level(self):
        for bus in TEST_BUSES:
            for ch in TEST_CHANNELS:
                _log(f"connectivity check bus={bus} ch={ch}")
                v = self._query_level(ch, bus)
                self.assertIsNotNone(v, f"XR18 did not return level query for bus={bus}, ch={ch}")
                _log(f"connectivity ok bus={bus} ch={ch} value={v:.4f}", "PASS")

    def test_simulated_linear_motion_and_restore(self):
        detents = int(SIM_DETENTS)
        sign = 1 if detents >= 0 else -1
        steps = abs(detents)
        step_delta = sign * float(STEP_SIZE)
        total_delta = detents * float(STEP_SIZE)

        for bus in TEST_BUSES:
            for ch in TEST_CHANNELS:
                _log(f"linear motion bus={bus} ch={ch} detents={detents}")
                st = self._state_for(bus, ch)
                if st is None:
                    self.skipTest(f"No query response for bus={bus}, ch={ch}")

                before = st.ch_level[ch]
                expected = _clamp(before + total_delta)
                _log(f"linear start bus={bus} ch={ch} before={before:.4f} total_delta={total_delta:.4f} expected={expected:.4f}")

                if steps > 0:
                    interval = max(0.0, float(SIM_DURATION_S)) / steps
                    for i in range(steps):
                        add_group(self.osc, st, "test", step_delta)
                        _log(f"linear step {i+1}/{steps} bus={bus} ch={ch} step_delta={step_delta:+.4f}")
                        if interval > 0:
                            time.sleep(interval)

                time.sleep(0.1)
                _log(f"querying post-linear level bus={bus} ch={ch}")
                after = self._sync_channel(st, ch)
                _log(f"linear end bus={bus} ch={ch} after={after:.4f}")

                self.assertAlmostEqual(
                    after,
                    expected,
                    delta=0.005,
                    msg=(
                        f"Expected ~{expected:.3f} after linear move "
                        f"(bus={bus}, ch={ch}, detents={SIM_DETENTS}, step={STEP_SIZE}, duration_s={SIM_DURATION_S}); got {after:.3f}"
                    ),
                )

                restored = self._restore_channel(st, ch, before)
                _log(f"linear restore bus={bus} ch={ch} restored={restored:.4f} target={before:.4f}")
                self.assertAlmostEqual(restored, before, places=3)
                _log(f"linear motion PASS bus={bus} ch={ch}", "PASS")

    def test_simulated_back_and_forth_motion_and_restore(self):
        steps = max(1, abs(int(SIM_DETENTS)))
        delta = float(STEP_SIZE)

        for bus in TEST_BUSES:
            for ch in TEST_CHANNELS:
                _log(f"back-forth motion bus={bus} ch={ch} steps={steps}")
                st = self._state_for(bus, ch)
                if st is None:
                    self.skipTest(f"No query response for bus={bus}, ch={ch}")

                baseline = st.ch_level[ch]
                _log(f"back-forth start bus={bus} ch={ch} baseline={baseline:.4f} steps={steps} step={delta:.4f}")

                for i in range(steps):
                    add_group(self.osc, st, "test", delta)
                    _log(f"back-forth up step {i+1}/{steps} bus={bus} ch={ch} delta={delta:+.4f}")
                    if SIM_DURATION_S > 0:
                        time.sleep(SIM_DURATION_S / (2 * steps))
                for i in range(steps):
                    add_group(self.osc, st, "test", -delta)
                    _log(f"back-forth down step {i+1}/{steps} bus={bus} ch={ch} delta={-delta:+.4f}")
                    if SIM_DURATION_S > 0:
                        time.sleep(SIM_DURATION_S / (2 * steps))

                time.sleep(0.1)
                _log(f"querying post-back-forth level bus={bus} ch={ch}")
                after = self._sync_channel(st, ch)
                _log(f"back-forth end bus={bus} ch={ch} after={after:.4f} baseline={baseline:.4f}")
                self.assertAlmostEqual(after, baseline, delta=0.01)

                restored = self._restore_channel(st, ch, baseline)
                _log(f"back-forth restore bus={bus} ch={ch} restored={restored:.4f}")
                self.assertAlmostEqual(restored, baseline, places=3)
                _log(f"back-forth PASS bus={bus} ch={ch}", "PASS")

    def test_boundary_clamp_low_high(self):
        for bus in TEST_BUSES:
            for ch in TEST_CHANNELS:
                _log(f"clamp boundary test bus={bus} ch={ch}")
                st = self._state_for(bus, ch)
                if st is None:
                    self.skipTest(f"No query response for bus={bus}, ch={ch}")

                before = st.ch_level[ch]
                _log(f"boundary start bus={bus} ch={ch} before={before:.4f}")

                set_group(self.osc, st, "test", -0.25)
                time.sleep(0.1)
                _log(f"querying low-clamp level bus={bus} ch={ch}")
                low = self._sync_channel(st, ch)
                _log(f"boundary low bus={bus} ch={ch} value={low:.4f}")
                self.assertGreaterEqual(low, 0.0)
                self.assertLessEqual(low, 0.01)

                set_group(self.osc, st, "test", 1.25)
                time.sleep(0.1)
                _log(f"querying high-clamp level bus={bus} ch={ch}")
                high = self._sync_channel(st, ch)
                _log(f"boundary high bus={bus} ch={ch} value={high:.4f}")
                self.assertLessEqual(high, 1.0)
                self.assertGreaterEqual(high, 0.99)

                restored = self._restore_channel(st, ch, before)
                _log(f"boundary restore bus={bus} ch={ch} restored={restored:.4f}")
                self.assertAlmostEqual(restored, before, places=3)
                _log(f"boundary PASS bus={bus} ch={ch}", "PASS")

    def test_group_consistency_multi_channel(self):
        if len(self.group_channels) < 2:
            self.skipTest("Provide --group-channels with 2+ channels to run group consistency test")

        for bus in TEST_BUSES:
            _log(f"group consistency bus={bus} channels={self.group_channels}")
            st = State(bus=bus)
            st.ensure_channels(18)
            st.groups = {"test": self.group_channels}

            before = {ch: self._query_level(ch, bus) for ch in self.group_channels}
            for ch, v in before.items():
                self.assertIsNotNone(v, f"No query response for group channel {ch} on bus {bus}")

            set_group(self.osc, st, "test", 0.42)
            time.sleep(0.1)

            after = {ch: self._query_level(ch, bus) for ch in self.group_channels}
            for ch, v in after.items():
                self.assertIsNotNone(v, f"No query response for group channel {ch} after write on bus {bus}")

            vals = list(after.values())
            span = max(vals) - min(vals)
            self.assertLessEqual(span, 0.01, f"Expected group channels to match closely, got {after}")
            _log(f"group consistency PASS bus={bus} span={span:.4f}", "PASS")

            # restore channel-by-channel
            for ch, v in before.items():
                addr = f"/ch/{ch:02d}/mix/{bus:02d}/level"
                self.osc.send(addr, float(v))
            time.sleep(0.15)

    def test_bus_correctness_targeted_write(self):
        if len(TEST_BUSES) < 2:
            self.skipTest("Need at least two buses configured in TEST_BUSES")

        target_bus = TEST_BUSES[0]
        alt_bus = TEST_BUSES[1]

        for ch in TEST_CHANNELS:
            _log(f"bus correctness target={target_bus} alt={alt_bus} ch={ch}")
            st = self._state_for(target_bus, ch)
            if st is None:
                self.skipTest(f"No query response for bus={target_bus}, ch={ch}")

            primary_before = self._query_level(ch, target_bus)
            alt_before = self._query_level(ch, alt_bus)
            if primary_before is None or alt_before is None:
                self.skipTest(f"Could not query both buses for ch={ch}")

            set_group(self.osc, st, "test", _clamp(primary_before + 0.02))
            time.sleep(0.1)
            primary_after = self._query_level(ch, target_bus)
            alt_after = self._query_level(ch, alt_bus)

            self.assertIsNotNone(primary_after)
            self.assertIsNotNone(alt_after)
            self.assertNotAlmostEqual(primary_before, primary_after, delta=0.005)
            self.assertAlmostEqual(alt_before, alt_after, delta=0.005)

            restored = self._restore_channel(st, ch, primary_before)
            self.assertAlmostEqual(restored, primary_before, places=3)
            _log(f"bus correctness PASS ch={ch}", "PASS")

    def test_query_latency_budget(self):
        for bus in TEST_BUSES:
            for ch in TEST_CHANNELS:
                _log(f"latency test bus={bus} ch={ch} n={LATENCY_QUERIES}")
                samples = []
                for i in range(int(LATENCY_QUERIES)):
                    t0 = time.time()
                    v = self._query_level(ch, bus)
                    dt_ms = (time.time() - t0) * 1000.0
                    self.assertIsNotNone(v, f"Latency test query returned None for bus={bus}, ch={ch}")
                    samples.append(dt_ms)
                    _log(f"latency sample bus={bus} ch={ch} i={i+1}/{LATENCY_QUERIES} dt_ms={dt_ms:.1f} value={v:.4f}")

                p95 = sorted(samples)[max(0, int(len(samples) * 0.95) - 1)]
                _log(f"latency summary bus={bus} ch={ch} p95={p95:.1f}ms samples={samples}")
                self.assertLessEqual(
                    p95,
                    float(LATENCY_MAX_MS),
                    msg=f"p95 query latency {p95:.1f}ms exceeds budget {LATENCY_MAX_MS:.1f}ms; samples={samples}",
                )
                _log(f"latency PASS bus={bus} ch={ch} p95={p95:.1f}ms", "PASS")

    def test_idempotent_restore_two_cycles(self):
        for bus in TEST_BUSES:
            for ch in TEST_CHANNELS:
                _log(f"idempotent restore bus={bus} ch={ch}")
                st = self._state_for(bus, ch)
                if st is None:
                    self.skipTest(f"No query response for bus={bus}, ch={ch}")

                baseline = st.ch_level[ch]
                for _ in range(2):
                    add_group(self.osc, st, "test", 0.02)
                    time.sleep(0.05)
                    _ = self._sync_channel(st, ch)
                    set_group(self.osc, st, "test", baseline)
                    time.sleep(0.05)
                    cur = self._sync_channel(st, ch)
                    self.assertAlmostEqual(cur, baseline, places=3)
                _log(f"idempotent PASS bus={bus} ch={ch}", "PASS")

    def test_timeout_behavior_on_unreachable_peer(self):
        from osc import OscClient

        _log(f"timeout behavior test ip={DROP_TEST_IP}")
        bad = OscClient(DROP_TEST_IP, local_port=int(LOCAL_PORT) + 11, timeout_s=1.0)
        try:
            bus = TEST_BUSES[0]
            ch = TEST_CHANNELS[0]
            t0 = time.time()
            v = bad.query(f"/ch/{ch:02d}/mix/{bus:02d}/level", tries=2)
            dt = time.time() - t0
            self.assertIsNone(v, "Expected no response from unreachable test IP")
            self.assertLessEqual(
                dt,
                float(DROP_TEST_MAX_S),
                msg=f"Unreachable peer timeout took too long: {dt:.2f}s (budget {DROP_TEST_MAX_S}s)",
            )
            _log(f"timeout behavior PASS dt={dt:.2f}s", "PASS")
        finally:
            bad.close()


if __name__ == "__main__":
    unittest.main()
