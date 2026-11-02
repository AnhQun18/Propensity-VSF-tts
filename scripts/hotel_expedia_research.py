"""Research and publication layer for HOTEL and EXPEDIA, matching Airbnb's depth.

All calculations describe raw observations. Protocols are specifications only;
this module never fits a model, materializes splits, or exports feature data.
"""
from __future__ import annotations

import hashlib
import json
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from scripts.eda_diagnostics import section, combine

LAYOUT = [
    ("glossary", "Thuật ngữ và cách đọc báo cáo"),
    ("executive", "Tóm tắt điều hành"),
    ("problem", "1. Bài toán và lý do chọn dữ liệu"),
    ("overview", "2. Tổng quan bộ dữ liệu"),
    ("quality_main", "3. Chất lượng dữ liệu"),
    ("univariate", "4. Phân tích đơn biến"),
    ("multivariate_main", "5. Nhãn, liên hệ đa biến, thời gian và nhóm con"),
    ("risks", "6. Tổng hợp giới hạn và mức độ phù hợp"),
    ("design", "7. Thuật toán và thiết kế đánh giá đề xuất"),
    ("appendix", "Phụ lục — từ điển và bảng bổ sung"),
    ("reproducibility", "Tái lập và kiểm soát phạm vi"),
]
BLUE, ORANGE = "#245D80", "#C76A37"
HOTEL_SOURCE = "https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/"
EXPEDIA_SOURCE = "https://www.kaggle.com/competitions/expedia-personalized-sort/data"
CALIBRATION = "https://scikit-learn.org/stable/modules/calibration.html"
RANKING = "https://lightgbm.readthedocs.io/en/stable/Parameters.html#objective"


def walk(sections):
    for item in sections:
        yield item
        yield from walk(item.get("blocks", []))


def grouped_rates(frame, keys, target="is_canceled"):
    from scripts.build_descriptive_reports import wilson
    out = frame.groupby(keys, observed=True, dropna=False)[target].agg(n="size", positive="sum").reset_index()
    out["rate_pct"] = out.positive / out.n * 100
    out["ci95_low_pct"], out["ci95_high_pct"] = wilson(out.positive, out.n)
    out["n_under_100"] = out.n < 100
    return out


def categorical_effect(counts, positive="positive"):
    """Uncorrected Cramér V for an aggregate K by binary table; no iid p-value."""
    table = np.column_stack([counts.n - counts[positive], counts[positive]]).astype(float)
    table = table[table.sum(axis=1) > 0]
    n = table.sum()
    if len(table) < 2 or n == 0 or (table.sum(axis=0) == 0).any():
        return np.nan
    expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / n
    return float(np.sqrt(((table - expected)**2 / expected).sum() / n))


def rank_effect(values, target):
    valid = values.notna() & target.notna()
    a, b = values[valid & target.eq(1)], values[valid & target.eq(0)]
    if not len(a) or not len(b):
        return np.nan
    u = stats.mannwhitneyu(a, b, method="asymptotic").statistic
    return float(2 * u / (len(a) * len(b)) - 1)


def hotel_associations(frame):
    categories = {"hotel", "arrival_date_year", "arrival_date_month", "arrival_date_week_number",
                  "arrival_date_day_of_month", "meal", "country", "market_segment", "distribution_channel",
                  "is_repeated_guest", "reserved_room_type", "assigned_room_type", "deposit_type",
                  "agent", "company", "customer_type"}
    populations = {"all": frame, "unique": frame.drop_duplicates(),
                   "city": frame[frame.hotel.eq("City Hotel")], "resort": frame[frame.hotel.eq("Resort Hotel")]}
    rows = []
    for col in frame.columns.difference(["is_canceled", "reservation_status", "reservation_status_date"], sort=False):
        row = {"variable": col, "effect_metric": "Cramér V" if col in categories else "Rank-biserial"}
        for name, pop in populations.items():
            if col in categories:
                # Explicit missing category; no imputation of raw values.
                x = pop[col].astype(object).where(pop[col].notna(), "<MISSING>")
                counts = pop.groupby(x, dropna=False).is_canceled.agg(n="size", positive="sum")
                value = categorical_effect(counts)
            else:
                value = rank_effect(pop[col], pop.is_canceled)
            row["effect_" + name] = value
        row["n_nonmissing"] = len(frame) if col in categories else int(frame[col].notna().sum())
        rows.append(row)
    return pd.DataFrame(rows)


def standardize_hotels(frame):
    cells = frame.groupby(["market_segment", "hotel"], observed=True).is_canceled.agg(n="size", positive="sum")
    sizes = cells.n.unstack("hotel", fill_value=0)
    support = sizes.index[(sizes >= 100).all(axis=1)]
    weights = sizes.loc[support].sum(axis=1)
    weights = weights / weights.sum()
    out = []
    for hotel in sizes.columns:
        s = cells.xs(hotel, level="hotel").loc[support]
        pop = frame[frame.hotel.eq(hotel)]
        out.append([hotel, len(pop), pop.is_canceled.mean()*100, int(s.n.sum()),
                    s.n.sum()/len(pop)*100, float((weights*s.positive/s.n).sum()*100)])
    return pd.DataFrame(out, columns=["hotel", "n", "rate_pct", "support_n", "support_pct", "standardized_pct"])


def hotel_temporal_protocol(frame, arrival):
    """Arrival-cohort diagnostic only; raw snapshots cannot reconstruct t0."""
    status = pd.to_datetime(frame.reservation_status_date, errors="coerce")
    # Conservative retrospective availability: both arrival and final status passed.
    ready = pd.concat([arrival, status], axis=1).max(axis=1) + pd.Timedelta(days=1)
    rows = []
    for origin in pd.to_datetime(["2016-07-01", "2016-09-01", "2016-11-01", "2017-05-01", "2017-06-01"]):
        end = origin + pd.offsets.MonthBegin(1)
        historic = (arrival < origin) & (ready <= origin) & status.notna() & arrival.notna()
        evaluation = (arrival >= origin) & (arrival < end)
        rows.append([str(origin.date()), "đánh giá cuối" if origin.year == 2017 else "phát triển",
                     int(historic.sum()), int(evaluation.sum()), int(frame.loc[evaluation, "is_canceled"].sum()),
                     frame.loc[evaluation, "is_canceled"].mean()*100,
                     int(((arrival < origin) & ~historic).sum())])
    return pd.DataFrame(rows, columns=["origin", "role", "history_n", "evaluation_n", "positive", "rate_pct", "pending_n"])


def effect_plot(report, associations, columns, fields, labels):
    table = associations[associations.variable.isin(columns)].copy()
    # Keep V and rank-biserial separate, as their scales have different meanings.
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [1.2, 1]})
    for ax, metric in zip(axes, ["Cramér V", "Rank-biserial"]):
        part = table[table.effect_metric.eq(metric)]
        y = np.arange(len(part))
        for i, (field, label) in enumerate(zip(fields, labels)):
            ax.scatter(part[field], y+(i-.5)*.17, label=label, s=32)
        ax.set_yticks(y, part.variable)
        ax.set(xlim=(0, 1) if metric == "Cramér V" else (-1, 1), xlabel=metric,
               title="Liên hệ với nhãn hủy/no-show")
        ax.axvline(0, color="#aaaaaa", lw=.6)
        ax.grid(axis="x", alpha=.2)
        ax.legend(fontsize=8)
    fig.tight_layout(w_pad=3)
    return report.savefig("association_strength", fig)


