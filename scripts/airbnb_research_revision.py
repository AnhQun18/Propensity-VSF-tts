"""Conditional 90-day labels, calendar embargo and profile-completeness EDA.

All labels and windows are diagnostics in memory; no model or feature file is fit.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REVISION = "airbnb_90day_embargo_profile_v2"


def conditional_labels(train, account, assume_365=True):
    booking = pd.to_datetime(train.date_first_booking, errors="coerce")
    lag = (booking - account).dt.days
    source_positive = train.country_destination.ne("NDF")
    labels = pd.Series(pd.NA, index=train.index, dtype="Int64")
    valid_positive = source_positive & lag.ge(0) & account.notna()
    labels.loc[valid_positive] = lag[valid_positive].le(90).astype(int)
    if assume_365:
        labels.loc[~source_positive & booking.isna() & account.notna()] = 0
    return labels, lag


def protocol_90(train, account, labels):
    """Day 90 is included; require its end strictly before a prediction origin."""
    windows = [
        ("Lượt 1 · học", "2010-01-01", "2012-10-02", "2013-01-01", "học"),
        ("Lượt 1 · kiểm định", "2013-01-01", "2013-03-31", "2013-01-01", "kiểm định"),
        ("Lượt 2 · học", "2010-01-01", "2013-04-01", "2013-07-01", "học"),
        ("Lượt 2 · kiểm định", "2013-07-01", "2013-08-31", "2013-07-01", "kiểm định"),
        ("Lượt 3 · học", "2010-01-01", "2013-06-02", "2013-09-01", "học"),
        ("Lượt 3 · kiểm định", "2013-09-01", "2013-10-02", "2013-09-01", "kiểm định"),
        ("Huấn luyện lại", "2010-01-01", "2013-10-02", "2014-01-01", "học"),
        ("Hiệu chỉnh xác suất", "2014-01-01", "2014-01-30", "2014-01-01", "hiệu chỉnh"),
        ("Đánh giá cuối", "2014-05-01", "2014-06-30", "2014-05-01", "đánh giá"),
    ]
    rows = []
    for purpose, start, end, origin, role in windows:
        mask = account.between(start, end)
        chosen = mask & labels.notna()
        ready = pd.Timestamp(end) + pd.Timedelta(days=91)
        if role == "học":
            assert ready <= pd.Timestamp(origin)
            gap_start = pd.Timestamp(end) + pd.Timedelta(days=1)
            gap_end = pd.Timestamp(origin) - pd.Timedelta(days=1)
        elif role == "hiệu chỉnh":
            assert ready <= pd.Timestamp("2014-05-01")
            gap_start, gap_end = pd.Timestamp(end)+pd.Timedelta(days=1), pd.Timestamp("2014-04-30")
        else:
            gap_start = gap_end = pd.NaT
        rows.append({
            "proposed_use": purpose, "account_from": start, "account_to": end,
            "users": int(mask.sum()), "eligible_90": int(chosen.sum()),
            "observed_bookings": int(labels[chosen].sum()),
            "booking_pct": float(labels[chosen].mean()*100) if chosen.any() else np.nan, "prediction_origin": origin,
            "labels_ready_on": str(ready.date()), "role": role,
            "gap_start": str(gap_start.date()) if pd.notna(gap_start) else "—",
            "gap_end": str(gap_end.date()) if pd.notna(gap_end) else "—",
            "embargo_days": int((gap_end-gap_start).days+1) if pd.notna(gap_start) else 0,
        })
    result = pd.DataFrame(rows)
    assert result.loc[result.role.isin(["học", "hiệu chỉnh"]), "embargo_days"].eq(90).all()
    return result


def rates_two_targets(frame, keys):
    from scripts.build_descriptive_reports import wilson
    rows = []
    for values, group in frame.groupby(keys, observed=True, dropna=False, sort=True):
        values = values if isinstance(values, tuple) else (values,)
        row = dict(zip(keys, values))
        row.update(n=len(group), source_rate=group.observed_booking.mean()*100)
        valid = group.y90.dropna()
        lo, hi = wilson(int(valid.sum()), len(valid))
        row.update(n90=len(valid), positive90=int(valid.sum()), rate90=float(valid.mean()*100),
                   lower90=float(lo), upper90=float(hi), n_under_100=len(valid)<100)
        rows.append(row)
    return pd.DataFrame(rows)


def profile_evidence(train, account, labels):
    from scripts.airbnb_deep_dive import categorical_association
    frame = train.assign(observed_booking=train.country_destination.ne("NDF").astype(int),
                         y90=labels, age_missing=train.age.isna(),
                         gender_unknown=train.gender.eq("-unknown-"))
    recent = frame[account.dt.year.eq(2014)].copy()
    gender = rates_two_targets(recent, ["gender"])
    age = rates_two_targets(recent, ["age_missing"])
    overlap = rates_two_targets(recent, ["age_missing", "gender_unknown"])
    apps = rates_two_targets(recent, ["age_missing", "gender_unknown", "signup_app"])
    apps.insert(0, "Năm đăng ký", 2014)
    v = categorical_association(recent.age_missing, recent.gender_unknown)["v"]
    summary = pd.DataFrame([{
        "Năm đăng ký": 2014, "FEMALE · nhãn y (%)": gender.set_index("gender").loc["FEMALE", "source_rate"],
        "MALE · nhãn y (%)": gender.set_index("gender").loc["MALE", "source_rate"],
        "Không rõ giới tính · nhãn y (%)": gender.set_index("gender").loc["-unknown-", "source_rate"],
        "Có tuổi · nhãn y (%)": age.set_index("age_missing").loc[False, "source_rate"],
        "Thiếu tuổi · nhãn y (%)": age.set_index("age_missing").loc[True, "source_rate"],
        "V giữa hai cờ thiếu hồ sơ": v,
    }])
    # Empirical group entropy is a descriptive same-sample calculation, not validation.
    contrasts = []
    def entropy(p):
        return float(-(p*np.log(p)+(1-p)*np.log1p(-p))) if 0 < p < 1 else 0.
    for target, label in [("observed_booking", "Nhãn y hiện có"), ("y90", "Nhãn y90 · giả định 365 ngày")]:
        chosen = recent[recent[target].notna()]
        grouped = chosen.groupby("age_missing")[target].agg(["size", "mean"])
        prevalence = float(chosen[target].mean())
        constant_loss = entropy(prevalence)
        group_loss = sum(row["size"]*entropy(float(row["mean"])) for _, row in grouped.iterrows())/len(chosen)
        high = grouped.loc[grouped["mean"].idxmax()]
        assert high["size"]/len(chosen) >= .2
        contrasts.append([label, len(chosen), constant_loss, group_loss,
                          (constant_loss-group_loss)/constant_loss*100, float(high["mean"])/prevalence])
    contrast = pd.DataFrame(contrasts, columns=["Mục tiêu", "Số người dùng · 2014", "Entropy xác suất hằng", "Entropy theo hai nhóm tuổi", "Giảm entropy cùng mẫu (%)", "Lift kỳ vọng top 20% cùng mẫu"])
    return recent, gender, age, overlap, apps, summary, contrast


def timeline_with_embargo(report):
    import matplotlib.dates as mdates
    from matplotlib.patches import Patch
    table = report.airbnb_evidence["protocol"]
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2, 1]}, layout="constrained")
    palette = {"học": "#245D80", "kiểm định": "#468477", "hiệu chỉnh": "#C76A37", "đánh giá": "#8A6598"}
    for ax, rows, left in [(axes[0], table, "2009-12-01"), (axes[1], table.iloc[6:], "2013-07-01")]:
        for pos, row in enumerate(rows.itertuples(index=False)):
            start, end = pd.Timestamp(row.account_from), pd.Timestamp(row.account_to)+pd.Timedelta(days=1)
            ax.broken_barh([(mdates.date2num(start), (end-start).days)], (pos-.3, .6), facecolors=palette[row.role])
            if row.embargo_days:
                gap = pd.Timestamp(row.gap_start)
                ax.broken_barh([(mdates.date2num(gap), row.embargo_days)], (pos-.3, .6), facecolors="#e6e6e6", edgecolors="#909090", hatch="///")
            ax.annotate(f"n={row.eligible_90:,}", (mdates.date2num(pd.Timestamp("2014-08-01")), pos), va="center", fontsize=9)
        ax.set_yticks(range(len(rows)), rows.proposed_use)
        ax.invert_yaxis()
        ax.set_xlim(mdates.date2num(pd.Timestamp(left)), mdates.date2num(pd.Timestamp("2014-12-01")))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6 if ax is axes[0] else 2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
        ax.grid(axis="x", alpha=.2)
    axes[0].set_title("Nhãn 90 ngày · cửa sổ học và khoảng đệm theo ngày lịch")
    axes[1].set_title("Phóng to: huấn luyện lại → đệm 90 ngày → hiệu chỉnh → đệm 90 ngày → đánh giá")
    axes[1].set_xlabel("Ngày tạo tài khoản")
    handles = [Patch(facecolor=color, label=label) for label, color in palette.items()]
    handles.append(Patch(facecolor="#e6e6e6", hatch="///", label="Đệm 90 ngày · không đưa vào tập trước"))
    axes[1].legend(handles=handles, loc="upper center", bbox_to_anchor=(.5, -.25), ncol=3, frameon=False)
    return report.savefig("evaluation_timeline", fig)


def apply_research_revision(report):
    from scripts.airbnb_report_presentation import capture_evidence, walk_sections
    from scripts.eda_diagnostics import section
    context = report.airbnb_context
    train, account, frame = context["train"], context["account"], context["frame"]
    labels, lag = conditional_labels(train, account)
    no_assumption, _ = conditional_labels(train, account, assume_365=False)
    recent, gender, age, overlap, apps, profile_summary, contrast = profile_evidence(train, account, labels)
    protocol = protocol_90(train, account, labels)
    positive, eligible, unknown = int(labels.eq(1).sum()), int(labels.notna().sum()), int(labels.isna().sum())
    source_positive = train.country_destination.ne("NDF")
    summary90 = pd.DataFrame([{
        "Giả định theo dõi (ngày)": 365, "Thời hạn (ngày)": 90,
        "Toàn bộ người dùng": len(train), "Dương tính y90": positive,
        "Âm tính y90 có điều kiện": int(labels.eq(0).sum()), "Chưa gán nhãn": unknown,
        "Mẫu hợp lệ": eligible, "Dương tính trên toàn bộ dòng (%)": positive/len(train)*100,
        "Dương tính trên mẫu hợp lệ (%)": positive/eligible*100,
    }])
    construction = pd.DataFrame([
        ["Đã đặt chỗ, độ trễ từ 0 đến 90 ngày", int((source_positive & lag.between(0,90)).sum()), "1", "Đã quan sát lượt đặt chỗ trong thời hạn"],
        ["Đã đặt chỗ, độ trễ lớn hơn 90 ngày", int((source_positive & lag.gt(90)).sum()), "0", "Lượt đặt chỗ đầu tiên xảy ra sau thời hạn"],
        ["NDF", int((~source_positive).sum()), "0 có điều kiện", "Chỉ gán âm khi chấp nhận giả định theo dõi đủ 365 ngày"],
        ["Ngày đặt chỗ âm hoặc không xác định", unknown, "Chưa gán", "Loại khỏi mẫu nghiên cứu 90 ngày cho đến khi xác minh"],
    ], columns=["Trường hợp", "Số người dùng", "Nhãn y90", "Căn cứ"])
    sensitivity = pd.DataFrame([
        ["Giả định mỗi người được theo dõi 365 ngày", positive, int(labels.eq(0).sum()), unknown, eligible],
        ["Chỉ dùng bằng chứng lượt đặt chỗ đã ghi nhận", int(no_assumption.eq(1).sum()), int(no_assumption.eq(0).sum()), int(no_assumption.isna().sum()), int(no_assumption.notna().sum())],
    ], columns=["Kịch bản", "Dương tính", "Âm tính xác định trong kịch bản", "Chưa xác định", "Mẫu gán được nhãn"])
    by_key = {item["key"]: item for item in walk_sections(report.sections)}
    delay = by_key["booking_delay"]
    delay["text"] = delay["text"].split("Ngày đặt chỗ muộn nhất")[0] + """Ngày đặt chỗ muộn nhất là 2015-06-29, cách ngày tạo tài khoản cuối 2014-06-30 là 364 ngày. Độ trễ lớn nhất của từng nhóm năm đăng ký đều bằng 365 ngày. Hai quan sát này ủng hộ mạnh giả thuyết mỗi người được theo dõi tối đa 365 ngày kể từ đăng ký. Chúng chưa trực tiếp xác nhận thời gian theo dõi của từng người mang mã NDF.

