"""Conditional 90-day labels, monthly as-of evaluation and profile diagnostics.

All labels and windows are diagnostics in memory; no model or feature file is fit.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REVISION = "airbnb_asof_monthly_t0_branches_v3"
MAIN_T0_COLUMNS = ("date_account_created",)
REGISTRATION_EXTENSION = ("signup_method", "signup_flow", "signup_app")
PROFILE_UPDATE_DETAILS = {"edit_profile", "update_user", "update_user_profile", "user_profile_content_update"}
PROFILE_ACTION_NAMES = {"account", "edit", "update", "settings", "profile_pic", "has_profile_pic", "update_country_of_residence"}


def conditional_labels(train, account, assume_followup_90=True):
    booking = pd.to_datetime(train.date_first_booking, errors="coerce")
    lag = (booking - account).dt.days
    source_positive = train.country_destination.ne("NDF")
    labels = pd.Series(pd.NA, index=train.index, dtype="Int64")
    valid_positive = source_positive & lag.ge(0) & account.notna()
    labels.loc[valid_positive] = lag[valid_positive].le(90).astype(int)
    if assume_followup_90:
        labels.loc[~source_positive & booking.isna() & account.notna()] = 0
    return labels, lag


def protocol_90(train, account, labels):
    """Monthly as-of refits; calibration uses historical out-of-fold scores."""
    development = list(pd.date_range("2013-07-01", "2013-12-01", freq="MS"))
    final = list(pd.date_range("2014-05-01", "2014-06-01", freq="MS"))
    rows = []
    for origin in development + final:
        cutoff = origin - pd.Timedelta(days=91)
        end = origin + pd.offsets.MonthEnd(0)
        train_mask = account.le(cutoff) & labels.notna()
        evaluation_mask = account.between(origin, end) & labels.notna()
        calibration_from = cutoff - pd.Timedelta(days=89)
        calibration_mask = account.between(calibration_from, cutoff) & labels.notna()
        assert not (train_mask & evaluation_mask).any()
        assert (account[train_mask]+pd.Timedelta(days=90) < origin).all()
        ready = end + pd.Timedelta(days=91)
        if origin in development:
            assert ready <= pd.Timestamp("2014-05-01")
        rows.append({
            "prediction_origin": str(origin.date()), "role": "phát triển" if origin in development else "đánh giá cuối",
            "train_from": "2010-01-01", "train_to": str(cutoff.date()), "train_n": int(train_mask.sum()),
            "train_positive90": int(labels[train_mask].sum()), "train_rate90": float(labels[train_mask].mean()*100) if train_mask.any() else np.nan,
            "calibration_from": str(calibration_from.date()), "calibration_to": str(cutoff.date()),
            "calibration_n": int(calibration_mask.sum()),
            "evaluation_from": str(origin.date()), "evaluation_to": str(end.date()),
            "evaluation_n": int(evaluation_mask.sum()), "evaluation_positive90": int(labels[evaluation_mask].sum()),
            "evaluation_rate90": float(labels[evaluation_mask].mean()*100) if evaluation_mask.any() else np.nan,
            "labels_ready_on": str(ready.date()), "maturity_gap_days": 90,
        })
    return pd.DataFrame(rows)


def profile_action_counts(chunk):
    parts = []
    for field, selected in [("action_detail", PROFILE_UPDATE_DETAILS), ("action", PROFILE_ACTION_NAMES)]:
        chosen = chunk.user_id.notna() & chunk[field].isin(selected)
        if chosen.any():
            table = chunk.loc[chosen, ["user_id", field]].rename(columns={field: "value"})
            counts = table.groupby(["user_id", "value"], sort=False).size().reset_index(name="event_n")
            counts["field"] = field
            parts.append(counts[["user_id", "field", "value", "event_n"]])
    return parts


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
    for target, label in [("observed_booking", "Nhãn y hiện có"), ("y90", "Nhãn y90 · giả định theo dõi ít nhất 90 ngày")]:
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


def indirect_profile_evidence(report, recent):
    signup = rates_two_targets(recent, ["signup_method", "age_missing", "gender_unknown"])
    signup["within_method_pct"] = signup.n / signup.groupby("signup_method").n.transform("sum") * 100
    signup["within_profile_pct"] = signup.n / signup.groupby(["age_missing", "gender_unknown"]).n.transform("sum") * 100
    cohorts = []
    cutoff = pd.to_datetime(report.airbnb_context["train"].date_first_booking).max()
    for source, data in [("Train", report.airbnb_context["train"]), ("Test", report.airbnb_context["test"])]:
        frame = data.assign(month=pd.to_datetime(data.date_account_created).dt.to_period("M").astype(str),
                            age_missing=data.age.isna(), gender_unknown=data.gender.eq("-unknown-"))
        table = frame.groupby("month").agg(n=("id", "size"), age_missing_pct=("age_missing", "mean"), gender_unknown_pct=("gender_unknown", "mean")).reset_index()
        table[["age_missing_pct", "gender_unknown_pct"]] *= 100
        table.insert(0, "source", source)
        table["days_from_month_end_to_proxy_cutoff"] = [(cutoff - pd.Period(month).end_time.normalize()).days for month in table.month]
        cohorts.append(table)
    cohorts = pd.concat(cohorts, ignore_index=True)
    counts = getattr(report, "profile_action_counts", pd.DataFrame(columns=["user_id", "field", "value", "event_n"]))
    joined = counts.merge(recent[["id", "y90", "age_missing", "gender_unknown"]], left_on="user_id", right_on="id", how="inner", validate="many_to_one")
    actions = []
    for (field, value), group in joined.groupby(["field", "value"], sort=True):
        actions.append([field, value, len(group), int(group.event_n.sum()), float(group.y90.mean()*100),
                        group.age_missing.mean()*100, group.gender_unknown.mean()*100,
                        "Chi tiết chỉnh sửa/cập nhật hồ sơ" if field == "action_detail" else "Tên hành động rộng, cần đối chiếu nghiệp vụ"])
    actions = pd.DataFrame(actions, columns=["Trường", "Tên ghi nhận", "Số người năm 2014", "Số sự kiện", "Tỷ lệ y90=1 (%)", "Thiếu tuổi (%)", "Không rõ giới tính (%)", "Cách chọn ứng viên"])
    strict_users = set(joined.loc[joined.field.eq("action_detail"), "user_id"])
    # Denominators include all 2014 users with logs, not only those who updated.
    log_users = set(report.airbnb_context["session_user_ids"])
    logs = recent[recent.id.isin(log_users)].assign(profile_update=lambda x: x.id.isin(strict_users))
    strata = []
    for (missing_age, missing_gender), group in logs.groupby(["age_missing", "gender_unknown"]):
        strata.append([missing_age, missing_gender, len(group), int(group.profile_update.sum()), group.profile_update.mean()*100,
                       float(group.loc[group.profile_update,"y90"].mean()*100) if group.profile_update.any() else np.nan,
                       float(group.loc[~group.profile_update,"y90"].mean()*100) if (~group.profile_update).any() else np.nan])
    strata = pd.DataFrame(strata, columns=["Thiếu tuổi", "Không rõ giới tính", "Người có nhật ký", "Có ứng viên cập nhật hồ sơ", "Tỷ lệ có ứng viên cập nhật (%)", "y90=1 · có ứng viên cập nhật (%)", "y90=1 · còn lại (%)"])
    return signup, cohorts, actions, strata


def followup_evidence(train, account, labels, lag):
    from scripts.build_descriptive_reports import wilson
    rows = []
    for month in sorted(account[account.dt.year.eq(2014)].dt.to_period("M").unique()):
        chosen = account.dt.to_period("M").eq(month)
        valid = chosen & train.country_destination.ne("NDF") & lag.ge(0)
        n, within = int(valid.sum()), int((valid & lag.le(90)).sum())
        lo, hi = wilson(within, n)
        rows.append([str(month), int(chosen.sum()), n, within, within/n*100, float(lo), float(hi)])
    monthly = pd.DataFrame(rows, columns=["Tháng đăng ký", "Người dùng", "Người đã đặt chỗ · độ trễ hợp lệ", "Đặt chỗ trong 90 ngày", "Trong 90 ngày trên nhóm đã đặt chỗ (%)", "Cận dưới Wilson 95% (%)", "Cận trên Wilson 95% (%)"])
    cutoff = pd.to_datetime(train.date_first_booking).max()
    gaps = (cutoff-account).dt.days
    calendar = pd.DataFrame([[str(cutoff.date()), days, int(gaps.ge(days).sum()), len(train), gaps.ge(days).mean()*100]
                             for days in [90,365]], columns=["Ngày kết thúc giả định chung", "Khoảng lịch tối thiểu (ngày)", "Số người có đủ khoảng lịch", "Mẫu số", "Tỷ lệ (%)"])
    eligible = labels.notna()
    source_ndf = train.country_destination.eq("NDF") & eligible
    positive = int(labels.eq(1).sum())
    sensitivity = []
    for name, scope in [("Mọi NDF", source_ndf), ("Chỉ NDF đăng ký năm 2014", source_ndf & account.dt.year.eq(2014))]:
        for q in [0., .01, .05, .10]:
            extra = int(scope.sum())*q
            sensitivity.append([name, q*100, int(scope.sum()), int(eligible.sum()), positive, extra,
                                (positive+extra)/eligible.sum()*100])
    sensitivity = pd.DataFrame(sensitivity, columns=["Phạm vi sai nhãn giả định", "NDF có đặt chỗ 90 ngày chưa ghi nhận (%)", "NDF chịu tác động", "Mẫu người dùng giữ cố định", "Dương tính đã ghi nhận", "Dương tính bổ sung kỳ vọng", "Tỷ lệ dương kỳ vọng (%)"])
    return monthly, calendar, sensitivity


def timeline_with_embargo(report):
    import matplotlib.dates as mdates
    from matplotlib.patches import Patch
    table = report.airbnb_evidence["protocol"]
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2, 1]}, layout="constrained")
    for ax, rows, left in [(axes[0], table, "2009-12-01"), (axes[1], table[table.role.eq("đánh giá cuối")], "2013-07-01")]:
        for pos, row in enumerate(rows.itertuples(index=False)):
            start, end = pd.Timestamp(row.train_from), pd.Timestamp(row.train_to)+pd.Timedelta(days=1)
            origin = pd.Timestamp(row.prediction_origin)
            evaluation_end = pd.Timestamp(row.evaluation_to)+pd.Timedelta(days=1)
            ax.broken_barh([(mdates.date2num(start), (end-start).days)], (pos-.3, .6), facecolors="#245D80")
            ax.broken_barh([(mdates.date2num(end), (origin-end).days)], (pos-.3, .6), facecolors="#eeeeee", edgecolors="#909090", hatch="///")
            cfrom = pd.Timestamp(row.calibration_from)
            ax.broken_barh([(mdates.date2num(cfrom), (end-cfrom).days)], (pos-.25, .5), facecolors="none", edgecolors="#C76A37", linewidth=2)
            ax.broken_barh([(mdates.date2num(origin), (evaluation_end-origin).days)], (pos-.3,.6), facecolors="#8A6598" if row.role=="đánh giá cuối" else "#468477")
            ax.annotate(f"học n={row.train_n:,}", (mdates.date2num(pd.Timestamp("2014-08-01")), pos), va="center", fontsize=9)
        ax.set_yticks(range(len(rows)), [f"{r.prediction_origin} · {r.role}" for r in rows.itertuples()])
        ax.invert_yaxis()
        ax.set_xlim(mdates.date2num(pd.Timestamp(left)), mdates.date2num(pd.Timestamp("2014-12-01")))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6 if ax is axes[0] else 2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
        ax.grid(axis="x", alpha=.2)
    axes[0].set_title("Mỗi mốc tháng: học trên toàn bộ nhãn đã hoàn tất, dự đoán trong tháng đó")
    axes[1].set_title("Hai mốc cuối: mẫu hiệu chỉnh OOF nằm trong lịch sử đã có nhãn")
    axes[1].set_xlabel("Ngày tạo tài khoản")
    handles = [Patch(facecolor="#245D80",label="Toàn bộ nhãn đã hoàn tất"), Patch(facecolor="#468477",label="Tháng phát triển"),
               Patch(facecolor="#8A6598",label="Tháng đánh giá cuối"), Patch(facecolor="#eeeeee",hatch="///",label="Nhãn chưa hoàn tất"),
               Patch(facecolor="none",edgecolor="#C76A37",label="Nhãn có dự đoán OOF để hiệu chỉnh")]
    axes[1].legend(handles=handles, loc="upper center", bbox_to_anchor=(.5, -.25), ncol=2, frameon=False)
    return report.savefig("evaluation_timeline", fig)


def apply_research_revision(report):
    from scripts.airbnb_report_presentation import capture_evidence, walk_sections
    from scripts.eda_diagnostics import section
    context = report.airbnb_context
    train, account, frame = context["train"], context["account"], context["frame"]
    labels, lag = conditional_labels(train, account)
    no_assumption, _ = conditional_labels(train, account, assume_followup_90=False)
    recent, gender, age, overlap, apps, profile_summary, contrast = profile_evidence(train, account, labels)
    protocol = protocol_90(train, account, labels)
    context["session_user_ids"] = report.session_user_ids
    signup, cohort_missing, profile_actions, update_strata = indirect_profile_evidence(report, recent)
    monthly_coverage, calendar_followup, sensitivity = followup_evidence(train, account, labels, lag)
    cells = overlap.set_index(["age_missing", "gender_unknown"])
    for flags, name in [((False,True), "Có tuổi, không rõ giới tính · y90 (%)"), ((False,False), "Có tuổi, có khai báo giới tính · y90 (%)"),
                        ((True,False), "Thiếu tuổi, có khai báo giới tính · y90 (%)"), ((True,True), "Thiếu cả hai thông tin · y90 (%)")]:
        profile_summary[name] = cells.loc[flags, "rate90"]
    positive, eligible, unknown = int(labels.eq(1).sum()), int(labels.notna().sum()), int(labels.isna().sum())
    source_positive = train.country_destination.ne("NDF")
    summary90 = pd.DataFrame([{
        "Giả định theo dõi tối thiểu (ngày)": 90, "Thời hạn (ngày)": 90,
        "Toàn bộ người dùng": len(train), "Dương tính y90": positive,
        "Âm tính y90 có điều kiện": int(labels.eq(0).sum()), "Chưa gán nhãn": unknown,
        "Mẫu hợp lệ": eligible, "Dương tính trên toàn bộ dòng (%)": positive/len(train)*100,
        "Dương tính trên mẫu hợp lệ (%)": positive/eligible*100,
    }])
    construction = pd.DataFrame([
        ["Đã đặt chỗ, độ trễ từ 0 đến 90 ngày", int((source_positive & lag.between(0,90)).sum()), "1", "Đã quan sát lượt đặt chỗ trong thời hạn"],
        ["Đã đặt chỗ, độ trễ lớn hơn 90 ngày", int((source_positive & lag.gt(90)).sum()), "0", "Lượt đặt chỗ đầu tiên xảy ra sau thời hạn"],
        ["NDF", int((~source_positive).sum()), "0 có điều kiện", "Cần theo dõi đủ ít nhất 90 ngày, không cần đủ 365 ngày"],
        ["Ngày đặt chỗ âm hoặc không xác định", unknown, "Chưa gán", "Loại khỏi mẫu nghiên cứu 90 ngày cho đến khi xác minh"],
    ], columns=["Trường hợp", "Số người dùng", "Nhãn y90", "Căn cứ"])
    observed_limits = pd.DataFrame([
        ["Giả định mọi người được theo dõi ít nhất 90 ngày", positive, int(labels.eq(0).sum()), unknown, eligible],
        ["Chỉ dùng bằng chứng lượt đặt chỗ đã ghi nhận", int(no_assumption.eq(1).sum()), int(no_assumption.eq(0).sum()), int(no_assumption.isna().sum()), int(no_assumption.notna().sum())],
    ], columns=["Phạm vi mô tả", "Dương tính", "Âm tính có căn cứ trong phạm vi", "Chưa xác định", "Mẫu gán được nhãn"])
    by_key = {item["key"]: item for item in walk_sections(report.sections)}
    delay = by_key["booking_delay"]
    delay["text"] = delay["text"].split("Ngày đặt chỗ muộn nhất")[0] + """Nhãn y90 chỉ yêu cầu được theo dõi ít nhất 90 ngày. Giới hạn độ trễ 365 ngày trong các nhóm năm là bằng chứng về cấu trúc dữ liệu, không phải điều kiện cần của y90 và không chứng minh mọi NDF đã được theo dõi một năm.