def deepen_hotel(report, frame, arrival):
    by = {s["key"]: s for s in walk(report.sections)}
    association = hotel_associations(frame)
    sensitivity = []
    for name, pop in [("Giữ nguyên", frame), ("Giả định bỏ trùng", frame.drop_duplicates())]:
        tab = grouped_rates(pop, ["hotel"])
        tab.insert(0, "scenario", name)
        sensitivity.append(tab)
    sensitivity = pd.concat(sensitivity, ignore_index=True)
    standardized = standardize_hotels(frame)
    duplicate = pd.DataFrame({"hotel": frame.hotel, "duplicate": frame.duplicated()})
    duplicate = duplicate.groupby("hotel").duplicate.agg(n="size", duplicate_n="sum").reset_index()
    duplicate["duplicate_pct"] = duplicate.duplicate_n/duplicate.n*100
    by["appendix"]["blocks"].extend([
        section("full_association", "Liên hệ của đủ 29 cột ứng viên", "Cramér V ∈ [0; 1] cho biến phân loại, gồm missing như một nhóm. Rank-biserial ∈ [−1; 1] cho biến số không thiếu; dấu dương nghĩa nhãn 1 thường có giá trị lớn hơn. Không dùng p-value vì các booking có phụ thuộc và trùng lặp. V chưa hiệu chỉnh thiên lệch theo số nhóm; ID nhiều nhóm có thể trông mạnh hơn. Không so trực tiếp độ lớn giữa hai thước đo.", [("Đối chiếu raw, giả định bỏ trùng và từng khách sạn", association)]),
        section("duplicate_by_hotel", "Độ nhạy với dòng trùng trong từng khách sạn", "Đếm trùng giữ lần đầu trên toàn bộ 32 cột. Bỏ trùng chỉ là kịch bản mô tả; không xác nhận hai dòng giống nhau là cùng booking.", [("Dòng trùng theo cơ sở", duplicate), ("Tỷ lệ theo kịch bản và cơ sở", sensitivity)]),
    ])
    chosen = ["market_segment", "deposit_type", "customer_type", "hotel", "lead_time", "previous_cancellations", "booking_changes", "total_of_special_requests", "adr"]
    path = effect_plot(report, association, chosen, ["effect_all", "effect_unique"], ["Giữ nguyên", "Giả định bỏ trùng"])
    report.figure_notes[path.name] = "**Quan sát:** bảng cạnh hình đối chiếu liên hệ trước và sau giả định bỏ dòng trùng; độ nhạy cần được xét trước lựa chọn mô hình.\n\n**Phạm vi và cách đọc:** toàn bộ booking trong từng kịch bản; biến phân loại gồm missing, biến số bỏ NA riêng từng cột. Hai thước đo có trục riêng. Cột có liên hệ mạnh vẫn bị chặn nếu chưa có bằng chứng tại t0."
    signal = section("signal", "Độ mạnh liên hệ và độ nhạy với trùng lặp", "Khảo sát đủ 29 cột ngoài nhãn và hai cột trạng thái cuối. Bảng chính chọn chín biến để đọc; phụ lục giữ đầy đủ, gồm kết quả riêng từng cơ sở. Đây là liên hệ đơn biến, chưa phải chất lượng dự đoán. Đặt cọc, thay đổi booking và yêu cầu bổ sung cần kiểm tra thời điểm ghi nhận trước khi thử mô hình.", [("Các liên hệ chính", association[association.variable.isin(chosen)])], [path])
    strata = grouped_rates(frame, ["hotel", "market_segment"])
    by["appendix"]["blocks"].append(section("strata", "Tỷ lệ và Wilson 95% theo cơ sở × phân khúc", "Các khoảng chỉ mang tính tham khảo dưới giả định booking độc lập; dòng trùng, khách lặp và đoàn có thể làm bất định lớn hơn.", [("Từng nhóm kết hợp", strata)]))
    support_gap = float(standardized.standardized_pct.iloc[0]-standardized.standardized_pct.iloc[1])
    confounding = section("stratification", "Tách khác biệt cơ cấu khách khỏi chênh lệch hai cơ sở", f"Dùng cùng trọng số phân khúc thị trường cho hai khách sạn trên phần giao có ít nhất 100 booking mỗi cơ sở. Trọng số tỷ lệ với tổng booking của cả hai cơ sở trong phần giao. Chênh lệch City − Resort sau chuẩn hóa là {support_gap:.2f} điểm phần trăm. Đây là chuẩn hóa mô tả một biến; chưa điều chỉnh quốc gia, thời gian, đặt cọc hoặc khách lặp, nên không suy ra tác động của loại khách sạn.", [("Raw và tỷ lệ cùng cơ cấu phân khúc", standardized)])
    by["multivariate_main"]["blocks"] = [signal, confounding, *by["multivariate_main"]["blocks"]]
    protocol = hotel_temporal_protocol(frame, arrival)
    report.research_protocol = protocol
    report.research_evidence = {"association": association, "sensitivity": sensitivity, "standardized": standardized, "protocol": protocol}
    report.facts.update(columns_association_audited=len(association), standardized_gap_pp=support_gap,
                        protocol_kind="arrival_cohort_diagnostic_only")


def expedia_protocol(query):
    dates = pd.to_datetime(query.date_min, unit="ns")
    rows = []
    for origin in pd.to_datetime(["2013-02-01", "2013-03-01", "2013-04-01", "2013-05-01", "2013-06-01"]):
        # A seven-day gap is a proposed sensitivity setting, not proven label maturity.
        cutoff = origin-pd.Timedelta(days=7)
        history = dates < cutoff
        evaluation = (dates >= origin) & (dates < origin+pd.offsets.MonthBegin(1))
        s = query.loc[evaluation]
        rows.append([str(origin.date()), "đánh giá cuối" if origin.month >= 5 else "phát triển",
                     str(cutoff.date()), int(history.sum()), int(query.loc[history, "n"].sum()),
                     len(s), int(s.n.sum()), int(s.bookings.sum()), s.bookings.sum()/s.n.sum()*100 if s.n.sum() else np.nan])
    return pd.DataFrame(rows, columns=["origin", "role", "history_before", "history_searches", "history_n", "evaluation_searches", "evaluation_n", "positive", "rate_pct"])