Báo cáo dùng giả thuyết theo dõi đủ 365 ngày làm giả định làm việc để xây dựng nhãn nghiên cứu y90 ngay trong EDA. Đây là phân tích có điều kiện và có kịch bản độ nhạy, thay vì chặn toàn bộ nghiên cứu 90 ngày. Xác nhận chính thức cơ chế theo dõi vẫn là điều kiện trước khi suy rộng hoặc triển khai.

Nhãn y90 bằng 1 nếu ngày đặt chỗ đầu tiên cách ngày tạo tài khoản từ 0 đến 90 ngày, gồm cả hai đầu. Nhãn bằng 0 cho lượt đặt chỗ muộn hơn 90 ngày và cho NDF dưới giả định theo dõi đủ 365 ngày. Các ngoại lệ ngày đặt chỗ âm để trạng thái chưa gán. Ngày 0 được giữ theo độ phân giải ngày của CSV; Q1/Q2 vẫn cần làm rõ thứ tự trong ngày."""
    delay["tables"].extend([("B9 · Nhãn nghiên cứu 90 ngày dưới giả định theo dõi 365 ngày", summary90),
                            ("Quy tắc gán nhãn 90 ngày và số lượng", construction), ("Độ nhạy khi không giả định theo dõi cho NDF", sensitivity)])
    profile_text = f"""Trong nhóm đăng ký năm 2014, tỷ lệ có nhãn y=1 của FEMALE và MALE gần bằng nhau, lần lượt {profile_summary.iloc[0,1]:.2f}% và {profile_summary.iloc[0,2]:.2f}%. Nhóm không rõ giới tính chỉ đạt {profile_summary.iloc[0,3]:.2f}%. Vì vậy, liên hệ biên của cột giới tính chủ yếu phản ánh sự khác nhau giữa hồ sơ có và thiếu thông tin, không nên trình bày như một hiệu ứng riêng của giới tính.

