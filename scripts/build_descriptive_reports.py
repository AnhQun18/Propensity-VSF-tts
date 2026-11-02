"""Rebuild descriptive EDA reports; no feature dataset or model is produced.

Run from the project root:
    python scripts/build_descriptive_reports.py
    python scripts/build_descriptive_reports.py --dataset HOTEL

The generated notebooks call the functions below against raw CSVs, retain their
executed outputs under notebooks/; Markdown reports and figures live under reports/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CHUNK_SIZE = 250_000
COLORS = ["#245D80", "#C76A37", "#468477", "#8A6598"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 120, "savefig.dpi": 150})


def pct(value):
    return f"{100 * value:.2f}%"


def count(value):
    return f"{int(value):,}"


def md_table(df):
    def fmt(v, column):
        if pd.isna(v):
            return "—"
        if "year" in str(column).lower() and isinstance(v, (int, float, np.integer, np.floating)) and float(v).is_integer():
            return str(int(v))
        if isinstance(v, (float, np.floating)):
            return f"{v:,.4f}".rstrip("0").rstrip(".")
        if isinstance(v, (int, np.integer)):
            return f"{v:,}"
        return str(v).replace("|", "\\|").replace("\n", " ")
    headers = [str(c) for c in df.columns]
    rows = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    rows += ["| " + " | ".join(fmt(v, c) for c, v in zip(df.columns, row)) + " |" for row in df.itertuples(index=False, name=None)]
    return "\n".join(rows)


def wilson(successes, n):
    n = np.asarray(n, dtype=float)
    p = np.asarray(successes, dtype=float) / n
    z = 1.959963984540054
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    half = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return (center-half)*100, (center+half)*100


def rate_table(df, group, target, limit=None, ci=True):
    key = df[group].astype("object").where(df[group].notna(), "<MISSING>")
    out = df.groupby(key, observed=True, dropna=False)[target].agg(n="size", positive="sum")
    out = out.sort_values("n", ascending=False)
    out["rate_pct"] = out.positive / out.n * 100
    if ci:
        out["ci95_low_pct"], out["ci95_high_pct"] = wilson(out.positive, out.n)
    out["n_under_100"] = out.n < 100
    out.index.name = group
    return out.head(limit).reset_index() if limit else out.reset_index()


def numeric_table(df, cols):
    out = df[cols].describe(percentiles=[.01, .25, .5, .75, .95, .99]).T
    out["missing_pct"] = df[cols].isna().mean()*100
    out["skewness"] = df[cols].skew()
    return out.rename_axis("column").reset_index()


def categorical_table(df, cols, top=8):
    rows = []
    for col in cols:
        s = df[col].astype("object").where(df[col].notna(), "<MISSING>")
        for k, v in s.value_counts(dropna=False).head(top).items():
            rows.append([col, str(k), int(v), v/len(df)*100])
    return pd.DataFrame(rows, columns=["column", "value", "n", "pct_all_rows"])


def drift_table(train, test, cols):
    """Total variation, including missing; no fitted transformations."""
    rows = []
    for col in cols:
        a = train[col].fillna("<MISSING>").astype(str).value_counts(normalize=True)
        b = test[col].fillna("<MISSING>").astype(str).value_counts(normalize=True)
        idx = a.index.union(b.index)
        tv = (a.reindex(idx, fill_value=0)-b.reindex(idx, fill_value=0)).abs().sum()/2
        rows.append([col, tv, len(b.index.difference(a.index)), train[col].isna().mean()*100,
                     test[col].isna().mean()*100])
    return pd.DataFrame(rows, columns=["column", "total_variation_0_1", "test_only_categories",
                                        "train_missing_pct", "test_missing_pct"]).sort_values("total_variation_0_1", ascending=False)


def metadata_table(df, meanings):
    return pd.DataFrame([[c, str(df[c].dtype), int(df[c].nunique(dropna=True)),
                          int(df[c].isna().sum()), df[c].isna().mean()*100,
                          *meanings[c]] for c in df.columns],
                        columns=["column", "pandas_dtype", "distinct_nonnull", "missing_n",
                                 "missing_pct", "meaning", "role_or_caution"])


@dataclass
class Report:
    dataset: str
    title: str
    root: Path
    sections: list = field(default_factory=list)
    facts: dict = field(default_factory=dict)
    figure_notes: dict = field(default_factory=dict)

    @property
    def directory(self):
        p = self.root / "reports" / self.dataset
        p.mkdir(parents=True, exist_ok=True)
        return p

    def add(self, key, title, text, tables=None, figures=None):
        self.sections.append(dict(key=key, title=title, text=text.strip(),
                                  tables=tables or [], figures=figures or []))

    def savefig(self, name, fig):
        p = self.directory / "figures" / f"{name}.png"
        p.parent.mkdir(exist_ok=True)
        fig.savefig(p, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return p

    def publish(self):
        environment = pd.DataFrame([["Python", platform.python_version()], ["pandas", pd.__version__],
                                    ["numpy", np.__version__], ["matplotlib", matplotlib.__version__],
                                    ["Phương pháp", "Thống kê mô tả, không mô hình"],
                                    ["Chunk CSV lớn", str(CHUNK_SIZE)]], columns=["component", "value"])
        if self.dataset == "AIRBNB":
            import scipy
            import nbformat
            import IPython
            environment = pd.concat([environment, pd.DataFrame(
                [["scipy", scipy.__version__], ["nbformat", nbformat.__version__], ["IPython", IPython.__version__]],
                columns=environment.columns)], ignore_index=True)
        sampling_note = ("Expedia tính thống kê trên toàn bộ train, gồm quantile tuyến tính, skewness không chệch theo pandas và Spearman xếp hạng trung bình cho ties, loại NA theo từng cặp. Chỉ scatter (tối đa 4.000 điểm) và hình pattern missing (300 dòng) lấy mẫu hiển thị với numpy default_rng, seed=42; các bảng và heatmap tổng hợp dùng toàn bộ train. Cột raw được đệm tạm trên đĩa để giới hạn RAM và xóa sau khi xuất báo cáo; không tạo tập processed. Test chỉ là đối chiếu schema/chất lượng và các phân phối tổng hợp, không dùng tính thống kê train. " if self.dataset == "EXPEDIA" else "Hình lấy mẫu hiển thị dùng seed=42. ")
        self.add("reproducibility", "Tái lập và kiểm soát phạm vi", "Chạy notebook theo thứ tự từ đầu, hoặc chạy `python scripts/build_descriptive_reports.py --dataset " + self.dataset + "` tại thư mục gốc. Script chỉ đọc CSV raw, viết báo cáo/biểu đồ và lưu notebook trong notebooks/; không sửa raw, không ghi data/processed, không gọi pipeline huấn luyện. Các thời điểm phân tích dùng Asia/Ho_Chi_Minh. SHA-256 ở danh mục file nhận diện nguồn; số dòng theo CSV parser được đối chiếu với data_lines của file chính. Ngày tải raw chưa được ghi nhận; không suy từ mtime/ctime. " + sampling_note + "Script thực thi các cell bằng IPython trong cùng tiến trình và lưu output thật vào notebook; không khởi tạo kernel mạng. Phụ thuộc dựng báo cáo gồm pandas, numpy, scipy, matplotlib, nbformat và IPython; có thể mở notebook bằng Jupyter để Run All.", [("Môi trường thực thi", environment)])
        if self.dataset == "AIRBNB":
            from scripts.airbnb_deep_dive import reproducibility_section
            self.sections[-1] = reproducibility_section(self, environment)
        parts = [f"# {self.title}",
                 "> Phạm vi: EDA trên dữ liệu gốc. Không làm sạch/thay thế dữ liệu, không tạo tập feature, không huấn luyện mô hình.",
                 f"Ngày phân tích: {datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date().isoformat()}. Đây không phải ngày thu thập dữ liệu."]
        def render(s, level=2):
            parts.append(f"{'#'*level} {s['title']}")
            if s["text"]: parts.append(s["text"])
            for label, table in s["tables"]:
                parts.extend([f"**{label}**", md_table(table)])
            for p in s["figures"]:
                parts.append(f"![{p.stem.replace('_', ' ')}](figures/{p.name})")
                if p.name not in self.figure_notes:
                    raise ValueError(f"Chart lacks an interpretation: {p}")
                parts.append(self.figure_notes[p.name])
            for block in s.get("blocks",[]): render(block,level+1)
        for s in self.sections: render(s)
        (self.directory / "README.md").write_text("\n\n".join(parts)+"\n", encoding="utf-8")
        (self.directory / "analysis_metadata.json").write_text(json.dumps({
            "dataset": self.dataset, "facts": self.facts,
            "analysis_date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "diagnostics_script_sha256": hashlib.sha256((self.root / "scripts/eda_diagnostics.py").read_bytes()).hexdigest(),
            **({"airbnb_deep_dive_script_sha256": hashlib.sha256((self.root / "scripts/airbnb_deep_dive.py").read_bytes()).hexdigest()} if self.dataset == "AIRBNB" else {}),
            **({"full_train_script_sha256": hashlib.sha256((self.root / "scripts/expedia_full_train.py").read_bytes()).hexdigest()} if self.dataset == "EXPEDIA" else {}),
            "environment": dict(environment.itertuples(index=False, name=None)),
            "section_keys": [s["key"] for s in self.sections],
            "download_date": "not_recorded" if self.dataset == "AIRBNB" else None,
            "download_date_note": "Người cung cấp xác nhận không lưu ngày tải hoặc mã phiên bản Kaggle, 2026-11-02; định danh bản local bằng SHA-256." if self.dataset == "AIRBNB" else "Chưa được ghi nhận; không suy từ mtime/ctime.",
            "figure_seed": 42,
            "figure_notes": self.figure_notes,
        }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return self


def show_section(report, key):
    from IPython.display import Markdown, display, Image
    section = next(s for s in report.sections if s["key"] == key)
    def show(s, nested=False):
        if nested: display(Markdown(f"### {s['title']}"))
        if s["text"]: display(Markdown(s["text"]))
        for label, table in s["tables"]:
            display(Markdown(f"**{label}**"))
            with pd.option_context("display.max_rows", max(100, len(table)), "display.max_columns", 30,
                                   "display.float_format", lambda x: f"{x:,.4f}"):
                display(table)
        for p in s["figures"]:
            display(Image(filename=str(p)))
            display(Markdown(report.figure_notes[p.name]))
        for block in s.get("blocks",[]): show(block,True)
    show(section)


def manifest(root, dataset):
    rows = []
    for p in sorted((root/"data"/"raw"/dataset).glob("*.csv")):
        h = hashlib.sha256()
        lines = 0
        tail = b"\n"
        with p.open("rb") as f:
            header = f.readline()
            h.update(header)
            while chunk := f.read(8*1024*1024):
                h.update(chunk)
                lines += chunk.count(b"\n")
                tail = chunk[-1:]
        rows.append([p.name, lines+(tail != b"\n"), len(header.decode("utf-8-sig").strip().split(",")),
                     p.stat().st_size, h.hexdigest()])
    return pd.DataFrame(rows, columns=["file", "data_lines", "columns", "bytes", "sha256"])


HOTEL_MEANINGS = {
    "hotel": ("City Hotel / Resort Hotel", "Phân khúc; chỉ hai cơ sở gốc, không đại diện toàn ngành"),
    "is_canceled": ("Nhãn kết quả booking, 0/1", "Target; dữ liệu hiện tại gộp Canceled và No-Show vào 1"),
    "lead_time": ("Số ngày từ lúc nhập booking đến ngày đến", "Kiểm tra mốc dự đoán và lịch sử thay đổi ngày đến"),
    "arrival_date_year": ("Năm đến dự kiến", "Thời gian; không coi là đại lượng liên tục thông thường"),
    "arrival_date_month": ("Tháng đến dự kiến", "Thời gian dạng tên tháng"),
    "arrival_date_week_number": ("Tuần của ngày đến", "Thời gian, chồng lặp thông tin với ngày/tháng"),
    "arrival_date_day_of_month": ("Ngày trong tháng của ngày đến", "Thời gian"),
    "stays_in_weekend_nights": ("Số đêm cuối tuần đặt/lưu trú", "Số đếm; xác minh snapshot"),
    "stays_in_week_nights": ("Số đêm ngày thường đặt/lưu trú", "Số đếm; xác minh snapshot"),
    "adults": ("Số người lớn", "Kiểm tra 0 và số lượng lớn"),
    "children": ("Số trẻ em", "Có missing; không mặc định missing = 0"),
    "babies": ("Số em bé", "Số đếm"),
    "meal": ("Gói bữa ăn", "Undefined/SC có thể có nghĩa không có gói ăn"),
    "country": ("Quốc gia nguồn gốc khách", "Mã phân loại; có thể cập nhật gần check-in"),
    "market_segment": ("Phân khúc thị trường", "Biến phân loại"),
    "distribution_channel": ("Kênh phân phối", "Biến phân loại; có liên hệ market_segment"),
    "is_repeated_guest": ("Khách quay lại, 0/1", "Đã tồn tại trong raw; không tạo lại feature"),
    "previous_cancellations": ("Số booking hủy trước booking hiện tại", "Lịch sử; cần xác minh cách chốt thời gian"),
    "previous_bookings_not_canceled": ("Số booking trước không hủy", "Lịch sử; cần xác minh cách chốt thời gian"),
    "reserved_room_type": ("Mã loại phòng đã đặt", "Biến phân loại"),
    "assigned_room_type": ("Mã loại phòng được phân", "Có thể cập nhật sau đặt; chưa chứng minh có sẵn tại t0"),
    "booking_changes": ("Số lần sửa booking đến check-in/hủy", "Biến tích lũy; nguy cơ dùng thông tin tương lai"),
    "deposit_type": ("Trạng thái đặt cọc từ thanh toán", "Không mặc định đồng nghĩa chính sách đã biết lúc tạo booking"),
    "agent": ("ID đại lý", "Phân loại; NULL có thể là không áp dụng, không phải số liên tục"),
    "company": ("ID công ty/thực thể trả tiền", "Phân loại; NULL có thể là không áp dụng"),
    "days_in_waiting_list": ("Số ngày chờ trước xác nhận", "Chỉ biết đầy đủ khi kết thúc chờ"),
    "customer_type": ("Contract / Group / Transient / Transient-Party", "Biến phân loại"),
    "adr": ("Average Daily Rate, tiền/đêm", "Theo nguồn là tổng giao dịch lưu trú / số đêm; xác minh thời điểm và đơn vị"),
    "required_car_parking_spaces": ("Số chỗ đỗ xe yêu cầu", "Có thể cập nhật theo booking"),
    "total_of_special_requests": ("Số yêu cầu đặc biệt", "Có thể cập nhật theo booking"),
    "reservation_status": ("Trạng thái cuối: Canceled / Check-Out / No-Show", "Kết quả sau sự kiện; rò rỉ nhãn"),
    "reservation_status_date": ("Ngày thiết lập trạng thái cuối", "Kết quả sau sự kiện; không dùng làm đầu vào dự đoán"),
}


def hotel_report(root):
    r = Report("HOTEL", "HOTEL — Hiểu dữ liệu đặt phòng và kết quả hủy/no-show", root)
    df = pd.read_csv(root/"data/raw/HOTEL/hotel_bookings.csv")
    inventory = manifest(root, "HOTEL")
    n = len(df)
    y = df.is_canceled
    duplicate_n = int(df.duplicated().sum())
    unique = df.drop_duplicates()
    # Temporary calendar and group labels below are for EDA only.
    arrival = pd.to_datetime(df.arrival_date_year.astype(str)+"-"+df.arrival_date_month+"-"+df.arrival_date_day_of_month.astype(str), format="%Y-%B-%d", errors="coerce")
    r.facts = dict(rows=n, columns=len(df.columns), positive=int(y.sum()), rate=float(y.mean()),
                   duplicates=duplicate_n, deduplicated_rows=len(unique), deduplicated_rate=float(unique.is_canceled.mean()))
    r.add("scope", "1. Bối cảnh, quần thể và câu hỏi phân tích", f"""