Báo cáo gán y90 dưới giả định NDF được theo dõi đủ 90 ngày. Với mốc kết thúc chung giả định 2015-06-29, toàn bộ train có khoảng lịch ít nhất 90 ngày, còn khoảng 99.72% có đủ 365 ngày. Mốc này chỉ là phép kiểm tra lịch có điều kiện, không phải ngày theo dõi thực tế đã xác nhận cho từng người.

Nhãn y90 bằng 1 khi độ trễ đặt chỗ từ 0 đến 90 ngày, gồm cả hai đầu. Các lượt đặt chỗ sau ngày 90 có nhãn 0. NDF chỉ có nhãn 0 dưới giả định theo dõi tối thiểu trên. Ngoại lệ ngày đặt chỗ âm chưa được gán. Nhóm chỉ gồm người đã đặt chỗ có thể mô tả phần nhãn quan sát được nhưng bị chọn theo kết quả, nên không được dùng làm tập huấn luyện hoặc gọi là phân tích độ nhạy."""
    delay["tables"].extend([("B9 · Nhãn y90 dưới giả định theo dõi ít nhất 90 ngày", summary90),
                            ("Quy tắc gán nhãn 90 ngày và số lượng", construction)])
    profile_text = f"""Trong nhóm đăng ký năm 2014, tỷ lệ có nhãn y=1 của FEMALE và MALE gần bằng nhau, lần lượt {profile_summary.iloc[0,1]:.2f}% và {profile_summary.iloc[0,2]:.2f}%. Nhóm không rõ giới tính chỉ đạt {profile_summary.iloc[0,3]:.2f}%. Vì vậy, liên hệ biên của cột giới tính chủ yếu phản ánh sự khác nhau giữa hồ sơ có và thiếu thông tin, không nên trình bày như một hiệu ứng riêng của giới tính.