def deepen_expedia(report, train, test):
    by = {s["key"]: s for s in walk(report.sections)}
    query = train["queries"]
    rows = []
    for column in ["site_id", "visitor_location_country_id", "prop_country_id", "prop_starrating", "prop_brand_bool", "promotion_flag", "srch_saturday_night_bool", "random_bool", "price_group", "window_group"]:
        counts = train["groups"][column]
        rows.append([column, "Cramér V", len(counts), int(counts.n.sum()), categorical_effect(counts, "clicks"), categorical_effect(counts, "bookings")])
    association = pd.DataFrame(rows, columns=["variable", "effect_metric", "groups", "n", "effect_click", "effect_booking"])
    histogram = query.groupby(["clicks", "bookings"]).agg(searches=("n", "size"), n=("n", "sum")).reset_index()
    histogram["pct_searches"] = histogram.searches/len(query)*100
    macro_click, macro_booking = (query.clicks/query.n).mean()*100, (query.bookings/query.n).mean()*100
    weighting = pd.DataFrame([
        ["Mỗi cặp có trọng số bằng nhau", train["rows"], query.clicks.sum()/query.n.sum()*100, query.bookings.sum()/query.n.sum()*100],
        ["Mỗi search có trọng số bằng nhau", len(query), macro_click, macro_booking],
    ], columns=["population", "units", "click_pct", "booking_pct"])
    mixed = int(query.random_min.ne(query.random_max).sum())
    strata = train["groups"]["random_star"]
    price_strata = train["groups"]["random_price"]
    by["appendix"]["blocks"].extend([
        section("search_outcomes", "Phân phối kết quả ở cấp lượt tìm kiếm", "Mẫu số là số search train; mỗi search giữ nguyên danh sách khách sạn. Không có người dùng định danh để kiểm tra phụ thuộc giữa các search.", [("Số click và booking trong từng search", histogram)]),
        section("strata", "Phân tầng cơ chế sắp xếp theo sao và giá", "Tính trên toàn bộ train; không coi random_bool là bằng chứng tự đủ về phân bổ ngẫu nhiên hoặc tiếp xúc ngang nhau. Tỷ lệ theo nhóm vẫn có phụ thuộc trong search.", [("Cơ chế × hạng sao", strata), ("Cơ chế × khoảng giá USD", price_strata)]),
    ])
    fig, ax = plt.subplots(figsize=(11, 5))
    y = np.arange(len(association))
    ax.scatter(association.effect_click, y-.1, label="Click", color=BLUE)
    ax.scatter(association.effect_booking, y+.1, label="Booking", color=ORANGE)
    ax.set_yticks(y, association.variable)
    ax.set(xlim=(0, 1), xlabel="Cramér V (0–1)", title="Liên hệ nhóm với hai nhãn · toàn bộ train")
    ax.grid(axis="x", alpha=.2); ax.legend(); fig.tight_layout()
    path = report.savefig("association_strength", fig)
    report.figure_notes[path.name] = "**Quan sát:** mỗi biến có hai điểm cho liên hệ với click và booking, cho phép kiểm tra liệu tín hiệu hai hành vi có đồng nhất.\n\n**Phạm vi và cách đọc:** toàn bộ train; chỉ mười cách nhóm công bố, chưa phải toàn bộ 49 cột ứng viên. Cramér V không hiệu chỉnh số nhóm, không là điểm chất lượng mô hình hoặc quan hệ nhân quả. Không dùng p-value giả định 9.9 triệu dòng độc lập."
    signal = section("signal", "Độ mạnh liên hệ với click và booking", "Tính V từ bảng chéo đếm đủ train; không lấy mẫu cho thống kê. Giá và thời gian đặt trước dùng các khoảng EDA đã công bố. Số nhóm và cách chia khoảng ảnh hưởng V. Không so hệ số này với tương quan của các biến số hoặc xếp hạng tự động đầu vào.", [("Mười góc nhìn phân nhóm với hai nhãn", association)], [path])
    context = section("search_context", "Mẫu số lượt tìm kiếm, độ dài danh sách và cơ chế sắp xếp", f"Có {mixed:,} search chứa nhiều giá trị random_bool. Bảng so sánh trọng số phân biệt tỷ lệ ở cấp cặp và trung bình tỷ lệ trong từng search: danh sách dài đóng góp nhiều hơn trong tỷ lệ cấp dòng. Booking trung bình theo search là {macro_booking:.4f}%, không phải tỷ lệ search có ít nhất một booking. Không dùng Wilson trên từng cặp vì các ứng viên cạnh tranh trong một search.", [("Ảnh hưởng của cách đặt trọng số", weighting)])
    by["multivariate_main"]["blocks"] = [context, signal, *by["multivariate_main"]["blocks"]]
    dates = pd.to_datetime(query.date_min, unit="ns")
    month_frame = query.assign(month=dates.dt.to_period("M").astype(str))
    monthly = month_frame.groupby("month").agg(searches=("n", "size"), n=("n", "sum"), bookings=("bookings", "sum"), clicks=("clicks", "sum"))
    monthly["booking_pct"] = monthly.bookings/monthly.n*100
    monthly["click_pct"] = monthly.clicks/monthly.n*100
    by["appendix"]["blocks"].append(section("monthly_queries", "Quy mô search theo tháng", "Tháng đầu và cuối có thể không đầy đủ. Train và test cùng phủ 2012-11–2013-06; test Kaggle không phải tập tương lai có nhãn.", [("Số search, số cặp và hai nhãn", monthly.reset_index())]))
    report.research_protocol = expedia_protocol(query)
    report.research_evidence = {"association": association, "weighting": weighting, "strata": strata, "price_strata": price_strata, "protocol": report.research_protocol, "monthly": monthly}
    report.facts.update(columns_association_audited=len(association), searches_mixed_random_bool=mixed,
                        macro_search_click_pct=float(macro_click), macro_search_booking_pct=float(macro_booking),
                        protocol_kind="search_time_conditional_label_maturity")


def glossary(dataset):
    common = [
        ["Propensity", "Xác suất thực hiện hành vi trong quần thể và thời hạn đã định; không phải tác động của chiến dịch."],
        ["t0", "Thời điểm chấm điểm; mọi đầu vào và trạng thái thiếu của chúng phải được biết tại thời điểm này."],
        ["Rò rỉ nhãn", "Dùng thông tin chỉ có sau hành vi cần dự đoán làm đầu vào."],
        ["Nhãn hoàn tất", "Kết quả đã được ghi nhận và sẵn có trước mốc học hoặc hiệu chỉnh."],
        ["Nhóm theo thời gian", "Các booking/search cùng giai đoạn; thay đổi cơ cấu có thể làm đổi tỷ lệ nhãn."],
        ["Cramér V", "Độ mạnh liên hệ giữa nhóm và nhãn, từ 0 đến 1; không chứng minh nhân quả."],
        ["OOF theo thời gian", "Điểm ngoài tập học tạo bằng mô hình chỉ dùng lịch sử sẵn có trước quan sát đó."],
        ["Hiệu chỉnh xác suất", "Kiểm tra và điều chỉnh để điểm xác suất phù hợp với tần suất thực tế."],
        ["AP / log loss / Brier", "AP đánh giá phân hạng nhị phân; log loss và Brier đánh giá dự đoán xác suất, càng thấp càng tốt."],
    ]
    if dataset == "HOTEL":
        common += [["Hủy/no-show", "Nhãn 1 gồm Canceled và No-Show; nhãn 0 là Check-Out."], ["Rank-biserial", "Chênh ưu thế thứ hạng biến số của nhãn 1 so với nhãn 0; từ −1 đến 1."], ["Wilson 95%", "Khoảng tham khảo cho tỷ lệ nếu booking độc lập; trùng/lặp khách có thể làm khoảng quá hẹp."]]
    else:
        common += [["Search–property", "Một khách sạn trong một lượt tìm kiếm; nhiều dòng dùng chung srch_id."], ["NDCG@5", "Chất lượng thứ tự năm kết quả đầu, tính riêng mỗi search rồi lấy trung bình."], ["Sai lệch vị trí", "Kết quả ở trên thường được nhìn thấy nhiều hơn; click không chỉ phản ánh sở thích."]]
    return section("glossary", LAYOUT[0][1], "Quy ước số: dấu chấm là phần thập phân; dấu phẩy phân tách hàng nghìn. Tên cột và mã giá trị gốc được giữ trong bảng để đối chiếu CSV. Mọi chỉ số mô hình ở mục 7 là tiêu chí đề xuất, chưa được đo.", [("Thuật ngữ", pd.DataFrame(common, columns=["Thuật ngữ", "Cách hiểu trong báo cáo"]))])


