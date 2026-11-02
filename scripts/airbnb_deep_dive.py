"""Airbnb-specific descriptive evidence and a proposed research protocol.

No estimator is fitted, no preprocessing is learned, and no feature/split file
is written. User/event joins and diagnostic bins exist only in memory for EDA.
"""
from __future__ import annotations

import hashlib
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from scripts.eda_diagnostics import BLUE, ORANGE, GREEN, SEED, combine, fig_note, section

CATEGORICAL = [
    "gender", "signup_method", "signup_flow", "language", "affiliate_channel",
    "affiliate_provider", "first_affiliate_tracked", "signup_app",
    "first_device_type", "first_browser",
]
TRANSACTION_PATTERN = r"(?:^|_)(?:book[a-z]*|reserv[a-z]*|pay[a-z]*|checkout|receipt|itinerar[a-z]*|confirm[a-z]*|request[a-z]*|billing)(?:_|$)"
AIRBNB_LAYOUT = [
    ("glossary", "Thuật ngữ và cách đọc báo cáo"),
    ("executive", "Tóm tắt điều hành"),
    ("problem", "1. Bài toán và lý do chọn dữ liệu"),
    ("overview", "2. Tổng quan bộ dữ liệu"),
    ("quality_main", "3. Chất lượng dữ liệu"),
    ("univariate", "4. Phân tích đơn biến"),
    ("multivariate_main", "5. Nhãn, liên hệ đa biến, cohort và sessions"),
    ("risks", "6. Hạn chế, rủi ro và quyền riêng tư"),
    ("research_design", "7. Thuật toán và thiết kế đánh giá đề xuất"),
    ("conclusion_main", "8. Bằng chứng về mức độ phù hợp"),
    ("appendix", "Phụ lục — từ điển và bảng bổ sung"),
    ("reproducibility", "Tái lập và kiểm soát phạm vi"),
]


def session_action_counts(chunk):
    """Count selected names per user, deduplicating presence only after chunks.

    All action_type values are retained. action/action_detail names are selected
    lexically, without inspecting their association with the target.
    """
    parts = []
    for column in ["action", "action_type", "action_detail"]:
        values = chunk[column].fillna("<NA>").astype(str)
        matches = [value for value in values.unique() if re.search(TRANSACTION_PATTERN, value, re.I)]
        chosen = pd.Series(True, index=chunk.index) if column == "action_type" else values.isin(matches)
        chosen &= chunk.user_id.notna()
        if not chosen.any():
            continue
        rows = pd.DataFrame({"user_id": chunk.loc[chosen, "user_id"], "value": values[chosen]})
        part = rows.groupby(["user_id", "value"], observed=True, sort=False).size().reset_index(name="event_n")
        part["field"] = column
        parts.append(part[["user_id", "field", "value", "event_n"]])
    return parts


def grouped_rates(frame, keys):
    from scripts.build_descriptive_reports import wilson
    result = frame.groupby(keys, observed=True, dropna=False).observed_booking.agg(n="size", positive="sum").reset_index()
    result["rate_pct"] = result.positive / result.n * 100
    result["ci95_low_pct"], result["ci95_high_pct"] = wilson(result.positive, result.n)
    result["n_under_100"] = result.n.lt(100)
    return result


def categorical_association(values, target):
    values = values.astype("object").where(values.notna(), "<NA>").astype(str)
    table = pd.crosstab(values, target).reindex(columns=[0, 1], fill_value=0)
    n = int(table.to_numpy().sum())
    if len(table) < 2 or (table.sum(axis=0) == 0).any():
        return {"n": n, "groups": len(table), "v": np.nan, "p": np.nan, "small_expected_pct": np.nan}
    chi2, p, _, expected = stats.chi2_contingency(table, correction=False)
    # The binary target makes min(r-1, c-1) equal to one.
    v = np.sqrt(chi2 / (n * min(table.shape[0]-1, table.shape[1]-1)))
    return {"n": n, "groups": len(table), "v": float(v), "p": float(p),
            "small_expected_pct": float((expected < 5).mean()*100)}


def bh_qvalues(pvalues):
    values = np.asarray(pvalues, dtype=float)
    result = np.full(len(values), np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    order = valid[np.argsort(values[valid])]
    if len(order):
        adjusted = values[order] * len(order) / np.arange(1, len(order)+1)
        result[order] = np.minimum(1, np.minimum.accumulate(adjusted[::-1])[::-1])
    return result


def p_text(value):
    if pd.isna(value):
        return "không tính"
    return "<1e-300" if value < 1e-300 else f"{value:.3g}"


def association_tables(train, account, first):
    frame = train.assign(observed_booking=train.country_destination.ne("NDF").astype(int))
    is2014 = account.dt.year.eq(2014)
    candidates = {c: frame[c] for c in CATEGORICAL}
    candidates.update({
        "age: cờ thiếu (EDA)": frame.age.isna().map({True: "Thiếu tuổi", False: "Có tuổi"}),
        "date_account_created: tháng (EDA)": account.dt.to_period("M").astype(str),
        "timestamp_first_active: tháng (EDA)": first.dt.to_period("M").astype(str),
    })
    records = []
    for name, values in candidates.items():
        all_stats = categorical_association(values, frame.observed_booking)
        recent = categorical_association(values[is2014], frame.loc[is2014, "observed_booking"])
        records.append({"variable": name, "effect_metric": "Cramér V",
                        "effect_all": all_stats["v"], "effect_2014": recent["v"],
                        "n_all": all_stats["n"], "n_2014": recent["n"],
                        "groups_all": all_stats["groups"], "p_raw": all_stats["p"],
                        "expected_cells_under_5_pct": all_stats["small_expected_pct"]})
    age_rows = frame.age.between(16, 100)
    age_record = {}
    for scope, mask in [("all", age_rows), ("2014", age_rows & is2014)]:
        positive = frame.loc[mask & frame.observed_booking.eq(1), "age"]
        negative = frame.loc[mask & frame.observed_booking.eq(0), "age"]
        result = stats.mannwhitneyu(positive, negative, alternative="two-sided", method="asymptotic")
        age_record[f"effect_{scope}"] = 2*result.statistic/(len(positive)*len(negative))-1
        age_record[f"n_{scope}"] = len(positive)+len(negative)
        if scope == "all":
            age_record["p_raw"] = result.pvalue
    records.append({"variable": "age: chỉ cửa sổ 16–100 (EDA)", "effect_metric": "Rank-biserial",
                    **age_record, "groups_all": np.nan, "expected_cells_under_5_pct": np.nan})
    result = pd.DataFrame(records)
    result["q_bh"] = bh_qvalues(result.p_raw)
    # Keep scientific p/q strings so small p-values are never printed as zero.
    result["p_chi2_or_mwu"] = result.p_raw.map(p_text)
    result["q_bh_14_tests"] = result.q_bh.map(p_text)
    return result.drop(columns=["p_raw", "q_bh"]), frame


def booking_delay_tables(train, account):
    booking = pd.to_datetime(train.date_first_booking, errors="coerce")
    positive = train.country_destination.ne("NDF")
    lag = (booking-account).dt.days
    valid = positive & lag.ge(0)
    values = lag[valid]
    summary = pd.DataFrame([{
        "booked_users": int(positive.sum()), "valid_nonnegative_lags": int(valid.sum()),
        "negative_lags": int((positive & lag.lt(0)).sum()),
        "missing_or_unparsed_booked_dates": int((positive & booking.isna()).sum()),
        "median_days": values.median(), "p75_days": values.quantile(.75),
        "p90_days": values.quantile(.90), "p95_days": values.quantile(.95),
        "max_days": values.max(),
    }])
    horizons = pd.DataFrame([{
        "horizon_days": h, "bookings_within_h": int(values.le(h).sum()),
        "denominator_valid_bookings": len(values), "pct_valid_bookings": values.le(h).mean()*100,
        "pct_all_observed_bookings": values.le(h).sum()/positive.sum()*100,
    } for h in [7, 30, 60, 90, 180, 365]])
    cohort = []
    for year in sorted(account.dt.year.dropna().unique()):
        in_year = account.dt.year.eq(year)
        year_valid = values[in_year[valid]]
        cohort.append({
            "account_year": str(year), "users": int(in_year.sum()),
            "valid_bookings": len(year_valid),
            "negative_lags": int((in_year & positive & lag.lt(0)).sum()),
            "within_30_pct": year_valid.le(30).mean()*100,
            "within_60_pct": year_valid.le(60).mean()*100,
            "within_90_pct": year_valid.le(90).mean()*100,
            "max_lag_days": year_valid.max(),
            "latest_booking": str(booking[in_year].max().date()),
        })
    # A sensitivity calculation under an explicitly unverified common cutoff.
    cutoff = booking.max()
    possible_followup = (cutoff-account).dt.days
    followup = pd.DataFrame([{
        "assumed_common_cutoff": str(cutoff.date()), "horizon_days": h,
        "users_with_calendar_gap_ge_h": int(possible_followup.ge(h).sum()),
        "pct_users": possible_followup.ge(h).mean()*100,
        "status": "Chỉ đúng nếu mọi user thực sự được theo dõi tới mốc giả định",
    } for h in [30, 60, 90, 365]])
    return lag, valid, summary, horizons, pd.DataFrame(cohort), followup


def cohort_strata(frame, account, column):
    rows = pd.DataFrame({
        "account_year": account.dt.year.astype(str),
        column: frame[column].astype("object").where(frame[column].notna(), "<NA>").astype(str),
        "observed_booking": frame.observed_booking,
    })
    return grouped_rates(rows, ["account_year", column])


def compact_strata(table, column):
    work = table.copy()
    work["rate_and_n"] = [f"{r.rate_pct:.2f}% (n={r.n:,})" for r in work.itertuples()]
    return work.pivot(index=column, columns="account_year", values="rate_and_n").fillna("Không có user").reset_index()


def heatmap_rates(ax, rates, counts, title, xlabel, ylabel, vmin=0, vmax=100):
    im = ax.imshow(rates.to_numpy(dtype=float), aspect="auto", cmap="YlGnBu", vmin=vmin, vmax=vmax)
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.set_xticks(range(len(rates.columns))); ax.set_xticklabels(rates.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(rates.index))); ax.set_yticklabels(rates.index)
    for i in range(len(rates)):
        for j in range(len(rates.columns)):
            value = rates.iloc[i, j]
            n = counts.iloc[i, j]
            label = "Không có" if pd.isna(value) else f"{value:.1f}%\nn={int(n):,}" + ("*" if n < 100 else "")
            ax.text(j, i, label, ha="center", va="center", fontsize=7.5,
                    color="white" if pd.notna(value) and value > 60 else "#172a35")
    return im