Cờ thiếu tuổi và cờ không rõ giới tính có Cramér V={profile_summary['V giữa hai cờ thiếu hồ sơ'].iloc[0]:.3f}. Tuy vậy, nhóm có tuổi nhưng không rõ giới tính có y90={cells.loc[(False,True),'rate90']:.2f}%, cao hơn nhóm có cả tuổi và khai báo giới tính ({cells.loc[(False,False),'rate90']:.2f}%). Bốn ô không tăng đơn điệu theo số thông tin được điền. Vì vậy, báo cáo không diễn giải hai cờ thành một thang mức độ đầy đủ hồ sơ.

Một cơ chế có thể là luồng đăng ký khác nhau hoặc hồ sơ được bổ sung khi đặt chỗ. Các bảng phương thức đăng ký, nhóm thời gian gồm cả test và ứng viên cập nhật hồ sơ trong nhật ký kiểm tra gián tiếp các giả thuyết này. Chúng không xác định được thời điểm điền tuổi hay giới tính vì CSV thiếu lịch sử hồ sơ và nhật ký không có thời điểm sự kiện. Hai cờ nằm ngoài nhánh chính; chỉ được đưa vào nhánh có điều kiện khi Q1 có bằng chứng xác nhận.

Bảng và hình dưới tách đồng thời năm đăng ký, tình trạng thiếu tuổi và tình trạng không rõ giới tính trước khi so sánh ứng dụng. Chúng báo cả nhãn y hiện có và nhãn y90 có điều kiện. Các khoảng Wilson dành cho tỷ lệ y90 trong từng ô, với n<100 được đánh dấu. Giá trị tuổi và các cờ thiếu vẫn phải được xác minh là có sẵn tại t0."""
    signup_lookup = signup.set_index(["signup_method", "age_missing", "gender_unknown"])
    basic_unknown, basic_known = signup_lookup.loc[("basic",False,True)], signup_lookup.loc[("basic",False,False)]
    basic_missing, facebook_missing = signup_lookup.loc[("basic",True,True)], signup_lookup.loc[("facebook",True,True)]
    recent_cohorts = cohort_missing[cohort_missing.source.eq("Train") & cohort_missing.month.ge("2014-01")]
    test_cohorts = cohort_missing[cohort_missing.source.eq("Test")]
    log_n, update_n = int(update_strata.iloc[:,2].sum()), int(update_strata.iloc[:,3].sum())
    profile_text += f"""\n\n**Kết quả kiểm tra gián tiếp:** trong năm 2014, nhóm thiếu cả hai thông tin chiếm {basic_missing.within_method_pct:.2f}% người đăng ký basic, so với {facebook_missing.within_method_pct:.2f}% qua facebook (B12). Cơ cấu luồng đăng ký vì vậy là một lời giải thích cần kiểm tra. Tuy nhiên, ngay trong basic, nhóm có tuổi nhưng không rõ giới tính vẫn có y90={basic_unknown.rate90:.2f}%, so với {basic_known.rate90:.2f}% ở nhóm có cả hai thông tin. Tách cách đăng ký chưa giải thích hết chênh lệch.

