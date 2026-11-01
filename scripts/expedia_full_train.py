"""Exact Expedia train diagnostics with temporary, disk-backed raw columns.

The arrays are an EDA working cache, deleted after report generation. They retain
every parsed train row, including missing and extreme values; no model is fitted.
"""
from __future__ import annotations

import gc
import math
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import numpy as np
import pandas as pd


CORRELATION_COLUMNS = [
    "price_usd", "prop_starrating", "prop_review_score", "prop_location_score1",
    "prop_location_score2", "prop_log_historical_price", "srch_length_of_stay",
    "srch_booking_window", "srch_room_count",
]


def progress(message):
    print(message, flush=True)
    if sys.stdout is not sys.__stdout__:
        print(message, file=sys.__stdout__, flush=True)


@contextmanager
def working_directory():
    # Inherit normal temp-directory access on Windows. Python 3.14's private
    # mkdtemp ACL can prevent the restricted execution identity reopening files.
    directory = Path(gettempdir()) / f"expedia-full-train-{uuid4().hex}"
    directory.mkdir()
    try:
        yield directory
    finally:
        # Only this invocation's direct working files exist here; no recursion.
        for path in directory.iterdir():
            path.unlink()
        directory.rmdir()


class TrainColumns:
    """Context-managed, exact raw-column cache; bounded working RAM."""

    def __init__(self, rows, numeric_columns):
        self.rows = int(rows)
        self.numeric_columns = list(numeric_columns)
        self.arrays = {}
        self.offset = 0
        self.schema = None
        self.temporary = working_directory()

    def __enter__(self):
        self.directory = self.temporary.__enter__()
        for column in self.numeric_columns + ["click_bool", "booking_bool"]:
            dtype = np.uint8 if column.endswith("_bool") else np.float64
            self.arrays[column] = np.lib.format.open_memmap(
                self.directory / f"{column}.npy", mode="w+",
                dtype=dtype, shape=(self.rows,),
            )
        return self

    def append(self, chunk):
        if self.schema is None:
            self.schema = list(chunk.columns)
            self.arrays["_missing_bits"] = np.lib.format.open_memmap(
                self.directory / "missing_bits.npy", mode="w+",
                dtype=np.uint8, shape=(self.rows, math.ceil(len(self.schema) / 8)),
            )
        if list(chunk.columns) != self.schema:
            raise ValueError("Expedia schema changed between CSV chunks")
        end = self.offset + len(chunk)
        if end > self.rows:
            raise ValueError("CSV parser row count exceeds the raw-file inventory")
        for column in self.numeric_columns + ["click_bool", "booking_bool"]:
            self.arrays[column][self.offset:end] = chunk[column].to_numpy()
        self.arrays["_missing_bits"][self.offset:end] = np.packbits(
            chunk.isna().to_numpy(), axis=1, bitorder="little",
        )
        self.offset = end

    def finish(self):
        if self.offset != self.rows:
            raise ValueError(f"Incomplete train cache: {self.offset} != {self.rows}")
        for array in self.arrays.values():
            array.flush()

    def frame(self, columns):
        # Each Series views a separate memmap; no full dense matrix is built.
        return pd.DataFrame({c: self.arrays[c] for c in columns}, copy=False)

    def __exit__(self, *_):
        for array in self.arrays.values():
            array._mmap.close()
        self.arrays.clear()
        gc.collect()
        self.temporary.__exit__(None, None, None)


def full_numeric_statistics(store, basic):
    """Linear quantiles and pandas unbiased sample skewness, all non-NA rows."""
    result = basic.copy()
    probabilities = [.01, .25, .5, .75, .95, .99]
    quantiles = []
    skewness = []
    for column in result.column:
        values = pd.Series(store.arrays[column], copy=False)
        quantiles.append(values.quantile(probabilities, interpolation="linear").to_numpy())
        skewness.append(float(values.skew()))
        progress(f"Full train quantiles/skewness: {column}")
    for i, suffix in enumerate(["p1", "p25", "p50", "p75", "p95", "p99"]):
        result[f"full_{suffix}"] = [row[i] for row in quantiles]
    result["full_skewness"] = skewness
    return result