def session_audit(train, account, per_user, action_counts):
    from scripts.build_descriptive_reports import wilson
    y = train.country_destination.ne("NDF").astype(int)
    is2014 = account.dt.year.eq(2014)
    frame = pd.DataFrame({"id": train.id, "observed_booking": y,
                          "has_sessions": train.id.isin(per_user.index), "account_year": account.dt.year})
    rates2014 = grouped_rates(frame[is2014], ["has_sessions"])
    counts = frame.merge(per_user[["event_n"]], how="left", left_on="id", right_index=True, validate="one_to_one")
    counts["event_n"] = counts.event_n.fillna(0).astype(int)
    descriptions = []
    for (has_log, label), group in counts[is2014].groupby(["has_sessions", "observed_booking"]):
        descriptions.append({"has_sessions": has_log, "observed_booking": label,
                             "users": len(group), "mean_events": group.event_n.mean(),
                             "median_events": group.event_n.median(), "p90_events": group.event_n.quantile(.9),
                             "p99_events": group.event_n.quantile(.99), "max_events": group.event_n.max()})
    observed = frame[is2014 & frame.has_sessions]
    denominators = observed.observed_booking.value_counts().reindex([0, 1], fill_value=0)
    # action_counts is already one row per user/field/value, across all chunks.
    joined = action_counts.merge(observed[["id", "observed_booking"]], left_on="user_id", right_on="id", how="inner", validate="many_to_one")
    audit = []
    for (field, value), group in joined.groupby(["field", "value"], observed=True, sort=True):
        n = len(group)
        booked_n = int(group.observed_booking.sum())
        ndf_n = n-booked_n
        lo, hi = wilson(booked_n, n)
        audit.append({"field": field, "value": value, "users_with_action": n,
                      "booked_users": booked_n, "ndf_users": ndf_n,
                      "booking_rate_pct": booked_n/n*100,
                      "ci95_low_pct": float(lo), "ci95_high_pct": float(hi),
                      "pct_booked_users_with_action": booked_n/denominators[1]*100,
                      "pct_ndf_users_with_action": ndf_n/denominators[0]*100,
                      "events": int(group.event_n.sum()), "n_under_100": n < 100,
                      "transaction_name_match": bool(re.search(TRANSACTION_PATTERN, value, re.I))})
    audit = pd.DataFrame(audit).sort_values(["field", "users_with_action"], ascending=[True, False])
    return rates2014, pd.DataFrame(descriptions), audit, observed, counts


def proposed_protocol(train, account):
    windows = [
        ("Rolling 1: học", "2010-01-01", "2012-12-31"),
        ("Rolling 1: kiểm định", "2013-01-01", "2013-06-30"),
        ("Rolling 2: học", "2010-01-01", "2013-06-30"),
        ("Rolling 2: kiểm định", "2013-07-01", "2013-12-31"),
        ("Rolling 3: học", "2010-01-01", "2013-12-31"),
        ("Rolling 3: kiểm định", "2014-01-01", "2014-03-31"),
        ("Refit sau chọn cấu hình", "2010-01-01", "2014-03-31"),
        ("Hiệu chỉnh xác suất", "2014-04-01", "2014-04-30"),
        ("Đánh giá nội bộ cuối", "2014-05-01", "2014-06-30"),
    ]
    booked = train.country_destination.ne("NDF")
    result = []
    for purpose, start, end in windows:
        chosen = account.between(start, end)
        result.append([purpose, start, end, int(chosen.sum()), int(booked[chosen].sum()), booked[chosen].mean()*100])
    return pd.DataFrame(result, columns=["proposed_use", "account_from", "account_to", "users", "observed_bookings", "booking_pct"])


def reproducibility_section(report, environment):
    return section("reproducibility", "Tái lập và kiểm soát phạm vi", """
Để chạy lại notebook, cần thư mục scripts/ và năm CSV train_users_2.csv, test_users.csv, sessions.csv, countries.csv, age_gender_bkts.csv tại data/raw/AIRBNB/. Notebook đã lưu kết quả để đọc trực tiếp. Ô mở đầu hướng dẫn chuẩn bị thư mục và cài thư viện EDA. Dữ liệu gốc được lấy riêng theo hướng dẫn vì không được đính kèm kho mã.

Từ thư mục gốc, chạy `python scripts/build_descriptive_reports.py --dataset AIRBNB`. Cách khác là mở notebook bằng Jupyter, chọn Restart Kernel rồi Run All. Script đọc CSV gốc và xuất báo cáo Markdown, metadata JSON, hình và notebook có kết quả thực thi.

Người cung cấp xác nhận ngày 2026-11-02 rằng **ngày tải dữ liệu không được lưu**. Mã phiên bản Kaggle cũng chưa được ghi nhận. Vì vậy, bản dữ liệu đang dùng được nhận diện bằng SHA-256 của từng file và của danh mục file có thứ tự trong metadata. Ngày phân tích được ghi theo múi giờ Asia/Ho_Chi_Minh.

Các bảng dùng toàn bộ người dùng hoặc toàn bộ sessions có khóa hợp lệ trong phạm vi ghi cạnh bảng. Hình về mẫu thiếu chỉ hiển thị tối đa 300 dòng với seed=42.

Phép tính Cramér V dùng chi-square không hiệu chỉnh Yates. Bảng báo p-value xấp xỉ và tỷ lệ ô có tần số kỳ vọng dưới 5 để kiểm tra độ phù hợp của xấp xỉ. Kiểm định Mann–Whitney hai phía dùng xấp xỉ có hiệu chỉnh các giá trị đồng hạng. Hệ số rank-biserial được tính bằng 2U/(n_y1 × n_y0) − 1. Trong công thức này, U là thống kê Mann–Whitney với nhóm y=1 đứng trước, còn n_y1 và n_y0 là cỡ mẫu hai nhóm.

Phương pháp Benjamini–Hochberg (BH) điều chỉnh p-value cho 14 phép kiểm định trên toàn kỳ và cho ra giá trị q trong bảng. Việc chọn biến sẽ được kiểm tra bằng thí nghiệm mô hình. Khoảng Wilson 95% giả định các người dùng độc lập. Khoảng này mô tả bất định của tỷ lệ, đồng thời cần xem xét riêng sai lệch chọn mẫu và khác biệt giữa các nhóm đăng ký.

Các kết quả được tính lại trong lần phân tích hiện tại. Bảng môi trường dưới đây và SHA-256 của ba module dựng báo cáo trong metadata nhận diện mã đã chạy. Thuật toán, cửa sổ chia dữ liệu, bootstrap và ngưỡng chấp nhận ở phần 7 là thiết kế cho giai đoạn tiếp theo.
""", [("Môi trường thực thi chính xác", environment)])