Tỷ lệ không rõ giới tính ở train tháng 1–6/2014 nằm trong {recent_cohorts.gender_unknown_pct.min():.2f}–{recent_cohorts.gender_unknown_pct.max():.2f}%, còn test tháng 7–9/2014 là {test_cohorts.gender_unknown_pct.min():.2f}–{test_cohorts.gender_unknown_pct.max():.2f}% (B13). Test mới hơn có tỷ lệ thiếu cao hơn, nhưng cơ cấu đăng ký và quá trình thu thập cũng có thể thay đổi. So sánh này chưa tách được các cơ chế.

Trong {log_n:,} người đăng ký năm 2014 có nhật ký, {update_n:,} người ({update_n/log_n*100:.2f}%) có ít nhất một chi tiết hành động thuộc nhóm chỉnh sửa/cập nhật hồ sơ (B14 và bảng giao cờ bên cạnh). Mỗi người chỉ được đếm một lần trong tổng này. Các tên hành động rộng được báo riêng. Nhật ký cho thấy có hoạt động liên quan đến hồ sơ, nhưng không cho biết đó có phải thay đổi tuổi/giới tính hay xảy ra trước hoặc sau đăng ký/đặt chỗ. Do đó, Q1 vẫn chặn nhánh B."""
    profile_display = pd.DataFrame([[name, str(int(value)) if name == "Năm đăng ký" else f"{value:.3f}" if name.startswith("V ") else f"{value:.2f}"]
                                    for name, value in profile_summary.iloc[0].items()], columns=["Chỉ tiêu", "Giá trị"])
    profile = section("profile_completeness", "Cơ chế thiếu hồ sơ và rủi ro về thời điểm có sẵn", profile_text,
                      [("B10 · Bốn nhóm hồ sơ và hai cờ liên hệ mạnh · năm 2014", profile_display)])
    by_key["multivariate_main"]["blocks"].insert(2, profile)
    by_key["appendix"]["blocks"].append(section("profile_details", "Chi tiết phân tầng theo giao hai cờ hồ sơ", "Mỗi hàng dùng người đăng ký năm 2014 trong nhóm tương ứng. Nhãn y và y90 là hai mục tiêu khác nhau. Các bảng giữ cỡ mẫu và khoảng Wilson của y90.",
        [("Giới tính khai báo · hai mục tiêu", gender), ("Tình trạng tuổi · hai mục tiêu", age), ("Giao hai cờ thiếu hồ sơ", overlap),
         ("B11 · Ứng dụng trong từng nhóm giao hai cờ hồ sơ", apps),
         ("B12 · Phương thức đăng ký và giao hai cờ hồ sơ", signup),
         ("B13 · Tỷ lệ thiếu theo tháng đăng ký gồm cả test", cohort_missing),
         ("B14 · Ứng viên chỉnh sửa hồ sơ trong nhật ký năm 2014", profile_actions),
         ("Ứng viên cập nhật hồ sơ theo giao hai cờ · mẫu số là người có nhật ký", update_strata)]))
    by_key["appendix"]["blocks"].append(section("observed_label_limits", "Giới hạn của phần nhãn quan sát được", "Hàng chỉ có người đã đặt chỗ bị chọn theo kết quả. Nó là phạm vi mô tả nhãn, không phải tập huấn luyện hay kịch bản độ nhạy.", [("Phạm vi nhãn có thể mô tả từ dữ liệu", observed_limits)]))
    followup = section("followup_checks", "Theo dõi 90 ngày: bằng chứng theo tháng và độ nhạy giả định", "Tỷ lệ trong 90 ngày trên nhóm đã đặt chỗ được kiểm tra theo tháng để tìm dấu hiệu cắt cụt ở cuối train. Sự ổn định của tỷ lệ này chưa xác nhận thời gian theo dõi NDF. Phân tích độ nhạy giữ nguyên mẫu người dùng: giả sử một tỷ lệ NDF có đặt chỗ 90 ngày chưa được ghi nhận, rồi tính khoảng thay đổi tỷ lệ dương. Tham số này chưa được ước lượng từ dữ liệu. Các kết quả không phải nhãn thật mới, không dùng huấn luyện và chưa đánh giá độ nhạy của chất lượng mô hình.",
                       [("B15 · Mức bao phủ 90 ngày theo tháng trên nhóm đã đặt chỗ", monthly_coverage),
                        ("Khoảng lịch theo một ngày kết thúc chung giả định", calendar_followup),
                        ("B16 · Độ nhạy với sai nhãn NDF trên cùng mẫu người dùng", sensitivity)])
    followup["text"] += f"\n\nB15 cho thấy tỷ lệ trong 90 ngày trên người đã đặt chỗ ở tháng 1–6/2014 nằm trong {monthly_coverage.iloc[:,4].min():.2f}–{monthly_coverage.iloc[:,4].max():.2f}%. Tỷ lệ không giảm dần về cuối train, nên chưa thấy dấu hiệu cắt cụt từ phép kiểm tra này. B16 kiểm tra giả định khác: nếu có đặt chỗ sớm chưa được ghi nhận trong NDF, tỷ lệ dương thay đổi ra sao khi vẫn giữ nguyên {eligible:,} người. Đây là độ nhạy của tỷ lệ nhãn với sai nhãn giả định, chưa phải độ nhạy của chất lượng dự đoán."
    by_key["multivariate_main"]["blocks"].insert(1, followup)
    plot_followup_and_cohorts(report, monthly_coverage, cohort_missing, followup)
    plot_profiles(report, recent, apps, profile)
    by_key["signal"]["text"] += "\n\nCramér V của giới tính và cờ thiếu tuổi không được xem là hai bằng chứng dự báo độc lập. Phần cơ chế thiếu hồ sơ bên dưới định lượng mức chồng lặp và tách chênh lệch ứng dụng trong từng nhóm hồ sơ."
    risk = by_key["risks"]
    risk["text"] = """Nhãn y90 dùng giả định theo dõi NDF ít nhất 90 ngày. Rủi ro đầu vào được quản lý bằng nhánh chính không dùng tuổi, giới tính hoặc cờ thiếu hồ sơ. Dữ liệu hiện tại chỉ xác nhận trực tiếp mốc tạo tài khoản; mọi mở rộng cần bằng chứng về sự kiện gốc tại t0. Hai cờ hồ sơ và các thuộc tính có thể cập nhật chỉ nằm trong nhánh có điều kiện. Chưa có mô hình nào được chấp nhận hoặc triển khai."""
    suitability = risk["tables"][0][1]
    suitability.loc[suitability.criterion.eq("Nhãn tin cậy"), ["status", "remaining_condition"]] = ["Nghiên cứu y90 có điều kiện", "Cần theo dõi ít nhất 90 ngày; kiểm tra theo tháng và độ nhạy sai nhãn NDF. Loại 29 ngoại lệ khỏi mẫu y90."]
    suitability.loc[suitability.criterion.eq("Đủ tín hiệu"), ["evidence_in_report", "status"]] = ["Bốn nhóm giao cờ có tỷ lệ y90 không đơn điệu; chênh lệch ứng dụng còn sau phân tầng. Chưa đo chất lượng ngoài thời gian.", "Có giả thuyết để kiểm tra, chưa xác nhận đầu vào tại t0"]
    suitability.loc[suitability.criterion.eq("Đủ tín hiệu"), "remaining_condition"] = "Kiểm tra giá trị bổ sung so với Logistic Regression mạnh. Các chỉ báo thiếu hồ sơ có liên hệ chồng lặp, không được cộng bằng chứng độc lập."
    questions = by_key["open_questions"]["tables"][0][1]
    questions.iloc[0, 4] = "Đối chiếu B12–B14 về luồng đăng ký, độ mới của nhóm train/test và ứng viên cập nhật hồ sơ. Đây là kiểm tra gián tiếp; để đóng Q1 cần lịch sử hồ sơ hoặc tài liệu sự kiện xác nhận từng giá trị có trước t0."
    questions.iloc[0, 5] = "Nhánh chính không dùng hai cờ hồ sơ. Nhánh có tuổi/giới tính/cờ chỉ được fit sau khi có bằng chứng Q1. Mọi cột khác cũng cần kiểm tra khả dụng; không suy từ tên cột thành bằng chứng đã xác nhận."
    questions.iloc[2, 4] = "Đối chiếu B15 theo tháng và mốc lịch giả định; tìm tài liệu xác nhận NDF được theo dõi ít nhất 90 ngày. Không yêu cầu mọi người đủ 365 ngày."
    questions.iloc[2, 5] = "Cho phép nghiên cứu có điều kiện trên giả định tối thiểu 90 ngày; trước triển khai phải xác nhận cơ chế theo dõi. Độ nhạy B16 giữ nguyên mẫu người dùng, không chọn riêng người đã đặt chỗ."
    questions.iloc[2, 6] = "Giả thuyết được dữ liệu ủng hộ; đã dùng làm giả định nghiên cứu, chưa xác nhận chính thức"
    by_key["open_questions"]["text"] += "\n\nB15 chưa cho thấy mức bao phủ 90 ngày giảm ở cuối train trong người đã đặt chỗ. Điều này chưa xác nhận theo dõi NDF. Giả định tối thiểu 90 ngày được công khai và B16 định lượng độ nhạy sai nhãn trên cùng mẫu; xác nhận cơ chế vẫn cần trước triển khai."
    by_key["implications"]["tables"][0][1].iloc[0, 1:3] = ["Nghiên cứu y90 dưới giả định theo dõi ít nhất 90 ngày", "Kiểm tra tháng và độ nhạy sai nhãn NDF trên cùng mẫu người dùng"]
    problem = by_key["problem"]
    problem["text"] = """Bài toán nghiên cứu chính là ước lượng xác suất người dùng mới có lượt đặt chỗ đầu tiên trong 90 ngày kể từ lúc đăng ký. Thời điểm dự đoán t0 là ngay sau khi tạo tài khoản.