def usage_decisions(report):
    by = {s["key"]: s for s in walk(report.sections)}
    schema = by["dictionary"]["tables"][0][1]
    columns = schema["column"]
    rows = []
    for col in columns:
        if report.dataset == "HOTEL":
            if col == "is_canceled":
                decision, branch, evidence = "Nhãn", "Chỉ tạo/đối chiếu y", "Gồm hủy và no-show; không là đầu vào"
            elif col in {"reservation_status", "reservation_status_date"}:
                decision, branch, evidence = "Chặn đầu vào", "Kiểm tra nhãn và khả dụng lịch sử", "Thông tin trạng thái cuối; rò rỉ kết quả"
            elif col in {"assigned_room_type", "booking_changes", "deposit_type", "days_in_waiting_list", "adr", "required_car_parking_spaces", "total_of_special_requests"}:
                decision, branch, evidence = "Chặn khi thiếu lịch sử", "H1 · snapshot tại t0", "Có thể tích lũy/cập nhật sau đặt; cần lịch sử thay đổi"
            else:
                decision, branch, evidence = "Ứng viên có điều kiện", "H0 · dữ liệu booking tại t0", "Cần xác nhận giá trị và cờ thiếu tại t0; CSV cuối không đủ"
        else:
            if col in {"click_bool", "booking_bool"}:
                decision, branch, evidence = "Nhãn", "Click và booking tách riêng", "Không dùng click thực tế cho dự đoán trước hiển thị"
            elif col in {"gross_bookings_usd", "position"}:
                decision, branch, evidence = "Chặn đầu vào chính", "Chỉ EDA kết quả/tiếp xúc", "Gross sau booking; position train-only và thuộc cơ chế hiển thị"
            elif col == "srch_id":
                decision, branch, evidence = "Khóa nhóm", "Chia tập, bootstrap, xếp hạng", "Không đưa mã số search vào mô hình như đại lượng liên tục"
            elif col == "prop_id":
                decision, branch, evidence = "Nhánh mở rộng riêng", "E2 · ghi nhớ khách sạn", "So có/không ID; chỉ tính lịch sử từ train, báo khách sạn chưa gặp"
            elif col == "random_bool":
                decision, branch, evidence = "Phân tầng thiết kế", "EDA và đánh giá theo cơ chế", "Nhánh chính loại cờ cơ chế; chỉ thử nếu biết chính sách tại t0"
            else:
                decision, branch, evidence = "Ứng viên có điều kiện", "E0/E1 · trước hiển thị", "Xác nhận nguồn, timestamp và cách tính; không dùng thống kê gộp tương lai"
        rows.append([col, decision, branch, evidence])
    return pd.DataFrame(rows, columns=["Cột gốc", "Quyết định", "Vai trò hoặc nhánh", "Điều kiện và căn cứ"])


def questions(dataset):
    if dataset == "HOTEL":
        rows = [
            ["H-Q1 · Snapshot", "Giá trị từng cột và cờ thiếu tại lúc tạo booking có được lưu?", HOTEL_SOURCE, "Đối chiếu lịch sử PMS và truy vấn trích xuất theo từng cột", "Có snapshot tại t0; nếu chưa có chỉ nghiên cứu liên hệ hồi cứu"],
            ["H-Q2 · Dòng trùng", "Các dòng giống nhau là booking thật, đoàn hay lỗi sao chép?", "Người cung cấp CSV gộp; khóa booking từ PMS", "Đối chiếu booking ID và log ETL; không suy từ thuộc tính giống nhau", "Xác nhận đơn vị; chốt chính sách trùng và nhóm qua các tập"],
            ["H-Q3 · Quần thể và nhãn", "Chấm lúc tạo booking hay trước ngày đến, và nhãn có sẵn lúc nào?", HOTEL_SOURCE, "Xác định booking còn hiệu lực tại t0, mốc hoàn tất và lịch chọn mẫu theo ngày đến", "Có quần thể đủ điều kiện và thời gian theo dõi; không dùng booking đã hủy làm đối tượng can thiệp"],
        ]
    else:
        rows = [
            ["E-Q1 · Chọn mẫu", "Vì sao mọi search train có click, và áp dụng cho quần thể nào?", EXPEDIA_SOURCE, "Xin quy trình chọn search và dữ liệu search không click", "Giới hạn mô hình trong mẫu đã chọn; mở rộng website chỉ khi có quần thể đích"],
            ["E-Q2 · Thời điểm nhãn", "Click/booking được ghi đến lúc nào sau date_time?", EXPEDIA_SOURCE, "Xin timestamp sự kiện, quy tắc gán nhãn và hạn theo dõi", "Xác nhận nhãn sẵn có trước mốc học; khoảng đệm 7 ngày chưa đủ bằng chứng"],
            ["E-Q3 · Tiếp xúc và đầu vào", "Cờ random và điểm khách sạn/giá được tạo khi nào?", EXPEDIA_SOURCE, "Đối chiếu cơ chế phân bổ vị trí, timestamp từng điểm và snapshot giá", "Duyệt đầu vào tại t0; chỉ nghiên cứu nhân quả khi có thiết kế tiếp xúc phù hợp"],
        ]
    table = pd.DataFrame(rows, columns=["Câu hỏi", "Thông tin còn thiếu", "Nguồn có thể trả lời", "Cách xác minh", "Điều kiện kết thúc hoặc quyết định"])
    table["Vai trò đề xuất"] = "Tác giả tổng hợp; người cung cấp dữ liệu xác nhận; người hướng dẫn duyệt phạm vi"
    table["Trạng thái"] = "Mở · chưa đủ bằng chứng"
    note = (f"Đã đọc [nghiên cứu gốc]({HOTEL_SOURCE}) ngày 2026-11-02; chưa có lịch sử PMS hoặc hồ sơ ETL của bản gộp local." if dataset == "HOTEL" else f"Đã mở [trang dữ liệu Kaggle]({EXPEDIA_SOURCE}) ngày 2026-11-02 nhưng công cụ web không đọc được nội dung; liên kết là nguồn cần xác minh, không phải bằng chứng đã xác nhận.")
    return section("open_questions", "Câu hỏi mở và cách xác minh", note + " Vai trò trong bảng là đề xuất theo dõi, chưa phải người đã nhận việc. Ngày tải/mã phiên bản chưa được ghi nhận; giữ SHA-256 để định danh bản local.", [("Danh mục xác minh", table)])


