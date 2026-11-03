"""Exercise new dataset schemas, missing labels and standalone CSV notebooks."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

import numpy as np
import pandas as pd
import nbformat

from scripts import eda_all_datasets as eda


class ReusableEDATests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).resolve().parents[1]
        self.folder = self.workspace / (".eda_reuse_test_" + uuid4().hex)
        self.folder.mkdir()

    def tearDown(self):
        self.assertEqual(self.folder.resolve().parent, self.workspace)
        shutil.rmtree(self.folder)

    def test_report_new_name_has_no_legacy_preparation_and_supports_hooks(self):
        report = eda.Report("NEW_SCHEMA", "New data", str(self.folder))
        report.add("overview", "Overview", "Different schema", [("Counts", pd.DataFrame({"n": [3]}))])
        report.facts["rows"] = np.int64(3)
        with patch.object(eda, "hotel_expedia_prepare_publication", side_effect=AssertionError("legacy called")), \
             patch.object(eda, "airbnb_prepare_publication", side_effect=AssertionError("legacy called")):
            report.publish()
            report.publish()
        self.assertEqual(sum(s["key"] == "reproducibility" for s in report.sections), 1)
        metadata = json.loads((report.directory / "analysis_metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["facts"]["rows"], 3)
        self.assertNotIn("research_script_sha256", metadata)

        calls = []
        report.prepare = lambda r: calls.append(r.dataset)
        report.publish()
        report.publish(prepare=lambda r: calls.append("override"))
        self.assertEqual(calls, ["NEW_SCHEMA", "override"])

    def test_partial_dictionary_and_label_denominators(self):
        frame = pd.DataFrame({"channel": ["a", "a", "a", "b"],
                              "responded": pd.Series([1, None, 0, None], dtype="Int64")})
        dictionary = eda.metadata_table(frame, {"channel": ("Channel", "Known at signup")}).set_index("column")
        self.assertEqual(dictionary.loc["responded", "meaning"], "")
        rates = eda.rate_table(frame, "channel", "responded").set_index("channel")
        self.assertEqual(rates.loc["a", "n"], 2)
        self.assertEqual(rates.loc["a", "rate_pct"], 50)
        self.assertEqual(rates.loc["b", "n"], 0)
        self.assertTrue(pd.isna(rates.loc["b", "ci95_low_pct"]))
        with self.assertRaisesRegex(ValueError, "0/1"):
            eda.rate_table(pd.DataFrame({"g": ["x"], "target": [2]}), "g", "target")

    def test_three_different_dataframes_can_publish_without_raw_files(self):
        labelled = pd.DataFrame({"amount": [1., None, 4.], "segment": ["x", "y", "x"], "converted": [1, 0, None]})
        before = labelled.copy(deep=True)
        reports = [
            eda.dataframe_report(labelled, "SALES", self.folder, target="converted", group_columns=["segment"]),
            eda.dataframe_report(pd.DataFrame({"sensor": [2., 3., 4.]}), "SENSORS", self.folder),
            eda.dataframe_report(pd.DataFrame({"choice": ["yes", None, "no"]}), "SURVEY", self.folder),
        ]
        for report in reports:
            self.assertTrue((report.directory / "README.md").is_file())
            self.assertIsNone(report.prepare)
        self.assertEqual(reports[0].facts["labelled_rows"], 2)
        self.assertNotIn("target", [s["key"] for s in reports[1].sections])
        pd.testing.assert_frame_equal(labelled, before)

    def test_disk_cache_custom_nullable_label_and_unlabelled_diagnostics(self):
        frame = pd.DataFrame({"value/a": [1., None, 3., 4., 5.], "other": [2., 2., None, 4., 8.],
                              "responded": pd.Series([0, 1, None, 1, 0], dtype="Int64")})
        with eda.TrainColumns(len(frame), ["value/a", "other"], label_columns=["responded"]) as store:
            cache = store.directory
            store.append(frame.iloc[:2])
            store.append(frame.iloc[2:])
            store.finish()
            self.assertTrue(np.isnan(store.arrays["responded"][2]))
            correlation, _ = eda.exact_spearman(store)
            pd.testing.assert_frame_equal(correlation, frame[["value/a", "other"]].corr(method="spearman"))
            train = {"store": store, "missing": frame.isna().sum()}
            report = eda.Report("RESPONSES", "Missing", self.folder)
            _, rates, counts, corr = eda.full_missing_diagnostics(report, train, label_column="responded")
            self.assertEqual(counts.full_group_n.sum(), len(frame))
            self.assertEqual(counts.set_index("responded").loc["<MISSING>", "full_group_n"], 1)
            selected = list(rates.columns.drop("responded"))
            expected_group = frame.responded.astype(object).where(frame.responded.notna(), "<MISSING>")
            expected = frame[selected].isna().groupby(expected_group).mean() * 100
            pd.testing.assert_frame_equal(rates.set_index("responded"), expected, check_index_type=False)
            pd.testing.assert_frame_equal(corr.set_index("column"), frame[selected].isna().corr(), check_names=False)
        self.assertFalse(cache.exists())
        with eda.TrainColumns(len(frame), ["other"], label_columns=()) as store:
            store.append(frame[["other"]])
            store.finish()
            train = {"store": store, "missing": frame[["other"]].isna().sum()}
            _, _, counts, _ = eda.full_missing_diagnostics(report, train, label_column=None)
            self.assertEqual(counts.full_group_n.tolist(), [len(frame)])

    def test_missing_axes_and_categorical_drift_have_no_dataset_dispatch(self):
        frame = pd.DataFrame({"feature": [1., None, 2.], "group": ["a", "b", "b"]})
        report = eda.Report("CUSTOM", "Custom", self.folder)
        saved = {}
        original_savefig = report.savefig
        def savefig(name, fig):
            saved["xlabel"] = fig.axes[0].get_xlabel()
            saved["ylabel"] = fig.axes[1].get_ylabel()
            return original_savefig(name, fig)
        report.savefig = savefig
        eda.missing_plot(report, frame, ["feature"], frame.group, "group", "all rows",
                         axis_labels={"xlabel": "Measurements", "group_ylabel": "Cohort"})
        self.assertEqual(saved, {"xlabel": "Measurements", "ylabel": "Cohort"})
        train = pd.DataFrame({"cat": pd.Categorical(["a", None])})
        test = pd.DataFrame({"cat": pd.Categorical(["b", None])})
        self.assertEqual(eda.drift_table(train, test, ["cat"]).iloc[0].total_variation_0_1, .5)

    def test_custom_builder_registry(self):
        with patch.dict(eda.REPORTS), patch.dict(eda.REPORT_LAYOUTS), \
             patch.dict(eda.REPORT_CONFIGS), patch.dict(eda.REPORT_NOTEBOOK_SETUP):
            eda.register_report("EXPERIMENT", lambda root: eda.dataframe_report(
                pd.DataFrame({"value": [1, 2]}), "EXPERIMENT", root, plots=False))
            report = eda.build_report("EXPERIMENT", self.folder)
            self.assertEqual(report.facts["rows"], 2)
            with self.assertRaisesRegex(ValueError, "notebook_setup"):
                eda.make_notebook(self.folder, "EXPERIMENT")
            with self.assertRaisesRegex(ValueError, "Unknown dataset"):
                eda.build_report("MISSING", self.folder)

    def test_cli_three_new_datasets_and_notebook_registration_roundtrip(self):
        script = self.folder / "scripts" / "eda_all_datasets.py"
        script.parent.mkdir()
        shutil.copy2(Path(eda.__file__), script)
        datasets = {
            "NEW_A": (pd.DataFrame({"amount": [1., 2., 3.], "bought": [1, 0, None]}), {"target": "bought"}),
            "NEW_B": (pd.DataFrame({"temperature": [2., None, 4.]}), {}),
            "NEW_C": (pd.DataFrame({"answer": ["yes", None, "no"]}), {}),
        }
        config = {}
        for name, (frame, options) in datasets.items():
            raw = self.folder / "data" / "raw" / name
            raw.mkdir(parents=True)
            frame.to_csv(raw / "train.csv", index=False)
            config[name] = {"file": "train.csv", "plots": False, **options}
        config_file = self.folder / "eda_config.json"
        config_file.write_text(json.dumps(config), encoding="utf-8")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run([sys.executable, str(script), "--root", str(self.folder), "--config", str(config_file)],
                                cwd=self.folder, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual({p.name for p in (self.folder / "reports").iterdir()}, set(datasets))
        for name in datasets:
            notebook = self.folder / "notebooks" / name / f"{name.lower()}_descriptive_report.ipynb"
            nb = nbformat.read(notebook, as_version=4)
            nbformat.validate(nb)
            self.assertIn("eda.register_csv_report", nb.cells[1].source)
            for cell in nb.cells:
                if cell.cell_type == "code":
                    self.assertTrue(cell.execution_count)
                    self.assertFalse([o for o in cell.outputs if o.output_type == "error"])
            meta = json.loads((self.folder / "reports" / name / "analysis_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["facts"]["rows"], 3)


if __name__ == "__main__":
    unittest.main()