Nhãn y90 được xây dựng dưới giả định NDF được theo dõi ít nhất 90 ngày. Cột điểm đến gốc vẫn xác định nhãn y để mô tả bộ dữ liệu; y và y90 là hai mục tiêu khác nhau. Thiết kế mô hình và bảng B7 dùng y90. Quy tắc và mẫu số nằm ở B9.

Thông tin đầu vào chỉ hợp lệ nếu phản ánh hồ sơ tại t0. Các cột ngày đặt chỗ, cờ thiếu ngày đặt chỗ và nhật ký chưa có thời điểm sự kiện bị loại khỏi thiết kế chính. Các ngoại lệ ngày đặt chỗ âm được giữ trong EDA nhãn y nhưng chưa gán y90."""
    glossary = by_key["glossary"]["tables"][0][1]
    by_key["glossary"]["text"] = by_key["glossary"]["text"].replace("“nhãn y” cho mục tiêu nhị phân và", "“nhãn y” cho kết quả gốc, “nhãn y90” cho mục tiêu nghiên cứu 90 ngày và")
    glossary.loc[len(glossary)] = ["Nhãn y90", "1 nếu độ trễ từ 0 đến 90 ngày; 0 nếu muộn hơn hoặc NDF dưới giả định theo dõi ít nhất 90 ngày. Ngoại lệ ngày âm chưa gán."]
    glossary.loc[len(glossary)] = ["Nhãn đã hoàn tất tại mốc tháng", "Chỉ dùng người có ngày đăng ký + 90 ngày nhỏ hơn mốc dự đoán. Mô hình tại mỗi mốc học trên toàn bộ nhãn hợp lệ đã hoàn tất."]
    glossary.loc[len(glossary)] = ["LR (Logistic Regression)", "Hồi quy logistic, mô hình đối chứng ước lượng xác suất. Phiên bản có tương tác cặp cho phép ảnh hưởng của một biến thay đổi theo biến khác."]
    glossary.loc[len(glossary)] = ["OOF theo thời gian", "Dự đoán ngoài tập học: mô hình tạo điểm cho một người chỉ học nhãn đã sẵn có trước mốc lịch sử của người đó. Người được chấm không thuộc tập học tạo điểm."]
    glossary.loc[len(glossary)] = ["Hiệu chỉnh xác suất", "Điều chỉnh điểm dự đoán để xác suất phù hợp hơn với tỷ lệ thực tế, dùng dữ liệu ngoài tập học của mô hình tạo điểm."]
    glossary.loc[len(glossary)] = ["ECE", "Sai lệch hiệu chỉnh kỳ vọng: chia dự đoán thành các nhóm, lấy trung bình có trọng số của chênh lệch tuyệt đối giữa xác suất trung bình và tỷ lệ dương từng nhóm. Thiết kế dùng 10 nhóm đồng số mẫu."]
    revise_research_design(report, by_key, contrast)
    revise_executive(report, by_key, summary90, profile_summary, apps)
    report.facts.update({"research_revision": REVISION, "primary_target": "conditional_first_booking_within_90_days_assuming_minimum_90_day_followup",
                         "followup_assumption_days": 90, "conditional_90_positive": positive,
                         "conditional_90_eligible": eligible, "conditional_90_unassigned": unknown,
                         "conditional_90_rate_pct": positive/eligible*100, "conditional_90_fraction_all_rows_pct": positive/len(train)*100,
                         "age_gender_missing_cramers_v_2014": float(profile_summary['V giữa hai cờ thiếu hồ sơ'].iloc[0]),
                         "label_maturity_days": 90, "main_t0_columns": list(MAIN_T0_COLUMNS),
                         "development_monthly_origins": 6, "final_monthly_origins": 2})
    report.facts["base_evidence_fingerprint"] = report.facts["statistical_fingerprint"]
    capture_evidence(report, {**report.airbnb_evidence, "protocol": protocol, "conditional_label_summary": summary90,
                             "conditional_label_rules": construction, "conditional_label_sensitivity": sensitivity,
                             "profile_summary": profile_summary, "profile_overlap": overlap, "profile_apps": apps,
                             "descriptive_baseline_contrast": contrast, "signup_profile": signup, "cohort_missing_train_test": cohort_missing,
                             "profile_action_audit": profile_actions, "profile_update_strata": update_strata,
                             "monthly_observed_coverage": monthly_coverage, "calendar_followup": calendar_followup})
    report.research_tables = {"B9": summary90, "B10": profile_display, "B11": apps,
                              "B15": monthly_coverage, "B16": sensitivity, "B17": by_key["algorithms"]["tables"][0][1]}
    report.airbnb_context["y90"] = labels


def plot_profiles(report, recent, apps, section):
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.4), layout="constrained")
    overlap = rates_two_targets(recent, ["age_missing", "gender_unknown"])
    axes[0].errorbar(overlap.rate90, range(len(overlap)),
                    xerr=np.vstack([overlap.rate90-overlap.lower90, overlap.upper90-overlap.rate90]),
                    fmt="o", capsize=4, color="#C76A37")
    axes[0].set_yticks(range(len(overlap)), [f"{'Thiếu tuổi' if r.age_missing else 'Có tuổi'} / {'không rõ giới tính' if r.gender_unknown else 'có giới tính'}\nn={r.n90:,}" for r in overlap.itertuples()])
    axes[0].set(xlim=(0,100), xlabel="Có lượt đặt chỗ trong 90 ngày (%)", title="Bốn nhóm hồ sơ không tạo thành một thang đơn điệu")
    axes[0].grid(axis="x", alpha=.2)
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
        "**Quan sát:** có tuổi nhưng không rõ giới tính là nhóm có tỷ lệ y90 cao nhất, vượt nhóm có cả hai thông tin. Chênh lệch ứng dụng còn trong nhóm có tuổi và có khai báo giới tính.\n\n"
        "**Phạm vi và cách đọc:** cả hai hình dùng y90 dưới giả định theo dõi NDF ít nhất 90 ngày và khoảng Wilson 95%. Bảng B11 giữ cả bốn nhóm giao cờ. "
        "Đây là phân tầng mô tả, chưa kiểm soát mọi khác biệt và chưa xác nhận thông tin có sẵn tại t0."
    )


def plot_followup_and_cohorts(report, monthly, cohorts, section):
    fig, axes = plt.subplots(1,2,figsize=(15,5.2),layout="constrained")
    rate = monthly.iloc[:,4].to_numpy()
    axes[0].errorbar(monthly.iloc[:,0], rate, yerr=np.vstack([rate-monthly.iloc[:,5],monthly.iloc[:,6]-rate]),fmt="o-",capsize=4,color="#245D80")
    axes[0].set(title="Mức bao phủ 90 ngày trong người đã đặt chỗ",ylabel="Trong 90 ngày (%)",ylim=(70,95))
    axes[0].tick_params(axis="x",rotation=30)
    recent = cohorts[cohorts.month.ge("2013-07")]
    for source, style in [("Train","-"),("Test","--")]:
        data = recent[recent.source.eq(source)]
        for field, label, color in [("age_missing_pct","Thiếu tuổi","#245D80"),("gender_unknown_pct","Không rõ giới tính","#C76A37")]:
            axes[1].plot(data.month,data[field],style,marker="o",color=color,label=f"{label} · {source}")
    axes[1].set(title="Thiếu hồ sơ theo tháng, gồm test không có nhãn",ylabel="Người dùng trong tháng (%)",ylim=(25,70))
    axes[1].tick_params(axis="x",rotation=60,labelsize=8)
    axes[1].legend(fontsize=8)
    path=report.savefig("followup_profile_cohorts",fig)
    section["figures"]=[path]
    report.figure_notes[path.name] = "**Quan sát:** mức bao phủ trong người đã đặt chỗ không giảm dần ở các tháng cuối train; tỷ lệ thiếu hồ sơ khác nhau giữa các tháng và giữa train/test.\n\n**Phạm vi và cách đọc:** hình trái chỉ có người đã đặt chỗ với độ trễ hợp lệ, nên chưa xác nhận theo dõi NDF. Hình phải dùng mọi người trong từng tháng, kể cả test không có nhãn. Mức độ mới của tháng và cơ cấu luồng đăng ký cùng thay đổi; không diễn giải xu hướng thành bằng chứng thời điểm cập nhật hồ sơ."


def revise_research_design(report, by_key, contrast):
    from scripts.eda_diagnostics import section
    branches = pd.DataFrame([
        ["A0 · Nhánh chính tối thiểu", "Ngày tạo tài khoản; các thông tin lịch suy ra từ t0", "Mốc tạo tài khoản có ngay khi sự kiện hoàn tất. Không dùng tuổi, giới tính, cờ thiếu, kênh hay nhật ký.", "Có thể đặc tả độc lập với Q1; chưa huấn luyện"],
        ["A1 · Mở rộng sự kiện đăng ký", "Cách đăng ký, luồng đăng ký, ứng dụng đăng ký", "Chỉ mở khi tài liệu hoặc hợp đồng dữ liệu xác nhận chúng được ghi tại sự kiện tạo tài khoản. CSV và tên cột chưa đủ chứng minh lịch sử bất biến.", "Chờ kiểm tra nguồn; nếu chưa xác nhận thì giữ A0"],
        ["B · Hồ sơ có điều kiện", "Tuổi, giới tính, hai cờ thiếu và các tương tác liên quan", "Q1 là điều kiện chặn. Cần lịch sử hoặc mô tả trích xuất xác nhận tại t0. Các bảng gián tiếp chưa đáp ứng điều kiện này.", "Không dùng trong nhánh chính khi Q1 còn mở"],
        ["C · Kênh/thiết bị có điều kiện", "Kênh tiếp cận, nhà cung cấp, thiết bị và các thuộc tính khác", "Chỉ thêm từng cột có bằng chứng tại t0; không mặc định mọi hồ sơ thô là thông tin đăng ký.", "Khai báo rõ danh sách cột được chấp nhận trước mỗi thí nghiệm"],
    ], columns=["Nhánh", "Thông tin", "Căn cứ và điều kiện", "Trạng thái hiện tại"])
    models = pd.DataFrame([
        ["Xác suất hằng", "Tỷ lệ y90 trong tập học tại mốc tháng", "Đối chứng cơ bản trong mỗi nhánh"],
        ["LR L2 · hiệu ứng chính", "Chỉ các cột đã được chấp nhận của nhánh", "Không dùng hai cờ để định nghĩa baseline chính khi Q1 chưa đóng"],
        ["LR L2 · tương tác cặp", "Các cột trên và one-hot cặp nhóm được chấp nhận", "A1: ứng dụng × cách/luồng đăng ký; B: cờ × ứng dụng, cờ × cờ; C: ứng dụng × kênh. Chỉ tạo cặp khi cả hai cột hợp lệ tại t0."],
        ["CatBoost", "Cùng nguồn thông tin được chấp nhận với LR", "Phải so với LR tốt nhất gồm cả cấu hình có tương tác; chọn bằng các tháng phát triển"],
        ["Hiệu chỉnh sigmoid từ OOF theo thời gian", "Dự đoán lịch sử ngoài tập học, có nhãn đã hoàn tất tại mốc hiện tại", "Áp dụng cùng quy trình cho LR và CatBoost; không hiệu chỉnh bằng dự đoán trong mẫu"],
    ], columns=["Ứng viên", "Thông tin sử dụng", "Vai trò và kiểm soát"])
    by_key["algorithms"]["text"] = """Thiết kế tách tính hợp lệ của đầu vào khỏi độ mạnh liên hệ. Nhánh chính A0 không phụ thuộc hồ sơ và hai cờ thiếu. A1 chỉ mở rộng bằng thông tin sự kiện đăng ký được xác nhận; B và C là nhánh có điều kiện. Không thể gọi một cột chắc chắn có tại t0 chỉ vì tên cột gợi ý như vậy. Mọi kết quả của B khi Q1 còn mở chỉ là phân tích mô tả, không thay thế đối chứng của A0/A1.

