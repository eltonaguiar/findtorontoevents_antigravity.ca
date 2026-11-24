import unittest

from tools.db_health_check import ghost_row_verdict


class GhostRowVerdictTest(unittest.TestCase):
    def test_zero_is_green_pass(self):
        v = ghost_row_verdict(0)
        self.assertEqual(v["tier"], "green")
        self.assertTrue(v["threshold_pass"])

    def test_yellow_band_fails(self):
        v = ghost_row_verdict(500)
        self.assertEqual(v["tier"], "yellow")
        self.assertFalse(v["threshold_pass"])

    def test_current_cohort_is_red_fail(self):
        v = ghost_row_verdict(22947)
        self.assertEqual(v["tier"], "red")
        self.assertFalse(v["threshold_pass"])

    def test_none_is_zero(self):
        v = ghost_row_verdict(None)
        self.assertEqual(v["tier"], "green")
        self.assertTrue(v["threshold_pass"])


if __name__ == "__main__":
    unittest.main()
