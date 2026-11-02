"""Protect statistical denominators and the limits of temporal availability."""
import unittest

import numpy as np
import pandas as pd

from scripts.hotel_expedia_research import (
    categorical_effect, expedia_protocol, hotel_temporal_protocol, rank_effect,
)


class ResearchEvidenceTests(unittest.TestCase):
    def test_effects_do_not_turn_absent_classes_into_signals(self):
        perfect = pd.DataFrame({"n": [10, 10], "positive": [0, 10]})
        self.assertAlmostEqual(categorical_effect(perfect), 1)
        perfect["positive"] = 0
        self.assertTrue(np.isnan(categorical_effect(perfect)))
        self.assertAlmostEqual(rank_effect(pd.Series([1, 2, 3, 4, np.nan]), pd.Series([0, 0, 1, 1, 1])), 1)

    def test_hotel_waits_for_both_arrival_and_final_status(self):
        frame = pd.DataFrame({"reservation_status_date": ["2016-06-20", "2016-06-30", "2016-07-02", None], "is_canceled": [1, 0, 0, 1]})
        arrival = pd.Series(pd.to_datetime(["2016-06-30", "2016-07-02", "2016-06-29", "2016-06-25"]))
        first = hotel_temporal_protocol(frame, arrival).iloc[0]
        self.assertEqual(first.history_n, 1)
        self.assertEqual(first.pending_n, 2)
        self.assertEqual(first.evaluation_n, 1)

    def test_search_window_keeps_whole_lists_and_excludes_gap_boundary(self):
        query = pd.DataFrame({
            "date_min": pd.to_datetime(["2013-01-24", "2013-01-25", "2013-02-01", "2013-03-01"]).as_unit("ns").asi8,
            "n": [10, 20, 30, 40], "clicks": [1, 1, 2, 1], "bookings": [0, 0, 1, 0],
        })
        first = expedia_protocol(query).iloc[0]
        self.assertEqual(first.history_searches, 1)
        self.assertEqual(first.history_n, 10)
        self.assertEqual(first.evaluation_searches, 1)
        self.assertEqual(first.evaluation_n, 30)
        self.assertEqual(first.positive, 1)


if __name__ == "__main__":
    unittest.main()
