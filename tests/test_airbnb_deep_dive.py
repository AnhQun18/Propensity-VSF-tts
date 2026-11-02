"""Statistical denominator, cohort and chunk-presence checks for Airbnb EDA."""
import unittest

import numpy as np
import pandas as pd

from scripts.airbnb_deep_dive import (
    bh_qvalues, booking_delay_tables, categorical_association,
    session_action_counts, session_audit,
)
from scripts.airbnb_report_presentation import normalize_text


class AirbnbDiagnosticTests(unittest.TestCase):
    def test_number_formatting_preserves_intervals_and_grouped_counts(self):
        text = "Xác suất [0,1]; tuổi [16,100]; hệ số [−1,1]; tỷ lệ 41,65%; V=0,207; n=213,451"
        self.assertEqual(normalize_text(text), "Xác suất [0; 1]; tuổi [16; 100]; hệ số [−1; 1]; tỷ lệ 41.65%; V=0.207; n=213,451")

    def test_number_formatting_keeps_numeric_cells_numeric(self):
        for value in [0.4165, 213451, True, None]:
            self.assertIs(normalize_text(value), value)

    def test_cramers_v_independence_and_perfect_association(self):
        y = pd.Series([0, 0, 1, 1])
        independent = categorical_association(pd.Series(["a", "b", "a", "b"]), y)
        perfect = categorical_association(pd.Series(["a", "a", "b", "b"]), y)
        self.assertAlmostEqual(independent["v"], 0)
        self.assertAlmostEqual(perfect["v"], 1)
        self.assertEqual(perfect["n"], 4)
        # Missing is retained as a category; it must not reduce the denominator.
        missing = categorical_association(pd.Series(["a", None, "a", None]), y)
        self.assertEqual(missing["groups"], 2)
        self.assertEqual(missing["n"], 4)

    def test_lag_coverage_keeps_negative_bookings_separate(self):
        train = pd.DataFrame({
            "country_destination": ["US", "US", "US", "NDF"],
            "date_first_booking": ["2014-01-09", "2014-01-10", "2014-02-15", None],
        })
        account = pd.Series(pd.to_datetime(["2014-01-10", "2014-01-10", "2014-01-01", "2014-01-01"]))
        lag, valid, summary, horizons, cohorts, _ = booking_delay_tables(train, account)
        self.assertEqual(int(valid.sum()), 2)
        self.assertEqual(int(summary.iloc[0].negative_lags), 1)
        self.assertEqual(int(summary.iloc[0].booked_users), 3)
        row = horizons.set_index("horizon_days").loc[30]
        self.assertEqual(row.bookings_within_h, 1)
        self.assertEqual(row.denominator_valid_bookings, 2)
        self.assertAlmostEqual(row.pct_valid_bookings, 50)
        self.assertAlmostEqual(row.pct_all_observed_bookings, 100/3)
        self.assertEqual(int(cohorts.iloc[0].negative_lags), 1)
        self.assertTrue(pd.isna(lag.iloc[3]), "NDF has no observed delay; it is not a zero-day booking")

    def test_session_presence_deduplicates_chunks_and_uses_2014_only(self):
        train = pd.DataFrame({
            "id": ["old", "a", "b", "c", "d"],
            "country_destination": ["US", "US", "NDF", "NDF", "US"],
        })
        account = pd.Series(pd.to_datetime(["2013-01-01"]+["2014-01-01"]*4))
        chunks = [
            pd.DataFrame({"user_id": ["old", "a", "a", "b"], "action": ["book"]*4,
                          "action_type": ["booking_request"]*4, "action_detail": ["checkout"]*4}),
            pd.DataFrame({"user_id": ["a", "b"], "action": ["book", "search"],
                          "action_type": ["booking_request", "click"], "action_detail": ["checkout", "search"]}),
        ]
        parts = [part for chunk in chunks for part in session_action_counts(chunk)]
        counts = pd.concat(parts).groupby(["user_id", "field", "value"], sort=False).event_n.sum().reset_index()
        per_user = pd.DataFrame({"event_n": [1, 3, 2]}, index=["old", "a", "b"])
        rates, description, audit, observed, _ = session_audit(train, account, per_user, counts)
        self.assertEqual(set(observed.id), {"a", "b"})
        self.assertEqual(int(rates.n.sum()), 4, "Coverage comparison includes all 2014 users, including no-log users")
        self.assertEqual(int(description.users.sum()), 4)
        row = audit[(audit.field == "action") & (audit.value == "book")].iloc[0]
        self.assertEqual(row.users_with_action, 2)
        self.assertEqual(row.events, 4)
        self.assertEqual(row.booked_users, 1)
        self.assertEqual(row.ndf_users, 1)
        self.assertAlmostEqual(row.booking_rate_pct, 50)
        self.assertAlmostEqual(row.pct_booked_users_with_action, 100)
        self.assertAlmostEqual(row.pct_ndf_users_with_action, 100)

    def test_bh_controls_family_and_preserves_missing(self):
        actual = bh_qvalues([.04, .001, .02, np.nan])
        np.testing.assert_allclose(actual[:3], [.04, .003, .03])
        self.assertTrue(np.isnan(actual[3]))

    def test_transaction_keywords_match_tokens_not_facebook_substring(self):
        chunk = pd.DataFrame({
            "user_id": ["a", "b", "c"],
            "action": ["facebook_auto_login", "populate_from_facebook", "booking"],
            "action_type": ["click", "click", "booking_request"],
            "action_detail": ["search", "search", "checkout"],
        })
        result = pd.concat(session_action_counts(chunk), ignore_index=True)
        self.assertEqual(set(result.loc[result.field.eq("action"), "value"]), {"booking"})


if __name__ == "__main__":
    unittest.main()