def proposed_design(report):
    hotel = report.dataset == "HOTEL"
    branches = ([
        ["H0 · Booking tại t0", "Các thuộc tính đã xác nhận lúc tạo booking; không gồm cột bị chặn", "Chưa có snapshot, chưa được fit như mô hình vận hành"],
        ["H1 · Mở rộng snapshot", "Thêm từng cột cập nhật có lịch sử xác nhận tại mốc dự đoán", "Mỗi cột và cờ thiếu cần bằng chứng; không dùng trạng thái cuối"],
        ["Độ nhạy trùng", "Giữ raw / giả định bỏ trùng trên cùng thiết kế thời gian", "Không tự coi kịch bản bỏ trùng là chân lý; ngăn nhóm giống hệt giao tập"],
    ] if hotel else [
        ["E0 · Trước hiển thị", "Ngữ cảnh search, thuộc tính khách sạn và giá đã xác nhận tại t0", "Loại srch_id khỏi feature; không dùng position, click, gross và random_bool"],
        ["E1 · Điểm lịch sử/đối thủ", "Bổ sung các điểm Expedia, lịch sử và 24 cột đối thủ có bằng chứng tại t0", "Chỉ tính lịch sử từ quá khứ; missing không tự suy ra không có đối thủ"],
        ["E2 · Định danh khách sạn", "E0/E1 + prop_id dạng category", "So với nhánh không ID và báo riêng khách sạn mới; không target-encode bằng toàn dữ liệu"],
    ])
    models = ([
        ["Xác suất hằng", "Tỷ lệ hủy/no-show của tập học", "Đối chứng xác suất cơ bản"],
        ["Logistic Regression L2", "Hiệu ứng chính và tương tác hotel × segment, lead-time × segment khi hợp lệ", "One-hot, spline/biến đổi số và L2 chỉ chọn từ lịch sử phát triển"],
        ["CatBoost", "Cùng tập thông tin được phê duyệt với LR", "So với LR mạnh nhất gồm tương tác; không dùng mọi cột raw mặc định"],
        ["Sigmoid từ OOF theo thời gian", "Áp dụng cùng quy trình cho cả LR và CatBoost", "Điểm OOF tạo từ lịch sử cũ, nhãn đã hoàn tất; không học hiệu chỉnh từ điểm trong mẫu"],
    ] if hotel else [
        ["Xác suất hằng", "Tỷ lệ click/booking riêng của train", "Hai nhãn riêng; chỉ có nghĩa trong quần thể search đã chọn"],
        ["Logistic Regression L2", "Hiệu ứng chính và giá × sao, cửa sổ đặt × số đêm khi hợp lệ", "Cùng feature và tập thời gian với mô hình cây; xử lý category chỉ fit train"],
        ["LightGBM binary", "Dự đoán click và booking riêng", "Mục tiêu xác suất; hiệu chỉnh sigmoid từ OOF theo thời gian, giữ nguyên search"],
        ["LightGBM LambdaRank", "Nhánh xếp hạng riêng, group=srch_id", "Mức liên quan 0=không click, 1=click không booking, 2=booking; đặt label_gain=[0,1,5]. Điểm rank không là xác suất."],
    ])
    if hotel:
        time_text = """Bảng là kiểm tra tính khả thi theo tháng đến, chưa phải mô phỏng chấm tại lúc tạo booking. Lịch sử chỉ gồm booking có ngày đến trước O và max(ngày đến, ngày trạng thái cuối)+1 ngày ≤ O; không dùng ngày trạng thái làm đầu vào. Các tháng 7, 9, 11/2016 dùng phát triển; tháng 5–6/2017 dự kiến giữ để đánh giá cuối nếu triển khai thí nghiệm. Ngày kết quả trong CSV chỉ là cận kiểm tra lịch sử, chưa xác nhận lúc hệ thống thực sự nhận nhãn.

Không suy ngày tạo booking chính xác bằng ngày đến − lead_time khi chưa biết lịch sử đổi lịch. Tập có các booking đã hủy trước O nên không phải quần thể booking còn hiệu lực trước ngày đến. Cần H-Q1/H-Q3 để thay bảng hồi cứu bằng lịch đúng t0 và quần thể đủ điều kiện. Không thể dùng kết quả từ bảng này để khẳng định chất lượng vận hành.

Trong thí nghiệm có dữ liệu phù hợp, chốt cấu hình trên các tháng phát triển; hiệu chỉnh bằng điểm OOF chỉ học từ nhãn đã có tại từng mốc. Học lại tại O bằng mọi nhãn hợp lệ đã có. Giữ các booking giống hệt trong cùng nhóm; nếu có ID thì nhóm thêm theo khách/đoàn. Không đổi cấu hình sau khi xem tháng cuối."""
    else:
        time_text = """Dùng timestamp search để giữ trật tự thời gian và đặt toàn bộ srch_id trong một tập. Phát triển tháng 2–4/2013, chốt cấu hình trước tháng 5; đánh giá cuối lần lượt tháng 5 và 6/2013. Bảng tính quy mô với khoảng đệm bảy ngày: lịch sử có date_time < O−7 ngày. Đây là giả định nghiên cứu cần E-Q2 xác nhận, không phải kết luận booking hoàn tất sau bảy ngày. Kiểm tra độ nhạy với 0/7/14/30 ngày; không chọn khoảng đệm bằng điểm trên hai tháng cuối.

Khi có timestamp kết quả, chỉ dùng nhãn đã có trước O và tạo điểm OOF bằng mô hình chỉ học nhãn sẵn có trước search đó. Hiệu chỉnh dùng OOF trên các tháng lịch sử đã hoàn tất, không dùng điểm trong mẫu. Học lại mỗi tháng chỉ cập nhật dữ liệu cũ, không đổi cấu hình từ kết quả cuối. Test Kaggle cùng giai đoạn và không nhãn, chỉ dùng kiểm tra schema/phân phối.

Đánh giá xác suất bằng cả trọng số theo cặp và trung bình theo search; định rõ cách tính trước thí nghiệm. Bootstrap ghép cặp theo srch_id (giữ toàn danh sách), phân tầng theo tháng và random_bool; không bootstrap từng dòng độc lập. Không có user ID nên vẫn chưa kiểm soát được một người tạo nhiều search."""
    criteria = [
        ["Khả dụng tại t0 · điều kiện chặn", "0 cột kết quả/đầu vào/cờ thiếu chưa được xác nhận tại t0; 0 nhóm giao tập", "Chặn mọi mô hình nếu vi phạm; liên hệ EDA không thay được chứng cứ thời điểm"],
        ["Thứ tự nhãn và hiệu chỉnh", "100% nhãn học/hiệu chỉnh sẵn có trước O; 100% điểm hiệu chỉnh là OOF theo thời gian", "HOTEL cần snapshot; EXPEDIA cần timestamp kết quả hoặc quy tắc theo dõi đã xác nhận"],
        ["Chuẩn xác suất tuyệt đối", "|Trung bình xác suất − tỷ lệ nhãn| ≤2 điểm phần trăm; ECE 10 nhóm đồng số mẫu ≤3 điểm phần trăm", "Đề xuất áp dụng từng tháng cuối và mẫu gộp; báo log loss, Brier, AP, ROC-AUC và biểu đồ độ tin cậy"],
        ["Giá trị bổ sung của cây so với LR mạnh", "Log loss giảm ≥1% tương đối; cận trên 95% của Δlog loss (cây − LR) <0", "So ghép cặp cùng mẫu và cùng nhánh; nếu không đạt thì chỉ dùng LR nếu LR qua chuẩn tuyệt đối"],
        ["Độ bền", "Báo riêng từng tháng, nhóm chính và kịch bản trùng/cơ chế hiển thị", "Không có mô hình được chấp nhận nếu không ứng viên nào qua điều kiện bắt buộc"],
    ]
    if hotel:
        criteria.append(["Ưu tiên can thiệp", "Lift@20% tăng ≥5% tương đối so với LR, cận dưới 95% của Δlift >0", "Ngân sách 20% là đề xuất; bootstrap theo nhóm booking/khách nếu có. Không suy thành hiệu quả giữ chân"])
    else:
        criteria.append(["Nhánh xếp hạng", "NDCG@5 tăng ≥2% tương đối so với xếp hạng bằng LR-booking; cận dưới 95% của ΔNDCG >0", "Macro theo search; gain=[0,1,5] dùng nhất quán. Báo riêng random_bool; không gọi điểm LambdaRank là propensity"])
    return combine("design", LAYOUT[8][1], [
        section("model_design", "Baseline, mô hình chính và xác suất", "Các nhánh dưới đây là đặc tả đề xuất, chưa tạo feature, fit mô hình hoặc hiệu chỉnh. Mọi ứng viên so sánh trên cùng tập thông tin đã được chấp nhận tại t0.", [("Nhánh đầu vào", pd.DataFrame(branches, columns=["Nhánh", "Thông tin", "Điều kiện"])), ("Ứng viên và đối chứng", pd.DataFrame(models, columns=["Ứng viên", "Vai trò", "Kiểm soát"]))]),
        section("protocol", "Chia theo thời gian và kiểm soát đánh giá", time_text + f"\n\n[Tài liệu hiệu chỉnh scikit-learn]({CALIBRATION}) mô tả dùng điểm ngoài tập học; lịch thời gian và tính sẵn có nhãn ở đây là đặc tả riêng cần kiểm tra." + (f" [Tài liệu LightGBM]({RANKING}) phân biệt mục tiêu binary và ranking; gain [0,1,5] là lựa chọn nghiên cứu của báo cáo." if not hotel else ""), [("Quy mô tại các mốc đề xuất · chưa chia tập", report.research_protocol)]),
        section("acceptance", "Tiêu chí chấp nhận đặt trước", "Các ngưỡng dưới đây là đề xuất nghiên cứu, chưa phải chuẩn phổ quát hoặc kết quả đo. Chốt trước khi huấn luyện. Độ bất định cần phản ánh cấu trúc phụ thuộc của dữ liệu.", [("Điều kiện chấp nhận", pd.DataFrame(criteria, columns=["Tiêu chí", "Ngưỡng đề xuất", "Cách diễn giải"]))]),
    ])