Dữ liệu hiện có gồm **{count(n)} booking, 32 cột**, từ City Hotel và Resort Hotel. Mỗi dòng là một booking, không phải một khách hàng duy nhất. Không có booking ID hoặc customer ID để xác nhận danh tính, lịch sử khách hoặc nguyên nhân các dòng trùng.

**Bài toán phù hợp:** xác suất một booking có kết quả hủy/no-show. Không đồng nhất việc hủy một booking với customer churn. Mốc dự đoán (lúc tạo booking hay trước ngày đến) và tập booking còn có thể can thiệp chưa được xác lập; báo cáo chỉ đánh giá tính phù hợp dữ liệu, không ước lượng xác suất bằng mô hình.

Các câu hỏi EDA: nhãn thực sự gồm hành vi nào; khác biệt giữa hai khách sạn; mối liên hệ giữa nhãn và kênh/lead time; tác động của trùng lặp; độ phủ thời gian; biến nào tiết lộ kết quả hoặc chưa chứng minh có sẵn tại thời điểm dự đoán.

Nguồn nghiệp vụ: [Antonio, de Almeida & Nunes — Hotel booking demand datasets](https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/). Nguồn mô tả hai khách sạn tại Bồ Đào Nha và mốc trích xuất gắn với ngày trước ngày đến. Bản CSV trong dự án có thêm cột `hotel` để phân biệt hai cơ sở. Không suy rộng trực tiếp sang toàn ngành hoặc thị trường Việt Nam.
""", [("Danh mục file gốc; data_lines đếm dòng sau header, đối chiếu số dòng pandas", inventory)])
    r.add("dictionary", "2. Từ điển dữ liệu và kiểu dữ liệu thực tế", "Kiểu pandas không đồng nghĩa vai trò thống kê. `agent` và `company` được đọc như số nhưng là ID phân loại. Các cột lịch không phải các phép đo liên tục độc lập. Bảng dưới kiểm kê đủ 32 cột trên toàn bộ dữ liệu.", [("Schema, độ đa dạng và missing", metadata_table(df, HOTEL_MEANINGS))])
    zero_guests = df[["adults", "children", "babies"]].fillna(0).sum(axis=1).eq(0)
    zero_nights = (df.stays_in_weekend_nights+df.stays_in_week_nights).eq(0)
    status = pd.crosstab(df.reservation_status, y).reindex(columns=[0, 1], fill_value=0).reset_index()
    checks = pd.DataFrame([
        ["Dòng trùng hoàn toàn; giữ lần xuất hiện đầu để đếm", duplicate_n, duplicate_n/n*100],
        ["Tổng số khách bằng 0 sau quy ước missing children=0 chỉ để kiểm tra", int(zero_guests.sum()), zero_guests.mean()*100],
        ["Tổng số đêm bằng 0", int(zero_nights.sum()), zero_nights.mean()*100],
        ["ADR âm", int(df.adr.lt(0).sum()), df.adr.lt(0).mean()*100],
        ["ADR bằng 0", int(df.adr.eq(0).sum()), df.adr.eq(0).mean()*100],
        ["ADR > 1.000 (ngưỡng kiểm tra, không phải kết luận lỗi)", int(df.adr.gt(1000).sum()), df.adr.gt(1000).mean()*100],
        ["Ngày đến không parse được", int(arrival.isna().sum()), arrival.isna().mean()*100],
        ["Nhãn ngoài {0,1} hoặc thiếu", int((~y.isin([0,1])).sum()), (~y.isin([0,1])).mean()*100],
    ], columns=["check", "n", "pct_all_bookings"])
    sensitivity = pd.DataFrame([["Raw: giữ nguyên", n, int(y.sum()), y.mean()*100],
                                ["Giả định bỏ mọi dòng trùng (chỉ phân tích độ nhạy)", len(unique), int(unique.is_canceled.sum()), unique.is_canceled.mean()*100]],
                               columns=["scenario", "n", "positive", "positive_pct"])
    r.add("quality", "3. Chất lượng dữ liệu và định nghĩa nhãn", f"""
`is_canceled=1` có **{count(y.sum())} booking ({pct(y.mean())})**. Bảng chéo xác nhận nhãn này gồm cả `Canceled` và `No-Show`; nhãn 0 là `Check-Out`. Vì vậy tên mục tiêu trong báo cáo là **hủy/no-show**, thay vì chỉ hủy chủ động.

`reservation_status` tiết lộ hoàn toàn nhãn. `reservation_status_date` là ngày trạng thái cuối, cũng thuộc thông tin kết quả. Hai cột chỉ được dùng để hiểu dữ liệu.

`company`/`agent` có nhiều NULL; theo nghiên cứu gốc, NULL ở các cột này có thể nghĩa **không áp dụng**. Không coi các ID này là số liên tục hay mặc định thay NULL bằng trung vị. Với `children`/`country`, nguyên nhân thiếu chưa được xác minh từ CSV.

Nếu giả định loại tất cả dòng trùng, tỷ lệ nhãn 1 đổi từ **{pct(y.mean())}** thành **{pct(unique.is_canceled.mean())}**. Đây là độ nhạy đáng kể, không phải chỉ định phải deduplicate. Không có khóa booking nên chưa phân biệt được lỗi lặp với các booking thật có cùng thuộc tính. Các dòng gốc vẫn được giữ nguyên.

ADR âm/cao hoặc booking 0 đêm/0 khách là trường hợp cần xác minh. CSV không chứng minh nguyên nhân là hoàn tiền, voucher hay nhập sai; không clipping hay xóa trong báo cáo.
""", [("Kiểm tra bất thường (các điều kiện có thể chồng lặp)", checks), ("Trạng thái cuối × nhãn", status), ("Độ nhạy theo giả định về duplicate", sensitivity)])
    num = [c for c in df.select_dtypes(include="number").columns if c not in ["agent", "company", "is_canceled", "is_repeated_guest", "arrival_date_year", "arrival_date_week_number", "arrival_date_day_of_month"]]
    cats = ["hotel", "market_segment", "distribution_channel", "deposit_type", "customer_type", "meal", "country", "reserved_room_type", "assigned_room_type", "is_repeated_guest"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    ax[0].hist(df.lead_time, bins=50, color=COLORS[0]); ax[0].set(title="Lead time — all bookings", xlabel="Days", ylabel="Bookings")
    visible = df.adr.between(0, 500)
    ax[1].hist(df.loc[visible, "adr"], bins=50, color=COLORS[1]); ax[1].set(title=f"ADR 0–500; {count((~visible).sum())} outside", xlabel="ADR (source monetary unit / night)", ylabel="Bookings")
    fig.tight_layout()
    r.add("distributions", "4. Phân phối đơn biến và mức độ bao phủ", "Thống kê định lượng dùng toàn bộ dữ liệu, bỏ NA riêng ở từng cột. p1/p95/p99 cho thấy phần đuôi mà mean/median có thể che khuất. Bảng category hiển thị top 8 mỗi biến, tỷ lệ luôn chia cho toàn bộ booking (kể cả missing), nên tổng top 8 có thể nhỏ hơn 100%. ADR trên biểu đồ chỉ giới hạn vùng nhìn; dữ liệu và thống kê không bị cắt.", [("Thống kê định lượng toàn bộ", numeric_table(df, num)), ("Phân bố phân loại — top 8/cột", categorical_table(df, cats))], [r.savefig("distributions", fig)])
    grouped = [(f"Tỷ lệ nhãn 1 theo {c}", rate_table(df, c, "is_canceled", limit=15 if c == "country" else None)) for c in ["hotel", "market_segment", "distribution_channel", "deposit_type", "customer_type", "is_repeated_guest", "country"]]
    lead_groups = pd.cut(df.lead_time, [-1, 0, 7, 30, 90, 180, 365, np.inf], labels=["0", "1–7", "8–30", "31–90", "91–180", "181–365", ">365"])
    diag = pd.DataFrame({"lead_time_group": lead_groups, "is_canceled": y})
    lead = rate_table(diag, "lead_time_group", "is_canceled")
    grouped.append(("Lead time — nhóm chỉ phục vụ thống kê EDA", lead))
    interaction = df.groupby(["hotel", "market_segment"], observed=True).is_canceled.agg(n="size", positive="sum").reset_index()
    interaction["positive_pct"] = interaction.positive/interaction.n*100
    grouped.append(("Đối chiếu phân khúc trong từng khách sạn", interaction))
    fig, ax = plt.subplots(figsize=(8, 4))
    hotel_rates = rate_table(df, "hotel", "is_canceled")
    ax.bar(hotel_rates.hotel, hotel_rates.rate_pct, color=COLORS[:2])
    ax.set(title="Cancellation / no-show by hotel", ylabel="% of bookings", ylim=(0, 60))
    for i, v in enumerate(hotel_rates.rate_pct): ax.text(i, v+1, f"{v:.2f}%", ha="center")
    fig.tight_layout()
    r.add("target", "5. Mối liên hệ với nhãn và tương tác phân khúc", "Mẫu số là booking trong từng nhóm; không phải tỷ trọng nhóm trong toàn dữ liệu. Các khoảng Wilson 95% là mô tả tham khảo dưới giả định quan sát độc lập; duplicate, booking theo đoàn và khách lặp có thể làm mức bất định thực tế lớn hơn. Nhóm dưới 100 quan sát được gắn cờ, không xếp hạng chắc chắn. Các liên hệ không phải tác động nhân quả của kênh, đặt cọc hoặc thời gian đặt trước. Bảng hotel × market_segment giúp kiểm tra việc khác cơ cấu khách giữa hai cơ sở.", grouped, [r.savefig("target_by_hotel", fig)])
    temporal = pd.DataFrame({"year_month": arrival.dt.to_period("M").astype(str), "hotel": df.hotel, "is_canceled": y})
    timeline = temporal.groupby(["year_month", "hotel"]).is_canceled.agg(n="size", positive="sum").reset_index()
    timeline["positive_pct"] = timeline.positive/timeline.n*100
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for i, hotel in enumerate(timeline.hotel.unique()):
        s = timeline[timeline.hotel.eq(hotel)]
        axes[0].plot(s.year_month, s.n, label=hotel, color=COLORS[i])
        axes[1].plot(s.year_month, s.positive_pct, label=hotel, color=COLORS[i])
    axes[0].set(title="Bookings by arrival year-month", ylabel="Bookings"); axes[0].legend()
    axes[1].set(ylabel="Cancellation / no-show (%)", xlabel="Arrival year-month")
    axes[1].tick_params(axis="x", rotation=60); fig.tight_layout()
    r.add("time", "6. Thời gian, mùa vụ và giới hạn đánh giá", f"Ngày đến parse được nằm trong **{arrival.min().date()}–{arrival.max().date()}**. Đây là thời gian ngày đến, không phải thời gian tạo booking. Các tháng đầu/cuối không bao phủ đủ năm, nên không gộp số booking theo tên tháng rồi kết luận mùa vụ. Đồ thị dưới giữ năm–tháng và tách hai khách sạn. Chưa đủ cơ sở để chọn một cách chia tập cuối cùng: cần định nghĩa t0, nhãn đã trưởng thành và đối tượng còn có thể can thiệp; nếu đánh giá tương lai thì ưu tiên giữ trật tự thời gian, đồng thời kiểm tra duplicate qua các tập.", [("Toàn bộ năm–tháng × khách sạn", timeline)], [r.savefig("calendar", fig)])
    # Raw numerical relationship, not a feature-selection decision.
    corr_cols = ["lead_time", "stays_in_weekend_nights", "stays_in_week_nights", "adults", "children", "babies", "previous_cancellations", "previous_bookings_not_canceled", "booking_changes", "adr", "total_of_special_requests"]
    corr = df[corr_cols].corr(method="spearman")
    pairs = [(a, b, corr.loc[a,b]) for i,a in enumerate(corr_cols) for b in corr_cols[i+1:]]
    pairs = pd.DataFrame(pairs, columns=["column_a", "column_b", "spearman_rho"]).sort_values("spearman_rho", key=abs, ascending=False).head(12)
    r.add("dependencies", "7. Phụ thuộc giữa các biến", "Bảng Spearman là tương quan cặp giữa các biến số gốc, dùng các cặp không thiếu. Các phép đo nhiều giá trị 0, category được mã hóa bằng số và dữ liệu lặp có thể làm cách diễn giải khác thường. Không dùng bảng này để tự động loại biến. `market_segment` và `distribution_channel` có thể mô tả chồng lặp; bảng chéo bên dưới kiểm tra cấu trúc thay vì xem hai cột độc lập.", [("12 cặp số có |rho| lớn nhất trong danh sách công bố", pairs), ("Market segment × distribution channel", pd.crosstab(df.market_segment, df.distribution_channel).reset_index())])
    r.add("conclusions", "8. Kết luận và câu hỏi còn mở", f"""
**Kết luận đã kiểm chứng:** nhãn 1 chiếm {pct(y.mean())}, gồm hủy và no-show; có {count(duplicate_n)} dòng trùng hoàn toàn; tỷ lệ thay đổi mạnh theo giả định bỏ trùng; hai cơ sở và các kênh có cơ cấu khác nhau. Thông tin trạng thái cuối không thể là đầu vào dự đoán.

