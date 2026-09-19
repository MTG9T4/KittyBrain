"""Showcase determinism and labeling tests (SPEC §3.4). Offline."""
import unittest

from cat import showcase


class DeterminismTest(unittest.TestCase):
    def test_same_seed_identical(self):
        self.assertEqual(
            showcase.generate_series(seed=7, n=120),
            showcase.generate_series(seed=7, n=120),
        )

    def test_different_seeds_diverge(self):
        self.assertNotEqual(
            showcase.generate_series(seed=7, n=120),
            showcase.generate_series(seed=8, n=120),
        )

    def test_shape_and_start(self):
        series = showcase.generate_series(seed=7, n=50, start=42.0)
        self.assertEqual(len(series), 50)
        self.assertEqual(series[0], 42.0)
        self.assertTrue(all(p > 0 for p in series))


class LabelingTest(unittest.TestCase):
    def test_mode_and_flag(self):
        self.assertEqual(showcase.MODE, "showcase")
        self.assertIs(showcase.ILLUSTRATIVE, True)

    def test_disclaimer_honest(self):
        text = showcase.DISCLAIMER.lower()
        self.assertIn("illustrative", text)
        self.assertIn("synthetic", text)
        self.assertIn("not financial advice", text)
        self.assertNotIn("profit", text)


if __name__ == "__main__":
    unittest.main()
