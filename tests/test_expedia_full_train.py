"""Checks for exact full-train diagnostics, ties, missing pairs and chunk edges."""
import contextlib
import io
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts import build_descriptive_reports as builder
from scripts.expedia_full_train import TrainColumns, exact_spearman, full_missing_diagnostics, working_directory


class ExpediaFullTrainTests(unittest.TestCase):
    def test_full_scan_pairwise_ranks_and_missing_reconcile(self):
        frame = pd.DataFrame({c: np.ones(12) for c in builder.EXPEDIA_MEANINGS})
        frame["date_time"] = "2013-01-01 12:00:00"
        frame["srch_id"] = np.repeat([10, 20, 30], 4)
        frame["prop_id"] = np.arange(12)
        frame["price_usd"] = [10, 10, 20, 30, 40, 50, 50, 80, 90, 100, 200, 90000]
        frame["prop_review_score"] = [1, 2, np.nan, 2, 3, 1, np.nan, 4, 4, 3, 2, 5]
        frame["prop_starrating"] = [1, 1, 2, 2, 3, 4, 4, 2, 5, 3, 4, 5]
        frame["click_bool"] = [1, 0, 0, 0] * 3
        frame["booking_bool"] = [1, 0, 0, 0] + [0] * 8
        frame["gross_bookings_usd"] = [20] + [np.nan] * 11
        frame.loc[[1, 2, 5, 11], "comp1_rate"] = np.nan
        numeric = builder.EXPEDIA_NUM + [f"comp{i}_rate_percent_diff" for i in range(1, 9)] + ["gross_bookings_usd"]
        with working_directory() as folder:
            path = Path(folder) / "train.csv"
            frame.to_csv(path, index=False)
            with TrainColumns(len(frame), numeric) as store, contextlib.redirect_stdout(io.StringIO()):
                cache_path = store.directory
                with patch.object(builder, "CHUNK_SIZE", 3):
                    result = builder.scan_expedia(path, True, store)
                self.assertEqual(result["rows"], len(frame))
                self.assertEqual(result["queries"].n.to_dict(), {10: 4, 20: 4, 30: 4})
                self.assertEqual(result["duplicate_pairs"], 0)
                table = result["stats"].set_index("column")
                for column in numeric:
                    expected = frame[column]
                    self.assertAlmostEqual(table.loc[column, "full_p50"], expected.median())
                    if expected.notna().sum() > 2:
                        self.assertAlmostEqual(table.loc[column, "full_skewness"], expected.skew())
                self.assertEqual(table.loc["price_usd", "full_max"], 90000)
                columns = ["price_usd", "prop_review_score", "prop_starrating"]
                actual, pairs = exact_spearman(store, columns)
                pd.testing.assert_frame_equal(actual, frame[columns].corr(method="spearman"), atol=1e-14, rtol=1e-14)
                pair = pairs[(pairs.column_a == "price_usd") & (pairs.column_b == "prop_review_score")].iloc[0]
                self.assertEqual(pair.full_pairwise_nonnull_n, 10)

                def savefig(name, fig):
                    output = Path(folder) / f"{name}.png"
                    fig.savefig(output)
                    plt.close(fig)
                    return output

                report = SimpleNamespace(savefig=savefig, figure_notes={})
                _, rates, counts, correlation = full_missing_diagnostics(report, result)
                selected = list(rates.columns.drop("booking_bool"))
                expected_rates = frame[selected].isna().groupby(frame.booking_bool).mean() * 100
                pd.testing.assert_frame_equal(rates.set_index("booking_bool"), expected_rates, check_index_type=False)
                expected_corr = frame[selected].isna().corr()
                pd.testing.assert_frame_equal(correlation.set_index("column"), expected_corr, check_names=False, atol=1e-14, rtol=1e-14)
                self.assertEqual(counts.full_group_n.sum(), len(frame))
            self.assertFalse(cache_path.exists(), "Working raw-column cache must be deleted")


if __name__ == "__main__":
    unittest.main()
