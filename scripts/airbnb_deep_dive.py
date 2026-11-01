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
Notebook cần package scripts/ và năm CSV train_users_2.csv, test_users.csv, sessions.csv, countries.csv, age_gender_bkts.csv tại data/raw/AIRBNB/. Chỉ nộp một file notebook thì xem được output lưu sẵn, chưa thể chạy lại độc lập. Ô mở đầu notebook ghi cấu trúc thư mục và cách cài đúng các thư viện EDA; raw không được đính kèm repo.

Từ thư mục gốc chạy: python scripts/build_descriptive_reports.py --dataset AIRBNB. Hoặc mở notebook bằng Jupyter, Restart Kernel và Run All. Script chỉ đọc CSV raw, xuất Markdown, JSON, hình và notebook có output thật; không tạo data/processed, tập feature, tập chia train/test hay mô hình.

Ngày tải **không được lưu**, đã được người cung cấp xác nhận ngày 2026-11-02. Mã phiên bản Kaggle cũng chưa có bằng chứng. Không điền một ngày giả định: snapshot local được định danh bằng SHA-256 từng file và hash danh mục có thứ tự ở metadata. Ngày phân tích theo Asia/Ho_Chi_Minh khác với ngày tải.

Mọi bảng dùng toàn bộ user hoặc toàn bộ sessions có khóa hợp lệ trong phạm vi ghi cạnh bảng. Chỉ mẫu hình thiếu hiển thị tối đa 300 dòng, seed=42. Cramér V dùng chi-square không hiệu chỉnh Yates; p chi-square là xấp xỉ, kèm tỷ lệ ô kỳ vọng dưới 5. Mann–Whitney hai phía dùng xấp xỉ có hiệu chỉnh ties; rank-biserial = 2U/(n_booked × n_NDF) − 1. BH điều chỉnh 14 phép sàng lọc toàn kỳ; không áp dụng ngưỡng p để tự động chọn feature. Wilson 95% giả định user độc lập và không bao gồm sai lệch chọn mẫu/cohort. Không bootstrap, fit, tối ưu tham số hay tính chất lượng mô hình trong lần chạy EDA.

