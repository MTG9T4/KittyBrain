"""App journal, export-cap, and config tests (SPEC §3.5). Offline, no sockets."""
import json
import os
import tempfile
import unittest

import app


def sample_obs(**over):
    row = {
        "ts": 1.0,
        "price": 100.0,
        "ma_fast": 100.0,
        "ma_slow": 100.0,
        "spread": 0.0,
        "signal": "neutral",
        "activity": 0.0,
        "mode": "showcase",
        "source": "showcase",
    }
    row.update(over)
    return row


class JournalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.tmp.close()
        self.conn = app.init_db(self.tmp.name)

    def tearDown(self):
        self.conn.close()
        os.unlink(self.tmp.name)

    def test_record_and_read_round_trip(self):
        app.record_observation(self.conn, sample_obs(ts=5.0, price=101.5))
        rows = app.last_observations(self.conn, 80)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["price"], 101.5)
        self.assertEqual(rows[0]["ts"], 5.0)

    def test_chronological_order(self):
        for ts in (3.0, 1.0, 2.0):
            app.record_observation(self.conn, sample_obs(ts=ts))
        rows = app.last_observations(self.conn, 80)
        self.assertEqual([r["ts"] for r in rows], [3.0, 1.0, 2.0])

    def test_last_80_cap(self):
        for i in range(100):
            app.record_observation(self.conn, sample_obs(ts=float(i)))
        rows = app.last_observations(self.conn, 80)
        self.assertEqual(len(rows), 80)
        self.assertEqual(rows[0]["ts"], 20.0)
        self.assertEqual(rows[-1]["ts"], 99.0)

    def test_limit_clamped_to_80(self):
        for i in range(100):
            app.record_observation(self.conn, sample_obs(ts=float(i)))
        self.assertEqual(len(app.last_observations(self.conn, 9999)), 80)
        self.assertEqual(len(app.last_observations(self.conn, 0)), 0)


class EnvelopeTest(unittest.TestCase):
    def test_showcase_envelope_labeled(self):
        env = app.build_envelope(mode="showcase", payload={"ok": True})
        self.assertEqual(env["brand"], "KITTYBRAIN")
        self.assertEqual(env["mode"], "showcase")
        self.assertIs(env["illustrative"], True)
        self.assertIn("disclaimer", env)

    def test_live_envelope_not_illustrative(self):
        env = app.build_envelope(mode="live", payload={})
        self.assertIs(env["illustrative"], False)