Trong mỗi nhánh hợp lệ, so sánh xác suất hằng, LR có hiệu ứng chính, LR có tương tác cặp và CatBoost. Các cặp ứng dụng × cờ và ứng dụng × kênh giúp LR biểu diễn chênh lệch đã thấy ở B11. Mã hóa cặp, xử lý nhóm hiếm và điều chuẩn L2 chỉ học/chọn trên lịch sử phát triển. Nếu one-hot giới tính đã chứa chỉ báo unknown thì không thêm một cột trùng hệt. CatBoost được so với LR tốt nhất trên cùng thông tin và cùng lịch đánh giá, không chỉ LR thiếu tương tác.

Chưa huấn luyện hoặc ước lượng chất lượng mô hình trong báo cáo. Phân tích entropy từ cờ hồ sơ được chuyển xuống phụ lục; nó không định nghĩa nhánh chính hoặc xác nhận tính khả dụng tại t0."""
    by_key["algorithms"]["tables"] = [("B17 · Các nhánh đầu vào và điều kiện tại t0", branches), ("Đối chứng có tương tác trong từng nhánh hợp lệ", models)]
    by_key["appendix"]["blocks"].append(section("profile_entropy_only", "Entropy hồ sơ: mô tả có điều kiện", "Đây là entropy và lift kỳ vọng trên cùng mẫu năm 2014, không phải kết quả kiểm định. Hai cờ chưa hợp lệ tại t0 khi Q1 còn mở, nên bảng không chứng minh một baseline có thể sử dụng. Không dùng bảng này để chọn hoặc chấp nhận nhánh chính.", [("Đối chiếu mô tả theo tình trạng thiếu tuổi", contrast)]))
    decisions = by_key["column_decisions"]["tables"][0][1]
    for column in ["age", "gender"]:
        mask = decisions["Cột gốc"].eq(column) & decisions["Bảng dữ liệu"].eq("Hồ sơ người dùng")
        decisions.loc[mask, "Quyết định cho thiết kế chính"] = "Ngoài nhánh chính; chỉ nhánh B sau xác nhận Q1, gồm cả cờ thiếu"
    for column in REGISTRATION_EXTENSION:
        decisions.loc[decisions["Cột gốc"].eq(column), "Quyết định cho thiết kế chính"] = "Nhánh A1 chỉ sau bằng chứng của sự kiện đăng ký; hiện chưa xác nhận từ CSV"
    by_key["column_decision_summary"]["tables"][0] = ("Tóm tắt quyết định sử dụng dữ liệu", decisions.groupby(["Bảng dữ liệu","Quyết định cho thiết kế chính"],sort=False).size().reset_index(name="Số cột"))
    by_key["evaluation"]["text"] = """B7 thay các cửa sổ không đều bằng mốc dự đoán đầu mỗi tháng. Sáu tháng 7–12/2013 phục vụ phát triển; các nhãn này đã hoàn tất trước khi chốt cấu hình vào 2014-05-01. Hai tháng 5 và 6/2014 là các lượt đánh giá cuối. Báo điểm từng tháng và điểm gộp theo số người; không để một cửa sổ nhỏ riêng quyết định mô hình.