def design_figures(report, overview, design):
    from matplotlib.patches import FancyBboxPatch
    hotel = report.dataset == "HOTEL"
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.set(xlim=(0, 12), ylim=(0, 3.5)); ax.axis("off")
    texts = (["Một CSV gộp\n119,390 booking · 32 cột", "Hai cơ sở\nKhông có booking/customer ID", "Kết quả cuối\nHủy/no-show hoặc Check-Out"] if hotel else
             ["Một search · srch_id\nNgữ cảnh và timestamp", "Nhiều khách sạn · prop_id\nMột dòng = một cặp search–property", "Click và booking\nPhụ thuộc trong cùng danh sách"])
    for i, label in enumerate(texts):
        x = .2+i*4
        ax.add_patch(FancyBboxPatch((x, 1.2), 3.4, 1.4, boxstyle="round,pad=0.12", facecolor="#e9f1f6", edgecolor=BLUE))
        ax.text(x+1.7, 1.9, label, ha="center", va="center", fontsize=10)
        if i < 2:
            ax.annotate("", (x+3.95, 1.9), (x+3.55, 1.9), arrowprops={"arrowstyle": "->", "color": BLUE})
    ax.text(6, .45, "Sơ đồ đơn vị quan sát; không phải mô hình đã huấn luyện", ha="center", color="#52616a")
    fig.tight_layout()
    path = report.savefig("observation_structure", fig)
    overview["figures"].append(path)
    report.figure_notes[path.name] = "**Quan sát:** " + ("mỗi booking có một kết quả cuối, nhưng không có khóa booking/khách hàng để xác minh dòng trùng." if hotel else "nhiều khách sạn cùng thuộc một search; số dòng không là số search hoặc số người dùng.") + "\n\n**Phạm vi và cách đọc:** sơ đồ cấu trúc dữ liệu raw hiện có, không biểu diễn quan hệ nhân quả."
    protocol = report.research_protocol
    fig, ax = plt.subplots(figsize=(12, 4.8))
    origins = pd.to_datetime(protocol.origin)
    xmin = pd.Timestamp("2015-07-01" if hotel else "2012-11-01")
    import matplotlib.dates as mdates
    for i, origin in enumerate(origins):
        cutoff = origin if hotel else origin-pd.Timedelta(days=7)
        ax.barh(i, (cutoff-xmin).days, left=mdates.date2num(xmin), color=BLUE, height=.45)
        if not hotel:
            ax.barh(i, 7, left=mdates.date2num(cutoff), color="#dddddd", hatch="///", height=.45)
        ax.barh(i, (origin+pd.offsets.MonthBegin(1)-origin).days, left=mdates.date2num(origin), color=ORANGE, height=.45)
    ax.set_yticks(np.arange(len(origins)), [d.strftime("%Y-%m") for d in origins])
    ax.xaxis_date(); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.set(title="Lịch đánh giá đề xuất · chưa chia tập hoặc huấn luyện", ylabel="Tháng đánh giá", xlabel="Xanh: khoảng lịch sử ứng viên · cam: tháng đánh giá")
    ax.grid(axis="x", alpha=.15); fig.autofmt_xdate(); fig.tight_layout()
    path = report.savefig("evaluation_timeline", fig)
    design["blocks"][1]["figures"].append(path)
    report.figure_notes[path.name] = "**Quan sát:** các cửa sổ đánh giá dùng thứ tự thời gian và lịch sử mở rộng.\n\n**Phạm vi và cách đọc:** " + ("trục là ngày đến, chỉ dùng chẩn đoán hồi cứu. Vùng xanh còn phải lọc kết quả đã hoàn tất trước O theo bảng; không xác nhận đầu vào có tại t0 hoặc booking còn hiệu lực." if hotel else "trục là timestamp search; vùng gạch chéo là khoảng đệm bảy ngày giả định. Chưa xác nhận độ trưởng thành nhãn; không fit nếu thiếu bằng chứng. Toàn bộ srch_id phải nằm trong một tập.")


HEADERS = {
    "item": "Nội dung", "description": "Mô tả", "column": "Cột gốc", "variable": "Biến",
    "n": "Số booking/cặp", "positive": "Số nhãn 1", "rate_pct": "Tỷ lệ nhãn 1 (%)",
    "ci95_low_pct": "Cận dưới 95% (%)", "ci95_high_pct": "Cận trên 95% (%)",
    "n_under_100": "Nhóm dưới 100", "meaning": "Ý nghĩa", "role_or_caution": "Vai trò và lưu ý",
    "pandas_dtype": "Kiểu dữ liệu", "distinct_nonnull": "Số giá trị khác nhau không thiếu",
    "missing_n": "Số thiếu", "missing_pct": "Tỷ lệ thiếu (%)", "scenario": "Kịch bản",
    "effect_metric": "Thước đo", "effect_all": "Liên hệ · raw", "effect_unique": "Liên hệ · bỏ trùng giả định",
    "effect_city": "Liên hệ · City", "effect_resort": "Liên hệ · Resort",
    "effect_click": "V với click", "effect_booking": "V với booking", "n_nonmissing": "Cỡ mẫu sử dụng",
    "support_n": "Booking trong phần giao", "support_pct": "Độ phủ phần giao (%)", "standardized_pct": "Tỷ lệ cùng cơ cấu (%)",
    "duplicate_n": "Dòng trùng", "duplicate_pct": "Tỷ lệ trùng (%)", "origin": "Mốc O",
    "role": "Vai trò", "history_n": "Booking/cặp lịch sử", "evaluation_n": "Booking/cặp đánh giá",
    "pending_n": "Lịch sử chưa qua điều kiện nhãn", "history_searches": "Search lịch sử",
    "evaluation_searches": "Search đánh giá", "history_before": "Search lịch sử trước ngày",
    "searches": "Số lượt tìm kiếm", "groups": "Số nhóm", "units": "Số đơn vị", "population": "Quần thể/cách tính",
    "clicks": "Số click", "bookings": "Số booking", "click_pct": "Tỷ lệ click (%)", "booking_pct": "Tỷ lệ booking (%)",
    "pct_searches": "Tỷ lệ search (%)", "check": "Kiểm tra", "value": "Giá trị", "metric": "Chỉ số",
    "numerator": "Tử số", "denominator": "Mẫu số", "pct": "Tỷ lệ (%)", "year_month": "Năm–tháng", "month": "Tháng", "year": "Năm",
    "file": "File", "data_lines": "Dòng dữ liệu", "columns": "Số cột", "bytes": "Dung lượng byte",
    "count": "Số không thiếu", "mean": "Trung bình", "std": "Độ lệch chuẩn", "min": "Nhỏ nhất", "max": "Lớn nhất",
    "skewness": "Độ lệch phân phối", "pct_all_rows": "Trong toàn bộ dòng (%)",
    "pct_all_bookings": "Trong toàn bộ booking (%)", "positive_pct": "Tỷ lệ nhãn 1 (%)",
    "train_missing_pct": "Thiếu train (%)", "test_missing_pct": "Thiếu test (%)",
    "full_missing_n": "Số thiếu toàn train", "full_missing_pct": "Tỷ lệ thiếu toàn train (%)",
    "total_variation_0_1": "Khác biệt phân phối (0–1)", "test_only_categories": "Nhóm chỉ có ở test",
    "in_test": "Có trong test", "issue": "Vấn đề", "evidence_or_limit": "Bằng chứng hoặc giới hạn",
    "topic": "Nội dung", "eda_basis": "Căn cứ EDA", "proposal_only": "Đề xuất chưa thực hiện",
    "component": "Thành phần", "analysis": "Phân tích", "method": "Phương pháp",
    "source_train_rows": "Số dòng train nguồn", "observed_domain_and_basis": "Miền giá trị và căn cứ",
}