def exact_spearman(store, columns=CORRELATION_COLUMNS):
    """Rank each pair after its own NA removal, including average ranks for ties.

    Ranking the full columns once then dropping NA would produce the wrong
    pairwise-complete Spearman coefficient when missing patterns differ.
    """
    from scipy.stats import rankdata

    matrix = pd.DataFrame(np.nan, index=columns, columns=columns)
    pairs = []
    for i, a in enumerate(columns):
        for b in columns[i:]:
            x, y = store.arrays[a], store.arrays[b]
            valid = ~np.isnan(x) & ~np.isnan(y)
            n = int(valid.sum())
            rho = np.nan
            if n > 1:
                ra = rankdata(x[valid], method="average")
                if a == b:
                    rho = 1.0 if np.ptp(ra) else np.nan
                else:
                    rb = rankdata(y[valid], method="average")
                    ra -= ra.mean()
                    rb -= rb.mean()
                    denominator = math.sqrt(float((ra * ra).sum()) * float((rb * rb).sum()))
                    if denominator:
                        rho = float((ra * rb).sum()) / denominator
                    del rb
                del ra
            matrix.loc[a, b] = matrix.loc[b, a] = rho
            if a != b:
                pairs.append([a, b, n, rho])
                progress(f"Full train Spearman: {a} / {b}; n={n:,}")
            del valid
    return matrix, pd.DataFrame(pairs, columns=[
        "column_a", "column_b", "full_pairwise_nonnull_n", "full_spearman_rho",
    ])


def full_missing_diagnostics(report, train, seed=42):
    """All-row missing rates by label and exact binary-indicator correlations."""
    import matplotlib.pyplot as plt

    store = train["store"]
    columns = list(train["missing"].sort_values(ascending=False).head(12).index)
    positions = [store.schema.index(c) for c in columns]
    groups = np.zeros((2, len(columns)), dtype=np.int64)
    denominators = np.zeros(2, dtype=np.int64)
    joint = np.zeros((len(columns), len(columns)), dtype=np.int64)
    for start in range(0, store.rows, 250_000):
        stop = min(start + 250_000, store.rows)
        mask = np.unpackbits(store.arrays["_missing_bits"][start:stop],
                             axis=1, count=len(store.schema), bitorder="little")[:, positions].astype(bool)
        labels = store.arrays["booking_bool"][start:stop]
        for label in [0, 1]:
            selection = labels == label
            denominators[label] += int(selection.sum())
            groups[label] += mask[selection].sum(axis=0)
        for i in range(len(columns)):
            for j in range(i, len(columns)):
                joint[i, j] += np.count_nonzero(mask[:, i] & mask[:, j])
    joint = joint + joint.T - np.diag(np.diag(joint))
    counts = np.diag(joint).astype(float)
    if not np.array_equal(counts, train["missing"].loc[columns].to_numpy()):
        raise AssertionError("Missing-mask counts disagree with full CSV scan")
    if not np.array_equal(groups.sum(axis=0), counts):
        raise AssertionError("Missing group counts do not reconcile")
    variances = counts * (store.rows - counts)
    divisor = np.sqrt(np.outer(variances, variances))
    correlation = np.divide(joint * float(store.rows) - np.outer(counts, counts),
                            divisor, out=np.full_like(divisor, np.nan), where=divisor != 0)
    rates = pd.DataFrame(groups / denominators[:, None] * 100,
                         index=pd.Index([0, 1], name="booking_bool"), columns=columns)
    display_ids = np.random.default_rng(seed).choice(store.rows, min(300, store.rows), replace=False)
    display = pd.DataFrame(np.unpackbits(store.arrays["_missing_bits"][display_ids],
                           axis=1, count=len(store.schema), bitorder="little")[:, positions], columns=columns)
    display = display.sort_values(columns, kind="stable")
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1.3, 1]})
    axes[0].imshow(display, aspect="auto", interpolation="nearest", cmap="Blues", vmin=0, vmax=1)
    axes[0].set(title=f"Missingness: {len(display)} displayed train rows", ylabel="Display only; sorted by pattern")
    im = axes[1].imshow(rates, aspect="auto", vmin=0, vmax=100, cmap="Blues")
    axes[1].set(title="Missing by booking: all train rows (%)", ylabel="booking_bool")
    axes[1].set_yticks([0, 1], labels=["0", "1"])
    for ax in axes:
        ax.set_xticks(range(len(columns)), labels=columns, rotation=65, ha="right")
    fig.colorbar(im, ax=axes[1], label="Missing (%)", fraction=.035, pad=.03)
    fig.tight_layout()
    path = report.savefig("missing_patterns", fig)
    differences = rates.max() - rates.min()
    largest = differences.idxmax()
    note = (
        f"Nhận xét: {columns[0]} thiếu {counts[0] / store.rows * 100:.2f}% trên toàn bộ train; "
        f"chênh lệch missing lớn nhất giữa hai nhãn là {differences[largest]:.4f} điểm phần trăm "
        f"ở {largest}. Bảng tỷ lệ, số đếm và tương quan cờ thiếu dùng đủ {store.rows:,} dòng. "
        f"Chỉ hình pattern bên trái hiển thị 300 dòng, seed={seed}, sắp theo pattern, không theo thời gian. "
        "Ô xanh là NA. Không suy cơ chế MCAR/MAR/MNAR từ hình; cờ thiếu gross booking vẫn tiết lộ kết quả."
    )
    report.figure_notes[path.name] = note
    count_table = pd.DataFrame(groups, index=rates.index, columns=columns).reset_index()
    count_table.insert(1, "full_group_n", denominators)
    return (path, rates.reset_index(), count_table,
            pd.DataFrame(correlation, index=columns, columns=columns).reset_index(names="column"))