Tại mốc O, học lại trên mọi người có nhãn hợp lệ và ngày đăng ký + 90 ngày < O. Vì nhãn gồm ngày thứ 90 và CSV chỉ ghi ngày, thời điểm sẵn có là ngày đăng ký + 91 ngày. Tại 2014-05-01, dùng dữ liệu đăng ký đến 2014-01-30; tại 2014-06-01, dùng đến 2014-03-02. Chỉ người chưa hoàn tất nhãn bị loại khỏi tập học. Không giữ thêm khoảng đệm riêng giữa tập học cuối và dữ liệu hiệu chỉnh.

Hiệu chỉnh dùng dự đoán OOF theo thời gian của các nhóm đăng ký trong 90 ngày gần nhất đã hoàn tất nhãn tại O. Mỗi dự đoán OOF phải được tạo bởi mô hình chỉ học các nhãn đã có trước đầu tháng đăng ký của chính người đó; người đó không thuộc tập học tạo dự đoán. Bộ hiệu chỉnh sigmoid học trên các dự đoán lịch sử này, rồi áp dụng cho mô hình nền được học lại trên toàn bộ nhãn đã hoàn tất tại O. Nhãn hiệu chỉnh có thể nằm trong tập học của mô hình nền cuối; điều bắt buộc là điểm dùng học bộ hiệu chỉnh phải là OOF. Đây là thiết kế đề xuất, chưa sinh dự đoán OOF hay fit bộ hiệu chỉnh.

Độ dài cửa sổ, dạng tương tác, điều chuẩn và phương pháp hiệu chỉnh được chốt bằng các tháng phát triển trước 2014-05-01. Tháng 6 chỉ học lại với nhãn mới đã hoàn tất, không chỉnh cấu hình theo kết quả cuối tháng 5. Khi dự đoán tháng 6, nhãn tháng 5 chưa hoàn tất nên không được dùng. Cần kiểm tra sự chuyển đổi từ điểm OOF của mô hình cũ sang mô hình học lại trong các tháng phát triển; không giả định hiệu chỉnh tự chuyển giao hoàn hảo.