**Mức độ phù hợp:** tốt cho nghiên cứu cancellation/no-show ở cấp booking. Chưa đủ để mô tả churn ở cấp khách hàng hoặc mô phỏng chấm điểm ngay lúc tạo booking một cách đáng tin cậy.

**Cần xác minh trước giai đoạn tiếp theo:** (1) thời điểm chấm điểm và tập booking còn hiệu lực; (2) lịch sử giá trị tại t0 cho từng biến, nhất là assigned_room_type, booking_changes, deposit_type, ADR và yêu cầu bổ sung; (3) định danh booking/nhóm để giải thích trùng; (4) ý nghĩa các booking 0 khách/0 đêm và ADR bất thường; (5) phạm vi áp dụng ngoài hai khách sạn.

Không xóa dòng, impute, clipping, encoding, tạo feature hoặc train model trong báo cáo này. Các phân nhóm ngày/tháng và lead time chỉ là bảng thống kê EDA; không được xuất thành tập huấn luyện.
""")
    from scripts.eda_diagnostics import enrich_hotel
    enrich_hotel(r,df,arrival)
    return r.publish()


AIRBNB_MEANINGS = {
    "id": ("Định danh người dùng", "Khóa ghép sessions.user_id; không phải phép đo"),
    "date_account_created": ("Ngày tạo tài khoản", "Mốc cohort; không tự xác định horizon nhãn"),
    "timestamp_first_active": ("Lần hoạt động đầu, dạng YYYYMMDDHHMMSS", "Có thể trước ngày tạo tài khoản; cần parse theo định dạng"),
    "date_first_booking": ("Ngày của lượt đặt chỗ đầu tiên", "Kết quả. Việc có giá trị hay bị thiếu tiết lộ nhãn y."),
    "gender": ("Giới tính khai báo", "-unknown- là sentinel, không phải giá trị biết rõ"),
    "age": ("Tuổi khai báo", "Thiếu và giá trị ngoài dải tham chiếu; chưa sửa tuổi/năm sinh"),
    "signup_method": ("Phương thức đăng ký", "Biến phân loại"),
    "signup_flow": ("Mã luồng/trang đăng ký", "Mã phân loại dù pandas đọc số"),
    "language": ("Ngôn ngữ ưu tiên", "Biến phân loại"),
    "affiliate_channel": ("Kênh marketing liên quan", "Không tự chứng minh tác động nhân quả của kênh"),
    "affiliate_provider": ("Nhà cung cấp/kênh cụ thể", "Biến phân loại"),
    "first_affiliate_tracked": ("Tương tác affiliate đầu được theo dõi", "NA và category untracked có nghĩa khác nhau"),
    "signup_app": ("Ứng dụng đăng ký", "Không đại diện mọi thiết bị dùng về sau"),
    "first_device_type": ("Thiết bị đầu tiên", "Khác device_type ở từng sự kiện sessions"),
    "first_browser": ("Trình duyệt đầu tiên", "Có sentinel -unknown-"),
    "country_destination": ("Điểm đến của lượt đặt chỗ đầu tiên hoặc NDF", "Cột điểm đến có 12 giá trị, được dùng để định nghĩa nhãn y."),
}


def airbnb_report(root):
    from scripts.airbnb_deep_dive import session_action_counts
    r = Report("AIRBNB", "AIRBNB — Hiểu người dùng mới, lượt đặt chỗ đầu tiên và độ phủ hành vi", root)
    folder = root/"data/raw/AIRBNB"
    train = pd.read_csv(folder/"train_users_2.csv")
    test = pd.read_csv(folder/"test_users.csv")
    countries = pd.read_csv(folder/"countries.csv")
    ages = pd.read_csv(folder/"age_gender_bkts.csv")
    inventory = manifest(root, "AIRBNB")
    n = len(train)
    booked = train.country_destination.ne("NDF")
    # Diagnostic label only, never exported as a modeling dataset.
    diagnostic = train.assign(observed_booking=booked.astype(int))
    r.add("scope", "1. Bối cảnh, đơn vị quan sát và phạm vi nhãn", f"""
Train gồm **{count(n)} người dùng, 16 cột**, test gồm **{count(len(test))} người dùng, 15 cột**. Cột `country_destination` có 12 giá trị, gồm `NDF` và 11 điểm đến hoặc nhóm điểm đến. Báo cáo định nghĩa nhãn y từ cột này để phân tích khả năng có lượt đặt chỗ đầu tiên ở cấp người dùng.

Mục tiêu gốc của bộ dữ liệu là dự đoán điểm đến của lượt đặt chỗ đầu tiên. Nhãn y kế thừa phạm vi theo dõi của bộ dữ liệu. Phần 5 phân tích độ trễ và thông tin cần bổ sung để xây dựng nhãn cho thời hạn 30, 60 hoặc 90 ngày.