def correlation_plot(report, train, seed=42):
    import matplotlib.pyplot as plt

    corr = train["correlation"]
    columns = list(corr.columns)
    store = train["store"]
    x, y = "prop_starrating", "price_usd"
    valid = np.flatnonzero(~np.isnan(store.arrays[x]) & ~np.isnan(store.arrays[y]))
    selected = np.random.default_rng(seed).choice(valid, min(4000, len(valid)), replace=False)
    del valid
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={"width_ratios": [1.2, 1]})
    im = axes[0].imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
    axes[0].set(title="Spearman: all train, pairwise complete")
    axes[0].set_xticks(range(len(columns)), labels=columns, rotation=65, ha="right", fontsize=8)
    axes[0].set_yticks(range(len(columns)), labels=columns, fontsize=8)
    fig.colorbar(im, ax=axes[0], label="Spearman rho", fraction=.03, pad=.03)
    axes[1].scatter(store.arrays[x][selected], store.arrays[y][selected], s=7, alpha=.15, color="#245D80", rasterized=True)
    axes[1].set(xlabel="prop_starrating (stars)", ylabel="price_usd (USD; symlog)",
                title=f"Display only: {len(selected):,} train pairs")
    axes[1].set_yscale("symlog", linthresh=1)
    fig.tight_layout()
    path = report.savefig("multivariate", fig)
    strongest = train["correlation_pairs"].dropna().sort_values("full_spearman_rho", key=abs).iloc[-1]
    report.figure_notes[path.name] = (
        f"Nhận xét: Spearman giá–hạng sao trên toàn bộ cặp hợp lệ của train là {corr.loc[x, y]:.3f}; "
        f"cặp có |rho| lớn nhất trong ma trận là {strongest.column_a}–{strongest.column_b} "
        f"(rho={strongest.full_spearman_rho:.3f}, n={int(strongest.full_pairwise_nonnull_n):,}). "
        "Ma trận tính lại thứ hạng trên các dòng không thiếu của từng cặp; số dòng từng cặp ở phụ lục. "
        f"Scatter chỉ hiển thị tối đa 4.000 điểm, seed={seed}, trục y symlog để đọc đuôi dài. "
        "Không biến đổi raw, không chọn feature hoặc kết luận nhân quả/đa cộng tuyến từ tương quan."
    )
    return path