[Tài liệu hiệu chỉnh của scikit-learn](https://scikit-learn.org/stable/modules/calibration.html) mô tả dùng dự đoán ngoài tập học để học bộ hiệu chỉnh. Ở đây việc tạo điểm ngoài tập học phải tuân thủ mốc thời gian và độ trễ nhãn, thay vì chia ngẫu nhiên. Toàn bộ chất lượng và ngưỡng dưới đây còn phải được đo sau khi huấn luyện."""
    criteria = pd.DataFrame([
        ["Toàn vẹn và khả dụng · điều kiện chặn", "0 biến kết quả hoặc log chưa chứng minh trước t0; 0 thuộc tính/cờ chưa có bằng chứng tại t0 trong nhánh được fit; 0 ID giao giữa học và tháng dự đoán", "Q1 chưa đóng thì nhánh B không được fit hoặc dùng để thay thế nhánh chính. Chặn cả LR và CatBoost nếu vi phạm."],
        ["Thứ tự nhãn và hiệu chỉnh", "Mọi nhãn dùng học hoặc hiệu chỉnh phải hoàn tất trước O; mọi điểm học bộ hiệu chỉnh phải là OOF theo thời gian", "Loại 29 ngoại lệ khỏi y90; dùng toàn bộ nhãn hợp lệ đã hoàn tất, không chọn theo việc đặt chỗ sớm"],
        ["Xác suất · chuẩn bắt buộc cho mọi mô hình", "Sai lệch tuyệt đối giữa xác suất trung bình và tỷ lệ y90 ≤2 điểm phần trăm; ECE 10 nhóm đồng số mẫu ≤3 điểm phần trăm", "Áp dụng cho cả LR lẫn CatBoost sau hiệu chỉnh, trên từng tháng cuối n≥100 và tập gộp. Báo khoảng tin cậy và biểu đồ độ tin cậy. Nếu cả hai không đạt thì chưa có mô hình được chấp nhận."],
        ["Giá trị bổ sung · tiêu chí chính", "Log loss CatBoost giảm ít nhất 1% tương đối so với baseline LR mạnh đã chọn; cận trên 95% của chênh log loss (CatBoost − LR) < 0", "So sánh ghép cặp trên cùng người, cùng mẫu y90 và cùng hiệu chỉnh; bootstrap theo người dùng"],
        ["Ưu tiên top 20%", "Lift@20% tăng ít nhất 5% tương đối so với LR; cận dưới 95% của chênh lift > 0", "Ngân sách 20% và mức 5% là đề xuất nghiên cứu; ngưỡng tuyệt đối 1.20 chỉ còn là thông tin tham khảo"],
        ["Phân biệt và xác suất", "AP không thấp hơn LR trên điểm ước lượng; báo ROC-AUC, Brier và độ hiệu chỉnh cho cả hai", "Brier không kém LR quá 0.002 tuyệt đối; báo khoảng tin cậy của chênh lệch"],
        ["Độ bền và chồng lặp tín hiệu", "Báo chênh log loss với LR trong từng tháng và từng nhóm đủ/thiếu hồ sơ; kiểm tra bỏ từng cờ và ứng dụng", "Nếu giá trị bổ sung không ổn định hoặc không đạt, ưu tiên LR đơn giản hơn"],
    ], columns=["Tiêu chí", "Điều kiện chấp nhận đề xuất", "Cách diễn giải"])
    by_key["acceptance"]["text"] = """Trước tiên, mọi ứng viên phải qua điều kiện t0, thứ tự nhãn và chuẩn xác suất tuyệt đối. Sau đó mới xét giá trị bổ sung của CatBoost so với LR tốt nhất, gồm cả LR có tương tác, trong cùng nhánh hợp lệ. Nếu CatBoost không đạt, LR chỉ được dùng khi chính LR qua các điều kiện bắt buộc. Nếu không ứng viên nào đạt thì báo chưa có mô hình được chấp nhận. Các ngưỡng là đề xuất đặt trước, chưa phải kết quả đã đo hoặc chuẩn phổ quát."""
    by_key["acceptance"]["tables"] = [("Điều kiện để CatBoost được chấp nhận thay cho LR", criteria)]


def research_roles():
    return pd.DataFrame([
        ["Chọn cấu hình", "Mốc đầu tháng 7–12/2013", "Tổng hợp mọi tháng phát triển đã hoàn tất nhãn; chốt cấu hình, nhánh đầu vào và quy trình hiệu chỉnh trước 2014-05-01"],
        ["Học lại tại từng mốc", "2014-05-01 và 2014-06-01", "Dùng toàn bộ nhãn hợp lệ đã hoàn tất: đăng ký đến 2014-01-30 và 2014-03-02 tương ứng"],
        ["Hiệu chỉnh tại từng mốc", "Các nhóm đăng ký trong 90 ngày gần nhất đã hoàn tất nhãn", "Học từ dự đoán lịch sử OOF theo thời gian. Không cần chia thêm khoảng đệm giữa mẫu này và tập học nền cuối; không dùng điểm dự đoán trong mẫu."],
        ["Đánh giá cuối", "Tháng 5 và tháng 6/2014", "Chỉ cập nhật trọng số mô hình và bộ hiệu chỉnh bằng lịch sử có sẵn; không đổi cấu hình theo kết quả đánh giá cuối"],
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
        f"2. **Nhãn nghiên cứu 90 ngày có điều kiện:** có {int(target['Dương tính y90']):,} người đặt chỗ trong 90 ngày, bằng {target['Dương tính trên toàn bộ dòng (%)']:.2f}% toàn bộ {int(target['Toàn bộ người dùng']):,} dòng. Với giả định NDF được theo dõi ít nhất 90 ngày và loại {int(target['Chưa gán nhãn']):,} ngoại lệ chưa gán, mẫu còn {int(target['Mẫu hợp lệ']):,} người, tỷ lệ dương {target['Dương tính trên mẫu hợp lệ (%)']:.2f}%. Không cần giả định mọi người được theo dõi một năm.",
        f"3. **Hai cờ hồ sơ có cơ chế cần kiểm tra:** trong năm 2014, nhóm có tuổi nhưng không rõ giới tính có y90={prof['Có tuổi, không rõ giới tính · y90 (%)']:.2f}%, cao hơn nhóm có cả hai thông tin ({prof['Có tuổi, có khai báo giới tính · y90 (%)']:.2f}%). Bốn nhóm không tăng đơn điệu theo mức điền hồ sơ, dù hai cờ có V={prof['V giữa hai cờ thiếu hồ sơ']:.3f}. Chưa thể quy về một tín hiệu đầy đủ chung hoặc xác nhận thời điểm có sẵn. Chúng nằm ngoài nhánh chính và chỉ được dùng sau khi Q1 có bằng chứng.",
        f"4. **Chênh lệch ứng dụng theo đúng mục tiêu y90:** trong nhóm năm 2014 có tuổi và có khai báo giới tính, Web đạt {complete.loc['Web','rate90']:.2f}%, iOS {complete.loc['iOS','rate90']:.2f}% và Android {complete.loc['Android','rate90']:.2f}%. Các nhóm giao cờ khác có tương quan ứng dụng khác nhau; LR đối chứng phải có tương tác cặp khi các cột được chấp nhận tại t0. Các tỷ lệ này là mô tả, không phải chất lượng của nhánh chính.",
        last.replace("Tỷ lệ có đặt chỗ", "Tỷ lệ có nhãn y=1 gốc"),
    ]
    next_steps = [
        "1. **Chốt giả định theo dõi tối thiểu.** Xác nhận NDF được theo dõi ít nhất 90 ngày và giữ 29 ngoại lệ ngoài mẫu y90. Kiểm tra theo tháng và thay đổi giả định sai nhãn NDF trên cùng mẫu người dùng; không dùng riêng nhóm đã đặt chỗ làm độ nhạy hoặc tập học.",
        "2. **Chặn đầu vào chưa có bằng chứng tại t0.** Nhánh chính tối thiểu dùng mốc tạo tài khoản. Mở rộng từng cột sự kiện đăng ký sau khi có căn cứ nguồn; hai cờ hồ sơ thuộc nhánh B và bị chặn khi Q1 còn mở. Ngày đặt chỗ và cờ thiếu của cột này tiết lộ nhãn y ở 100% trường hợp nên luôn bị loại khỏi đầu vào.",
        "3. **Đánh giá tại từng mốc tháng.** Tại 2014-05-01 học đến ngày đăng ký 2014-01-30; tại 2014-06-01 học đến 2014-03-02. Mỗi mốc dùng toàn bộ nhãn đã hoàn tất và điểm OOF theo thời gian để hiệu chỉnh. So sánh LR có tương tác với CatBoost trên cùng nhánh; mọi ứng viên phải đạt chuẩn hiệu chỉnh tuyệt đối trước khi được chấp nhận.",
    ]
    by_key["executive"]["text"] = (
        "**Kết luận:** nghiên cứu y90 cần giả định NDF được theo dõi ít nhất 90 ngày. Thiết kế chính không phụ thuộc hai cờ hồ sơ chưa xác nhận tại t0, đánh giá theo nhiều mốc tháng và học trên toàn bộ nhãn đã hoàn tất ở từng mốc. (Nguồn: bảng B9, B17 và B7.)"
        + "\n\n**Năm phát hiện chính**\n\n" + "\n\n".join(findings)
        + "\n\n**Ba việc cần giải quyết trước khi huấn luyện**\n\n" + "\n\n".join(next_steps))