class ConfigTest(unittest.TestCase):
    def test_loopback_clamp(self):
        self.assertEqual(app.resolve_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(app.resolve_host("0.0.0.0"), "127.0.0.1")
        self.assertEqual(app.resolve_host("example.com"), "127.0.0.1")

    def test_load_config_defaults(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as handle:
            json.dump({"mode": "live"}, handle)
            name = handle.name
        try:
            cfg = app.load_config(name)
        finally:
            os.unlink(name)
        self.assertEqual(cfg["mode"], "live")
        self.assertEqual(cfg["port"], 8000)
        self.assertEqual(cfg["poll_seconds"], 30)

    def test_blank_pair_blocks_live(self):
        self.assertIsNotNone(app.live_blocker({"mode": "live", "pair": ""}))
        self.assertIsNone(
            app.live_blocker({"mode": "live", "pair": "AbC123", "chain": "solana"})
        )
        self.assertIsNone(app.live_blocker({"mode": "showcase", "pair": ""}))


class EventsTest(unittest.TestCase):
    def test_log_appends_fields(self):
        state = {}
        ev = app.log_event(state, "observe", "start", "hello", ts=5.0)
        self.assertEqual(ev["ts"], 5.0)
        self.assertEqual(ev["stage"], "observe")
        self.assertEqual(ev["kind"], "start")
        self.assertEqual(ev["message"], "hello")
        self.assertEqual(len(state["events"]), 1)

    def test_consecutive_duplicate_skipped(self):
        state = {}
        app.log_event(state, "observe", "blocked", "same", ts=1.0)
        app.log_event(state, "observe", "blocked", "same", ts=2.0)
        self.assertEqual(len(state["events"]), 1)
        app.log_event(state, "observe", "blocked", "different", ts=3.0)
        self.assertEqual(len(state["events"]), 2)

    def test_ring_capped_chronological(self):
        state = {}
        for i in range(app.EVENTS_CAP + 10):
            app.log_event(state, "inspect", "observation", "msg-%d" % i, ts=float(i))
        self.assertEqual(len(state["events"]), app.EVENTS_CAP)
        self.assertEqual(state["events"][0]["message"], "msg-10")
        self.assertEqual(state["events"][-1]["message"], "msg-%d" % (app.EVENTS_CAP + 9))

    def test_recent_events_limit(self):
        state = {}
        for i in range(5):
            app.log_event(state, "observe", "x", "m%d" % i, ts=float(i))
        self.assertEqual(len(app.recent_events(state, 3)), 3)
        self.assertEqual(app.recent_events(state, 3)[0]["message"], "m2")
        self.assertEqual(app.recent_events(state, 0), [])
        self.assertEqual(len(app.recent_events(state, 9999)), 5)
        self.assertEqual(len(app.recent_events(state, "bad")), 5)


class RadarTest(unittest.TestCase):
    def test_warming_row_is_waiting_with_nulls(self):
        rows = app.build_radar(
            {"mode": "showcase", "showcase_seed": 7}, None,
            {"sample_count": 4, "needed": 20, "warming_up": True},
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["signal"], "waiting")
        self.assertIsNone(row["price"])
        self.assertIsNone(row["change_1h_pct"])
        self.assertIsNone(row["volume_24h_usd"])
        self.assertIsNone(row["liquidity_usd"])
        self.assertIn("warming up 4/20", row["note"])
        self.assertIn("SHOWCASE", row["label"])

    def test_observation_row_carries_latest(self):
        latest = {"price": 101.5, "signal": "positive", "spread": 0.004,
                  "activity": 0.24, "sample_count": 25}
        rows = app.build_radar({"mode": "showcase"}, latest, {"warming_up": False})
        row = rows[0]
        self.assertEqual(row["price"], 101.5)
        self.assertEqual(row["signal"], "positive")
        self.assertEqual(row["activity"], 0.24)
        self.assertIsNone(row["volume_24h_usd"])  # never zero-filled
        self.assertTrue(row["unavailable_reason"])

    def test_live_label_uses_chain_and_pair(self):
        latest = {"price": 2.0, "signal": "neutral", "spread": 0.0,
                  "activity": 0.12, "sample_count": 30}
        rows = app.build_radar(
            {"mode": "live", "chain": "solana", "pair": "AbC123"},
            latest, {"warming_up": False},
        )
        self.assertIn("solana", rows[0]["label"])
        self.assertEqual(rows[0]["pool"], "AbC123")


class WebFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, "assets"))
        with open(os.path.join(self.tmp.name, "a.css"), "w") as handle:
            handle.write("body{}")
        with open(os.path.join(self.tmp.name, "assets", "x.png"), "wb") as handle:
            handle.write(b"\x89PNG")

    def tearDown(self):
        self.tmp.cleanup()

    def test_serves_mapped_type(self):
        found = app.read_web_file("a.css", web_dir=self.tmp.name)
        self.assertIsNotNone(found)
        self.assertEqual(found[0], "text/css; charset=utf-8")
        self.assertEqual(found[1], b"body{}")

    def test_serves_nested_asset(self):
        found = app.read_web_file("assets/x.png", web_dir=self.tmp.name)
        self.assertIsNotNone(found)
        self.assertEqual(found[0], "image/png")

    def test_rejects_escape_and_unknown(self):
        self.assertIsNone(app.read_web_file("../app.py", web_dir=self.tmp.name))
        self.assertIsNone(app.read_web_file("/etc/hosts", web_dir=self.tmp.name))
        self.assertIsNone(app.read_web_file("assets/", web_dir=self.tmp.name))
        self.assertIsNone(app.read_web_file(".hidden.css", web_dir=self.tmp.name))
        self.assertIsNone(app.read_web_file("missing.js", web_dir=self.tmp.name))
        with open(os.path.join(self.tmp.name, "run.sh"), "w") as handle:
            handle.write("x")
        self.assertIsNone(app.read_web_file("run.sh", web_dir=self.tmp.name))


class PollEventsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.tmp.close()

    def tearDown(self):
        try:
            self.state["conn"].close()
        finally:
            os.unlink(self.tmp.name)

    def test_poll_logs_warming_then_observation(self):
        self.state = app.build_state({"mode": "showcase"}, db_path=self.tmp.name)
        self.assertEqual(self.state["events"][0]["kind"], "start")
        for _ in range(5):
            app.poll_once(self.state)
        kinds = [e["kind"] for e in self.state["events"]]
        self.assertIn("warming", kinds)
        for _ in range(20):
            app.poll_once(self.state)
        kinds = [e["kind"] for e in self.state["events"]]
        self.assertIn("observation", kinds)
        stages = {e["stage"] for e in self.state["events"]}
        self.assertTrue({"observe", "evaluate", "inspect"} <= stages)

    def test_blocked_live_logs_blocker(self):
        self.state = app.build_state(
            {"mode": "live", "chain": "solana", "pair": ""}, db_path=self.tmp.name
        )
        self.assertIsNone(app.poll_once(self.state))
        self.assertEqual(self.state["events"][-1]["kind"], "blocked")


if __name__ == "__main__":
    unittest.main()