Cờ thiếu tuổi và cờ không rõ giới tính có Cramér V={profile_summary.iloc[0,-1]:.3f}. Đây là liên hệ mạnh giữa hai chỉ báo đầu vào, cho thấy tín hiệu chồng lặp. Nó không tự chứng minh cộng tuyến hoàn toàn hoặc quan hệ nhân quả. Cần kiểm tra loại từng cờ trong cùng thiết kế Logistic Regression và CatBoost.

Bảng và hình dưới tách đồng thời năm đăng ký, tình trạng thiếu tuổi và tình trạng không rõ giới tính trước khi so sánh ứng dụng. Chúng báo cả nhãn y hiện có và nhãn y90 có điều kiện. Các khoảng Wilson dành cho tỷ lệ y90 trong từng ô, với n<100 được đánh dấu. Giá trị tuổi và các cờ thiếu vẫn phải được xác minh là có sẵn tại t0."""
    profile = section("profile_completeness", "Độ đầy đủ hồ sơ và chênh lệch ứng dụng sau phân tầng", profile_text,
                      [("B10 · Tín hiệu độ đầy đủ hồ sơ · năm 2014", profile_summary)])
    by_key["multivariate_main"]["blocks"].insert(2, profile)
    by_key["appendix"]["blocks"].append(section("profile_details", "Chi tiết phân tầng theo độ đầy đủ hồ sơ", "Mỗi hàng dùng người đăng ký năm 2014 trong nhóm tương ứng. Nhãn y và y90 là hai mục tiêu khác nhau. Các bảng giữ cỡ mẫu và khoảng Wilson của y90.",
        [("Giới tính khai báo · hai mục tiêu", gender), ("Tình trạng tuổi · hai mục tiêu", age), ("Giao hai cờ thiếu hồ sơ", overlap),
         ("B11 · Ứng dụng trong từng mức độ đầy đủ hồ sơ", apps)]))
    plot_profiles(report, recent, apps, profile)
    by_key["signal"]["text"] += "\n\nCramér V của giới tính và cờ thiếu tuổi không được xem là hai bằng chứng dự báo độc lập. Phần độ đầy đủ hồ sơ bên dưới định lượng mức chồng lặp và tách chênh lệch ứng dụng trong từng nhóm hồ sơ."
    risk = by_key["risks"]
    risk["text"] = """Airbnb phù hợp để nghiên cứu xác suất đặt chỗ đầu tiên tại thời điểm đăng ký. Báo cáo phân biệt nhãn y hiện có với nhãn nghiên cứu y90 dưới giả định theo dõi đủ 365 ngày. Nghiên cứu y90 có thể bắt đầu với giả định được công khai và kiểm tra độ nhạy. Việc triển khai còn cần xác minh hồ sơ tại t0 và cơ chế theo dõi NDF."""
    suitability = risk["tables"][0][1]
    suitability.loc[suitability.criterion.eq("Nhãn tin cậy"), ["status", "remaining_condition"]] = ["Nghiên cứu y90 có điều kiện", "Dùng giả định theo dõi 365 ngày và báo độ nhạy. Xác nhận chính thức Q3 trước triển khai; loại 29 ngoại lệ khỏi mẫu y90."]
    suitability.loc[suitability.criterion.eq("Đủ tín hiệu"), "remaining_condition"] = "Kiểm tra giá trị bổ sung so với Logistic Regression mạnh. Các chỉ báo thiếu hồ sơ có liên hệ chồng lặp, không được cộng bằng chứng độc lập."
    questions = by_key["open_questions"]["tables"][0][1]
    questions.iloc[2, 4] = "Đối chiếu giới hạn 365 ngày ở mọi nhóm năm và mốc booking cuối. Nghiên cứu dùng giả định theo dõi đủ 365 ngày; đồng thời tìm tài liệu xác nhận NDF thực sự được theo dõi đủ thời hạn."
    questions.iloc[2, 5] = "Cho phép nghiên cứu nhãn y90 có điều kiện ngay; trước triển khai phải lưu xác nhận chính thức cơ chế theo dõi. Báo cả kịch bản bỏ giả định NDF và loại ngoại lệ ngày âm."
    questions.iloc[2, 6] = "Giả thuyết được dữ liệu ủng hộ; đã dùng làm giả định nghiên cứu, chưa xác nhận chính thức"
    by_key["open_questions"]["text"] += "\n\nQ3 đã có bằng chứng định lượng mạnh và không còn chặn việc xây dựng nhãn nghiên cứu 90 ngày có điều kiện. Trạng thái chưa xác nhận chính thức chỉ giới hạn mức kết luận và triển khai."
    by_key["implications"]["tables"][0][1].iloc[0, 1:3] = ["Nghiên cứu nhãn y90 dưới giả định theo dõi 365 ngày", "Báo độ nhạy theo Q3; xác nhận cơ chế trước triển khai"]
    problem = by_key["problem"]
    problem["text"] = """Bài toán nghiên cứu chính là ước lượng xác suất người dùng mới có lượt đặt chỗ đầu tiên trong 90 ngày kể từ lúc đăng ký. Thời điểm dự đoán t0 là ngay sau khi tạo tài khoản.