[Mô tả cuộc thi Airbnb New User Bookings](https://www.kaggle.com/c/airbnb-recruiting-new-user-bookings/data) nêu người dùng trong tập đến từ Mỹ. Vì vậy tính đại diện về địa lý, thời kỳ và sản phẩm có giới hạn. Test công khai không có nhãn để tính chất lượng dự đoán hoặc so sánh booking rate với train.
""", [("Danh mục đầy đủ; submission chỉ là định dạng kết quả, không phải dữ liệu người dùng bổ sung", inventory)])
    r.add("dictionary", "2. Từ điển users và quan hệ giữa các bảng", "`id` là khóa users, ghép một–nhiều với `sessions.user_id`. Cần phân tích users trước và sau ghép mà không làm một người dùng bị nhân thành nhiều quan sát học. `countries` có khóa quốc gia; không ghép bằng điểm đến thật để dự đoán chính nhãn đó. `age_gender_bkts` là thống kê tổng hợp theo bucket/quốc gia/giới tính, không phải thêm 420 khách hàng.", [("Schema đầy đủ của train users", metadata_table(train, AIRBNB_MEANINGS)), ("So sánh schema train và test", pd.DataFrame([[c, c in train, c in test] for c in train.columns.union(test.columns, sort=False)], columns=["column", "in_train", "in_test"]))])
    account = pd.to_datetime(train.date_account_created, errors="coerce")
    first = pd.to_datetime(train.timestamp_first_active.astype(str), format="%Y%m%d%H%M%S", errors="coerce")
    booking = pd.to_datetime(train.date_first_booking, errors="coerce")
    matching = train.date_first_booking.notna().eq(booked)
    invalid_age = train.age.notna() & ~train.age.between(16,100)
    checks = pd.DataFrame([
        ["ID train bị lặp (beyond first)", int(train.id.duplicated().sum())],
        ["ID test bị lặp (beyond first)", int(test.id.duplicated().sum())],
        ["ID xuất hiện ở cả train và test", len(set(train.id)&set(test.id))],
        ["date_first_booking.notna không khớp nhãn có booking", int((~matching).sum())],
        ["date_first_booking có giá trị trong test", int(test.date_first_booking.notna().sum())],
        ["Tuổi có giá trị nhưng ngoài [16,100] (quy ước mô tả)", int(invalid_age.sum())],
        ["Lượt đặt chỗ đầu tiên trước ngày tạo tài khoản", int((booking<account).sum())],
        ["Hoạt động đầu trước ngày tạo tài khoản", int((first.dt.normalize()<account).sum())],
        ["Ngày account không parse được", int(account.isna().sum())],
        ["Timestamp hoạt động đầu không parse được", int(first.isna().sum())],
        ["Ngày booking có giá trị nhưng không parse được", int((train.date_first_booking.notna()&booking.isna()).sum())],
    ], columns=["check", "n"])
    sentinel = pd.DataFrame([[c, int(train[c].isna().sum()), int(train[c].eq("-unknown-").sum()),
                             int(train[c].eq("untracked").sum())] for c in ["gender", "first_browser", "first_affiliate_tracked"]],
                            columns=["column", "null_n", "minus_unknown_n", "untracked_n"])
    r.add("quality", "3. Chất lượng users, sentinel và rò rỉ nhãn", f"""
**Rò rỉ đã kiểm chứng:** việc `date_first_booking` có giá trị hay bị thiếu khớp nhãn y ở **{pct(matching.mean())}** người dùng train. Vì cột này tiết lộ kết quả cần dự đoán, thiết kế đầu vào loại cả ngày đặt chỗ và cờ thiếu ngày đặt chỗ. Giá trị thiếu ở đây phản ánh cách ghi nhận kết quả nên không cần điền ngày thay thế.

Tuổi ngoài [16,100] được thống kê riêng theo một **dải tham chiếu dùng cho EDA**. Các giá trị dạng 19xx/20xx gợi ý khả năng người dùng đã nhập năm sinh. Cần xác minh cách thu thập trước khi quyết định chuyển đổi hoặc thay thế tuổi. Các mã đặc biệt trong gender và browser được thống kê riêng với giá trị thiếu NA.

Người dùng có thể tìm kiếm trước khi đăng ký, nên ngày hoạt động đầu có thể sớm hơn ngày tạo tài khoản. Có **{count((booking<account).sum())}** dòng ghi ngày đặt chỗ trước ngày tạo tài khoản. Những trường hợp này cần được đối chiếu với định nghĩa các mốc thời gian trước khi quyết định đưa vào tập huấn luyện.
""", [("Kiểm tra định danh và logic thời gian", checks), ("NA và giá trị đặc biệt là các khái niệm khác nhau", sentinel), ("Ngày booking có/không × nhãn có/không booking", pd.crosstab(train.date_first_booking.notna().rename("has_booking_date"), booked.rename("observed_booking")).reset_index())])
    target = train.country_destination.value_counts().rename_axis("country_destination").reset_index(name="n")
    target["pct_all_users"] = target.n/n*100
    target["pct_booked_users"] = np.where(target.country_destination.ne("NDF"), target.n/booked.sum()*100, np.nan)
    age_groups = pd.DataFrame({"sample": ["Toàn bộ age không thiếu", "Chỉ age trong [16,100]; không thay đổi raw"],
                               "n": [train.age.notna().sum(), train.age.between(16,100).sum()],
                               "mean": [train.age.mean(), train.loc[train.age.between(16,100),"age"].mean()],
                               "median": [train.age.median(), train.loc[train.age.between(16,100),"age"].median()]})
    fig, ax = plt.subplots(1,2,figsize=(13,4))
    ax[0].bar(target.country_destination, target.pct_all_users, color=COLORS[0]); ax[0].set(title="Nhãn điểm đến đầu được ghi nhận", xlabel="Nhãn điểm đến", ylabel="Tỷ trọng toàn bộ user train (%)"); ax[0].tick_params(axis="x",rotation=45)
    ax[1].hist(train.loc[train.age.between(16,100),"age"], bins=35,color=COLORS[1]); ax[1].set(title="Tuổi 16–100: cửa sổ mô tả",xlabel="Tuổi khai báo (năm)",ylabel="Số người dùng")
    fig.tight_layout()
    r.add("distributions", "4. Nhãn, tuổi và phân phối kênh/thiết bị", f"""
Có booking được ghi nhận: **{count(booked.sum())}/{count(n)} ({pct(booked.mean())})**. Nhóm NDF chiếm **{pct((~booked).mean())}**. Bảng điểm đến trình bày hai mẫu số riêng: toàn bộ người dùng và chỉ người có booking; không nhầm tỷ trọng US trong toàn bộ users với tỷ trọng US trong nhóm đã book.

Độ tuổi được trình bày cả raw và cửa sổ [16,100] để thấy tác động của giá trị cực đoan. Top category có mẫu số là toàn bộ users, kể cả NA. `signup_flow` là mã phân loại; không báo cáo mean của mã như một đặc điểm khách hàng.
""", [("12 nhãn và hai mẫu số", target), ("Tuổi raw và cửa sổ mô tả", age_groups), ("Thống kê tuổi raw", numeric_table(train,["age"])), ("Phân phối category — top 8/cột", categorical_table(train,["gender","signup_method","signup_flow","language","affiliate_channel","affiliate_provider","first_affiliate_tracked","signup_app","first_device_type","first_browser"]))], [r.savefig("users_distributions",fig)])
    rates = [(f"Booking được ghi nhận theo {c}",rate_table(diagnostic,c,"observed_booking",limit=15)) for c in ["gender","signup_method","signup_app","affiliate_channel","first_device_type","first_affiliate_tracked"]]
    age_labels = pd.cut(train.age, [0,15,24,34,44,54,64,100,np.inf], labels=["1–15","16–24","25–34","35–44","45–54","55–64","65–100",">100"])
    age_diagnostic = pd.DataFrame({"reported_age_group":age_labels,"observed_booking":booked.astype(int)})
    rates.append(("Tuổi theo nhãn — NA giữ là nhóm riêng",rate_table(age_diagnostic,"reported_age_group","observed_booking")))
    r.add("target", "5. Quan hệ giữa hồ sơ đăng ký và nhãn", "Mỗi quan sát là một user train. Khoảng Wilson 95% chỉ phản ánh bất định nhị thức dưới giả định độc lập; không bao gồm sai lệch chọn mẫu, nhãn chưa trưởng thành hoặc khác thời gian theo dõi. Các nhóm n<100 cần thận trọng. Chênh lệch booking rate giữa kênh/app/thiết bị là liên hệ quan sát, không chứng minh kênh làm tăng booking. Phân nhóm tuổi phục vụ so sánh EDA, không tạo feature.",rates)
    # All event records; only per-user descriptive aggregates are held in memory.
    sess_rows=0; sess_missing=None; sess_unique={}; devices={}; actions={}; per_user=[]; transaction_parts=[]
    elapsed_n=0; elapsed_sum=0.; elapsed_min=np.inf; elapsed_max=-np.inf; elapsed_zero=0; elapsed_negative=0
    for chunk in pd.read_csv(folder/"sessions.csv",chunksize=CHUNK_SIZE):
        transaction_parts.extend(session_action_counts(chunk))
        sess_rows+=len(chunk)
        miss=chunk.isna().sum(); sess_missing=miss if sess_missing is None else sess_missing.add(miss,fill_value=0)
        for c in chunk.columns:
            if c != "secs_elapsed": sess_unique.setdefault(c,set()).update(chunk[c].dropna().unique())
        for mapping,c in [(devices,"device_type"),(actions,"action")]:
            for k,v in chunk[c].fillna("<MISSING>").value_counts().items(): mapping[k]=mapping.get(k,0)+int(v)
        s=chunk.secs_elapsed.dropna()
        elapsed_n+=len(s); elapsed_sum+=float(s.sum()); elapsed_zero+=int(s.eq(0).sum()); elapsed_negative+=int(s.lt(0).sum())
        if len(s): elapsed_min=min(elapsed_min,float(s.min())); elapsed_max=max(elapsed_max,float(s.max()))
        per_user.append(chunk.groupby("user_id",dropna=True).agg(event_n=("device_type","size"),elapsed_nonnull=("secs_elapsed","count"),elapsed_sum=("secs_elapsed","sum")))
    per_user=pd.concat(per_user).groupby(level=0).sum()
    transaction_counts=pd.concat(transaction_parts,ignore_index=True).groupby(["user_id","field","value"],observed=True,sort=False).event_n.sum().reset_index()
    ids=set(per_user.index); train_ids=set(train.id); test_ids=set(test.id)
    coverage=pd.DataFrame([["train",len(train),len(ids&train_ids),len(ids&train_ids)/len(train)*100],
                           ["test",len(test),len(ids&test_ids),len(ids&test_ids)/len(test)*100]],columns=["population","users","users_with_sessions","coverage_pct"])
    session_schema = {
        "user_id":("ID ghép users.id","Khóa; NA không ghép được"),
        "action":("Tên hành động","Không có timestamp sự kiện"),
        "action_type":("Nhóm hành động","Có NA/sentinel; không suy ra thứ tự thời gian"),
        "action_detail":("Chi tiết hành động","Có NA/sentinel"),
        "device_type":("Thiết bị ở sự kiện","Tỷ trọng sự kiện khác tỷ trọng người dùng"),
        "secs_elapsed":("Trường thời lượng theo mô tả nguồn","Không phải timestamp; không dùng để cắt trước/sau booking"),
    }
    sess_schema=pd.DataFrame([[c,len(sess_unique.get(c,[])) if c!="secs_elapsed" else "không tính",int(sess_missing[c]),sess_missing[c]/sess_rows*100,*session_schema[c]] for c in session_schema],columns=["column","distinct_nonnull","missing_n","missing_pct","meaning","caution"])
    device_table=pd.DataFrame(sorted(devices.items(),key=lambda kv:-kv[1]),columns=["device_type","events"])
    device_table["pct_all_events"]=device_table.events/sess_rows*100
    action_table=pd.DataFrame(sorted(actions.items(),key=lambda kv:-kv[1])[:20],columns=["action","events"])
    action_table["pct_all_events"]=action_table.events/sess_rows*100
    yearly=pd.DataFrame({"account_year":account.dt.year,"has_sessions":train.id.isin(ids)})
    yearly=yearly.groupby("account_year").has_sessions.agg(users="size",users_with_sessions="sum").reset_index()
    yearly["coverage_pct"]=yearly.users_with_sessions/yearly.users*100
    coverage_target=pd.DataFrame({"country_destination":train.country_destination,"has_sessions":train.id.isin(ids)})
    coverage_target=coverage_target.groupby("country_destination").has_sessions.agg(users="size",users_with_sessions="sum").reset_index()
    coverage_target["coverage_pct"]=coverage_target.users_with_sessions/coverage_target.users*100
    r.facts=dict(rows=n,columns=len(train.columns),positive=int(booked.sum()),rate=float(booked.mean()),sessions=sess_rows,session_users=len(ids),train_session_users=len(ids&train_ids),test_session_users=len(ids&test_ids),test_rows=len(test),sessions_missing_ids=int(sess_missing.user_id))
    fig,ax=plt.subplots(1,2,figsize=(12,4))
    year2014=yearly.loc[yearly.account_year.eq(2014)].iloc[0]
    compare_labels=["Train toàn kỳ","Train năm 2014","Test năm 2014"]
    compare_values=[coverage.iloc[0].coverage_pct,year2014.coverage_pct,coverage.iloc[1].coverage_pct]
    ax[0].bar(compare_labels,compare_values,color=[COLORS[0],COLORS[2],COLORS[1]]); ax[0].set(title="Độ phủ sessions: so sánh cùng cohort 2014",xlabel="Quần thể người dùng",ylabel="Người dùng có log (%)",ylim=(0,108)); ax[0].tick_params(axis="x",rotation=15)
    for i,value in enumerate(compare_values): ax[0].text(i,value+1,f"{value:.2f}%",ha="center")
    ax[1].bar(yearly.account_year.astype(str),yearly.coverage_pct,color=COLORS[0]); ax[1].set(title="Độ phủ sessions theo năm tạo tài khoản",xlabel="Năm tạo tài khoản train",ylabel="Người dùng có log (%)",ylim=(0,108)); fig.tight_layout()
    r.add("sessions", "6. Sessions: độ phủ, khóa ghép và giới hạn thời gian", f"""
Đã quét **toàn bộ {count(sess_rows)} sự kiện**, không dùng 500.000 dòng đầu. Có **{count(len(ids))} user_id khác nhau không thiếu**, gồm **{count(len(ids&train_ids))} train** và **{count(len(ids&test_ids))} test**; **{count(len(ids-train_ids-test_ids))} ID** không thuộc cả hai bảng users. Có **{count(sess_missing.user_id)} sự kiện thiếu user_id**, không gán được về người dùng.

Độ phủ train **{pct(len(ids&train_ids)/n)}**, test **{pct(len(ids&test_ids)/len(test))}** khác nhau rất mạnh. Bảng cohort cho thấy độ phủ gắn với năm tạo account; không diễn giải không có log thành không có hoạt động. Tỷ lệ thiết bị dưới đây có mẫu số là **sự kiện**, không phải người dùng, nên người hoạt động nhiều có trọng số lớn hơn.

**Giới hạn quan trọng:** sáu cột sessions không có timestamp sự kiện. Không thể chứng minh từ file này rằng toàn bộ log thuộc cửa sổ trước t0/booking. Các tổng theo user chỉ là mô tả để hiểu độ phủ và mức độ lặp; không xuất thành feature và không kết luận predictive signal hợp lệ theo thời gian.

`secs_elapsed` có {count(elapsed_n)} giá trị không thiếu; trung bình {elapsed_sum/elapsed_n:,.2f}, min {elapsed_min:,.2f}, max {elapsed_max:,.2f}; {count(elapsed_zero)} giá trị 0 và {count(elapsed_negative)} âm. Không đồng nhất tổng trường này với thời gian hoạt động độc lập liên tục hoặc thời điểm của hành động.
""",[("Schema toàn bảng sessions",sess_schema),("Độ phủ theo tập users",coverage),("Độ phủ theo năm account train",yearly),("Độ phủ theo nhãn điểm đến (mô tả, không dùng suy luận nhân quả)",coverage_target),("Số sự kiện mỗi user có log; NA user_id không nằm trong mẫu số",numeric_table(per_user.reset_index(drop=True),["event_n","elapsed_nonnull","elapsed_sum"])),("Thiết bị theo toàn bộ sự kiện",device_table),("Top 20 action theo toàn bộ sự kiện",action_table)],[r.savefig("session_coverage",fig)])
    cohort=pd.DataFrame({"account_month":account.dt.to_period("M").astype(str),"observed_booking":booked.astype(int)})
    cohort=cohort.groupby("account_month").observed_booking.agg(users="size",booked="sum").reset_index()
    cohort["booked_pct"]=cohort.booked/cohort.users*100
    cohort["ci95_low_pct"],cohort["ci95_high_pct"]=wilson(cohort.booked,cohort.users)
    range_table=pd.DataFrame([[label,df.date_account_created.min(),df.date_account_created.max(),len(df)] for label,df in [("train",train),("test",test)]],columns=["population","account_min","account_max","users"])
    fig,axes=plt.subplots(2,1,figsize=(13,6),sharex=True)
    x=np.arange(len(cohort))
    axes[0].bar(x,cohort.users,color=COLORS[0]); axes[0].set(title="Cohort tạo tài khoản trong train",ylabel="Số người dùng")
    axes[1].errorbar(x,cohort.booked_pct,yerr=np.vstack([cohort.booked_pct-cohort.ci95_low_pct,cohort.ci95_high_pct-cohort.booked_pct]),fmt="o-",markersize=3,capsize=2,color=COLORS[1],label="Tỷ lệ và khoảng Wilson 95%")
    axes[1].set(ylabel="Có booking được ghi nhận (%)",xlabel="Tháng tạo tài khoản"); axes[1].legend(loc="best")
    boundary=int(cohort.index[cohort.account_month.eq("2014-01")][0])
    for axis in axes: axis.axvline(boundary-.5,color=COLORS[2],linestyle="--",linewidth=1)
    axes[0].text(boundary-.7,axes[0].get_ylim()[1]*.94,"2014-01: bắt đầu có sessions",ha="right",va="top",color=COLORS[2])
    ticks=np.arange(0,len(cohort),3); axes[1].set_xticks(ticks); axes[1].set_xticklabels(cohort.account_month.iloc[ticks],rotation=60); fig.tight_layout()
    r.add("time", "7. Cohort thời gian và thay đổi train–test", "Train và test nối tiếp theo ngày tạo account. Đồ thị booking rate theo cohort phản ánh cả thành phần khách và thời gian có cơ hội được quan sát; không kết luận cohort mới kém chất lượng chỉ từ nhãn. Total variation trong [0,1] so sánh phân phối category (kể cả NA); 0 là giống nhau, 1 là không giao nhau. Đây là mô tả drift, không phải ngưỡng tự động loại biến hoặc chọn mô hình.",[("Khoảng thời gian account",range_table),("Cohort theo tháng — toàn bộ train",cohort),("Khác biệt category giữa train và test",drift_table(train,test,["gender","signup_method","signup_flow","language","affiliate_channel","affiliate_provider","first_affiliate_tracked","signup_app","first_device_type","first_browser"]))],[r.savefig("account_cohorts",fig)])
    aux_schema=pd.DataFrame([
        ["countries","country_destination","Mã quốc gia ứng viên/điểm đến","Khóa duy nhất phải được kiểm tra; không ghép theo nhãn thật"],
        ["countries","lat_destination / lng_destination","Vĩ độ / kinh độ","Thuộc quốc gia, không phải địa chỉ user"],
        ["countries","distance_km","Khoảng cách theo nguồn, km","Cần giữ định nghĩa gốc; không giả định khoảng cách từng user"],
        ["countries","destination_km2","Diện tích quốc gia, km²","Thống kê tổng hợp"],
        ["countries","destination_language ","Ngôn ngữ quốc gia","Tên cột gốc có dấu cách cuối; chưa đổi tên raw"],
        ["countries","language_levenshtein_distance","Khoảng cách ngôn ngữ theo nguồn","Định nghĩa cần tham chiếu nguồn"],
        ["age_gender_bkts","age_bucket","Nhóm tuổi","Không nối trực tiếp age số mà không xác định quy tắc bucket"],
        ["age_gender_bkts","country_destination / gender","Quốc gia và giới tính của ô tổng hợp","Khóa ghép tổng hợp; kiểm tra tính duy nhất"],
        ["age_gender_bkts","population_in_thousands","Quy mô theo đơn vị nghìn của bảng nguồn","Không phải số users train; không tự coi là tỷ lệ booking"],
        ["age_gender_bkts","year","Năm thống kê","Kiểm tra khả dụng tại t0 trước khi sử dụng"],
    ],columns=["table","column_or_columns","meaning","caution"])
    aux_checks=pd.DataFrame([["countries: số dòng",len(countries)],["countries: khóa quốc gia trùng",int(countries.country_destination.duplicated().sum())],["countries: tổng ô NA",int(countries.isna().sum().sum())],["age_gender_bkts: khóa bucket-country-gender-year trùng",int(ages.duplicated(["age_bucket","country_destination","gender","year"]).sum())],["age_gender_bkts: tổng ô NA",int(ages.isna().sum().sum())]],columns=["check","n"])
    r.add("auxiliary", "8. Bảng phụ: từ điển và khả năng ghép", "Chỉ kiểm tra bảng và quan hệ; chưa thực hiện feature engineering. Các mã NDF/other trong users không nhất thiết có dòng tương ứng trong countries; việc thiếu đó không phải lỗi khóa của users. Bất kỳ cách dùng thống kê ngoài bảng users phải xác minh nguồn, mốc công bố và ngữ nghĩa trước khi ghép vào đầu vào dự đoán.",[("Từ điển bảng phụ (đủ các cột raw)",aux_schema),("Kiểm tra khóa và missing bảng phụ",aux_checks),("Toàn bộ countries",countries),("Độ phủ năm và category trong age_gender_bkts",categorical_table(ages,["year","gender","country_destination"],top=12))])
    r.add("conclusions", "9. Kết luận và câu hỏi còn mở", f"""
**Đã kiểm chứng:** {pct(booked.mean())} users train có booking theo nhãn; date_first_booking tiết lộ nhãn; users và events có đơn vị khác nhau; độ phủ sessions chênh rất lớn giữa train/test và gắn với năm account; logs không có timestamp từng sự kiện.

**Mức độ phù hợp:** phù hợp cho nghiên cứu first-booking propensity ở cấp user nếu công bố rõ nhãn hiện tại là kết quả được quan sát, chưa phải một horizon chuẩn hóa. Bài toán điểm đến có 12 lớp khi gồm NDF; chỉ người có booking còn 11 giá trị điểm đến/other.

**Cần xác minh:** thời hạn nhãn và ngày kết thúc theo dõi; t0 chấm điểm; khoảng thời gian logs được thu thập và cắt log; ý nghĩa tuổi bất thường/unknown; thời điểm bảng phụ được công bố; khả năng áp dụng ngoài người dùng Mỹ và thời kỳ 2010–2014.

Chưa impute, sửa tuổi, encode, tổng hợp sessions thành tập feature, chọn feature, chia tập huấn luyện hay train model. Mọi bảng nhóm và nhãn nhị phân tạm thời trong code chỉ phục vụ thống kê EDA và không được xuất thành dữ liệu mô hình.
""")
    from scripts.eda_diagnostics import enrich_airbnb
    enrich_airbnb(r,train,test,ids,account,per_user,transaction_counts)
    return r.publish()


EXPEDIA_MEANINGS = {
    "srch_id": ("ID lượt tìm kiếm", "Khóa nhóm, không phải ID người dùng"),
    "date_time": ("Thời điểm tìm kiếm", "Thời gian, không giả định timezone không được công bố"),
    "site_id": ("ID website/điểm bán Expedia", "Phân loại"),
    "visitor_location_country_id": ("ID quốc gia vị trí người tìm", "Phân loại, không phải mã có thứ tự"),
    "visitor_hist_starrating": ("Mức sao trung bình trong lịch sử khách", "NA không đủ chứng minh khách mới/chưa đăng nhập"),
    "visitor_hist_adr_usd": ("ADR lịch sử của khách, USD", "Cần xác minh cửa sổ lịch sử và cách tính"),
    "prop_country_id": ("ID quốc gia khách sạn", "Phân loại"),
    "prop_id": ("ID khách sạn", "Thực thể có thể lặp qua searches; không phải số liên tục"),
    "prop_starrating": ("Hạng sao khách sạn", "0 cần xác minh nghĩa; không tự xem là 0 sao chất lượng thấp"),
    "prop_review_score": ("Điểm review khách sạn", "0 và NA là hai trường hợp cần phân biệt"),
    "prop_brand_bool": ("Cờ thuộc thương hiệu/chuỗi", "Nhị phân; cố định nhãn 0/1 khi vẽ"),
    "prop_location_score1": ("Điểm vị trí thứ nhất", "Thước đo do nguồn cung cấp"),
    "prop_location_score2": ("Điểm vị trí thứ hai", "Thước đo do nguồn cung cấp; có NA"),
    "prop_log_historical_price": ("Log giá lịch sử khách sạn", "Không tự khôi phục tiền khi chưa biết cơ số/cách tính"),
    "position": ("Vị trí hiển thị quan sát được", "Có trong train, không có trong test; có ảnh hưởng vị trí"),
    "price_usd": ("Giá hiển thị cho khách sạn trong search, USD", "Cần xác minh đơn vị giá theo đêm/toàn kỳ; có đuôi cực lớn"),
    "promotion_flag": ("Cờ hiển thị khuyến mãi", "Liên hệ quan sát không chứng minh tác động khuyến mãi"),
    "srch_destination_id": ("ID điểm đến tìm kiếm", "Phân loại"),
    "srch_length_of_stay": ("Số đêm lưu trú tìm kiếm", "Số đếm"),
    "srch_booking_window": ("Số ngày từ search đến ngày đến", "Đơn vị ngày"),
    "srch_adults_count": ("Số người lớn trong search", "Số đếm"),
    "srch_children_count": ("Số trẻ em trong search", "Số đếm"),
    "srch_room_count": ("Số phòng trong search", "Số đếm"),
    "srch_saturday_night_bool": ("Cờ kỳ lưu trú có đêm thứ Bảy", "Nhị phân"),
    "srch_query_affinity_score": ("Điểm liên quan query–property do nguồn cung cấp", "Cần xác minh cách sinh và tính sẵn có"),
    "orig_destination_distance": ("Khoảng cách nguồn–điểm đến theo nguồn", "Đơn vị cần xác minh; không tự gán km"),
    "random_bool": ("Cờ danh sách được sắp ngẫu nhiên", "Phân tích ảnh hưởng vị trí; không tự suy ra exposure propensity"),
    "click_bool": ("Khách sạn có click trong search, 0/1", "Target/biến kết quả; không dùng click tương lai dự đoán trước click"),
    "gross_bookings_usd": ("Giá trị booking ghi nhận, USD", "Kết quả sau booking; presence gần như tiết lộ nhãn"),
    "booking_bool": ("Khách sạn được book trong search, 0/1", "Target"),
}
for _i in range(1,9):
    EXPEDIA_MEANINGS[f"comp{_i}_rate"] = (f"So sánh giá với đối thủ {_i}, mã phân loại", "Không coi mã -1/0/1 là giá; xác minh hướng so sánh theo nguồn")
    EXPEDIA_MEANINGS[f"comp{_i}_inv"] = (f"So sánh tồn phòng với đối thủ {_i}", "Mã phân loại; NA không phải không có đối thủ")
    EXPEDIA_MEANINGS[f"comp{_i}_rate_percent_diff"] = (f"Chênh lệch giá phần trăm đối thủ {_i}", "NA có thể theo điều kiện sinh dữ liệu; xác minh mẫu số/hướng")


EXPEDIA_NUM = ["visitor_hist_starrating","visitor_hist_adr_usd","prop_starrating","prop_review_score",
               "prop_location_score1","prop_location_score2","prop_log_historical_price","price_usd",
               "srch_length_of_stay","srch_booking_window","srch_adults_count","srch_children_count",
               "srch_room_count","srch_query_affinity_score","orig_destination_distance"]


def _combine_group(parts, keys):
    return pd.concat(parts).groupby(keys,observed=True,dropna=False).sum(numeric_only=True).reset_index()


def scan_expedia(path, training, store=None):
    """Exact full-file aggregates, plus every train numeric value in a disk cache."""
    from scripts.expedia_full_train import progress
    rows=0; missing=None; dtypes={}; sums={}; squares={}; ns={}; mins={}; maxs={}
    query_parts=[]; pairs_a=[]; pairs_b=[]; properties=set(); query_ids=set()
    numeric_cols=EXPEDIA_NUM+[f"comp{i}_rate_percent_diff" for i in range(1,9)]+(["gross_bookings_usd"] if training else [])
    minimum="9999"; maximum=""; book_no_click=0; booking_missing_gross=0; nonbooking_gross=0; bad_labels=0
    zero_price=0; negative_price=0; high_price=0; very_high_price=0
    cat_cols=["site_id","visitor_location_country_id","prop_country_id","prop_starrating","prop_brand_bool",
              "promotion_flag","srch_saturday_night_bool","random_bool"]
    dictionary_categories=cat_cols+["srch_destination_id"]+[f"comp{i}_{kind}" for i in range(1,9) for kind in ["rate","inv"]]+(["position","click_bool","booking_bool"] if training else [])
    cat_parts={c:[] for c in dictionary_categories}
    group_parts={c:[] for c in cat_cols+["price_group","window_group","year_month","random_bool_position"]} if training else {}
    for chunk in pd.read_csv(path,chunksize=CHUNK_SIZE):
        rows+=len(chunk)
        progress(f"{path.name}: {rows:,} rows")
        miss=chunk.isna().sum(); missing=miss if missing is None else missing.add(miss,fill_value=0)
        for c in chunk.columns: dtypes.setdefault(c,str(chunk[c].dtype))
        minimum=min(minimum,chunk.date_time.min()); maximum=max(maximum,chunk.date_time.max())
        properties.update(chunk.prop_id.unique()); query_ids.update(chunk.srch_id.unique())
        zero_price+=int(chunk.price_usd.eq(0).sum()); negative_price+=int(chunk.price_usd.lt(0).sum())
        high_price+=int(chunk.price_usd.gt(1000).sum()); very_high_price+=int(chunk.price_usd.gt(10000).sum())
        for c in numeric_cols:
            v=chunk[c].dropna().to_numpy(dtype=float)
            ns[c]=ns.get(c,0)+len(v); sums[c]=sums.get(c,0.)+float(v.sum()); squares[c]=squares.get(c,0.)+float((v*v).sum())
            if len(v): mins[c]=min(mins.get(c,np.inf),float(v.min())); maxs[c]=max(maxs.get(c,-np.inf),float(v.max()))
        if training:
            if store is None: raise ValueError("Full train diagnostics require an exact raw-column cache")
            store.append(chunk)
        for c in dictionary_categories:
            vc=chunk[c].value_counts(dropna=False).rename("n").reset_index()
            vc.columns=[c,"n"]; cat_parts[c].append(vc)
        pairs_a.append(chunk.srch_id.to_numpy(copy=True)); pairs_b.append(chunk.prop_id.to_numpy(copy=True))
        if training:
            book_no_click+=int((chunk.booking_bool.eq(1)&chunk.click_bool.eq(0)).sum())
            booking_missing_gross+=int((chunk.booking_bool.eq(1)&chunk.gross_bookings_usd.isna()).sum())
            nonbooking_gross+=int((chunk.booking_bool.eq(0)&chunk.gross_bookings_usd.notna()).sum())
            bad_labels+=int((~chunk.click_bool.isin([0,1])|~chunk.booking_bool.isin([0,1])).sum())
            query_diag=chunk.assign(_date_ns=pd.to_datetime(chunk.date_time,format="%Y-%m-%d %H:%M:%S").astype("int64"))
            query_parts.append(query_diag.groupby("srch_id",sort=False).agg(n=("prop_id","size"),clicks=("click_bool","sum"),bookings=("booking_bool","sum"),date_min=("_date_ns","min"),date_max=("_date_ns","max")))
            for c in cat_cols:
                group_parts[c].append(chunk.groupby(c,dropna=False).agg(n=("srch_id","size"),clicks=("click_bool","sum"),bookings=("booking_bool","sum")).reset_index())
            price_group=pd.cut(chunk.price_usd,[-np.inf,0,50,100,150,250,500,1000,np.inf],labels=["<=0","(0,50]","(50,100]","(100,150]","(150,250]","(250,500]","(500,1000]",">1000"])
            window_group=pd.cut(chunk.srch_booking_window,[-np.inf,0,7,30,90,180,365,np.inf],labels=["<=0","1–7","8–30","31–90","91–180","181–365",">365"])
            for name,labels in [("price_group",price_group),("window_group",window_group),("year_month",chunk.date_time.str[:7])]:
                tmp=pd.DataFrame({name:labels,"click_bool":chunk.click_bool,"booking_bool":chunk.booking_bool,"srch_id":chunk.srch_id})
                group_parts[name].append(tmp.groupby(name,observed=True,dropna=False).agg(n=("srch_id","size"),clicks=("click_bool","sum"),bookings=("booking_bool","sum")).reset_index())
            group_parts["random_bool_position"].append(chunk.groupby(["random_bool","position"],dropna=False).agg(n=("srch_id","size"),clicks=("click_bool","sum"),bookings=("booking_bool","sum")).reset_index())
        else:
            query_diag=chunk.assign(_date_ns=pd.to_datetime(chunk.date_time,format="%Y-%m-%d %H:%M:%S").astype("int64"))
            query_parts.append(query_diag.groupby("srch_id",sort=False).agg(n=("prop_id","size"),date_min=("_date_ns","min"),date_max=("_date_ns","max")))
    # Exact pair duplicate check, not a probabilistic hash duplicate count.
    pairs=pd.DataFrame({"srch_id":np.concatenate(pairs_a),"prop_id":np.concatenate(pairs_b)})
    duplicate_pairs=int(pairs.duplicated().sum())
    del pairs,pairs_a,pairs_b
    query=pd.concat(query_parts).groupby(level=0).agg({"n":"sum",**({"clicks":"sum","bookings":"sum"} if training else {}),"date_min":"min","date_max":"max"})
    stats=[]
    for c in numeric_cols:
        vns=ns[c]; mean=sums[c]/vns if vns else np.nan
        std=math.sqrt(max(0,(squares[c]-sums[c]*sums[c]/vns)/(vns-1))) if vns>1 else np.nan
        stats.append([c,vns,mean,std,mins.get(c,np.nan),maxs.get(c,np.nan)])
    stats=pd.DataFrame(stats,columns=["column","full_count_nonnull","full_mean","full_std","full_min","full_max"])
    if training:
        from scripts.expedia_full_train import full_numeric_statistics
        store.finish()
        stats=full_numeric_statistics(store,stats)
    cat={c:_combine_group(parts,[c]) for c,parts in cat_parts.items()}
    groups={c:_combine_group(parts,["random_bool","position"] if c=="random_bool_position" else [c]) for c,parts in group_parts.items()}
    for g in groups.values():
        g["click_pct"]=g.clicks/g.n*100; g["booking_pct"]=g.bookings/g.n*100
    return dict(rows=rows,missing=missing,dtypes=dtypes,stats=stats,store=store,queries=query,
                query_ids=query_ids,properties=properties,cat=cat,groups=groups,min_date=minimum,max_date=maximum,
                duplicate_pairs=duplicate_pairs,book_no_click=book_no_click,booking_missing_gross=booking_missing_gross,
                nonbooking_gross=nonbooking_gross,bad_labels=bad_labels,zero_price=zero_price,negative_price=negative_price,
                high_price=high_price,very_high_price=very_high_price)


def expedia_report(root):
    from scripts.expedia_full_train import TrainColumns
    inventory=manifest(root,"EXPEDIA")
    rows=int(inventory.set_index("file").loc["train.csv","data_lines"])
    numeric=EXPEDIA_NUM+[f"comp{i}_rate_percent_diff" for i in range(1,9)]+["gross_bookings_usd"]
    with TrainColumns(rows,numeric) as store:
        return _expedia_report(root,inventory,store)


def _expedia_report(root,inventory,store):
    r=Report("EXPEDIA","EXPEDIA — Hiểu tìm kiếm, click và booking ở cấp khách sạn hiển thị",root)
    folder=root/"data/raw/EXPEDIA"
    train=scan_expedia(folder/"train.csv",True,store)
    test=scan_expedia(folder/"test.csv",False)
    from scripts.expedia_full_train import exact_spearman
    train["correlation"],train["correlation_pairs"]=exact_spearman(store)
    n=train["rows"]; query=train["queries"]; groups=train["groups"]
    clicks=int(query.clicks.sum()); bookings=int(query.bookings.sum())
    r.facts=dict(rows=n,columns=len(train["missing"]),test_rows=test["rows"],test_columns=len(test["missing"]),
                 searches=len(query),clicks=clicks,bookings=bookings,click_rate=clicks/n,booking_rate=bookings/n,
                 booking_given_click=bookings/clicks,searches_without_click=int(query.clicks.eq(0).sum()),
                 duplicate_pairs=train["duplicate_pairs"],test_duplicate_pairs=test["duplicate_pairs"],
                 statistics_population="full_train",statistics_rows=n,numeric_statistics_columns=len(train["stats"]),
                 quantile_method="linear; all nonmissing train values",spearman_method="average ranks; pairwise-complete full train",
                 sampled_statistics=False,display_only_samples={"scatter_max_points":4000,"missing_pattern_rows":300})
    r.add("scope","1. Nguồn, đơn vị quan sát và câu hỏi propensity",f"""
Schema hiện có thuộc [Personalize Expedia Hotel Searches — ICDM 2013](https://www.kaggle.com/c/expedia-personalized-sort/data), khác cuộc thi Expedia Hotel Recommendations dự đoán hotel cluster. Train có **{count(n)} dòng, 54 cột**; test có **{count(test['rows'])} dòng, 50 cột**. Mỗi dòng là một cặp **search–property**, không phải một khách hàng hoặc một lượt search độc lập.

Hai nhãn là `click_bool` và `booking_bool`. Phù hợp với click/booking propensity trong ngữ cảnh danh sách tìm kiếm, hoặc nghiên cứu xếp hạng. Không có ID người dùng để trực tiếp hình thành bài toán CRM theo khách hàng; `srch_id` chỉ định danh lượt tìm kiếm.

Câu hỏi EDA: cấu trúc nhóm, quan hệ click–booking, khác biệt tỷ lệ theo ngữ cảnh/khách sạn/vị trí, thiếu dữ liệu theo nhóm cột, khác train–test, và giới hạn suy rộng tỷ lệ từ tập dữ liệu quan sát.
""",[("Danh mục file; ba benchmark là thứ tự kết quả trên test, không phải dữ liệu train bổ sung",inventory)])
    unknown=set(train["missing"].index)-set(EXPEDIA_MEANINGS)
    if unknown: raise ValueError(f"Missing Expedia dictionary entries: {unknown}")
    schema=pd.DataFrame([[c,train["dtypes"][c],int(train["missing"][c]),train["missing"][c]/n*100,c in test["missing"].index,*EXPEDIA_MEANINGS[c]] for c in train["missing"].index],columns=["column","pandas_dtype","full_missing_n","full_missing_pct","in_test","meaning","role_or_caution"])
    r.add("dictionary","2. Từ điển đủ 54 cột và schema train–test","Các ID được đọc thành số nhưng mang ý nghĩa phân loại. Nhóm đối thủ có **8 × 3 = 24 cột**, không phải 16. Bốn cột chỉ có ở train là position, click_bool, booking_bool, gross_bookings_usd. Sau khi tách bốn cột này, có 50 cột chung với test; đây là số cột schema, chưa phải số feature được phê duyệt sử dụng. Nếu srch_id chỉ làm khóa nhóm thì còn 49 cột ứng viên; prop_id vẫn cần quyết định cách dùng phù hợp ở giai đoạn sau.",[("Schema và missing toàn bộ train",schema)])
    coverage=pd.DataFrame([
        ["Quy mô, khóa, missing, nhãn, category, nhóm, thời gian",n,"Toàn bộ train; không lấy mẫu"],
        ["Mean/std/min/max, p1/p25/p50/p75/p95/p99, skewness",n,"Toàn bộ giá trị không thiếu của từng biến; count_nonnull tại phụ lục"],
        ["IQR, số đếm outlier và boxplot",n,"Toàn bộ giá trị không thiếu; giữ nguyên outlier"],
        ["Spearman của 9 biến công bố",n,"Toàn bộ cặp không thiếu; số dòng từng cặp tại phụ lục"],
        ["Missing theo booking và tương quan cờ thiếu",n,"Toàn bộ train"],
        ["Scatter / hình pattern missing",n,"Chỉ hiển thị tối đa 4.000 điểm / 300 dòng; không tính thống kê từ mẫu hiển thị"],
    ],columns=["analysis","source_train_rows","method"])
    r.add("method","3. Phương pháp tính: toàn bộ tập train",f"""
**Mọi thống kê train dùng toàn bộ {count(n)} dòng thuộc {count(len(query))} searches.** CSV được quét theo chunk {count(CHUNK_SIZE)} dòng; cột số raw và cờ NA được đệm tạm trên đĩa để tính chính xác trong RAM giới hạn. Cache bị xóa sau khi xuất báo cáo, không phải tập processed hay feature.

Phân vị dùng nội suy tuyến tính trên toàn bộ giá trị không thiếu; std dùng ddof=1 và skewness không chệch theo pandas. IQR và số đếm outlier dùng cùng quần thể đầy đủ. Spearman tính thứ hạng trung bình khi trùng giá trị, bỏ NA và xếp hạng lại riêng từng cặp. Không dùng quantile sketch hoặc mẫu 5% cho thống kê.

**Chỉ lấy mẫu để hiển thị:** scatter tối đa 4.000 điểm và hình pattern missing 300 dòng, seed=42. Histogram, boxplot, heatmap tương quan, bảng missing theo nhãn và mọi kết luận định lượng dùng toàn bộ train. Phạm vi trục giá 0–1.000 USD chỉ là cửa sổ hiển thị; số dòng ngoài cửa sổ được công bố, không bị xóa khỏi thống kê.

Test được quét đầy đủ để đối chiếu schema, khóa, missing, mean/std/min/max và phân phối category/thời gian; không gộp test vào thống kê train. Khóa ghép (srch_id,prop_id) được kiểm tra bằng cặp ID thật. Danh mục file có SHA-256 để nhận diện phiên bản nguồn.
""",[("Phạm vi tính toán từng phân tích",coverage)])
    query_summary=pd.DataFrame([["train",len(query),query.n.mean(),query.n.median(),query.n.min(),query.n.max(),int(query.date_min.ne(query.date_max).sum())],
                                ["test",len(test['queries']),test['queries'].n.mean(),test['queries'].n.median(),test['queries'].n.min(),test['queries'].n.max(),int(test['queries'].date_min.ne(test['queries'].date_max).sum())]],columns=["population","searches","mean_properties","median_properties","min_properties","max_properties","searches_multiple_timestamps"])
    checks=pd.DataFrame([["Train: cặp srch_id-prop_id trùng (beyond first)",train["duplicate_pairs"]],["Test: cặp srch_id-prop_id trùng",test["duplicate_pairs"]],["srch_id xuất hiện cả train và test",len(train["query_ids"]&test["query_ids"])],["prop_id xuất hiện cả train và test",len(train["properties"]&test["properties"])],["Train: search không click",int(query.clicks.eq(0).sum())],["Train: search có >1 booking",int(query.bookings.gt(1).sum())],["Train: booking=1 nhưng click=0",train["book_no_click"]],["Train: booking=1 nhưng gross thiếu",train["booking_missing_gross"]],["Train: booking=0 nhưng gross có giá trị",train["nonbooking_gross"]],["Train: nhãn ngoài {0,1} hoặc thiếu",train["bad_labels"]]],columns=["check","n"])
    targets=pd.DataFrame([["Click / cặp search-property",clicks,n,clicks/n*100],["Booking / cặp search-property",bookings,n,bookings/n*100],["Booking / cặp đã click",bookings,clicks,bookings/clicks*100],["Search có booking / toàn bộ search train",int(query.bookings.gt(0).sum()),len(query),query.bookings.gt(0).mean()*100]],columns=["metric","numerator","denominator","pct"])
    r.add("quality","4. Cấu trúc nhóm, nhãn và giới hạn quần thể",f"""
Train gồm **{count(len(query))} searches**, trung bình **{query.n.mean():.2f} khách sạn/search**. Có **{count(query.clicks.eq(0).sum())} search không click** trong tập train. Vì vậy tập đang phân tích không có nhóm search hoàn toàn không tương tác; không ước lượng tỷ lệ mọi người dùng trên website quyết định click từ tỷ lệ 4–5% trên các dòng này.

Trong raw, mọi booking đều có click ở cùng cặp search–property; tỷ số bookings/clicks là thống kê có điều kiện đúng trên tập hiện tại. Nó không chứng minh việc làm tăng click sẽ gây tăng booking, không tự xác lập chiến lược marketing hay hiệu quả triển khai.

`gross_bookings_usd` là thông tin sau booking. Giá trị hiện diện chỉ ở dòng có booking; có {count(train['booking_missing_gross'])} booking bị thiếu gross. Không impute cột kết quả này thành feature. `position` là vị trí hiển thị quan sát được và không có trong test. Click thực tế không phải đầu vào hợp lệ của mô hình dự đoán trước click.

Các dòng trong một search phụ thuộc nhau. Vì vậy không đưa khoảng tin cậy nhị thức giả định mọi impression độc lập; nếu cần suy luận ở giai đoạn sau, phải xét cấu trúc nhóm. Nhóm khóa không trùng không đồng nghĩa người dùng độc lập vì không có user ID.
""",[("Kích thước danh sách theo search",query_summary),("Kiểm tra khóa và tính nhất quán kết quả",checks),("Tỷ lệ với tử số/mẫu số cụ thể — toàn bộ train",targets)])
    price_checks=pd.DataFrame([[pop,s["rows"],s["zero_price"],s["negative_price"],s["high_price"],s["very_high_price"]] for pop,s in [("train",train),("test",test)]],columns=["population","rows","price_zero","price_negative","price_above_1000","price_above_10000"])
    missing_compare=pd.DataFrame({"column":train["missing"].index,"train_missing_pct":train["missing"].to_numpy()/n*100,"test_missing_pct":[test["missing"].get(c,np.nan)/test["rows"]*100 for c in train["missing"].index]})
    comp=missing_compare[missing_compare.column.str.startswith("comp")]
    r.add("missing","5. Missing, giá trị đặc biệt và chất lượng giá","Missing được trình bày đủ các cột ở phần schema, với so sánh train–test bên dưới. Nhóm comp có mức thiếu rất khác nhau theo đối thủ và loại thuộc tính; không suy từ top 15 cột thiếu nhiều nhất rằng cả nhóm đều thiếu >93%. Không có dữ liệu đối thủ không chứng minh khách sạn không có đối thủ. Thiếu lịch sử khách không đủ để kết luận khách mới/chưa đăng nhập. Giá 0 và giá cực lớn được định lượng bằng ngưỡng kiểm tra công bố trước; không tự kết luận lỗi, đổi đơn vị hoặc clipping. Định nghĩa giá theo đêm/toàn kỳ chưa được xác minh từ CSV.",[("Toàn bộ 24 cột đối thủ — missing theo tập",comp),("Missing các cột ngoài comp",missing_compare[~missing_compare.column.str.startswith("comp")]),("Kiểm tra đuôi giá trên toàn bộ dữ liệu",price_checks)])
    fig,axes=plt.subplots(1,2,figsize=(13,4))
    prices=store.arrays["price_usd"]
    hist,edges=np.histogram(prices,bins=np.linspace(0,1000,51))
    axes[0].stairs(hist,edges,fill=True,color=COLORS[0]); axes[0].set(title=f"All train prices: 0–1000; {count(n-int(hist.sum()))} outside/NA",xlabel="Displayed price (USD)",ylabel="Train rows")
    axes[1].hist(query.n,bins=np.arange(4.5,float(query.n.max())+1.5),color=COLORS[1]); axes[1].set(title="All train queries: candidate-list sizes",xlabel="Properties per search",ylabel="Searches"); fig.tight_layout()
    cats=[]
    for c,t in train["cat"].items():
        z=t.sort_values("n",ascending=False).head(12).copy(); z["pct_all_rows"]=z.n/n*100; z.insert(0,"column",c); z=z.rename(columns={c:"value"}); cats.append(z)
    r.add("distributions","6. Phân phối định lượng và phân loại","Mọi cột full_* trong bảng train dùng toàn bộ giá trị không thiếu, gồm cả percentile và skewness. Mean/std nhạy với giá cực lớn; đọc cùng median/p95/p99 và max của cùng quần thể. Bảng có 24 biến định lượng, gồm 8 tỷ lệ chênh giá đối thủ và gross_bookings_usd (cột kết quả, không phải feature). Test chỉ đối chiếu thống kê cơ bản, không tính percentile mẫu. Tỷ trọng category tính theo cặp search-property, không phải khách hoặc search; search nhiều khách sạn đóng góp nhiều dòng hơn.",[("Train: thống kê chính xác toàn bộ giá trị không thiếu",train["stats"]),("Test: đối chiếu count/mean/std/min/max toàn file",test["stats"]),("Top 12 category/cột — toàn bộ train",pd.concat(cats,ignore_index=True))],[r.savefig("distributions",fig)])
    group_tables=[]
    for c in ["prop_starrating","prop_brand_bool","promotion_flag","srch_saturday_night_bool","site_id","price_group","window_group"]:
        t=groups[c].copy(); t["n_under_100"]=t.n<100
        group_tables.append((f"Tỷ lệ click/booking theo {c}; mẫu số là số cặp trong nhóm",t))
    r.add("target","7. Mối liên hệ với click/booking theo nhóm","Tất cả bảng dùng toàn bộ train. Phân nhóm giá và booking window chỉ là công cụ đọc bảng EDA; không xuất feature. Tỷ lệ có thể phản ánh vị trí hiển thị, thành phần search, thương hiệu, thời gian và cơ chế chọn mẫu cùng lúc. Không coi chênh lệch promotion_flag là uplift từ khuyến mãi. Bảng không kiểm định nhiều giả thuyết hoặc khẳng định quan hệ nhân quả.",group_tables)
    pos=groups["random_bool_position"]
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for i,(flag,z) in enumerate(pos.groupby("random_bool")):
        z=z.sort_values("position")
        axes[0].plot(z.position,z.click_pct,label=f"random_bool={flag}",color=COLORS[i%len(COLORS)])
        axes[1].plot(z.position,z.booking_pct,label=f"random_bool={flag}",color=COLORS[i%len(COLORS)])
    axes[0].set(title="Observed rates by displayed position",ylabel="Click (%)"); axes[0].legend()
    axes[1].set(ylabel="Booking (%)",xlabel="Displayed position"); fig.tight_layout()
    r.add("position","8. Vị trí hiển thị và cơ chế tiếp xúc","`position` và `random_bool` cần được đọc cùng nhau: khách sạn được hiển thị ở vị trí khác nhau có cơ hội được xem/click khác nhau. Biểu đồ mô tả liên hệ trong từng giá trị cờ; không ước lượng tác động nhân quả của vị trí, xác suất exposure hoặc áp dụng hiệu chỉnh bias. Theo [nghiên cứu dùng dữ liệu Expedia](https://hamsabastani.github.io/proxies.pdf), random_bool=1 đánh dấu danh sách được sắp ngẫu nhiên; vẫn cần xác minh định nghĩa và quy trình tạo tập trước khi suy luận can thiệp. Không dùng position làm feature mặc định cho schema test hiện có.",[("Toàn bộ random_bool × position, giữ số dòng mỗi ô",pos.sort_values(["random_bool","position"]))],[r.savefig("position",fig)])
    temporal=groups["year_month"].sort_values("year_month")
    date_ranges=pd.DataFrame([[pop,s["min_date"],s["max_date"],len(s["queries"])] for pop,s in [("train",train),("test",test)]],columns=["population","min_date_time","max_date_time","searches"])
    tv=[]
    for c in sorted(train["cat"].keys() & test["cat"].keys()):
        a=train["cat"][c].set_index(c).n/n; b=test["cat"][c].set_index(c).n/test["rows"]
        idx=a.index.union(b.index); tv.append([c,(a.reindex(idx,fill_value=0)-b.reindex(idx,fill_value=0)).abs().sum()/2,len(b.index.difference(a.index))])
    fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True)
    axes[0].bar(temporal.year_month,temporal.n,color=COLORS[0]); axes[0].set(title="All train rows by search month",ylabel="Search–property rows")
    axes[1].plot(temporal.year_month,temporal.click_pct,label="Click",color=COLORS[0]); axes[1].plot(temporal.year_month,temporal.booking_pct,label="Booking",color=COLORS[1]); axes[1].set(ylabel="% of rows",xlabel="Search month"); axes[1].legend(); fig.tight_layout()
    r.add("time","9. Thời gian và so sánh train–test","Khoảng thời gian và phân bố category được tính trực tiếp, không giả định test nằm sau train. Tháng đầu/cuối có thể không đầy đủ. Total variation so sánh phân phối category ở cấp dòng, không đại diện đầy đủ cho drift ở cấp search/user. Test không có nhãn nên không tính click/booking rate cho test. Bất kỳ đánh giá tương lai nào ở giai đoạn sau cần giữ nguyên srch_id trong một tập và thiết kế thời gian theo mục tiêu triển khai; chưa thực hiện chia tập ở đây.",[("Khoảng thời gian toàn bộ mỗi tập",date_ranges),("Train: tỷ lệ theo tháng",temporal),("Khác biệt category train–test, toàn bộ dòng",pd.DataFrame(tv,columns=["column","total_variation_0_1","test_only_categories"]).sort_values("total_variation_0_1",ascending=False))],[r.savefig("calendar",fig)])
    pairs=train["correlation_pairs"].sort_values("full_spearman_rho",key=abs,ascending=False)
    r.add("dependencies","10. Phụ thuộc giữa các biến trên toàn bộ train","Spearman dùng toàn bộ dòng không thiếu của từng cặp trong 9 biến công bố, xếp hạng lại sau khi bỏ NA. Số dòng hợp lệ được báo riêng từng cặp. Đây là thống kê mô tả, chưa chọn feature; biến ngữ cảnh lặp cho nhiều khách sạn cùng search nên số dòng không phải số người độc lập. Giá, sao, vị trí và giá lịch sử có thông tin chồng lặp; chưa loại hoặc kết hợp cột.",[("12 cặp có |rho| lớn nhất — toàn bộ train",pairs.head(12)),("Đủ 36 cặp và số dòng không thiếu của từng cặp",pairs)])
    r.add("conclusions","11. Kết luận và câu hỏi còn mở",f"""
**Đã kiểm chứng trên toàn bộ train:** {count(n)} cặp search-property thuộc {count(len(query))} searches; click {pct(clicks/n)}, booking {pct(bookings/n)}, booking/click {pct(bookings/clicks)}. Không có search hoàn toàn không click trong tập train hiện tại. Số cột đối thủ là 24 và tỷ lệ missing khác nhau mạnh theo đối thủ. Gross bookings là kết quả; position không có trong test.

**Mức độ phù hợp:** phù hợp nghiên cứu propensity/xếp hạng ở cấp khách sạn trong search, chưa phải propensity marketing theo user hoặc CTR/CVR toàn website. Two-stage click/booking là một khả năng định nghĩa bài toán, không phải kết luận bắt buộc từ tỷ số booking/click cao.

**Cần xác minh:** cơ chế đưa search vào dữ liệu và nhóm không click bị thiếu; tính sẵn có của từng điểm do Expedia sinh; nghĩa/đơn vị và cách hình thành giá; quy trình random_bool; khả năng nhận diện người dùng và lần tìm kiếm lặp; phạm vi áp dụng ngoài dữ liệu lịch sử.

Không class weighting, resampling, imputation, clipping, encoding, feature engineering hay train/rank model. Không tạo tập processed hoặc tự quyết định loại cột missing cao. Các câu hỏi và thống kê ở đây phục vụ hiểu dữ liệu trước giai đoạn tiếp theo.
""")
    from scripts.eda_diagnostics import enrich_expedia
    enrich_expedia(r,train,test)
    return r.publish()


def build_report(dataset, root):
    return {"HOTEL":hotel_report,"AIRBNB":airbnb_report,"EXPEDIA":expedia_report}[dataset](Path(root))


def make_notebook(root, dataset):
    import nbformat as nbf
    from scripts.eda_diagnostics import SECTION_LAYOUT
    titles = {dataset: [title for key,title in SECTION_LAYOUT]}
    keys = {dataset: [key for key,title in SECTION_LAYOUT]}
    cells = [nbf.v4.new_markdown_cell(f"# {dataset} — Báo cáo hiểu sâu dữ liệu\n\n**Phạm vi: EDA trên dữ liệu gốc; chưa feature engineering, chưa huấn luyện mô hình.**\n\nBáo cáo có từ điển dữ liệu, kiểm tra chất lượng/khóa/nhãn, thống kê theo nhóm, thời gian và giới hạn suy rộng. Các kết quả được tính lại từ CSV; bản đọc nhanh nằm ở `reports/{dataset}/README.md`.\n\nMọi phân nhóm tạm thời chỉ phục vụ mô tả, không tạo tập feature. Chạy tất cả các cell theo thứ tự; cell đầu quét dữ liệu đầy đủ nên có thể mất vài phút với Expedia. Phần tóm tắt điều hành nằm đầu; bảng kiểm kê dài chuyển sang phụ lục. Mỗi hình có nhận xét riêng ngay bên dưới."),
             nbf.v4.new_code_cell("from pathlib import Path\nimport importlib\nimport sys\n\nPROJECT_ROOT = Path.cwd().resolve()\nwhile not (PROJECT_ROOT / 'data' / 'raw').is_dir():\n    if PROJECT_ROOT == PROJECT_ROOT.parent:\n        raise FileNotFoundError('Không tìm thấy data/raw; hãy mở notebook trong dự án Propensity.')\n    PROJECT_ROOT = PROJECT_ROOT.parent\nif str(PROJECT_ROOT) not in sys.path:\n    sys.path.insert(0, str(PROJECT_ROOT))\nfrom scripts import build_descriptive_reports as eda\nimportlib.reload(eda)\n"+f"report = eda.build_report('{dataset}', PROJECT_ROOT)\n"+"print('Đã tính lại từ CSV raw; số chính:', report.facts)\nprint('Chỉ xuất báo cáo, metadata và biểu đồ; không tạo dữ liệu mô hình.')")]
    if dataset == "AIRBNB":
        from scripts.airbnb_deep_dive import AIRBNB_LAYOUT
        keys[dataset] = [key for key, _ in AIRBNB_LAYOUT]
        titles[dataset] = [title for _, title in AIRBNB_LAYOUT]
        introduction = """# AIRBNB — Báo cáo dữ liệu và thiết kế nghiên cứu propensity

**Phạm vi:** notebook phân tích mô tả dữ liệu gốc, gồm nhãn y, độ trễ và các nhóm đăng ký theo thời gian. Báo cáo đề xuất thiết kế thí nghiệm cho giai đoạn tiếp theo. Mọi số liệu là thống kê mô tả, chưa phải kết quả mô hình hoặc bằng chứng về tác động nhân quả.

Bảng thuật ngữ và tóm tắt điều hành nằm ở đầu phần kết quả. Các bảng chi tiết được chuyển xuống phụ lục để thuận tiện tra cứu.

Notebook có output lưu sẵn để đọc ngay. **Notebook phụ thuộc package scripts/ và CSV của dự án; một file notebook riêng không chạy độc lập.** Khi nộp cần kèm code và hướng dẫn lấy dữ liệu sau:

    Propensity/
      scripts/
        __init__.py
        build_descriptive_reports.py
        eda_diagnostics.py
        airbnb_deep_dive.py
      data/raw/AIRBNB/
        train_users_2.csv
        test_users.csv
        sessions.csv
        countries.csv
        age_gender_bkts.csv
      notebooks/AIRBNB/airbnb_descriptive_report.ipynb

CSV lấy từ cuộc thi Airbnb New User Bookings, không có trong Git. File sample_submission_NDF.csv là tùy chọn để kiểm kê, không dùng phân tích người dùng. Xem báo cáo Markdown được tạo tại reports/AIRBNB/README.md sau khi chạy.

Môi trường EDA đã kiểm tra: Python 3.14.2; pandas 2.3.3, numpy 2.4.1, scipy 1.17.1, matplotlib 3.10.8, nbformat 5.10.4 và IPython 9.9.0. Có thể cài các thư viện EDA trong môi trường riêng bằng:

    python -m pip install pandas==2.3.3 numpy==2.4.1 scipy==1.17.1 matplotlib==3.10.8 nbformat==5.10.4 ipython==9.9.0 tzdata

Dùng Jupyter với kernel của môi trường đó, Restart Kernel và Run All từ đầu; hoặc chạy python scripts/build_descriptive_reports.py --dataset AIRBNB ở thư mục gốc. Lần chạy tạo lại báo cáo, hình và metadata từ CSV; ngày thực thi được lưu trong metadata notebook. Seed hiển thị hình =42. **Ngày tải raw không được lưu**, đã được người cung cấp xác nhận; dùng SHA-256 để đối chiếu snapshot.
"""
        setup = """from pathlib import Path
import importlib
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

cwd = Path.cwd().resolve()
PROJECT_ROOT = next((p for p in (cwd, *cwd.parents)
                     if (p / 'scripts' / 'build_descriptive_reports.py').is_file()), None)
if PROJECT_ROOT is None:
    raise FileNotFoundError('Notebook cần package scripts/ của dự án; xem cấu trúc thư mục trong ô mở đầu.')
required = [PROJECT_ROOT / 'scripts' / name for name in
            ['__init__.py', 'build_descriptive_reports.py', 'eda_diagnostics.py', 'airbnb_deep_dive.py']]
required += [PROJECT_ROOT / 'data' / 'raw' / 'AIRBNB' / name for name in
             ['train_users_2.csv', 'test_users.csv', 'sessions.csv', 'countries.csv', 'age_gender_bkts.csv']]
missing = [str(p.relative_to(PROJECT_ROOT)) for p in required if not p.is_file()]
if missing:
    raise FileNotFoundError('Thiếu file để chạy lại Airbnb: ' + ', '.join(missing))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from scripts import build_descriptive_reports as eda
importlib.reload(eda)
report = eda.build_report('AIRBNB', PROJECT_ROOT)
print('Ngày tính lại (Asia/Ho_Chi_Minh):', datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat())
print('Đã tính EDA từ CSV raw; số chính:', report.facts)
print('Không tạo tập feature, tập chia hoặc mô hình. Ngày tải: không được lưu; snapshot theo SHA-256.')
"""
        cells = [nbf.v4.new_markdown_cell(introduction), nbf.v4.new_code_cell(setup)]
    for key,title in zip(keys[dataset],titles[dataset]):
        cells += [nbf.v4.new_markdown_cell(f"## {title}"),nbf.v4.new_code_cell(f"eda.show_section(report, '{key}')")]
    nb=nbf.v4.new_notebook(cells=cells)
    nb.metadata.update(kernelspec={"display_name":"Python 3 (ipykernel)","language":"python","name":"python3"},language_info={"name":"python","version":platform.python_version()})
    return nb


def write_summary(root):
    facts={d:json.loads((root/"reports"/d/"analysis_metadata.json").read_text(encoding="utf-8"))["facts"] for d in ["HOTEL","AIRBNB","EXPEDIA"]}
    h,a,e=(facts[d] for d in ["HOTEL","AIRBNB","EXPEDIA"])
    text=f"""# Báo cáo tổng hợp: mức độ phù hợp và hiểu sâu ba bộ dữ liệu

Ngày phân tích: {datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date().isoformat()}. Phạm vi là dữ liệu CSV hiện có trong dự án, không phải dữ liệu kinh doanh hiện tại. **Chưa feature engineering, chưa làm sạch/thay thế dữ liệu, chưa chia tập huấn luyện, chưa train mô hình.**

## Tóm tắt điều hành — 7 phát hiện có bằng chứng

1. **Ba đơn vị quan sát khác nhau:** HOTEL {count(h['rows'])} booking; AIRBNB {count(a['rows'])} users train; EXPEDIA {count(e['rows'])} cặp search-property. Không so trực tiếp conversion rate giữa ba mẫu số.
2. **HOTEL nhạy với duplicate:** {count(h['duplicates'])} dòng trùng; tỷ lệ hủy/no-show {pct(h['rate'])} ở raw so với {pct(h['deduplicated_rate'])} nếu giả định bỏ hết trùng. Bảng độ nhạy trong báo cáo HOTEL giải thích giới hạn.
3. **AIRBNB có leakage rõ:** presence `date_first_booking` khớp hoàn toàn nhãn có booking; không dùng ngày/cờ thiếu làm đầu vào. Xem bảng chéo và heatmap missing của AIRBNB.
4. **Độ phủ log AIRBNB cần so cùng cohort:** train 2014 {a.get('train_2014_session_coverage_pct',96.5331):.2f}% so với test 2014 {pct(a['test_session_users']/a['test_rows'])}; tỷ lệ train toàn kỳ {pct(a['train_session_users']/a['rows'])} thấp chủ yếu vì cohort 2010–2013 không có log. Sessions chưa được xác nhận trước t0.
5. **EXPEDIA thiếu quần thể không tương tác:** train có {count(e['searches'])} searches và {count(e['searches_without_click'])} search hoàn toàn không click; không coi CTR {pct(e['click_rate'])} là CTR toàn website.
6. **Đuôi giá và missing cần quy tắc rõ:** mỗi bộ đã có bảng hàng rào 1,5×IQR, tỷ lệ outlier, heatmap missing và ma trận tương quan. Expedia tính percentile, skewness, outlier, Spearman và missing theo nhãn trên toàn bộ train; chỉ scatter/pattern missing giới hạn số điểm hiển thị. Số liệu nằm cạnh hình ở từng báo cáo.
7. **Khả năng sử dụng có điều kiện:** HOTEL cho hủy/no-show, AIRBNB cho booking đầu ở cấp user, EXPEDIA cho search/ranking. Tất cả còn câu hỏi về t0/phạm vi áp dụng; ngày tải raw chưa được ghi nhận, giấy phép/điều khoản được trình bày tại nguồn của từng bộ, không gán mặc định quyền sử dụng mở.

Các báo cáo chi tiết cùng cấu trúc: tổng quan nguồn/phiên bản → chất lượng → đơn biến → đa biến/thời gian/nhóm con → rủi ro → kết luận và đề xuất; executive summary ở đầu, từ điển/bảng dài ở phụ lục. Mỗi hình có nhận xét định lượng ngay bên dưới. Đề xuất xử lý thiếu, mã hóa, feature engineering và mô hình chỉ là hướng cho giai đoạn sau, chưa thực hiện.

## 1. Kết luận phục vụ lựa chọn bài toán

Ba bộ dữ liệu phù hợp với ba hành vi và ba đơn vị dự đoán khác nhau. Propensity ở đây là xác suất hành vi; không phải propensity score nhận treatment hoặc ước lượng uplift. Chưa có thông tin can thiệp để kết luận tác động marketing.

| Bộ | Hành vi phù hợp | Đơn vị | Giới hạn quyết định |
| --- | --- | --- | --- |
| HOTEL | Hủy/no-show của booking | Booking | Không đồng nghĩa customer churn; cần xác minh snapshot tại thời điểm dự đoán |
| AIRBNB | Có booking đầu được ghi nhận; hoặc điểm đến đầu | Người dùng mới | Chưa có nhãn horizon 30/60/90 ngày chuẩn hóa; sessions thiếu timestamp và lệch độ phủ |
| EXPEDIA | Click/booking trong danh sách khách sạn | Cặp search-property | Phù hợp bối cảnh tìm kiếm/xếp hạng; không có ID khách để chấm CRM; thiếu search không click trong train |

Nếu đề tài nhắm đến chuyển đổi khách hàng mới, AIRBNB phù hợp về đơn vị quan sát. Nếu nghiên cứu vận hành hủy booking, HOTEL rõ mục tiêu và nhẹ hơn. Nếu nghiên cứu tương tác với danh sách tìm kiếm, EXPEDIA phù hợp hơn. Không xếp một bộ là tốt nhất cho mọi mục tiêu và không coi mọi cột thô là feature hợp lệ.

## 2. Quy mô đã đối chiếu trực tiếp

| File | Quan sát | Cột thô | Ý nghĩa dòng |
| --- | ---: | ---: | --- |
| HOTEL/hotel_bookings.csv | {count(h['rows'])} | 32 | Booking |
| AIRBNB/train_users_2.csv | {count(a['rows'])} | 16 | User train |
| AIRBNB/test_users.csv | {count(a['test_rows'])} | 15 | User test không có nhãn |
| AIRBNB/sessions.csv | {count(a['sessions'])} | 6 | Sự kiện, không phải thêm user |
| AIRBNB/countries.csv | 10 | 7 | Quốc gia |
| AIRBNB/age_gender_bkts.csv | 420 | 5 | Ô thống kê nhóm tuổi/giới tính/quốc gia |
| EXPEDIA/train.csv | {count(e['rows'])} | 54 | Cặp search-property |
| EXPEDIA/test.csv | {count(e['test_rows'])} | 50 | Cặp search-property không nhãn |

File submission Airbnb có 62.096 dòng × 2 cột; mỗi benchmark Expedia có 6.622.629 dòng × 2 cột. Đây là file định dạng/kết quả tham khảo, không phải dữ liệu huấn luyện bổ sung. Chi tiết file, dung lượng theo bytes và SHA-256 có trong từng báo cáo.

**Số cột ứng viên, chưa phải số feature cuối:** HOTEL có 31 cột ngoài target, còn 29 sau khi tách hai cột trạng thái cuối; các cột khác vẫn phải kiểm tra khả dụng tại t0. AIRBNB có 13 cột sau khi tách target, id và date_first_booking. EXPEDIA có 50 cột chung với test sau khi tách position, click_bool, booking_bool và gross_bookings_usd; nếu srch_id chỉ làm khóa nhóm còn 49 cột ứng viên. Chưa mã hóa, tạo feature hoặc chọn cột đầu vào cuối cùng.

## 3. Nhãn và mẫu số: không so sánh lẫn đơn vị

| Bộ / hành vi | Tử số | Mẫu số | Tỷ lệ trong dữ liệu |
| --- | ---: | ---: | ---: |
| HOTEL: hủy/no-show | {count(h['positive'])} | {count(h['rows'])} booking | {pct(h['rate'])} |
| AIRBNB: có booking được ghi nhận | {count(a['positive'])} | {count(a['rows'])} user train | {pct(a['rate'])} |
| EXPEDIA: click | {count(e['clicks'])} | {count(e['rows'])} cặp | {pct(e['click_rate'])} |
| EXPEDIA: booking | {count(e['bookings'])} | {count(e['rows'])} cặp | {pct(e['booking_rate'])} |
| EXPEDIA: booking / click | {count(e['bookings'])} | {count(e['clicks'])} cặp đã click | {pct(e['booking_given_click'])} |

Tỷ lệ theo booking, user và cặp search-property trả lời các câu hỏi khác nhau. Không dùng chúng để kết luận nền tảng nào chuyển đổi tốt hơn. Tỷ số booking/click cao là liên hệ trong dữ liệu quan sát, không chứng minh click gây booking hoặc cải thiện ranking sẽ tạo mức tăng doanh thu tương ứng.

## 4. Các phát hiện thay đổi cách sử dụng dữ liệu

### HOTEL

- Nhãn 1 bao gồm Canceled và No-Show. `reservation_status` xác định hoàn toàn nhãn; `reservation_status_date` cũng thuộc thông tin kết quả.
- Có {count(h['duplicates'])} dòng trùng hoàn toàn. Nếu giả định bỏ mọi dòng trùng, còn {count(h['deduplicated_rows'])} booking và tỷ lệ nhãn 1 thành {pct(h['deduplicated_rate'])}, so với {pct(h['rate'])} ở raw. Đây là phân tích độ nhạy, không phải quyết định xóa.
- Không có booking/customer ID để xác định nguyên nhân trùng hoặc nhận diện khách qua nhiều booking. Một booking bị hủy không chứng minh customer churn.
- Snapshot gốc không đồng nghĩa mọi cột có sẵn lúc tạo booking. Booking changes, phân phòng, đặt cọc, ADR và yêu cầu bổ sung cần được kiểm chứng theo t0.
- Phân tích năm–tháng tách theo khách sạn tránh nhầm số lần tháng được quan sát với mùa vụ.

### AIRBNB

- Presence của `date_first_booking` khớp hoàn toàn nhãn có booking trong train, nên không dùng nó hoặc cờ missing của nó làm đầu vào dự đoán hành vi đó.
- Có {count(a['session_users'])} user_id khác nhau không thiếu trong sessions, không phải tất cả thuộc train. So cùng cohort 2014: train {count(a.get('train_2014_session_users',73815))}/{count(a.get('train_2014_users',76466))} ({a.get('train_2014_session_coverage_pct',96.5331):.2f}%), test {count(a['test_session_users'])}/{count(a['test_rows'])} ({pct(a['test_session_users']/a['test_rows'])}). Tỷ lệ train toàn kỳ {pct(a['train_session_users']/a['rows'])} chịu hiệu ứng thành phần cohort. Có {count(a['sessions_missing_ids'])} sự kiện thiếu user_id.
- Độ phủ sessions gắn với năm account; thiếu log không đồng nghĩa khách không hoạt động. Logs không có timestamp sự kiện để xác nhận trước t0/booking.
- NDF không có nghĩa không bao giờ book; chưa có horizon nhãn chung được xác nhận. Nhãn gốc có 12 giá trị, còn 11 giá trị điểm đến/other sau khi chỉ xét người có booking.
- Bảng quốc gia không được ghép bằng nhãn thật để dự đoán chính nhãn đó; bảng tuổi–giới tính là tổng hợp, không phải user bổ sung.

### EXPEDIA

- Đã quét toàn bộ {count(e['rows'])} dòng train và {count(e['test_rows'])} dòng test. Toàn bộ thống kê train, gồm percentile, skewness, outlier, missing theo nhãn và tương quan, dùng đầy đủ các dòng hợp lệ. Test chỉ đối chiếu schema/chất lượng và phân phối tổng hợp.
- Train có {count(e['searches'])} searches, **{count(e['searches_without_click'])} search không click**. Không suy rộng tỷ lệ trong tập thành tỷ lệ tương tác của toàn website; cần xác minh cơ chế chọn mẫu.
- `gross_bookings_usd` là kết quả sau booking. `position` không có trong test; click tương lai không phải feature để chấm trước click.
- Nhóm đối thủ có 24 cột và mức thiếu khác nhau đáng kể, không phải toàn bộ đều thiếu 93–98%. Không khẳng định NA lịch sử = khách mới hoặc NA đối thủ = không có cạnh tranh.
- Các dòng cùng search phụ thuộc nhau. Báo cáo giữ cấu trúc nhóm, phân tích vị trí cùng random_bool và chưa thiết kế mô hình/chia tập.

## 5. Cách đọc các kết quả EDA

**HOTEL/AIRBNB:** thống kê mô tả trên toàn bộ bảng chính; AIRBNB quét toàn bộ sessions. Khoảng Wilson 95% trong bảng tỷ lệ user/booking là tham khảo theo giả định độc lập, không bao gồm mọi sai lệch dữ liệu. Nhóm n<100 được gắn cờ, không kết luận chắc chắn từ tỷ lệ cực đoan.

**EXPEDIA:** mọi thống kê train dùng toàn bộ dòng hợp lệ của từng biến/cặp biến, gồm quantile tuyến tính, skewness, hàng rào/số đếm outlier, Spearman và missing theo booking. Số dòng không thiếu được công bố; không lấy mẫu 5% để tính thống kê. Chỉ scatter hiển thị tối đa 4.000 điểm và pattern missing 300 dòng, seed=42; heatmap và bảng tổng hợp dùng toàn bộ train. Các dòng cùng search phụ thuộc nhau; không báo khoảng nhị thức coi impressions là độc lập.

Phân nhóm tuổi, lead time, giá hoặc cohort chỉ nhằm đọc dữ liệu. Không có tập feature được xuất, không impute, clipping, encoding, class weighting, resampling hoặc train model. Không có kết quả mô hình để báo AUC, calibration hoặc lift; việc thiếu các chỉ số mô hình không phải thiếu sót của giai đoạn EDA này.

## 6. Những câu hỏi còn phải giải quyết trước giai đoạn tiếp theo

| Vấn đề | HOTEL | AIRBNB | EXPEDIA |
| --- | --- | --- | --- |
| t0 và đối tượng được chấm | Lúc tạo booking hay trước đến; booking nào còn hiệu lực? | Thiết kế chính: ngay sau tạo account; cần xác minh snapshot hồ sơ | Trước hiển thị, trước click hay sau click? |
| Horizon/độ trưởng thành nhãn | Theo vòng đời booking; tránh đưa kết quả đã biết vào risk set | Cần ngày đóng nhãn và thời hạn chung | Nhãn trong search và cách quy thuộc booking |
| Khả dụng biến tại t0 | Cần log lịch sử/snapshot | Cần chứng minh cửa sổ sessions và bảng phụ | Cần xác minh điểm nội bộ, giá và metadata hiển thị |
| Định danh/phụ thuộc | Thiếu booking/customer ID | Users rõ khóa; events không có timestamp | Có search/property, thiếu user ID |
| Khả năng suy rộng | Hai khách sạn ở Bồ Đào Nha, dữ liệu lịch sử | Người dùng Mỹ, dữ liệu lịch sử | Cơ chế chọn search và ranking/exposure |

Các mục trên là câu hỏi dữ liệu/nghiệp vụ chưa được giải đáp, không phải các bước engineering đã làm. CSV không đủ bằng chứng để biến các giả thuyết nguyên nhân thành kết luận chắc chắn.

## 7. Báo cáo chi tiết và cách tái lập

- **HOTEL:** [Bản đọc đầy đủ](HOTEL/README.md) · [Notebook có output](../notebooks/HOTEL/hotel_descriptive_report.ipynb).
- **AIRBNB:** [Bản đọc đầy đủ](AIRBNB/README.md) · [Notebook có output](../notebooks/AIRBNB/airbnb_descriptive_report.ipynb).
- **EXPEDIA:** [Bản đọc đầy đủ](EXPEDIA/README.md) · [Notebook có output](../notebooks/EXPEDIA/expedia_descriptive_report.ipynb).

Notebook chỉ lưu trong `notebooks/HOTEL`, `notebooks/AIRBNB`, `notebooks/EXPEDIA`; `reports` chứa báo cáo Markdown, biểu đồ và metadata cần để dựng báo cáo tổng hợp. Mỗi notebook đọc lại CSV qua cùng [script EDA](../scripts/build_descriptive_reports.py); các bảng Markdown và hình được sinh từ cùng kết quả tính, tránh số liệu viết tay lệch nhau.

Chạy tại thư mục gốc dự án:

```powershell
python scripts/build_descriptive_reports.py
# Hoặc chỉ dựng lại một bộ:
python scripts/build_descriptive_reports.py --dataset AIRBNB
```

Để chạy lại notebook độc lập, mở notebook và Run All; cell đầu quét dữ liệu và cập nhật bản Markdown/biểu đồ của bộ đó. Chạy script toàn bộ để cập nhật ba notebook và báo cáo tổng hợp. Môi trường và SHA-256 nguồn được ghi trong báo cáo chi tiết; không sửa raw hoặc pipeline dự án.
"""
    (root/"reports/README.md").write_text(text,encoding="utf-8")


def main():
    import sys
    import nbformat
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output
    from traitlets.config import Config
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset",choices=["HOTEL","AIRBNB","EXPEDIA"])
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0,str(root))
    selected=[args.dataset] if args.dataset else ["HOTEL","AIRBNB","EXPEDIA"]
    shell_config=Config()
    shell_config.HistoryManager.hist_file=":memory:"
    shell=InteractiveShell.instance(config=shell_config)
    for dataset in selected:
        print(f"Executing {dataset} report notebook ...",flush=True)
        nb=make_notebook(root,dataset)
        shell.user_ns.clear()
        shell.init_user_ns()
        execution_count=0
        for cell in nb.cells:
            if cell.cell_type != "code": continue
            execution_count+=1
            with capture_output(stdout=True,stderr=True,display=True) as captured:
                result=shell.run_cell(cell.source,store_history=False,silent=False)
            if not result.success:
                print(captured.stdout,flush=True)
                print(captured.stderr,flush=True)
                raise RuntimeError(f"{dataset}: cell {execution_count} failed") from (result.error_in_exec or result.error_before_exec)
            outputs=[]
            if captured.stdout: outputs.append(nbformat.v4.new_output("stream",name="stdout",text=captured.stdout))
            if captured.stderr: outputs.append(nbformat.v4.new_output("stream",name="stderr",text=captured.stderr))
            for output in captured.outputs:
                outputs.append(nbformat.v4.new_output("display_data",data=output.data,metadata=output.metadata))
            cell.execution_count=execution_count
            cell.outputs=outputs
            print(f"{dataset}: executed cell {execution_count}",flush=True)
        nb.metadata["execution_method"]="IPython in-process; real cell execution and captured rich outputs"
        nb.metadata["execution_date"] = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat()
        nbformat.validate(nb)
        errors=[o for c in nb.cells if c.cell_type=="code" for o in c.get("outputs",[]) if o.output_type=="error"]
        if errors: raise RuntimeError(f"Notebook {dataset} contains execution errors")
        filename=f"{dataset.lower()}_descriptive_report.ipynb"
        path=root/"notebooks"/dataset/filename
        path.parent.mkdir(parents=True,exist_ok=True)
        nbformat.write(nb,path)
        print(f"Saved {dataset} notebook: {path}",flush=True)
    if all((root/"reports"/d/"analysis_metadata.json").exists() for d in ["HOTEL","AIRBNB","EXPEDIA"]):
        write_summary(root)
        print("Updated reports/README.md",flush=True)


if __name__=="__main__":
    main()