def deepen_airbnb(report, train, test, account, first, per_user, action_counts):
    from scripts.build_descriptive_reports import count, drift_table, rate_table
    association, frame = association_tables(train, account, first)
    lag, valid, lag_summary, horizons, lag_cohorts, followup = booking_delay_tables(train, account)
    s2014, event_summary, actions, session_users, event_users = session_audit(train, account, per_user, action_counts)
    is2014 = account.dt.year.eq(2014)
    base = {s["key"]: s for s in report.sections}
    appendix = base["appendix"]["blocks"]
    years = sorted(account.dt.year.dropna().astype(int).unique())
    strata = {c: cohort_strata(frame, account, c) for c in ["signup_app", "gender", "affiliate_channel"]}
    app2014 = strata["signup_app"].query("account_year == '2014'").set_index("signup_app")
    gender2014 = strata["gender"].query("account_year == '2014'").set_index("gender")
    v_by_name = association.set_index("variable")
    def coverage_at(h):
        return float(horizons.loc[horizons.horizon_days.eq(h), "pct_valid_bookings"].iloc[0])

    # Label delay: conditional coverage among observed, nonnegative bookings.
    values = lag[valid]
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.5))
    axes[0].hist(values, bins=np.arange(0, 381, 15), color=BLUE, edgecolor="white")
    axes[0].set(title="Độ trễ đến lượt đặt chỗ đầu tiên", xlabel="Ngày từ tạo tài khoản đến booking", ylabel="Số người có booking và độ trễ ≥ 0")
    x = np.sort(values.to_numpy())
    axes[1].plot(x, np.arange(1, len(x)+1)/len(x)*100, color=ORANGE)
    horizon_labels = []
    for h in [30, 60, 90]:
        value = coverage_at(h)
        axes[1].scatter([h], [value], color=GREEN, s=25, zorder=3)
        horizon_labels.append(f"{h} ngày: {value:.2f}%")
    axes[1].text(.55, .14, "\n".join(horizon_labels), transform=axes[1].transAxes,
                 fontsize=10, bbox={"facecolor":"white","edgecolor":"#c9d2d9","pad":8})
    axes[1].set(title="Tỷ lệ tích lũy trong các booking quan sát hợp lệ", xlabel="Độ trễ (ngày)", ylabel="Tỷ lệ booking có độ trễ ≤ x (%)", ylim=(0, 103), xlim=(0, 365))
    fig.tight_layout(); delay_figure = report.savefig("booking_delay", fig)
    fig_note(report, delay_figure, f"Nhận xét: trong {len(values):,} lượt đặt chỗ có độ trễ không âm, {coverage_at(30):.2f}% xảy ra trong 30 ngày, {coverage_at(60):.2f}% trong 60 ngày và {coverage_at(90):.2f}% trong 90 ngày. Phần tăng thêm từ ngày 30 đến ngày 90 cho thấy lợi ích về mức bao phủ khi kéo dài thời hạn. Mẫu số chỉ gồm các lượt đặt chỗ có độ trễ hợp lệ. Bảng ngoại lệ thống kê riêng {int(lag.lt(0).sum())} trường hợp độ trễ âm.")
    delay_section = section("booking_delay", "Độ trễ booking và giới hạn định nghĩa nhãn", f"""
Độ trễ là số ngày lịch từ ngày tạo tài khoản đến ngày đặt chỗ đầu tiên, tính bằng date_first_booking − date_account_created. Có {len(values):,} lượt đặt chỗ có độ trễ không âm. Báo cáo thống kê riêng {int(lag.lt(0).sum())} trường hợp có ngày đặt chỗ trước ngày tạo tài khoản để kiểm tra lại định nghĩa thời gian.

**Trong các lượt đặt chỗ có độ trễ hợp lệ, {coverage_at(90):.2f}% xảy ra trong 90 ngày đầu** và {100-coverage_at(90):.2f}% xảy ra muộn hơn. Vì mẫu số chỉ gồm người đã đặt chỗ, các tỷ lệ này mô tả tốc độ phát sinh đặt chỗ trong nhóm đó. Xác suất đặt chỗ của toàn bộ người dùng cần một mẫu số khác, gồm cả người mang nhãn y=0.

Ngày đặt chỗ muộn nhất là {pd.to_datetime(train.date_first_booking).max().date()}. Độ trễ lớn nhất trong mỗi nhóm năm tạo tài khoản đều là 365 ngày. Mẫu hình này gợi ý cần kiểm tra liệu dữ liệu có giới hạn theo dõi một năm cho từng người dùng hay không. Câu trả lời quyết định cách diễn giải nhãn y=0, nhất là ở các nhóm đăng ký gần cuối tập train.

Để xem kết quả phụ thuộc vào thời gian theo dõi như thế nào, báo cáo thử giả định mọi người dùng đều được theo dõi đến ngày đặt chỗ muộn nhất. Theo giả định này, toàn bộ train có khoảng cách lịch đủ 30, 60 và 90 ngày. Ngày kết thúc theo dõi thực tế vẫn cần được bổ sung để xác nhận ai đã được theo dõi đủ 90 ngày mà không đặt chỗ. Trong phạm vi hiện tại, bài toán dùng nhãn y được định nghĩa từ cột country_destination.
""", [("Phân phối độ trễ: mẫu số và ngoại lệ", lag_summary),
      ("Mức bao phủ các thời hạn trên lượt đặt chỗ đã ghi nhận", horizons),
      ("Độ trễ theo năm tạo tài khoản", lag_cohorts),
      ("Phân tích độ nhạy khi giả định cùng ngày kết thúc theo dõi", followup)], [delay_figure])

    # Full candidate audit: 10 categorical fields, age and two original dates.
    signal_section = section("signal", "Độ mạnh liên hệ với nhãn y trên toàn bộ biến ứng viên", f"""
Phân tích xem xét 13 cột ứng viên gốc, gồm 10 biến phân loại, age và hai mốc thời gian. Cờ thiếu tuổi bổ sung góc nhìn về mức độ đầy đủ của hồ sơ. Hai mốc thời gian được nhóm theo tháng để mô tả nhóm đăng ký. ID, country_destination và date_first_booking được loại khỏi danh sách biến ứng viên.

Cramér V = sqrt(chi-square / [n × min(r−1,c−1)]), với r và c là số hàng và cột của bảng chéo. V nằm trong [0,1] và tăng khi liên hệ giữa hai biến mạnh hơn. Cột effect_all mô tả toàn bộ train. Cột effect_2014 tính riêng cho người tạo tài khoản năm 2014 để đối chiếu ảnh hưởng của thành phần năm.

**Cách đọc kết quả:** gender có V={v_by_name.loc['gender','effect_all']:.3f} trên toàn kỳ và {v_by_name.loc['gender','effect_2014']:.3f} trong năm 2014. Báo cáo diễn giải mức khoảng 0,2 này là liên hệ yếu đến vừa. signup_app có V={v_by_name.loc['signup_app','effect_all']:.3f} và {v_by_name.loc['signup_app','effect_2014']:.3f}, thể hiện liên hệ yếu hơn gender trong cả hai phạm vi. Đây là cách diễn giải mô tả trên thang 0–1, không phải ngưỡng chung để chọn biến. Các kết quả cho thấy nên kiểm tra giá trị bổ sung của hai biến khi huấn luyện.

Tuổi trong dải tham chiếu 16–100 được so sánh giữa hai nhóm nhãn y bằng kiểm định Mann–Whitney hai phía. Hệ số rank-biserial đi kèm nằm trong [−1,1]. Dấu dương cho biết tuổi ở nhóm y=1 có xu hướng cao hơn nhóm y=0. Trị tuyệt đối gần 0 cho biết khác biệt về thứ hạng tuổi rất nhỏ. Vì rank-biserial và Cramér V đo hai dạng liên hệ khác nhau, chúng cần được diễn giải riêng. Tuổi ngoài dải và tuổi thiếu có thống kê riêng.

Bảng giữ p-value và giá trị q sau điều chỉnh nhiều phép kiểm định để người đọc kiểm tra phương pháp. Với cỡ mẫu lớn, cần đọc chúng cùng độ mạnh liên hệ. Tỷ lệ ô có tần số kỳ vọng dưới 5 giúp nhận biết những kiểm định chi-square có xấp xỉ kém tin cậy hơn.

Báo cáo này không đưa AUC vì chưa huấn luyện mô hình. Nguồn phương pháp: [Cramér V của SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.contingency.association.html), [Mann–Whitney của SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html).
""", [("Độ mạnh liên hệ toàn kỳ và trong cohort 2014; nêu đủ 14 phép sàng lọc", association)])

    frame["age_group_eda"] = pd.cut(frame.age, [15, 24, 34, 44, 54, 64, 100], labels=["16–24", "25–34", "35–44", "45–54", "55–64", "65–100"]).astype("object")
    frame.loc[frame.age.notna() & ~frame.age.between(16, 100), "age_group_eda"] = "Ngoài [16,100]"
    frame["age_group_eda"] = frame.age_group_eda.fillna("Thiếu tuổi")
    frame["age_missing_eda"] = frame.age.isna().map({True: "Thiếu tuổi", False: "Có tuổi"})
    display_columns = ["gender", "signup_app", "signup_method", "affiliate_channel", "first_device_type", "language", "age_group_eda", "age_missing_eda"]
    target_tables, extra_tables = [], []
    for c in display_columns:
        table = rate_table(frame, c, "observed_booking")
        if c == "language":
            target_tables.append(("Booking theo language — 10 nhóm đông nhất; phần còn lại ở phụ lục", table.head(10)))
            extra_tables.append(("Booking theo language — các nhóm còn lại", table.iloc[10:]))
        else:
            target_tables.append((f"Booking theo {c} — toàn bộ nhóm", table))
    for c in [c for c in CATEGORICAL if c not in display_columns]:
        extra_tables.append((f"Booking theo {c} — bổ sung", rate_table(frame, c, "observed_booking")))
    target_section = section("target_rates", "Tỷ lệ đặt chỗ theo hồ sơ, kênh, thiết bị và tình trạng thiếu tuổi", "Mỗi tỷ lệ được tính trên số người dùng trong nhóm. Cột n là số người dùng, positive là số người có nhãn y=1, rate_pct là tỷ lệ phần trăm. Hai cột ci95_low_pct và ci95_high_pct là cận dưới và cận trên của khoảng Wilson 95%. Nhóm có n<100 được đánh dấu vì ước lượng có thể kém chính xác. Các bảng giữ riêng NA, unknown và tuổi ngoài dải tham chiếu. Phần tiếp theo so sánh các nhóm trong từng năm đăng ký để xem chênh lệch thay đổi như thế nào.", target_tables)

    # Within-year comparison, with explicit absent cells and cell counts.
    fig = plt.figure(figsize=(22, 7), layout="constrained")
    grid = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1, .04])
    axes = [fig.add_subplot(grid[0, i]) for i in range(3)]
    color_axis = fig.add_subplot(grid[0, 3])
    labels = {"signup_app":"Ứng dụng đăng ký", "gender":"Giới tính khai báo", "affiliate_channel":"Kênh tiếp cận"}
    for ax, c in zip(axes, strata):
        table = strata[c]
        r = table.pivot(index=c, columns="account_year", values="rate_pct")
        n = table.pivot(index=c, columns="account_year", values="n")
        im = heatmap_rates(ax, r, n, f"{labels[c]} và năm tạo tài khoản", "Năm tạo tài khoản", labels[c])
    fig.colorbar(im, cax=color_axis, label="Có booking được ghi nhận (%)")
    strata_figure = report.savefig("cohort_strata", fig)
    fig_note(report, strata_figure, f"Nhận xét: trong năm 2014, tỷ lệ đặt chỗ của Web là {app2014.loc['Web','rate_pct']:.2f}%, iOS là {app2014.loc['iOS','rate_pct']:.2f}% và Android là {app2014.loc['Android','rate_pct']:.2f}%. Chênh lệch giữa các ứng dụng vẫn xuất hiện khi so sánh trong cùng năm. Nhóm FEMALE có tỷ lệ {gender2014.loc['FEMALE','rate_pct']:.2f}%, so với {gender2014.loc['-unknown-','rate_pct']:.2f}% ở nhóm giới tính unknown. Nhóm OTHER chỉ có {int(gender2014.loc['OTHER','n'])} người nên cần đọc cùng khoảng Wilson trong phụ lục. Dấu * đánh dấu ô có n<100.")
    strata_section = section("cohort_strata", "Tách thành phần cohort khỏi chênh lệch app, gender và kênh", """
Mỗi cột trong bảng tương ứng với một năm tạo tài khoản. Đọc theo cột giúp so sánh ứng dụng, giới tính hoặc kênh tiếp cận trong cùng nhóm đăng ký. Một số ứng dụng chỉ xuất hiện ở các năm sau, nên so sánh toàn kỳ có thể chịu ảnh hưởng của thành phần năm.

Việc tách theo năm giúp kiểm tra một phần ảnh hưởng này. Khác biệt theo tháng hoặc các đặc điểm khác vẫn cần được xem xét khi xây dựng mô hình. Phụ lục cung cấp khoảng Wilson 95% cho từng ô để đọc cùng số người dùng.
""", [(f"{c} × năm signup: tỷ lệ và n", compact_strata(t, c)) for c, t in strata.items()], [strata_figure])

    interaction_tables = []
    fig = plt.figure(figsize=(18, 6.5), layout="constrained")
    grid = fig.add_gridspec(1, 3, width_ratios=[1, 1, .035])
    axes = [fig.add_subplot(grid[0, i]) for i in range(2)]
    color_axis = fig.add_subplot(grid[0, 2])
    labels.update({"age_missing_eda":"Tình trạng tuổi"})
    for ax, (a, b) in zip(axes, [("signup_app", "affiliate_channel"), ("age_missing_eda", "gender")]):
        interaction = grouped_rates(frame[is2014], [a, b])
        interaction_tables.append((f"{a} × {b}, chỉ cohort 2014", interaction))
        rates = interaction.pivot(index=a, columns=b, values="rate_pct")
        ns = interaction.pivot(index=a, columns=b, values="n")
        im = heatmap_rates(ax, rates, ns, f"{labels[a]} và {labels[b].lower()} (2014)", labels[b], labels[a])
    fig.colorbar(im, cax=color_axis, label="Có booking được ghi nhận (%)")
    interaction_figure = report.savefig("multivariate", fig)
    app_channel = interaction_tables[0][1].set_index(["signup_app","affiliate_channel"])
    missing_gender = interaction_tables[1][1].set_index(["age_missing_eda","gender"])
    fig_note(report, interaction_figure, f"Nhận xét: với người dùng Web năm 2014, nhóm direct có tỷ lệ đặt chỗ {app_channel.loc[('Web','direct'),'rate_pct']:.2f}% (n={int(app_channel.loc[('Web','direct'),'n']):,}). Nhóm content có tỷ lệ {app_channel.loc[('Web','content'),'rate_pct']:.2f}% (n={int(app_channel.loc[('Web','content'),'n']):,}). Trong nhóm FEMALE cùng năm, tỷ lệ của người có tuổi là {missing_gender.loc[('Có tuổi','FEMALE'),'rate_pct']:.2f}%, so với {missing_gender.loc[('Thiếu tuổi','FEMALE'),'rate_pct']:.2f}% ở người thiếu tuổi. Các chênh lệch trong cùng năm là cơ sở để kiểm tra giá trị của những nhóm kết hợp khi huấn luyện. Dấu * đánh dấu ô có n<100.")
    interaction_section = section("interactions", "Tỷ lệ đặt chỗ theo các nhóm kết hợp trong năm 2014", "Hai biểu đồ kết hợp ứng dụng đăng ký với kênh tiếp cận, và tình trạng thiếu tuổi với giới tính khai báo. Cách nhìn này giúp xác định những nhóm cần kiểm tra thêm trong mô hình. Màu biểu diễn tỷ lệ đặt chỗ, còn n cho biết số người dùng trong ô. Dấu * đánh dấu ô có dưới 100 người. Các nhóm và cờ thiếu được tính tạm để lập bảng EDA.", figures=[interaction_figure])

    recent_users = int(is2014.sum())
    recent_logs = int(train.loc[is2014, "id"].isin(per_user.index).sum())
    coverage_recent = recent_logs/recent_users*100
    coverage_test = test.id.isin(per_user.index).mean()*100
    trans = actions[actions.transaction_name_match & actions.field.isin(["action", "action_type"])].copy()
    trans_display = trans.drop(columns=["events", "transaction_name_match"])
    receipt = trans[(trans.field=="action") & trans.value.eq("receipt")].iloc[0]
    requested = trans[(trans.field=="action") & trans.value.eq("requested")].iloc[0]
    session_section = section("sessions_evidence", "Sessions: so sánh cùng cohort và rà soát thông tin giao dịch", f"""
Phân tích đã quét toàn bộ {report.facts['sessions']:,} sự kiện. Trong nhóm đăng ký năm 2014, **{recent_logs:,}/{recent_users:,} người dùng train có sessions ({coverage_recent:.2f}%)**. Tỷ lệ tương ứng ở test là **{coverage_test:.2f}%**, cao hơn {coverage_test-coverage_recent:.2f} điểm phần trăm. Tỷ lệ trên toàn bộ train chỉ là 34,58% vì nhóm đăng ký năm 2010–2013 không có nhật ký trong dữ liệu hiện có. Vì vậy, cần so sánh độ phủ trong cùng năm đăng ký.

Nghiên cứu riêng sessions có phạm vi phù hợp là {recent_users:,} người dùng train đăng ký năm 2014. Tuy nhiên, thiết kế dự đoán tại t0 cần biết sự kiện nào đã xảy ra trước thời điểm đó. Vì sessions thiếu thời điểm sự kiện, thiết kế chính loại nguồn này khỏi đầu vào cho đến khi xác minh được khoảng thời gian ghi nhật ký.

Bảng dưới so sánh người có và không có sessions trong năm 2014. Bảng số sự kiện giữ cả người không có nhật ký và gán event_n=0 khi tính thống kê. Cột secs_elapsed là thời lượng, nên không xác định được thời điểm hoặc thứ tự hành động.

Để rà soát rủi ro rò rỉ, phân tích chọn tên hành động liên quan giao dịch hoặc xác minh bằng biểu thức **{TRANSACTION_PATTERN}**. Quy tắc tên được đặt trước khi xem liên hệ với nhãn y và khớp các thành phần tên phân cách bằng dấu gạch dưới. Bảng giữ đầy đủ action_type để đối chiếu. Mỗi người chỉ được đếm một lần cho mỗi tên hành động sau khi gộp toàn bộ dữ liệu.

**Kết quả rà soát:** trong những người có hành động receipt, {int(receipt.booked_users):,}/{int(receipt.users_with_action):,} người có nhãn y=1 ({receipt.booking_rate_pct:.2f}%). Với requested, con số tương ứng là {int(requested.booked_users):,}/{int(requested.users_with_action):,} ({requested.booking_rate_pct:.2f}%). Các tỷ lệ cao cho thấy cần xác minh liệu nhật ký có chứa bước gần hoặc sau thời điểm đặt chỗ. Tên hành động có thể bao gồm yêu cầu thất bại, xác minh tài khoản hoặc chuẩn bị thanh toán, nên cần dữ liệu thời gian và mô tả nghiệp vụ để xác định ý nghĩa.

Hai cột pct_booked_users_with_action và pct_ndf_users_with_action có mẫu số là số người có sessions trong từng nhóm y=1 và y=0. Cột booking_rate_pct có mẫu số là số người có hành động đó. Các cột trả lời hai câu hỏi khác nhau: hành động phổ biến đến đâu trong mỗi nhóm nhãn, và tỷ lệ đặt chỗ của người có hành động là bao nhiêu.
""", [("Độ phủ năm account train", next(t for name, t in next(b for b in base["multivariate_main"]["blocks"] if b["key"] == "sessions")["tables"] if "năm account" in name)),
      ("Booking trong nhóm có/không sessions — chỉ cohort 2014", s2014),
      ("Số sự kiện/user theo có log và nhãn — chỉ cohort 2014", event_summary),
      ("Presence tên ứng viên giao dịch/xác minh × nhãn, trong user 2014 có log", trans_display)],
      [report.directory/"figures/session_coverage.png"])
    fig_note(report, report.directory/"figures/session_coverage.png", f"Nhận xét: độ phủ sessions trên toàn bộ train là 34,58%. Khi giới hạn ở nhóm đăng ký năm 2014, độ phủ train đạt {coverage_recent:.2f}%, gần hơn với mức {coverage_test:.2f}% của test. Khoảng cách còn {coverage_test-coverage_recent:.2f} điểm phần trăm. Nhóm đăng ký năm 2010–2013 không có nhật ký, nên tỷ lệ toàn kỳ chịu ảnh hưởng lớn của phạm vi thu thập.")

    # Calendar table appears once in the body; monthly detail only in appendix.
    old_time = next(b for b in base["multivariate_main"]["blocks"] if b["key"] == "time")
    all_drift = drift_table(train, test, CATEGORICAL)
    recent_drift = drift_table(train[is2014], test, CATEGORICAL)
    drift = all_drift.rename(columns={"total_variation_0_1": "tv_all_train_vs_test"}).merge(
        recent_drift[["column", "total_variation_0_1"]].rename(columns={"total_variation_0_1": "tv_train2014_vs_test"}),
        on="column", validate="one_to_one")
    monthly = next(t for name, t in next(b for b in appendix if b["key"] == "calendar_tables")["tables"] if "Cohort theo tháng" in name)
    time_section = section("time", "Cohort tháng có bất định và drift train–test", """
Train gồm người tạo tài khoản từ tháng 1/2010 đến tháng 6/2014. Test nối tiếp từ tháng 7 đến tháng 9/2014. Hình biểu diễn tỷ lệ đặt chỗ theo từng tháng cùng khoảng Wilson 95%. Vạch tại tháng 1/2014 đánh dấu thời kỳ bắt đầu có sessions. Nhóm tháng ít người có khoảng tin cậy rộng hơn, nên dao động của tỷ lệ cần được đọc cùng cỡ mẫu.

Total variation (TV) đo mức khác nhau giữa hai phân phối của một biến, từ 0 (giống nhau) đến 1 (không giao nhau). Cột tv_all_train_vs_test so sánh toàn bộ train với test. Cột tv_train2014_vs_test giới hạn train ở năm 2014. Nếu TV giảm nhiều trong phép so sánh thứ hai, thành phần năm đăng ký là một yếu tố cần xem xét. Hai phép so sánh mô tả sự thay đổi phân phối đầu vào. Kiểm định mô hình theo thời gian ở phần 7 sẽ đánh giá khả năng dự báo khi dữ liệu thay đổi.
""", [("Khoảng thời gian account", old_time["tables"][0][1]), ("Khác biệt category train–test: toàn kỳ và cùng năm 2014", drift)],
      [report.directory/"figures/account_cohorts.png"])
    smallest = monthly.loc[monthly.users.idxmin()]
    fig_note(report, report.directory/"figures/account_cohorts.png", f"Nhận xét: nhóm đăng ký tháng {smallest.account_month} chỉ có {int(smallest.users)} người. Tỷ lệ đặt chỗ là {smallest.booked_pct:.2f}% với khoảng Wilson 95% từ {smallest.ci95_low_pct:.2f}% đến {smallest.ci95_high_pct:.2f}%. Vì cỡ mẫu nhỏ, ước lượng của tháng này có độ bất định lớn. Vạch đứt tháng 1/2014 đánh dấu thời kỳ bắt đầu có sessions.")

    # A concrete research target, with a separately blocked deployment horizon.
    problem = section("problem", "1. Bài toán và lý do chọn dữ liệu", f"""
**Bối cảnh nghiệp vụ:** doanh nghiệp muốn ưu tiên hỗ trợ và cá nhân hóa trải nghiệm cho người dùng mới dựa trên khả năng họ phát sinh lượt đặt chỗ đầu tiên. Mỗi người dùng nhận một điểm xác suất để phục vụ việc sắp thứ tự ưu tiên.

**Bài toán nghiên cứu:** ngay sau khi người dùng tạo tài khoản, mô hình dự kiến sử dụng thông tin đăng ký để ước lượng xác suất có lượt đặt chỗ đầu tiên được ghi nhận trong bộ dữ liệu. Đầu ra là xác suất trong [0,1] cho từng người dùng. Bài toán dự đoán điểm đến với 12 lớp được trình bày để giải thích nguồn dữ liệu.

**Thời điểm dự đoán t0:** báo cáo chọn thời điểm ngay sau khi hoàn tất tạo tài khoản. Vì date_account_created chỉ ghi ngày, dữ liệu hiện tại chỉ cho phép kiểm tra thứ tự giữa các ngày. Để dùng thông tin hồ sơ tại t0, cần xác minh mỗi giá trị phản ánh hồ sơ lúc đăng ký.

**Nhãn y:** y=1 khi country_destination khác NDF và y=0 khi country_destination bằng NDF. Nhãn y thể hiện kết quả được ghi nhận trong bộ dữ liệu. Có {int(lag.lt(0).sum())} trường hợp ngày đặt chỗ trước ngày tạo tài khoản. Các trường hợp này cần được đánh dấu để xác minh trước khi quyết định đưa vào tập huấn luyện.

**Thời hạn dự đoán:** bài toán hiện tại dùng nhãn y với thời gian theo dõi theo bộ dữ liệu. Phương án triển khai đề xuất thời hạn 90 ngày vì khoảng này bao phủ {coverage_at(90):.2f}% lượt đặt chỗ có độ trễ hợp lệ. Để xây dựng nhãn cho phương án đó, cần biết ngày kết thúc theo dõi của từng người dùng. Người không đặt chỗ chỉ được gán nhãn âm 90 ngày khi đã được theo dõi đủ khoảng thời gian này.
""", [("Lý do chọn Airbnb so với hai bộ còn lại", pd.DataFrame([
        ["AIRBNB", "User mới", f"{len(train):,} user; {frame.observed_booking.mean()*100:.2f}% có booking", "Đúng đối tượng chấm propensity khách hàng; có ID", "Chọn cho nghiên cứu, còn điều kiện nhãn/t0"],
        ["HOTEL", "Booking đã được tạo", "Nhãn hủy/no-show; không quan sát đầy đủ người chưa đặt", "Hợp cancellation propensity", "Không trả lời trực tiếp ai sẽ tạo lượt đặt chỗ đầu tiên"],
        ["EXPEDIA", "Cặp search–hotel", "Tương tác trong danh sách; thiếu user ID và search không click", "Hợp ranking/propensity trong search", "Không ưu tiên cho propensity onboarding theo user"],
    ], columns=["dataset", "unit", "evidence", "fit", "decision"]))])

    models = pd.DataFrame([
        ["Baseline xác suất hằng", "p bằng tỷ lệ booking trong phần train của từng fold", "Mốc đối chứng log loss/Brier; không dùng tỷ lệ toàn bộ dữ liệu", "Chưa chạy"],
        ["Baseline Logistic Regression + L2", "Quan hệ cộng, dễ đối chiếu với liên hệ biên EDA", "One-hot/nhóm hiếm và xử lý tuổi/missing chỉ học trên train; kiểm tra category mới", "Chưa chạy"],
        ["Mô hình chính đề xuất: CatBoost nhị phân", "Nhiều category, missing có cấu trúc và các nhóm kết hợp có tỷ lệ khác nhau", "Xử lý category bằng cơ chế của mô hình; numeric missing được hỗ trợ, categorical NA cần quy ước. Giới hạn độ sâu/L2 và early stopping", "Chưa chạy"],
        ["Hiệu chỉnh xác suất sigmoid", "Propensity cần xác suất có ý nghĩa, không chỉ xếp hạng", "Fit trên cohort calibration tách riêng; chỉ dùng isotonic như đối chứng nếu đủ dữ liệu và validation ủng hộ", "Chưa chạy"],
    ], columns=["candidate", "reason_from_eda", "proposed_controls", "status"])
    criteria = pd.DataFrame([
        ["Toàn vẹn và khả dụng", "0 ID trùng giữa các tập; 0 biến kết quả hoặc log chưa chứng minh trước t0; xử lý rõ 29 độ trễ âm", "Điều kiện bắt buộc trước fit"],
        ["Xác suất", "Log loss giảm ít nhất 2% tương đối so với baseline hằng tính từ train", "Đề xuất nghiên cứu; chưa có kết quả"],
        ["Phân biệt", "Average Precision cao hơn prevalence của tập đánh giá ít nhất 10% tương đối; báo thêm ROC-AUC", "Đánh giá trên phân phối tự nhiên"],
        ["Ưu tiên", "Lift@20% ít nhất 1,20 và cận dưới bootstrap user 95% >1", "20% là ngân sách nghiên cứu giả định, chưa phải ngân sách kinh doanh"],
        ["Calibration", "Sai lệch mean p so với booking rate ≤2 điểm phần trăm; ECE 10 bin đồng số mẫu ≤3 điểm, kèm reliability plot", "Báo cả Brier; hai số này chưa đủ đánh giá calibration riêng lẻ"],
        ["Độ bền thời gian", "Log loss tốt hơn baseline hằng trong từng tháng của tập đánh giá cuối; báo n/CI cho nhóm n≥100", "Không chọn mô hình chỉ từ một tháng thuận lợi"],
    ], columns=["criterion", "predeclared_acceptance", "interpretation"])
    research = combine("research_design", "7. Thuật toán và thiết kế đánh giá đề xuất", [
        section("algorithms", "Baseline, mô hình chính và xác suất", """
Thiết kế chính dự đoán nhãn y ở cấp người dùng. Hai nhóm y=1 và y=0 chiếm lần lượt 41,65% và 58,35%, nên thí nghiệm đầu tiên sẽ giữ phân phối lớp hiện có. Việc một số điểm đến có ít quan sát được xử lý riêng trong bối cảnh bài toán 12 lớp.

Các nhóm kết hợp có tỷ lệ đặt chỗ khác nhau trong EDA. Vì CatBoost có thể biểu diễn các quan hệ như vậy, báo cáo đề xuất so sánh mô hình này với xác suất hằng và Logistic Regression có điều chuẩn L2. Kết quả đánh giá sẽ quyết định mô hình nào phù hợp hơn.

Mỗi lượt chia dữ liệu có một tập huấn luyện riêng. Các quy tắc xử lý tuổi, giá trị thiếu, nhóm hiếm và thống kê dựa trên nhãn phải được học trong tập này rồi mới áp dụng cho tập kiểm định. Danh sách đầu vào của thiết kế chính loại ID, date_first_booking và sessions theo các bằng chứng ở phần 3 và phần 5.

Nguồn thuật toán: [xử lý category của CatBoost](https://catboost.ai/docs/en/concepts/algorithm-main-stages_cat-to-numberic). Hiệu chỉnh phải tách khỏi dữ liệu fit; [scikit-learn về calibration](https://scikit-learn.org/stable/modules/calibration.html) cũng lưu ý Brier/log loss đánh giá cả calibration lẫn khả năng phân biệt.
""", [("Ứng viên và lý do chọn — chưa thực hiện", models)]),
        section("evaluation", "Chia theo thời gian và kiểm soát đánh giá", """
Thiết kế đánh giá được đề xuất trước lần huấn luyện đầu tiên. Kiểm định theo các cửa sổ thời gian liên tiếp dùng để chọn cấu hình. Sau đó, mô hình được huấn luyện lại với dữ liệu đến hết tháng 3/2014, được hiệu chỉnh xác suất bằng dữ liệu tháng 4/2014 và được đánh giá cuối trên tháng 5–6/2014. Trong mỗi lượt chia, mỗi người dùng chỉ xuất hiện ở một giai đoạn. Tập huấn luyện mở rộng dần giữa các lượt chia. Test Kaggle tháng 7–9/2014 dùng để đối chiếu cấu trúc cột và phân phối vì tập này không có nhãn.

Bảng dưới kiểm kê số người dùng trong từng cửa sổ dự kiến. Để mô phỏng việc huấn luyện tại một thời điểm trong quá khứ, chỉ được dùng những nhãn đã có sẵn trước thời điểm đó. Với thời hạn 90 ngày, người mang nhãn âm trong tập huấn luyện phải hoàn tất đủ 90 ngày theo dõi trước mốc bắt đầu dự đoán của lượt chia. Điều kiện này cần được kiểm tra sau khi bổ sung thông tin theo dõi.

Tập kiểm định dùng để chọn tham số và thời điểm dừng huấn luyện. Dữ liệu phát triển dùng để chọn phương pháp hiệu chỉnh xác suất, sau đó bộ hiệu chỉnh được học trên tháng 4/2014. Tập đánh giá cuối chỉ được sử dụng sau khi đã chốt thiết kế. Khoảng tin cậy dự kiến được tính bằng cách lấy mẫu lặp lại theo người dùng (bootstrap), với seed=42.
""", [("Cửa sổ thời gian đề xuất và quy mô quan sát", proposed_protocol(train, account))]),
        section("acceptance", "Tiêu chí chấp nhận đặt trước", "Bảng dưới đề xuất các mức cải thiện xác suất, khả năng xếp hạng và độ ổn định theo thời gian. Các ngưỡng 2%, 10%, 1,20, sai lệch 2 hoặc 3 điểm phần trăm và tỷ lệ ưu tiên 20% là quy ước cho thí nghiệm nghiên cứu. Khi có thông tin chi phí và lợi ích thực tế, cần chốt lại các mức này và ghi phiên bản thiết kế trước khi huấn luyện. Trạng thái hiện tại của các tiêu chí là chưa đánh giá.", [("Điều kiện để chấp nhận kết quả mô hình", criteria)]),
    ])

    suitability = pd.DataFrame([
        ["Đủ tín hiệu", f"10 category được sàng lọc V; gender V={v_by_name.loc['gender','effect_all']:.3f}, trong 2014={v_by_name.loc['gender','effect_2014']:.3f}; có bảng tương tác/cohort", "Đạt ở mức EDA", "Chưa chứng minh dự báo ngoài mẫu; không dùng p-value thay AUC"],
        ["Đủ cỡ mẫu", f"{len(train):,} users; {int(frame.observed_booking.sum()):,} booking; cohort 2014 {recent_users:,}", "Đạt tổng thể", "Một số category/ô tương tác ít user; dùng n và CI"],
        ["Nhãn tin cậy", f"Việc có ngày đặt chỗ khớp nhãn y ở 100% trường hợp. Có {int(lag.lt(0).sum())} độ trễ âm và độ trễ tối đa 365 ngày.", "Cần xác minh", "Cần ngày kết thúc theo dõi của người có y=0 và giải thích ngoại lệ trước ngày tạo tài khoản."],
        ["Không rò rỉ", "date_first_booking và presence tiết lộ nhãn; sessions chứa tên giao dịch, thiếu timestamp", "Chưa đạt với toàn bộ raw", "Thiết kế chính loại các nguồn này; cần audit lại trước fit"],
        ["Biến khả dụng tại t0", "t0 đã chọn: sau tạo account; raw không cung cấp lịch sử cập nhật hồ sơ", "Cần xác minh", "Xác nhận snapshot từng biến; ngày account không có giờ"],
        ["Ổn định theo thời gian", "Booking rate/cohort, độ phủ sessions và TV category thay đổi; đã có đối chiếu cùng năm 2014", "Chưa đạt giả định ổn định", "Dùng kiểm định theo thời gian, không coi train/test là IID"],
        ["Khái quát hóa", "User từ Mỹ, giai đoạn lịch sử; test Kaggle không có nhãn; chưa có dữ liệu vận hành khác", "Chưa được chứng minh", "Chưa suy sang Việt Nam, thị trường hiện tại hoặc chiến dịch marketing"],
    ], columns=["criterion", "evidence_in_report", "status", "remaining_condition"])
    conclusion = section("conclusion_main", "8. Bằng chứng về mức độ phù hợp", """
**Kết luận lựa chọn:** trong ba bộ dữ liệu, Airbnb phù hợp nhất để nghiên cứu xác suất có lượt đặt chỗ đầu tiên ở cấp người dùng. Cỡ mẫu và các liên hệ quan sát được là cơ sở để tiến hành thí nghiệm mô hình sau khi xử lý các điều kiện dữ liệu trong bảng dưới.

Ba việc cần hoàn tất là xác minh thông tin hồ sơ tại t0, làm rõ các ngoại lệ ngày đặt chỗ và xác nhận thời gian theo dõi của từng người dùng. Chúng quyết định khả năng sử dụng dữ liệu cho phương án dự đoán trong 90 ngày. Bảng dưới phân biệt tiêu chí đã có bằng chứng với điều kiện còn cần giải quyết.
""", [("Bảng kiểm mức độ phù hợp", suitability)])

    # Remove body/appendix duplicates, retain only additional evidence.
    appendix = [b for b in appendix if b["key"] not in {"all_target_tables", "calendar_tables"}]
    for block in appendix:
        if block["key"] == "session_details":
            block["tables"] = [(name, t) for name, t in block["tables"] if not name.startswith("Độ phủ")]
        if block["key"] == "dictionary":
            table = block["tables"][0][1].copy()
            table.loc[table.column.eq("date_first_booking"), "role"] = "kết quả; loại khỏi đầu vào tại signup"
            table.loc[~table.column.isin(["id", "date_first_booking", "country_destination"]), "role"] = "ứng viên hồ sơ tại signup; cần xác minh snapshot"
            block["tables"][0] = (block["tables"][0][0], table)
    appendix.extend([
        section("extra_rates", "Tỷ lệ nhãn cho nhóm bổ sung", "Các bảng ở đây không lặp các nhóm đã công bố trong phần chính.", extra_tables),
        section("strata_details", "Phân tầng và các nhóm kết hợp: Wilson 95% cho từng ô", "Các bảng cung cấp cỡ mẫu, tỷ lệ đặt chỗ và khoảng tin cậy cho từng ô trên bản đồ nhiệt.", [(f"{c} × năm", t) for c, t in strata.items()] + interaction_tables),
        section("session_action_details", "Rà soát sessions bổ sung", "Mẫu số là user 2014 có log; action_type giữ toàn bộ, action_detail lọc bằng regex đã công bố. Các bảng không chứng minh thời điểm sự kiện.", [("Toàn bộ action_type và action_detail được rà soát", actions[~actions.field.eq("action")].drop(columns=["transaction_name_match"]))]),
        section("monthly_cohorts", "Cohort theo tháng và khoảng tin cậy", "Số liệu đứng sau hình account_cohorts; không lặp lại bảng khoảng thời gian hoặc drift.", [("Toàn bộ cohort tháng; Wilson 95%", monthly)]),
    ])
    recent_lags = []
    for month in sorted(account[is2014].dt.to_period("M").unique()):
        chosen = account.dt.to_period("M").eq(month)
        observed_lag = lag[chosen & valid]
        recent_lags.append({
            "account_month": str(month), "users": int(chosen.sum()),
            "ndf_users": int((chosen & frame.observed_booking.eq(0)).sum()),
            "valid_observed_bookings": len(observed_lag),
            "within30_pct_of_observed": observed_lag.le(30).mean()*100,
            "within60_pct_of_observed": observed_lag.le(60).mean()*100,
            "within90_pct_of_observed": observed_lag.le(90).mean()*100,
            "max_observed_lag_days": observed_lag.max(),
        })
    appendix.append(section("recent_lag_cohorts", "Độ trễ trong các cohort tháng gần cuối train",
        "Bảng so sánh các nhóm đăng ký từ tháng 1 đến tháng 6/2014. Các tỷ lệ trong ba cột within30/60/90 có mẫu số valid_observed_bookings, tức số lượt đặt chỗ có độ trễ hợp lệ của nhóm. Thời gian theo dõi của người có y=0 cần được xác định riêng.",
        [("Cohort 2014: NDF và mức bao phủ booking quan sát",pd.DataFrame(recent_lags))]))
    source = base["overview"]["blocks"][0]
    source["tables"][0][1].loc[source["tables"][0][1]["item"].eq("Ngày tải raw"), "description"] = "Không được lưu; người cung cấp xác nhận 2026-11-02. Mã phiên bản Kaggle chưa có bằng chứng; dùng snapshot SHA-256."
    scope = base["overview"]["blocks"][1]
    overview = combine("overview", "2. Tổng quan bộ dữ liệu", [source, scope])
    base["quality_main"]["title"] = "3. Chất lượng dữ liệu"
    base["univariate"]["title"] = "4. Phân tích đơn biến"
    base["risks"]["title"] = "6. Hạn chế, rủi ro và quyền riêng tư"
    risk_table = base["risks"]["tables"][0][1]
    risk_table.loc[risk_table.issue.eq("Quần thể"), "evidence_or_limit"] = "Users từ Mỹ trong giai đoạn lịch sử; thời gian theo dõi từng user chưa xác minh, sessions chỉ phủ cohort 2014."
    cov_absent = s2014.set_index("has_sessions")
    age_signal = v_by_name.loc["age: cờ thiếu (EDA)"]
    age_rank = v_by_name.loc["age: chỉ cửa sổ 16–100 (EDA)"]
    glossary = section("glossary", "Thuật ngữ và cách đọc báo cáo", """
Mọi số liệu trong báo cáo là thống kê mô tả từ dữ liệu gốc. Chúng cho biết các liên hệ trong mẫu, chưa phải kết quả dự báo hoặc bằng chứng về tác động nhân quả. Báo cáo dừng ở EDA và thiết kế thí nghiệm, chưa xử lý dữ liệu cho mô hình hoặc huấn luyện mô hình.

Báo cáo dùng thống nhất “nhãn y” cho mục tiêu nhị phân và “lượt đặt chỗ đầu tiên” cho hành vi cần dự đoán. Tên cột và mã giá trị được giữ nguyên để đối chiếu với dữ liệu.
""", [("Các thuật ngữ dùng trong báo cáo", pd.DataFrame([
        ["EDA", "Phân tích khám phá dữ liệu bằng bảng, biểu đồ và thống kê mô tả."],
        ["NDF", "Mã No Destination Found trong country_destination, nghĩa là bộ dữ liệu không ghi nhận lượt đặt chỗ. Mã này không có nghĩa người dùng sẽ không bao giờ đặt chỗ."],
        ["Nhãn y", "Mục tiêu nhị phân: y=1 nếu country_destination khác NDF, y=0 nếu bằng NDF. Cột country_destination giữ nguyên 12 giá trị điểm đến gốc."],
        ["Lượt đặt chỗ đầu tiên", "Lượt đặt chỗ đầu tiên được ghi nhận trong bộ dữ liệu (first booking)."],
        ["t0", "Thời điểm dự đoán, được chọn là ngay sau khi người dùng hoàn tất tạo tài khoản."],
        ["Thời hạn dự đoán (horizon)", "Khoảng thời gian tính từ t0 để xét hành vi, chẳng hạn 90 ngày. Thời gian theo dõi thực tế của nhãn y hiện có còn cần xác minh."],
        ["Nhóm đăng ký (cohort)", "Những người tạo tài khoản trong cùng một khoảng thời gian, thường là một tháng hoặc một năm."],
        ["Rò rỉ thông tin (leakage)", "Việc dùng thông tin tiết lộ kết quả hoặc chưa có sẵn tại t0 làm đầu vào dự đoán."],
        ["Cramér V", "Thước đo độ mạnh liên hệ giữa hai biến phân loại, từ 0 (không liên hệ) đến 1 (liên hệ hoàn toàn)."],
        ["Rank-biserial", "Thước đo chênh lệch thứ hạng giữa hai nhóm, từ −1 đến 1. Với tuổi, dấu dương nghĩa nhóm y=1 có xu hướng lớn tuổi hơn. Giá trị gần 0 nghĩa khác biệt rất nhỏ."],
        ["Khoảng Wilson 95%", "Khoảng tin cậy cho tỷ lệ trong một nhóm. Khoảng rộng cho biết ước lượng còn kém chính xác, thường do nhóm ít người."],
        ["Sessions", "Nhật ký hoạt động trên web hoặc ứng dụng. Mỗi người dùng có thể có nhiều sự kiện."],
        ["Train / test", "Tập có nhãn dùng cho nghiên cứu / tập Kaggle không có nhãn, dùng đối chiếu cấu trúc và phân phối."],
        ["NA / unknown / untracked", "Giá trị bị thiếu / mã không rõ thông tin / mã không theo dõi được. Báo cáo giữ riêng ba trường hợp."],
        ["Mốc bắt đầu dự đoán (origin)", "Thời điểm lịch bắt đầu một lượt đánh giá. Dữ liệu dùng huấn luyện phải có sẵn trước mốc này."],
    ], columns=["Thuật ngữ", "Giải nghĩa"]))])
    findings = [
        f"**Quy mô và nhãn y:** tập train có {len(train):,} người dùng, trong đó {int(frame.observed_booking.sum()):,} người có lượt đặt chỗ đầu tiên ({frame.observed_booking.mean()*100:.2f}%). Tập test có {len(test):,} người dùng. Hai nhóm nhãn y có quy mô đủ lớn để bắt đầu thí nghiệm với phân phối lớp hiện có.",
        f"**Thời gian phát sinh đặt chỗ:** trong {len(values):,} lượt đặt chỗ có độ trễ không âm, {coverage_at(30):.2f}% xảy ra trong 30 ngày, {coverage_at(60):.2f}% trong 60 ngày và {coverage_at(90):.2f}% trong 90 ngày. Vì phần lớn lượt đặt chỗ tập trung trong ba tháng đầu, 90 ngày là thời hạn đáng xem xét cho phương án triển khai.",
        f"**Liên hệ của hồ sơ đăng ký:** gender có V={v_by_name.loc['gender','effect_all']:.3f} trên toàn kỳ và {v_by_name.loc['gender','effect_2014']:.3f} trong năm 2014, được diễn giải ở mức yếu đến vừa trong báo cáo. signup_app có liên hệ yếu hơn, với V lần lượt là {v_by_name.loc['signup_app','effect_all']:.3f} và {v_by_name.loc['signup_app','effect_2014']:.3f}. Hai biến này là ứng viên để kiểm tra giá trị bổ sung trong mô hình.",
        f"**Độ đầy đủ của hồ sơ tuổi:** age thiếu ở {train.age.isna().mean()*100:.2f}% người dùng. Trong năm 2014, cờ thiếu tuổi có V={age_signal.effect_2014:.3f}, còn tuổi trong dải 16–100 có rank-biserial={age_rank.effect_2014:.3f}, gần 0. Mức độ đầy đủ của hồ sơ có liên hệ đáng chú ý với nhãn y, trong khi khác biệt thứ hạng tuổi giữa hai nhóm rất nhỏ.",
        f"**Phạm vi nhật ký hoạt động:** trong năm 2014, {coverage_recent:.2f}% người dùng train và {coverage_test:.2f}% người dùng test có sessions, chênh {coverage_test-coverage_recent:.2f} điểm phần trăm. Tỷ lệ có đặt chỗ trong nhóm có nhật ký là {cov_absent.loc[True,'rate_pct']:.2f}%, so với {cov_absent.loc[False,'rate_pct']:.2f}% ở nhóm thiếu nhật ký. Vì dữ liệu trước năm 2014 không có sessions, nghiên cứu riêng nguồn này cần tập trung vào {recent_users:,} người dùng train đăng ký năm 2014.",
    ]
    next_steps = [
        f"**Xác minh nhãn và thời gian theo dõi.** Làm rõ {int(lag.lt(0).sum())} trường hợp có ngày đặt chỗ trước ngày tạo tài khoản và lý do độ trễ lớn nhất quan sát được là 365 ngày. Bổ sung ngày kết thúc theo dõi của từng người dùng để có thể xây dựng nhãn âm cho thời hạn 90 ngày.",
        "**Chốt thông tin có sẵn tại t0.** Xác nhận hồ sơ phản ánh thời điểm đăng ký. Loại date_first_booking và cờ thiếu của cột này khỏi đầu vào vì chúng khớp nhãn y ở 100% trường hợp. Thiết kế chính cũng loại sessions vì nhật ký thiếu thời điểm sự kiện để xác định phần có trước t0.",
        "**Chốt thí nghiệm và tiêu chí đánh giá.** So sánh xác suất hằng, Logistic Regression có điều chuẩn L2 và CatBoost bằng các lượt chia theo thời gian. Dành tháng 4/2014 để hiệu chỉnh xác suất và tháng 5–6/2014 để đánh giá cuối. Trước khi huấn luyện, xác nhận nhãn dùng học đã có sẵn tại mốc bắt đầu dự đoán của mỗi lượt chia.",
    ]
    executive_text = (
        "**Kết luận:** Airbnb phù hợp nhất trong ba bộ dữ liệu để nghiên cứu xác suất người dùng mới có lượt đặt chỗ đầu tiên. Báo cáo chọn thời điểm dự đoán ngay sau khi tạo tài khoản và đề xuất bắt đầu thí nghiệm mô hình sau khi hoàn tất ba việc dưới đây."
        + "\n\n**Năm phát hiện chính**\n\n"
        + "\n\n".join(f"{i}. {text}" for i, text in enumerate(findings, 1))
        + "\n\n**Ba việc cần giải quyết trước khi huấn luyện**\n\n"
        + "\n\n".join(f"{i}. {text}" for i, text in enumerate(next_steps, 1))
    )
    report.sections = [
        glossary, section("executive", "Tóm tắt điều hành", executive_text),
        problem, overview, base["quality_main"], base["univariate"],
        combine("multivariate_main", "5. Nhãn, liên hệ đa biến, cohort và sessions",
                [delay_section, signal_section, target_section, strata_section, interaction_section, session_section, time_section]),
        base["risks"], research, conclusion,
        combine("appendix", "Phụ lục — từ điển và bảng bổ sung", appendix),
    ]
    inventory = next(b for b in appendix if b["key"] == "inventory")["tables"][0][1]
    snapshot_text = "\n".join(f"{row.file}:{row.bytes}:{row.sha256}" for row in inventory.sort_values("file").itertuples())
    report.facts.pop("download_date", None)
    report.facts.update({
        "download_date_status": "not_recorded_confirmed_by_provider_2026-11-02",
        "dataset_version_status": "unknown_kaggle_version_local_snapshot_identified",
        "local_snapshot_sha256": hashlib.sha256(snapshot_text.encode()).hexdigest(),
        "valid_booking_lags": int(valid.sum()), "negative_booking_lags": int(lag.lt(0).sum()),
        "booking_coverage_30_pct": coverage_at(30), "booking_coverage_60_pct": coverage_at(60),
        "booking_coverage_90_pct": coverage_at(90), "max_observed_booking_lag_days": int(values.max()),
        "train_2014_users": recent_users, "train_2014_session_users": recent_logs,
        "train_2014_session_coverage_pct": coverage_recent,
        "session_action_audit_names": len(actions), "association_screen_count": len(association),
        "prediction_time_design": "immediately_after_account_creation",
        "primary_target": "observed_first_booking_in_source_labels_not_fixed_horizon",
        "proposed_deployment_horizon_days": 90,
        "fixed_horizon_negative_followup_verified": False,
        "analysis_revision": "airbnb_readability_and_terminology_v3",
    })