Nhãn y90 được xây dựng có điều kiện dưới giả định mỗi người được theo dõi đủ 365 ngày. Cột điểm đến gốc vẫn xác định nhãn y để mô tả bộ dữ liệu; y và y90 là hai mục tiêu khác nhau. Các bảng EDA cũ tiếp tục ghi rõ nhãn y, còn thiết kế mô hình và bảng B7 dùng y90. Quy tắc và mẫu số của y90 nằm ở B9.

Thông tin đầu vào chỉ hợp lệ nếu phản ánh hồ sơ tại t0. Các cột ngày đặt chỗ, cờ thiếu ngày đặt chỗ và nhật ký chưa có thời điểm sự kiện bị loại khỏi thiết kế chính. Các ngoại lệ ngày đặt chỗ âm được giữ trong EDA nhãn y nhưng chưa gán y90."""
    glossary = by_key["glossary"]["tables"][0][1]
    by_key["glossary"]["text"] = by_key["glossary"]["text"].replace("“nhãn y” cho mục tiêu nhị phân", "“nhãn y” cho kết quả gốc và “nhãn y90” cho mục tiêu nghiên cứu 90 ngày")
    glossary.loc[len(glossary)] = ["Nhãn y90", "Nhãn nghiên cứu 90 ngày có điều kiện: 1 nếu độ trễ từ 0 đến 90; 0 nếu muộn hơn hoặc NDF dưới giả định theo dõi đủ 365 ngày. Ngoại lệ ngày âm chưa gán nhãn."]
    glossary.loc[len(glossary)] = ["Khoảng đệm thời gian (embargo)", "Khoảng ngày đăng ký bị bỏ khỏi tập trước để nhãn 90 ngày hoàn tất trước khi dự đoán tập sau. Ở đây đệm 90 ngày lịch và chỉ dùng nhãn đã có trước mốc dự đoán."]
    revise_research_design(report, by_key, contrast)
    revise_executive(report, by_key, summary90, profile_summary, apps)
    report.facts.update({"research_revision": REVISION, "primary_target": "conditional_first_booking_within_90_days_assuming_365_day_followup",
                         "followup_assumption_days": 365, "conditional_90_positive": positive,
                         "conditional_90_eligible": eligible, "conditional_90_unassigned": unknown,
                         "conditional_90_rate_pct": positive/eligible*100, "conditional_90_fraction_all_rows_pct": positive/len(train)*100,
                         "age_gender_missing_cramers_v_2014": float(profile_summary.iloc[0,-1]),
                         "protocol_embargo_calendar_days": 90})
    report.facts["base_evidence_fingerprint"] = report.facts["statistical_fingerprint"]
    capture_evidence(report, {**report.airbnb_evidence, "protocol": protocol, "conditional_label_summary": summary90,
                             "conditional_label_rules": construction, "conditional_label_sensitivity": sensitivity,
                             "profile_summary": profile_summary, "profile_overlap": overlap, "profile_apps": apps,
                             "descriptive_baseline_contrast": contrast})
    report.research_tables = {"B9": summary90, "B10": profile_summary, "B11": apps}
    report.airbnb_context["y90"] = labels


def plot_profiles(report, recent, apps, section):
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.4), layout="constrained")
    overlap = pd.crosstab(recent.age_missing, recent.gender_unknown)
    axes[0].imshow(overlap, cmap="Blues")
    axes[0].set_xticks([0,1], ["Có khai báo giới tính", "Không rõ giới tính"])
    axes[0].set_yticks([0,1], ["Có tuổi", "Thiếu tuổi"])
    axes[0].set_title("Hai chỉ báo thiếu hồ sơ · năm 2014")
    for i in range(2):
        for j in range(2):
            axes[0].text(j, i, f"n={overlap.iloc[i,j]:,}", ha="center", va="center",
                         color="white" if overlap.iloc[i,j] > 20000 else "#172a35", fontsize=12)
    complete = apps[~apps.age_missing & ~apps.gender_unknown]
    x = np.arange(len(complete))
    axes[1].errorbar(complete.rate90, x,
                     xerr=np.vstack([complete.rate90-complete.lower90, complete.upper90-complete.rate90]),
                     fmt="o", capsize=4, color="#245D80")
    axes[1].set_yticks(x, [f"{r.signup_app} · n={r.n90:,}" for r in complete.itertuples()])
    axes[1].set(xlim=(0,100), xlabel="Có lượt đặt chỗ trong 90 ngày (%)",
                title="Có tuổi và có khai báo giới tính · năm 2014")
    axes[1].grid(axis="x", alpha=.2)
    path = report.savefig("profile_completeness", fig)
    section["figures"] = [path]
    report.figure_notes[path.name] = (
        "**Quan sát:** thiếu tuổi thường đi cùng tình trạng không rõ giới tính. Chênh lệch ứng dụng vẫn xuất hiện trong nhóm có đủ hai thông tin này.\n\n"
        "**Phạm vi và cách đọc:** bên trái là số người dùng trong bốn ô hồ sơ. Bên phải là nhãn y90 dưới giả định theo dõi 365 ngày, "
        "chỉ trong nhóm có tuổi và có khai báo giới tính, với khoảng Wilson 95%. Bảng B11 giữ cả bốn mức đầy đủ hồ sơ. "
        "Đây là phân tầng mô tả, chưa kiểm soát mọi khác biệt và chưa xác nhận thông tin có sẵn tại t0."
    )


def revise_research_design(report, by_key, contrast):
    models = pd.DataFrame([
        ["Xác suất hằng", "Tỷ lệ y90 trong mỗi tập học", "Chỉ là mốc kiểm tra cơ bản"],
        ["Logistic Regression L2 · hồ sơ tối giản", "Cờ thiếu tuổi và cờ không rõ giới tính", "Đo mức tín hiệu dễ khai thác; kiểm tra bỏ lần lượt từng cờ"],
        ["Logistic Regression L2 · ít biến mạnh", "Hai cờ hồ sơ, ứng dụng đăng ký, kênh tiếp cận, cách đăng ký", "Baseline mạnh bắt buộc; mã hóa và chọn điều chuẩn trong tập học/kiểm định"],
        ["Logistic Regression L2 · cùng đầu vào", "Cùng tập biến hợp lệ tại t0 với CatBoost", "So sánh công bằng về nguồn thông tin; baseline chính là LR tốt nhất được chọn trên các lượt kiểm định"],
        ["CatBoost", "Cùng thông tin hợp lệ tại t0", "Chỉ chấp nhận nếu tăng giá trị so với LR đã chọn; kiểm tra bỏ cờ hồ sơ và ứng dụng"],
        ["Hiệu chỉnh sigmoid", "Áp dụng riêng cho từng ứng viên đã cố định", "Cùng cửa sổ hiệu chỉnh, cùng cửa sổ đánh giá; không ưu tiên riêng CatBoost"],
    ], columns=["Ứng viên", "Thông tin sử dụng", "Vai trò và kiểm soát"])
    by_key["algorithms"]["text"] = """Thiết kế mô hình dùng nhãn y90 có điều kiện dưới giả định theo dõi đủ 365 ngày. Xác suất hằng chỉ là mốc kiểm tra tối thiểu. Đối chứng quyết định giá trị của CatBoost là Logistic Regression L2 mạnh, gồm một cấu hình ít biến và một cấu hình có cùng đầu vào với CatBoost. Baseline LR được chọn bằng các lượt kiểm định có khoảng đệm, trước khi dùng tập cuối.