Output được tính lại trong lần phân tích hiện tại; môi trường dưới đây và SHA-256 ba module dựng báo cáo trong metadata nhận diện code đã chạy. Các đề xuất thuật toán, cửa sổ chia tập và ngưỡng chấp nhận chưa được thực thi.
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
    axes[0].set(title="Độ trễ đến booking đầu được ghi nhận", xlabel="Ngày từ tạo tài khoản đến booking", ylabel="Số người có booking và độ trễ ≥ 0")
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
    fig_note(report, delay_figure, f"Nhận xét: trong {len(values):,} booking có độ trễ không âm, {coverage_at(30):.2f}% xảy ra trong 30 ngày, {coverage_at(60):.2f}% trong 60 ngày và {coverage_at(90):.2f}% trong 90 ngày. Đây là phân phối có điều kiện trên người đã book; chưa xác định thời gian theo dõi của NDF. {int(lag.lt(0).sum())} độ trễ âm được báo riêng, không xóa khỏi raw.")
    delay_section = section("booking_delay", "Độ trễ booking và giới hạn định nghĩa nhãn", f"""
Độ trễ = date_first_booking − date_account_created, tính bằng ngày lịch; ngày booking chỉ dùng để kiểm tra nhãn. Có {len(values):,} độ trễ không âm và {int(lag.lt(0).sum())} độ trễ âm. Không diễn giải độ trễ âm là booking tương lai và không sửa chúng trong EDA.

**Cửa sổ 90 ngày bao phủ {coverage_at(90):.2f}% booking quan sát có độ trễ hợp lệ**, còn khoảng {100-coverage_at(90):.2f}% nằm sau 90 ngày. Các tỷ lệ dưới đây không phải xác suất booking 30/60/90 ngày của toàn bộ user.

Ngày booking lớn nhất là {pd.to_datetime(train.date_first_booking).max().date()}. Độ trễ lớn nhất ở cả năm cohort là 365 ngày. Điều này phù hợp với giả thuyết nhãn có giới hạn khoảng một năm theo từng user, nhưng chưa chứng minh cơ chế đóng nhãn hoặc thời gian theo dõi của NDF. **Không thể kết luận NDF ở cohort mới chỉ là chưa kịp booking, cũng chưa thể bác bỏ khả năng đó.**

Nếu giả định mọi user đều được theo dõi tới ngày booking lớn nhất, toàn bộ train có khoảng cách lịch đủ 30/60/90 ngày. Đây là phân tích độ nhạy theo một giả định chưa kiểm chứng, không phải bằng chứng xác nhận NDF đã trưởng thành. Bài toán chính dùng nhãn nguồn; 90 ngày là horizon triển khai cần dữ liệu bổ sung để xác nhận nhãn âm.
""", [("Phân phối độ trễ: mẫu số và ngoại lệ", lag_summary),
      ("Mức bao phủ các horizon trên booking đã quan sát", horizons),
      ("Độ trễ theo năm tạo tài khoản", lag_cohorts),
      ("Giả định chung ngày đóng nhãn: chỉ là độ nhạy", followup)], [delay_figure])

    # Full candidate audit: 10 categorical fields, age and two original dates.
    signal_section = section("signal", "Độ mạnh liên hệ với nhãn trên toàn bộ biến ứng viên", """
Phạm vi sàng lọc gồm 13 cột ứng viên gốc: 10 biến phân loại, age và hai mốc thời gian. Cờ thiếu tuổi là một góc nhìn EDA bổ sung, không được xuất thành feature. Ngày tạo account/hoạt động đầu được nhóm theo tháng chỉ để mô tả cohort. ID, nhãn và date_first_booking không được dùng để chứng minh tín hiệu đầu vào.

Cramér V = sqrt(chi-square / [n × min(r−1,c−1)]), trong [0,1]; càng lớn là liên hệ biên càng mạnh. Cột effect_2014 tính lại trên cohort 2014 để kiểm tra ảnh hưởng thành phần năm. Không áp một ngưỡng V chung để tuyên bố biến hữu ích cho mô hình. P-value nhỏ khi n lớn chưa đảm bảo hiệu ứng có giá trị; các category hiếm làm kiểm định chi-square xấp xỉ kém hơn.

Tuổi được kiểm định Mann–Whitney hai phía trong cửa sổ tham chiếu 16–100, kèm rank-biserial trong [−1,1]. Dấu dương nghĩa tuổi ở nhóm booked có xu hướng cao hơn NDF; trị tuyệt đối gần 0 là khác biệt nhỏ. Không so trực tiếp trị số rank-biserial với V như cùng một thang đo. Tuổi ngoài dải và NA vẫn được báo riêng.

Đây là bằng chứng **liên hệ thống kê trong mẫu**, thay cho việc bịa ra AUC ở giai đoạn chưa train; chưa chứng minh khả năng dự báo ngoài thời gian hoặc tác động nhân quả. Nguồn phương pháp: [Cramér V của SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.contingency.association.html), [Mann–Whitney của SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html).
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
    target_section = section("target_rates", "Tỷ lệ booking theo hồ sơ, kênh, thiết bị và missing tuổi", "Mỗi mẫu số là user trong nhóm. Bảng có n, số booking, tỷ lệ và Wilson 95%; n<100 là cờ thận trọng. Giữ riêng NA, giá trị unknown và tuổi ngoài dải. Các chênh lệch ở đây là liên hệ biên, được đối chiếu với phân tầng năm ở phần tiếp theo.", target_tables)

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
    fig_note(report, strata_figure, f"Nhận xét: riêng năm 2014, Web có booking rate {app2014.loc['Web','rate_pct']:.2f}% so với iOS {app2014.loc['iOS','rate_pct']:.2f}% và Android {app2014.loc['Android','rate_pct']:.2f}%; chênh lệch app vẫn hiện diện trong cùng năm. FEMALE đạt {gender2014.loc['FEMALE','rate_pct']:.2f}% so với gender unknown {gender2014.loc['-unknown-','rate_pct']:.2f}%. Nhóm OTHER chỉ có {int(gender2014.loc['OTHER','n'])} user 2014 nên cần đọc Wilson ở phụ lục. Dấu * là n<100. Phân tầng năm chưa kiểm soát nhiễu theo tháng hoặc biến khác.")
    strata_section = section("cohort_strata", "Tách thành phần cohort khỏi chênh lệch app, gender và kênh", """
Đọc theo từng cột năm để so sánh các nhóm trong cùng cohort. Một số ứng dụng không xuất hiện ở năm đầu nên không thể chuẩn hóa ngây thơ mọi nhóm theo cùng cơ cấu 2010–2014. Bảng tỷ lệ toàn kỳ không được dùng để kết luận app/kênh/giới tính gây tăng booking.

Ngay cả khi chênh lệch còn trong một năm, đó vẫn là liên hệ sau phân tầng năm, chưa phải ước lượng nhân quả hoặc đã kiểm soát mọi nhiễu. Bảng dài với Wilson 95% nằm ở phụ lục để kiểm tra các ô n nhỏ.
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
    fig_note(report, interaction_figure, f"Nhận xét: trong user Web năm 2014, nhóm direct có booking rate {app_channel.loc[('Web','direct'),'rate_pct']:.2f}% (n={int(app_channel.loc[('Web','direct'),'n']):,}), nhóm content {app_channel.loc[('Web','content'),'rate_pct']:.2f}% (n={int(app_channel.loc[('Web','content'),'n']):,}). Trong nhóm FEMALE cùng năm, có tuổi đạt {missing_gender.loc[('Có tuổi','FEMALE'),'rate_pct']:.2f}% so với thiếu tuổi {missing_gender.loc[('Thiếu tuổi','FEMALE'),'rate_pct']:.2f}%. Dấu * là n<100. Liên hệ không chỉ do trộn các năm, nhưng vẫn chưa chứng minh quan hệ nhân quả hoặc mô hình phi tuyến sẽ thắng baseline.")
    interaction_section = section("interactions", "Tương tác liên quan đến nhãn trong cohort 2014", "Thay biểu đồ hai trục ngày gần trùng nhau bằng signup_app × affiliate_channel và missing tuổi × gender. Nhóm tuổi/cờ thiếu chỉ tồn tại để tính bảng và hình EDA; chưa xuất dữ liệu đầu vào. Không kiểm định tương tác hàng loạt hoặc tự chọn feature từ hình.", figures=[interaction_figure])

    recent_users = int(is2014.sum())
    recent_logs = int(train.loc[is2014, "id"].isin(per_user.index).sum())
    coverage_recent = recent_logs/recent_users*100
    coverage_test = test.id.isin(per_user.index).mean()*100
    trans = actions[actions.transaction_name_match & actions.field.isin(["action", "action_type"])].copy()
    trans_display = trans.drop(columns=["events", "transaction_name_match"])
    receipt = trans[(trans.field=="action") & trans.value.eq("receipt")].iloc[0]
    requested = trans[(trans.field=="action") & trans.value.eq("requested")].iloc[0]
    session_section = section("sessions_evidence", "Sessions: so sánh cùng cohort và rà soát thông tin giao dịch", f"""
Đã quét toàn bộ {report.facts['sessions']:,} sự kiện. So sánh phù hợp hơn là **train cohort 2014: {recent_logs:,}/{recent_users:,} ({coverage_recent:.2f}%)** với **test cohort 2014: {coverage_test:.2f}%**; chênh {coverage_test-coverage_recent:.2f} điểm phần trăm. Tỷ lệ train toàn kỳ 34,58% chủ yếu phản ánh việc cohort 2010–2013 không có log, không phải bằng chứng user ít hoạt động.

**Về độ phủ, nghiên cứu sessions phải giới hạn cohort 2014 ({recent_users:,} user train), trong đó {recent_logs:,} có log.** Về thời điểm dự đoán, sessions vẫn chưa đủ điều kiện: không có timestamp nên không cắt được trước t0. Giới hạn cohort không tự loại được rò rỉ thời gian.

Bảng có/không có log dưới đây chỉ xét 2014. Bảng số sự kiện giữ cả user không có log với event_n=0 để không nhầm mẫu số. Thời lượng secs_elapsed không phải timestamp và tổng thời lượng không chứng minh thứ tự hành động.

Rà soát tên ứng viên giao dịch/xác minh theo regex **{TRANSACTION_PATTERN}**, trước khi xem liên hệ với nhãn; khớp token phân cách bởi dấu gạch dưới và giữ đầy đủ action_type để đối chiếu. Nhóm confirm/request có thể liên quan xác minh tài khoản hoặc yêu cầu, chưa mặc định là booking hoàn tất. Đếm presence theo user sau khi gộp toàn bộ chunk, tránh một người bị đếm lặp vì nhiều sự kiện. Mẫu số của hai cột pct_booked/pct_ndf là người có sessions trong từng lớp, không phải toàn bộ train.

**Dấu hiệu đáng điều tra:** receipt có {int(receipt.booked_users):,}/{int(receipt.users_with_action):,} user mang nhãn booked ({receipt.booking_rate_pct:.2f}%); requested có {int(requested.booked_users):,}/{int(requested.users_with_action):,} ({requested.booking_rate_pct:.2f}%). Tỷ lệ cao phù hợp với rủi ro log chứa bước sát hoặc sau kết quả, chưa chứng minh receipt luôn là hậu booking hoặc requested gây ra booking.

Tên như booking/payment/request là dấu hiệu cần điều tra. Hành động cũng có thể là yêu cầu thất bại, chuẩn bị thanh toán hoặc hoạt động sau booking; xuất hiện ở booked hay NDF chưa chứng minh thứ tự trước/sau kết quả. **Toàn bộ sessions bị loại khỏi phạm vi đầu vào của thiết kế chính tại signup**, cho tới khi có timestamp hoặc chứng cứ về cửa sổ log. Đây là quyết định phạm vi đề xuất, chưa tạo tập feature.
""", [("Độ phủ năm account train", next(t for name, t in next(b for b in base["multivariate_main"]["blocks"] if b["key"] == "sessions")["tables"] if "năm account" in name)),
      ("Booking trong nhóm có/không sessions — chỉ cohort 2014", s2014),
      ("Số sự kiện/user theo có log và nhãn — chỉ cohort 2014", event_summary),
      ("Presence tên ứng viên giao dịch/xác minh × nhãn, trong user 2014 có log", trans_display)],
      [report.directory/"figures/session_coverage.png"])
    fig_note(report, report.directory/"figures/session_coverage.png", f"Nhận xét: độ phủ train toàn kỳ 34,58% là hỗn hợp cohort; train 2014 đạt {coverage_recent:.2f}% so với test 2014 {coverage_test:.2f}%, chênh {coverage_test-coverage_recent:.2f} điểm phần trăm. Không có log ở cohort 2010–2013. Độ phủ cao không chứng minh log được ghi trước thời điểm dự đoán.")

    # Calendar table appears once in the body; monthly detail only in appendix.
    old_time = next(b for b in base["multivariate_main"]["blocks"] if b["key"] == "time")
    all_drift = drift_table(train, test, CATEGORICAL)
    recent_drift = drift_table(train[is2014], test, CATEGORICAL)
    drift = all_drift.rename(columns={"total_variation_0_1": "tv_all_train_vs_test"}).merge(
        recent_drift[["column", "total_variation_0_1"]].rename(columns={"total_variation_0_1": "tv_train2014_vs_test"}),
        on="column", validate="one_to_one")
    monthly = next(t for name, t in next(b for b in appendix if b["key"] == "calendar_tables")["tables"] if "Cohort theo tháng" in name)
    time_section = section("time", "Cohort tháng có bất định và drift train–test", """
Train có account 2010-01–2014-06; test 2014-07–2014-09 và không có nhãn. Hình giữ từng tháng, thêm Wilson 95% và ranh giới 2014-01 khi bắt đầu có sessions. Tháng ít user có khoảng rộng hơn; đường lên/xuống chưa chứng minh chất lượng khách hoặc mùa vụ.

Total variation trong [0,1] chỉ so sánh phân phối từng biến. Hai cột toàn kỳ và chỉ train 2014 giúp thấy phần thay đổi do thành phần cohort; chưa loại được drift trong năm hoặc drift quan hệ với nhãn. Các bảng khoảng thời gian và drift xuất hiện duy nhất tại đây; phụ lục chỉ giữ số liệu cohort tháng.
""", [("Khoảng thời gian account", old_time["tables"][0][1]), ("Khác biệt category train–test: toàn kỳ và cùng năm 2014", drift)],
      [report.directory/"figures/account_cohorts.png"])
    smallest = monthly.loc[monthly.users.idxmin()]
    fig_note(report, report.directory/"figures/account_cohorts.png", f"Nhận xét: tháng {smallest.account_month} chỉ có {int(smallest.users)} user, booking rate {smallest.booked_pct:.2f}% với Wilson 95% [{smallest.ci95_low_pct:.2f}%; {smallest.ci95_high_pct:.2f}%]; vì vậy dao động ở cohort nhỏ cần đọc cùng bất định. Vạch đứt 2014-01 đánh dấu thay đổi độ phủ sessions, không phải bằng chứng về tác động riêng của thời gian đăng ký.")

    # A concrete research target, with a separately blocked deployment horizon.
    problem = section("problem", "1. Bài toán và lý do chọn dữ liệu", f"""
**Bối cảnh nghiệp vụ:** ưu tiên hỗ trợ onboarding/cá nhân hóa cho người dùng mới dựa trên khả năng phát sinh booking đầu. Điểm propensity mô tả xu hướng hành vi; chưa phải tác động tăng thêm do một chiến dịch.

**Phát biểu bài toán nghiên cứu đã chọn:** với một user mới, sử dụng thông tin đăng ký sẵn có tại t0 để ước lượng xác suất có booking đầu được ghi nhận trong nhãn nguồn. Đầu ra là một xác suất [0,1] cho mỗi user, phục vụ sắp ưu tiên; bài toán điểm đến 12 lớp được giữ làm bối cảnh EDA.

**t0 thiết kế:** ngay sau khi hoàn tất tạo tài khoản. date_account_created chỉ chính xác tới ngày nên không xác minh được thứ tự trong ngày. Nhãn nghiên cứu y=1 khi country_destination khác NDF; y=0 khi NDF, không diễn giải thành “không bao giờ book”. Các giá trị hồ sơ phải được xác minh là snapshot tại signup. {int(lag.lt(0).sum())} booking có ngày trước account chưa thỏa logic first-booking tương lai tại t0; đề xuất cách ly để xác minh ở giai đoạn sau, chưa xóa.

**Horizon:** phạm vi hiện tại là kết quả được ghi nhận theo cơ chế nhãn nguồn, không tự đổi thành nhãn 90 ngày. Horizon nghiệp vụ đề xuất là 90 ngày vì bao phủ {coverage_at(90):.2f}% booking quan sát hợp lệ; muốn triển khai cần xác nhận ngày kết thúc theo dõi và nhãn âm. Nếu không xác minh được, chỉ được kết luận về bài toán nghiên cứu theo nhãn nguồn.
""", [("Lý do chọn Airbnb so với hai bộ còn lại", pd.DataFrame([
        ["AIRBNB", "User mới", f"{len(train):,} user; {frame.observed_booking.mean()*100:.2f}% có booking", "Đúng đối tượng chấm propensity khách hàng; có ID", "Chọn cho nghiên cứu, còn điều kiện nhãn/t0"],
        ["HOTEL", "Booking đã được tạo", "Nhãn hủy/no-show; không quan sát đầy đủ người chưa đặt", "Hợp cancellation propensity", "Không trả lời trực tiếp ai sẽ tạo booking đầu"],
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
Chọn nhị phân first-booking theo nhãn nguồn làm bài toán chính. Binary 41,65%/58,35% không cần mặc định resampling hoặc class weight; lớp điểm đến hiếm không phải lý do cân bằng lại nhãn nhị phân.

CatBoost là ứng viên chính để kiểm tra, không phải kết luận đã thắng baseline. Tín hiệu EDA và tương tác chỉ là cơ sở đặt giả thuyết. Mọi quy tắc xử lý tuổi, NA/category hiếm và mọi thống kê dựa nhãn phải học riêng trong train của mỗi fold. ID và date_first_booking không làm đầu vào; sessions chưa thuộc thiết kế chính.

Nguồn thuật toán: [xử lý category của CatBoost](https://catboost.ai/docs/en/concepts/algorithm-main-stages_cat-to-numberic). Hiệu chỉnh phải tách khỏi dữ liệu fit; [scikit-learn về calibration](https://scikit-learn.org/stable/modules/calibration.html) cũng lưu ý Brier/log loss đánh giá cả calibration lẫn khả năng phân biệt.
""", [("Ứng viên và lý do chọn — chưa thực hiện", models)]),
        section("evaluation", "Chia theo thời gian và kiểm soát đánh giá", """
Thiết kế dưới đây được đặt trước lần huấn luyện đầu tiên. Rolling validation dùng để chọn cấu hình; sau đó refit đến hết 2014-03, calibration trên 2014-04, đánh giá nội bộ cuối trên 2014-05–06. Mỗi user chỉ một dòng và một giai đoạn trong từng fold; các cửa sổ học tích lũy giữa fold là có chủ đích. Test Kaggle 2014-07–09 không có nhãn, chỉ dùng đối chiếu schema/drift.

Bảng chỉ kiểm kê quy mô các cửa sổ đề xuất, chưa tạo tập chia hoặc fit. Việc chia theo signup đánh giá thay đổi cohort, chưa mô phỏng đầy đủ một backtest tại thời điểm lịch: cần chứng minh nhãn train đã được đóng và có sẵn trước mỗi mốc dự đoán. Nếu sau này dùng horizon 90 ngày, phải thêm điều kiện trưởng thành nhãn trước origin; chưa được lấy booking tương lai để giả lập huấn luyện tại quá khứ.

Chọn tham số/early stopping bằng validation; chọn phương pháp calibration bằng dữ liệu phát triển, fit calibrator trên tháng 4. Giữ tập cuối cho một lần đánh giá sau khi khóa thiết kế. Các khoảng bootstrap đề xuất phải lấy mẫu theo user, seed=42; chưa chạy bootstrap.
""", [("Cửa sổ thời gian đề xuất và quy mô quan sát", proposed_protocol(train, account))]),
        section("acceptance", "Tiêu chí chấp nhận đặt trước", "Các mức 2%, 10%, 1,20, 2/3 điểm phần trăm và ngân sách top 20% là quy ước nghiên cứu đề xuất, không phải chuẩn phổ quát hoặc cam kết hiệu quả kinh doanh. Khi có chi phí/lợi ích thực tế cần chốt lại trước huấn luyện và ghi phiên bản protocol. Tất cả trạng thái hiện tại là chưa đánh giá.", [("Cổng chấp nhận cho giai đoạn mô hình hóa", criteria)]),
    ])

    suitability = pd.DataFrame([
        ["Đủ tín hiệu", f"10 category được sàng lọc V; gender V={v_by_name.loc['gender','effect_all']:.3f}, trong 2014={v_by_name.loc['gender','effect_2014']:.3f}; có bảng tương tác/cohort", "Đạt ở mức EDA", "Chưa chứng minh dự báo ngoài mẫu; không dùng p-value thay AUC"],
        ["Đủ cỡ mẫu", f"{len(train):,} users; {int(frame.observed_booking.sum()):,} booking; cohort 2014 {recent_users:,}", "Đạt tổng thể", "Một số category/ô tương tác ít user; dùng n và CI"],
        ["Nhãn tin cậy", f"Presence ngày booking khớp 100%; {int(lag.lt(0).sum())} độ trễ âm; max độ trễ 365 ngày", "Cần xác minh", "Chưa xác nhận horizon/follow-up của NDF và ngoại lệ trước account"],
        ["Không rò rỉ", "date_first_booking và presence tiết lộ nhãn; sessions chứa tên giao dịch, thiếu timestamp", "Chưa đạt với toàn bộ raw", "Thiết kế chính loại các nguồn này; cần audit lại trước fit"],
        ["Biến khả dụng tại t0", "t0 đã chọn: sau tạo account; raw không cung cấp lịch sử cập nhật hồ sơ", "Cần xác minh", "Xác nhận snapshot từng biến; ngày account không có giờ"],
        ["Ổn định theo thời gian", "Booking rate/cohort, độ phủ sessions và TV category thay đổi; đã có đối chiếu cùng năm 2014", "Chưa đạt giả định ổn định", "Dùng kiểm định theo thời gian, không coi train/test là IID"],
        ["Khái quát hóa", "User từ Mỹ, giai đoạn lịch sử; test Kaggle không có nhãn; chưa có dữ liệu vận hành khác", "Chưa được chứng minh", "Chưa suy sang Việt Nam, thị trường hiện tại hoặc chiến dịch marketing"],
    ], columns=["criterion", "evidence_in_report", "status", "remaining_condition"])
    conclusion = section("conclusion_main", "8. Bằng chứng về mức độ phù hợp", """
**Kết luận lựa chọn:** Airbnb phù hợp nhất trong ba bộ cho nghiên cứu propensity booking đầu ở cấp user. Có cỡ mẫu và liên hệ mô tả để tiếp tục thiết kế nghiên cứu. Chưa đủ bằng chứng xác nhận một mô hình triển khai tại signup với horizon 90 ngày.

Các điều kiện về t0, ngoại lệ nhãn và thời gian theo dõi là cổng dữ liệu cần giải quyết; không được biến thành giả định ngầm để đánh dấu mọi tiêu chí đều đạt. Chưa làm sạch, thay thế tuổi/NA, mã hóa, tạo feature, tạo tập chia hay huấn luyện mô hình. Các nhóm, cờ và tổng sessions chỉ dùng để tính bảng EDA trong bộ nhớ.
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
        section("strata_details", "Phân tầng và tương tác: Wilson 95% cho từng ô", "Dùng để đọc độ bất định của các ô heatmap; không phải kết quả mô hình.", [(f"{c} × năm", t) for c, t in strata.items()] + interaction_tables),
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
        "So 2014-01 đến 2014-06 để xem khác biệt trong các booking đã quan sát. Không gán thời gian theo dõi cho NDF từ phân phối dương; tỷ lệ trong ba cột horizon có mẫu số valid_observed_bookings.",
        [("Cohort 2014: NDF và mức bao phủ booking quan sát",pd.DataFrame(recent_lags))]))
    source = base["overview"]["blocks"][0]
    source["tables"][0][1].loc[source["tables"][0][1]["item"].eq("Ngày tải raw"), "description"] = "Không được lưu; người cung cấp xác nhận 2026-11-02. Mã phiên bản Kaggle chưa có bằng chứng; dùng snapshot SHA-256."
    scope = base["overview"]["blocks"][1]
    scope["text"] = scope["text"].replace("Chưa xác minh được ngày kết thúc theo dõi cho từng người dùng và độ trưởng thành nhãn ở mỗi cohort.", "Phân tích độ trễ và độ nhạy horizon ở phần 5 phân biệt nhãn nguồn với nhãn triển khai theo thời hạn.")
    overview = combine("overview", "2. Tổng quan bộ dữ liệu", [source, scope])
    base["quality_main"]["title"] = "3. Chất lượng dữ liệu"
    base["univariate"]["title"] = "4. Phân tích đơn biến"
    base["risks"]["title"] = "6. Hạn chế, rủi ro và quyền riêng tư"
    risk_table = base["risks"]["tables"][0][1]
    risk_table.loc[risk_table.issue.eq("Quần thể"), "evidence_or_limit"] = "Users từ Mỹ trong giai đoạn lịch sử; thời gian theo dõi từng user chưa xác minh, sessions chỉ phủ cohort 2014."
    cov_absent = s2014.set_index("has_sessions")
    age_signal = v_by_name.loc["age: cờ thiếu (EDA)"]
    age_rank = v_by_name.loc["age: chỉ cửa sổ 16–100 (EDA)"]
    insights = [
        f"**Bài toán đã chọn:** xác suất user mới có booking đầu được ghi nhận, t0 thiết kế ngay sau tạo account; {len(train):,} user train và {len(test):,} test. Horizon nguồn chưa được xác nhận; xem phần 1.",
        f"**Nhãn và độ trễ:** {int(frame.observed_booking.sum()):,} user có booking ({frame.observed_booking.mean()*100:.2f}%); trong {len(values):,} độ trễ không âm, 30/60/90 ngày bao phủ {coverage_at(30):.2f}%/{coverage_at(60):.2f}%/{coverage_at(90):.2f}%. Xem bảng độ trễ phần 5.",
        f"**Ngoại lệ nhãn:** {int(lag.lt(0).sum())} booking trước ngày account; max độ trễ ở mọi năm là 365 ngày. Đây là căn cứ điều tra cơ chế nhãn, chưa chứng minh NDF đã được theo dõi đủ một năm.",
        "**Leakage đã chứng minh:** presence date_first_booking khớp 100% nhãn; giữ bảng chéo tại phần 3. Cột này và cờ thiếu không là đầu vào dự đoán.",
        f"**Liên hệ có định lượng:** gender có V={v_by_name.loc['gender','effect_all']:.3f} toàn kỳ và {v_by_name.loc['gender','effect_2014']:.3f} trong 2014; signup_app tương ứng {v_by_name.loc['signup_app','effect_all']:.3f}/{v_by_name.loc['signup_app','effect_2014']:.3f}. Bảng đủ biến và phân tầng ở phần 5, chưa là chất lượng mô hình.",
        f"**So sessions cùng điều kiện:** train 2014 {coverage_recent:.2f}% so với test 2014 {coverage_test:.2f}%, chênh {coverage_test-coverage_recent:.2f} điểm phần trăm. {recent_users:,} user train nằm trong phạm vi cohort có log; xem phần sessions.",
        f"**Có log không đồng nghĩa nhãn giống nhau:** trong 2014, booking rate có log {cov_absent.loc[True,'rate_pct']:.2f}%, không log {cov_absent.loc[False,'rate_pct']:.2f}%. Cần đọc cùng n/Wilson; không dùng presence log làm tín hiệu tại signup khi chưa chứng minh t0.",
        f"**Missing và tuổi:** age thiếu {train.age.isna().mean()*100:.2f}%; trong 2014, cờ thiếu tuổi có V={age_signal.effect_2014:.3f}, còn rank-biserial của tuổi 16–100 là {age_rank.effect_2014:.3f}. Hai thước đo khác nhau; kết quả nhấn mạnh cần kiểm tra tính đầy đủ hồ sơ và snapshot tại t0. Giữ riêng NA, unknown và untracked.",
        "**Thiết kế tiếp theo đã cụ thể hóa:** baseline hằng/Logistic L2, CatBoost và calibration; rolling theo signup, calibration tháng 4/2014, đánh giá cuối tháng 5–6/2014. Đây là protocol đề xuất, chưa chia tập hay train.",
    ]
    report.sections = [
        section("executive", "Tóm tắt điều hành", "\n\n".join(f"{i}. {text}" for i, text in enumerate(insights, 1))),
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
        "analysis_revision": "airbnb_label_signal_cohort_sessions_protocol_v2",
    })