def display_header(value, dataset):
    if value == "n":
        return "Số booking" if dataset == "HOTEL" else "Số cặp"
    if value in HEADERS:
        return HEADERS[value]
    if isinstance(value, str) and value.startswith("full_"):
        return "Toàn train · " + HEADERS.get(value[5:], value[5:].replace("_", " "))
    return value


def prepare_publication(report):
    by = {s["key"]: s for s in walk(report.sections)}
    hotel = report.dataset == "HOTEL"
    problem_text = ("Đối tượng là một booking và hành vi là hủy/no-show, không phải khách hàng rời bỏ dịch vụ. Bài toán đề xuất là P(hủy/no-show | thông tin biết tại t0) cho booking đủ điều kiện. Dữ liệu phù hợp nghiên cứu quan hệ với kết quả cuối; muốn dự đoán ngay lúc tạo booking cần snapshot lịch sử và xác nhận cách chọn mẫu. Không áp thời hạn 90 ngày của Airbnb vì nhãn HOTEL gắn vòng đời booking." if hotel else "Đối tượng là khách sạn trong một search. Bài toán chính là P(booking | ngữ cảnh search và thuộc tính khách sạn trước hiển thị, thuộc quần thể đã chọn); click là mục tiêu phụ. Nhánh xếp hạng đánh giá thứ tự ứng viên theo từng search. Không có user ID và search không click nên chưa thể gọi đây là propensity CRM hoặc conversion toàn website. Không áp thời hạn 90 ngày của Airbnb cho hành vi trong search.")
    problem = section("problem", LAYOUT[2][1], problem_text)
    usage = usage_decisions(report)
    report.facts["columns_with_usage_decision"] = len(usage)
    by["appendix"]["blocks"].append(section("column_decisions", "Quyết định sử dụng theo từng cột", "Phân biệt nhãn, khóa, thông tin hậu kết quả và ứng viên có điều kiện. Chưa phê duyệt các cột chỉ dựa trên tên hoặc độ mạnh liên hệ.", [("Toàn bộ cột raw", usage)]))
    by["quality_main"]["blocks"].append(section("roles", "Vai trò dữ liệu trong thiết kế chính", "Bảng quyết định chi tiết từng cột nằm trong phụ lục. Đầu vào của mọi mô hình phải qua kiểm tra t0 trước khi so sánh chất lượng.", [("Kiểm kê vai trò", usage.groupby("Quyết định", sort=False).size().rename("Số cột").reset_index())]))
    # Keep the existing detailed conclusion as a traceable finding-to-action table.
    old_conclusion = by["conclusion_main"]
    old_conclusion["title"] = "Kết luận và hướng nghiên cứu"
    by["risks"].setdefault("blocks", []).extend([old_conclusion, questions(report.dataset)])
    design = proposed_design(report)
    design_figures(report, by["overview"], design)
    evidence = []
    facts = report.facts
    def point(text, key, values):
        evidence.append({"finding": text, "section_key": key, "values": values})
        return text
    if hotel:
        rates = report.research_evidence["sensitivity"]
        raw = rates[rates.scenario.eq("Giữ nguyên")].set_index("hotel")
        findings = [
            point(f"**Đơn vị và quy mô:** {facts['rows']:,} booking × {facts['columns']} cột, chỉ hai cơ sở; không có khóa khách hàng.", "dictionary", {"rows": facts["rows"], "columns": facts["columns"]}),
            point(f"**Nhãn:** {facts['positive']:,} hủy/no-show ({facts['rate']*100:.2f}%); bảng chéo xác nhận nhãn 0 là Check-Out.", "quality", {"positive": facts["positive"], "rate": facts["rate"]}),
            point(f"**Độ nhạy trùng:** {facts['duplicates']:,} dòng trùng; giả định bỏ trùng còn {facts['deduplicated_rows']:,}, tỷ lệ {facts['deduplicated_rate']*100:.2f}%. Chưa quyết định xóa.", "duplicate_by_hotel", {k: facts[k] for k in ["duplicates", "deduplicated_rows", "deduplicated_rate"]}),
            point(f"**Khác biệt cơ sở:** City {raw.loc['City Hotel','rate_pct']:.2f}% so với Resort {raw.loc['Resort Hotel','rate_pct']:.2f}%; cần đọc cùng chuẩn hóa phân khúc.", "stratification", {"city_pct": float(raw.loc['City Hotel','rate_pct']), "resort_pct": float(raw.loc['Resort Hotel','rate_pct'])}),
            point(f"**Liên hệ và đầu vào:** đã kiểm tra {facts['columns_association_audited']} cột ứng viên; cả {facts['columns_with_usage_decision']} cột raw có quyết định vai trò. Liên hệ mạnh chưa bảo đảm hợp lệ tại t0.", "signal", {"audited": facts["columns_association_audited"], "decisions": facts["columns_with_usage_decision"]}),
            point("**Thiết kế đề xuất:** LR có tương tác so với CatBoost trên cùng nhánh hợp lệ; chia theo thời gian, hiệu chỉnh OOF và kiểm tra độ nhạy trùng. Lịch theo tháng đến chỉ là chẩn đoán hồi cứu khi chưa có snapshot.", "design", {}),
        ]
    else:
        findings = [
            point(f"**Đơn vị và quy mô:** {facts['rows']:,} cặp thuộc {facts['searches']:,} search; {facts['columns']} cột train và {facts['test_columns']} cột test. Không có user ID để chấm CRM.", "quality", {k: facts[k] for k in ["rows", "searches", "columns", "test_columns"]}),
            point(f"**Hai hành vi:** click {facts['clicks']:,} ({facts['click_rate']*100:.2f}%), booking {facts['bookings']:,} ({facts['booking_rate']*100:.2f}%). Mẫu số là cặp search–property.", "quality", {k: facts[k] for k in ["clicks", "bookings", "click_rate", "booking_rate"]}),
            point(f"**Quần thể có điều kiện:** {facts['searches_without_click']} search hoàn toàn không click trong train; không suy CTR/CVR toàn website từ mẫu này.", "quality", {"searches_without_click": facts["searches_without_click"]}),
            point(f"**Phụ thuộc trong search:** {facts['searches_mixed_random_bool']} search có cờ random không đồng nhất; đã tách trọng số theo dòng/search và phân tầng giá, sao theo cơ chế.", "search_context", {"mixed_random": facts["searches_mixed_random_bool"]}),
            point(f"**Đầu vào và rò rỉ:** đủ {facts['columns_with_usage_decision']} cột raw có quyết định; position, gross và hai nhãn bị chặn khỏi đầu vào trước hiển thị; srch_id chỉ làm khóa.", "column_decisions", {"decisions": facts["columns_with_usage_decision"]}),
            point("**Thiết kế đề xuất:** LR có tương tác so với LightGBM binary cho xác suất; LambdaRank là nhánh riêng. Giữ nguyên search qua các tập; khoảng đệm nhãn cần xác nhận, bootstrap theo search.", "design", {}),
        ]
    executive = section("executive", LAYOUT[1][1], "\n\n".join(f"{i}. {text}" for i, text in enumerate(findings, 1)))
    report.executive_evidence = evidence
    trace = pd.DataFrame([[i, item["finding"], item["section_key"]] for i, item in enumerate(evidence, 1)], columns=["STT", "Phát hiện", "Khóa mục bằng chứng"])
    by["appendix"]["blocks"].append(section("executive_trace", "Truy vết tóm tắt điều hành", "Số liệu tóm tắt được tạo từ cùng bảng/facts dùng xuất báo cáo. Metadata lưu giá trị gốc để đối chiếu, không chép tay số liệu.", [("Phát hiện và nguồn trong báo cáo", trace)]))
    chosen = {**by, "glossary": glossary(report.dataset), "executive": executive, "problem": problem, "design": design}
    report.sections = [chosen[key] for key, _ in LAYOUT]
    for s, (_, title) in zip(report.sections, LAYOUT):
        s["title"] = title
    scopes = {"calendar.png": "Số lượng và tỷ lệ theo năm–tháng; tháng đầu/cuối có thể thiếu ngày. Không kết luận mùa vụ chỉ từ số tháng gộp.",
              "missing_patterns.png": "Bảng tổng hợp dùng toàn bộ dữ liệu; hình pattern tối đa 300 dòng seed=42. Không xác định cơ chế MCAR/MAR/MNAR.",
              "multivariate.png": "Tương quan dùng từng cặp không thiếu; scatter tối đa 4.000 điểm chỉ để hiển thị.",
              "position.png": "Toàn bộ train, phân tầng random_bool. Vị trí là cơ chế tiếp xúc; không diễn giải thành tác động nhân quả."}
    for name, note in list(report.figure_notes.items()):
        if "**Quan sát:**" not in note:
            report.figure_notes[name] = "**Quan sát:** " + note.removeprefix("Nhận xét: ") + "\n\n**Phạm vi và cách đọc:** " + scopes.get(name, "Quần thể, mẫu số và cửa sổ hiển thị ghi trên hình và bảng cạnh hình. Giữ nguyên giá trị raw; nhóm nhỏ cần đọc thận trọng.")
    top_level_ids = {id(s) for s in report.sections}
    for s in walk(report.sections):
        s["title"] = re.sub(r"^\d+\.\s*", "", s["title"]) if id(s) not in top_level_ids else s["title"]
        s["tables"] = [(label, table.rename(columns=lambda c: display_header(c, report.dataset))) for label, table in s["tables"]]
    reproducibility = chosen["reproducibility"]
    reproducibility["text"] += "\n\nPhần nghiên cứu bổ sung do scripts/hotel_expedia_research.py tạo từ cùng CSV. V tính từ bảng chéo K×2 không hiệu chỉnh; rank-biserial = 2U/(n1×n0)−1, với U của nhãn 1 và xử lý hòa hạng của SciPy. Không dùng kiểm định giả định các dòng độc lập để khẳng định ý nghĩa thống kê. Thống kê bổ sung Expedia dùng toàn bộ search và các bảng đếm toàn train. Các lịch chia tập chỉ là bảng quy mô, chưa sinh tập học hoặc dự đoán.\n\nChạy riêng: `python scripts/build_descriptive_reports.py --dataset " + report.dataset + "`. Cần package scripts/, pandas, numpy, scipy, matplotlib, nbformat và IPython cùng dữ liệu raw tương ứng. SHA-256 từng CSV ở phụ lục; ngày tải và phiên bản chưa được ghi nhận. Không suy ngày tải từ timestamp file."
    fingerprint = json.dumps({k: v.to_json(orient="split", double_precision=15) for k, v in sorted(report.research_evidence.items())}, sort_keys=True)
    report.facts.update(research_revision="hotel_expedia_airbnb_structure_v1", research_evidence_sha256=hashlib.sha256(fingerprint.encode()).hexdigest())
    previous = report.directory/"analysis_metadata.json"
    if previous.exists():
        old = json.loads(previous.read_text(encoding="utf-8"))["facts"]
        for key in ["rows", "columns", "positive", "rate", "duplicates", "deduplicated_rows", "deduplicated_rate", "searches", "clicks", "bookings", "click_rate", "booking_rate"]:
            if key in old and old[key] != facts[key]:
                raise ValueError(f"Underlying raw fact changed: {report.dataset}/{key}")
    from scripts.build_descriptive_reports import md_table
    report.rendered_tables_sha256 = sorted(hashlib.sha256(md_table(t).encode()).hexdigest() for s in walk(report.sections) for _, t in s["tables"])