Hai cờ hồ sơ có liên hệ mạnh nên cần kiểm tra loại lần lượt cờ thiếu tuổi, cờ không rõ giới tính, rồi ứng dụng đăng ký. Mọi xử lý thiếu, mã hóa và thống kê dựa nhãn chỉ học trên tập học. Chưa huấn luyện mô hình, tính AUC hoặc tối ưu tham số trong báo cáo này."""
    by_key["algorithms"]["tables"] = [("Đối chứng từ đơn giản đến mạnh và so sánh công bằng", models)]
    by_key["algorithms"]["tables"].append(("Đối chiếu mô tả: mức tín hiệu chỉ từ tình trạng thiếu tuổi", contrast))
    by_key["algorithms"]["text"] += "\n\nBảng entropy bên dưới tính từ tỷ lệ của hai nhóm tuổi trên chính mẫu năm 2014. Đây là phép tính mô tả cùng mẫu, có xu hướng lạc quan, không phải log loss kiểm định hoặc kết quả mô hình. Lift top 20% là kỳ vọng khi chọn ngẫu nhiên trong nhóm có tỷ lệ cao nhất, vì nhóm đó lớn hơn 20% mẫu. Nó cho thấy ngưỡng cũ so với xác suất hằng dễ đạt, nhưng không chứng minh một mô hình đã đạt ngoài thời gian."
    by_key["evaluation"]["text"] = """Bảng B7 dùng nhãn y90 và có khoảng đệm 90 ngày lịch trước mỗi cửa sổ kiểm định, trước hiệu chỉnh và giữa hiệu chỉnh với đánh giá cuối. Ngày thứ 90 được tính vào nhãn. Vì CSV chỉ chính xác đến ngày, nhãn chỉ được dùng khi ngày đăng ký + 90 ngày nhỏ hơn mốc dự đoán. Cột ngày nhãn sẵn có tương ứng ngày đăng ký cuối + 91 ngày.