def verify_artifacts(root, dataset, notebook):
    """Check executed notebook and Markdown have identical complete evidence."""
    path = root/"reports"/dataset
    markdown = (path/"README.md").read_text(encoding="utf-8")
    meta = json.loads((path/"analysis_metadata.json").read_text(encoding="utf-8"))
    headings = [c.source.removeprefix("## ") for c in notebook.cells if c.cell_type == "markdown" and c.source.startswith("## ")]
    assert headings == re.findall(r"^## (.+)$", markdown, re.MULTILINE)
    hashes = []
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        assert cell.execution_count
        for out in cell.outputs:
            assert out.output_type != "error"
            value = out.get("data", {}).get("text/markdown", "")
            value = "".join(value) if isinstance(value, list) else value
            if value.startswith("| "):
                assert value in markdown, "Notebook table differs from README"
                hashes.append(hashlib.sha256(value.encode()).hexdigest())
    assert sorted(hashes) == meta["rendered_tables_sha256"], "Table missing or truncated"
    assert meta["facts"]["columns_with_usage_decision"] == (32 if dataset == "HOTEL" else 54)
    keys = {s["key"] for s in walk_sections_from_metadata(meta)}
    assert {k for k, _ in LAYOUT} == keys
    for name in meta["figure_notes"]:
        assert (path/"figures"/name).is_file()
        assert f"figures/{name}" in markdown
    assert len(meta["executive_evidence"]) == 6


def walk_sections_from_metadata(meta):
    return [{"key": key} for key in meta["section_keys"]]