Ba lượt kiểm định kết thúc ở các nhóm đăng ký tháng 1–3/2013, tháng 7–8/2013 và tháng 9 đến 2013-10-02. Nhãn của lượt cuối sẵn có từ 2014-01-01. Khi đó chốt cấu hình và huấn luyện lại với người đăng ký đến 2013-10-02. Hiệu chỉnh dùng người đăng ký từ 2014-01-01 đến 2014-01-30. Nhãn hiệu chỉnh hoàn tất trước mốc đánh giá 2014-05-01; ngày đăng ký 2014-01-31 đến 2014-04-30 nằm trong khoảng đệm.

Đánh giá cuối dùng người đăng ký tháng 5–6/2014 và chỉ tính kết quả sau khi nhãn hoàn tất từ 2014-09-29. Không đưa người trong khoảng đệm vào tập trước, kể cả người đã đặt chỗ sớm, để tránh chọn mẫu theo kết quả. Các số lượng chỉ là kiểm kê cửa sổ trên mẫu y90 hợp lệ, chưa xuất tập chia hoặc huấn luyện.

[TimeSeriesSplit của scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) có tham số gap tính theo số dòng. Thiết kế ở đây dùng ngày lịch vì số người đăng ký mỗi ngày không đều. Khoảng đệm bảo đảm thứ tự nhãn theo giả định đã nêu; mọi độ trễ cập nhật dữ liệu thực tế cần được cộng thêm khi có bằng chứng."""
    criteria = pd.DataFrame([
        ["Toàn vẹn và thời gian", "0 ID giao nhau trong mỗi lượt; ngày đăng ký + 90 < mốc dự đoán cho mọi nhãn dùng học; loại 29 ngoại lệ khỏi y90", "Kiểm tra cả học, hiệu chỉnh và thời điểm chọn cấu hình"],
        ["Giá trị bổ sung · tiêu chí chính", "Log loss CatBoost giảm ít nhất 1% tương đối so với baseline LR mạnh đã chọn; cận trên 95% của chênh log loss (CatBoost − LR) < 0", "So sánh ghép cặp trên cùng người, cùng mẫu y90 và cùng hiệu chỉnh; bootstrap theo người dùng"],
        ["Ưu tiên top 20%", "Lift@20% tăng ít nhất 5% tương đối so với LR; cận dưới 95% của chênh lift > 0", "Ngân sách 20% và mức 5% là đề xuất nghiên cứu; ngưỡng tuyệt đối 1.20 chỉ còn là thông tin tham khảo"],
        ["Phân biệt và xác suất", "AP không thấp hơn LR trên điểm ước lượng; báo ROC-AUC, Brier và độ hiệu chỉnh cho cả hai", "Brier không kém LR quá 0.002 tuyệt đối; báo khoảng tin cậy của chênh lệch"],
        ["Hiệu chỉnh", "Báo sai lệch xác suất trung bình, ECE 10 nhóm đồng số mẫu và biểu đồ độ tin cậy cho cả LR và CatBoost", "Không lấy riêng log loss hoặc ECE làm bằng chứng đầy đủ về hiệu chỉnh"],
        ["Độ bền và chồng lặp tín hiệu", "Báo chênh log loss với LR trong từng tháng và từng nhóm đủ/thiếu hồ sơ; kiểm tra bỏ từng cờ và ứng dụng", "Nếu giá trị bổ sung không ổn định hoặc không đạt, ưu tiên LR đơn giản hơn"],
    ], columns=["Tiêu chí", "Điều kiện chấp nhận đề xuất", "Cách diễn giải"])
    by_key["acceptance"]["text"] = """Các ngưỡng dưới đây là đề xuất đặt trước cho giá trị bổ sung của CatBoost so với Logistic Regression mạnh. Chúng không phải kết quả đã đo hoặc chuẩn phổ quát. Thay đổi đối chứng là điểm chính; chỉ tăng một ngưỡng so với xác suất hằng vẫn chưa đủ. Mức giảm log loss 2% so với hằng và lift tuyệt đối 1.20 của bản trước không còn dùng để chấp nhận CatBoost. Chọn LR đối chứng và bộ tham số bằng dữ liệu phát triển, không chọn theo tập cuối."""
    by_key["acceptance"]["tables"] = [("Điều kiện để CatBoost được chấp nhận thay cho LR", criteria)]


def research_roles():
    return pd.DataFrame([
        ["Chọn cấu hình", "Ba lượt kiểm định trong năm 2013", "Nhãn lượt cuối sẵn có từ 2014-01-01; lúc đó mới chốt mô hình và LR đối chứng"],
        ["Huấn luyện lại", "Người đăng ký đến 2013-10-02", "Đệm 2013-10-03 đến 2013-12-31; dự đoán hiệu chỉnh từ 2014-01-01"],
        ["Hiệu chỉnh", "Người đăng ký 2014-01-01 đến 2014-01-30", "Đệm 2014-01-31 đến 2014-04-30; mô hình nền giữ cố định"],
        ["Đánh giá cuối", "Người đăng ký 2014-05-01 đến 2014-06-30", "Mô hình và bộ hiệu chỉnh cố định trước 2014-05-01; kết quả hoàn tất từ 2014-09-29"],
        ["Test Kaggle", "Người đăng ký tháng 7–9/2014", "Chỉ kiểm tra cấu trúc và thay đổi phân phối vì không có nhãn"],
    ], columns=["Giai đoạn", "Cửa sổ", "Thời điểm và điều kiện sử dụng"])


def revise_executive(report, by_key, summary90, profile, apps):
    target = summary90.iloc[0]
    prof = profile.iloc[0]
    complete = apps[~apps.age_missing & ~apps.gender_unknown].set_index("signup_app")
    # Preserve finding 1 and 5; combine completeness into one finding and separate residual app differences.
    old = by_key["executive"]["text"].split("\n\n")
    first = next(p for p in old if p.startswith("1. **Quy mô"))
    last = next(p for p in old if p.startswith("5. **Phạm vi"))
    findings = [
        first,
        f"2. **Nhãn nghiên cứu 90 ngày có điều kiện:** có {int(target['Dương tính y90']):,} người đặt chỗ trong 90 ngày, bằng {target['Dương tính trên toàn bộ dòng (%)']:.2f}% toàn bộ {int(target['Toàn bộ người dùng']):,} dòng. Với giả định theo dõi đủ 365 ngày và loại {int(target['Chưa gán nhãn']):,} ngoại lệ chưa gán, mẫu nghiên cứu còn {int(target['Mẫu hợp lệ']):,} người, tỷ lệ dương {target['Dương tính trên mẫu hợp lệ (%)']:.2f}%. Đây là tỷ lệ trên toàn bộ mẫu người dùng tương ứng, khác với mức bao phủ trong nhóm đã đặt chỗ.",
        f"3. **Tín hiệu chung về độ đầy đủ hồ sơ:** trong năm 2014, FEMALE và MALE có tỷ lệ nhãn y=1 gần như nhau ({prof['FEMALE · nhãn y (%)']:.2f}% và {prof['MALE · nhãn y (%)']:.2f}%). Nhóm không rõ giới tính có tỷ lệ {prof['Không rõ giới tính · nhãn y (%)']:.2f}%. Người có tuổi đạt {prof['Có tuổi · nhãn y (%)']:.2f}%, so với {prof['Thiếu tuổi · nhãn y (%)']:.2f}% ở người thiếu tuổi. Hai cờ thiếu hồ sơ có V={prof['V giữa hai cờ thiếu hồ sơ']:.3f}, nên đây là tín hiệu chồng lặp cần kiểm tra giá trị bổ sung, không phải hai phát hiện dự báo độc lập. Cả hai chỉ được dùng sau khi xác minh tại t0.",
        f"4. **Chênh lệch ứng dụng sau phân tầng hồ sơ:** trong nhóm năm 2014 có tuổi và có khai báo giới tính, tỷ lệ nhãn y=1 của Web là {complete.loc['Web','source_rate']:.2f}%, iOS {complete.loc['iOS','source_rate']:.2f}% và Android {complete.loc['Android','source_rate']:.2f}%. Chênh lệch vẫn hiện diện sau khi tách hai cờ hồ sơ. Bảng chi tiết báo cả nhãn y và y90 cùng cỡ mẫu; kết quả vẫn là mô tả và chưa kiểm soát mọi khác biệt.",
        last,
    ]
    next_steps = [
        "1. **Chốt giả định nhãn và xử lý ngoại lệ.** Cho phép nghiên cứu y90 dưới giả định theo dõi đủ 365 ngày, báo độ nhạy khi không gán âm cho NDF và giữ 29 ngoại lệ ngoài mẫu y90. Q3 cần xác nhận chính thức trước triển khai, thay vì chặn toàn bộ nghiên cứu có điều kiện.",
        "2. **Chốt thông tin có sẵn tại t0.** Xác minh hồ sơ và các cờ thiếu phản ánh lúc đăng ký. Loại ngày đặt chỗ và cờ thiếu của cột này khỏi đầu vào vì mức khớp nhãn y là 100%. Nhật ký thiếu thời điểm sự kiện vẫn ngoài thiết kế chính.",
        "3. **Dùng đối chứng mạnh và khoảng đệm.** Chọn cấu hình cùng LR đối chứng trên các lượt kiểm định có đệm 90 ngày. Huấn luyện lại đến 2013-10-02, hiệu chỉnh trên 2014-01-01 đến 2014-01-30, rồi đánh giá tháng 5–6/2014. CatBoost phải tăng giá trị so với LR trên cùng nhãn y90 và cùng cửa sổ, không chỉ vượt xác suất hằng.",
    ]
    by_key["executive"]["text"] = (
        "**Kết luận:** có thể nghiên cứu xác suất đặt chỗ trong 90 ngày bằng nhãn có điều kiện dưới giả định theo dõi đủ 365 ngày. Thiết kế đánh giá dùng khoảng đệm theo ngày lịch và đối chứng Logistic Regression mạnh để kiểm tra giá trị bổ sung của CatBoost. (Nguồn: bảng B9 và B7.)"
        + "\n\n**Năm phát hiện chính**\n\n" + "\n\n".join(findings)
        + "\n\n**Ba việc cần giải quyết trước khi huấn luyện**\n\n" + "\n\n".join(next_steps))
