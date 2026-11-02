"""Presentation and publication checks for the single Airbnb report."""
from __future__ import annotations

import hashlib
import json
import numbers
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

STAGE = 4

NAMES = {
    "id": "Định danh người dùng", "age": "Tuổi khai báo", "gender": "Giới tính khai báo",
    "language": "Ngôn ngữ", "signup_app": "Ứng dụng đăng ký", "signup_method": "Cách đăng ký",
    "signup_flow": "Luồng đăng ký", "affiliate_channel": "Kênh tiếp cận",
    "affiliate_provider": "Nhà cung cấp tiếp cận", "first_affiliate_tracked": "Tương tác tiếp cận đầu tiên",
    "first_device_type": "Thiết bị đầu tiên", "first_browser": "Trình duyệt đầu tiên",
    "age_group_eda": "Nhóm tuổi", "age_missing_eda": "Tình trạng thiếu tuổi",
    "date_account_created": "Ngày tạo tài khoản", "timestamp_first_active": "Thời điểm hoạt động đầu tiên",
    "date_first_booking": "Ngày đặt chỗ đầu tiên", "country_destination": "Điểm đến ghi nhận",
    "account_year": "Năm đăng ký", "account_month": "Tháng đăng ký",
    "has_sessions": "Có nhật ký hoạt động", "observed_booking": "Nhãn y",
    "action": "Hành động", "action_type": "Loại hành động", "action_detail": "Chi tiết hành động",
    "countries": "Bảng quốc gia", "age_gender_bkts": "Bảng tổng hợp tuổi và giới tính",
    "sessions": "Nhật ký hoạt động", "user_id": "Định danh trong nhật ký",
}

DISPLAY_HEADERS = {
    **NAMES, "item": "Nội dung", "description": "Mô tả", "dataset": "Bộ dữ liệu",
    "unit": "Đơn vị", "evidence": "Bằng chứng", "fit": "Mức phù hợp", "decision": "Quyết định",
    "check": "Nội dung kiểm tra", "n": "Số người dùng", "positive": "Số có nhãn y=1",
    "rate_pct": "Tỷ lệ đặt chỗ (%)", "ci95_low_pct": "Cận dưới 95% (%)", "ci95_high_pct": "Cận trên 95% (%)",
    "n_under_100": "Nhóm dưới 100 người", "variable": "Biến", "effect_metric": "Thước đo",
    "effect_all": "Liên hệ · toàn kỳ", "effect_2014": "Liên hệ · năm 2014",
    "n_all": "Cỡ mẫu · toàn kỳ", "n_2014": "Cỡ mẫu · năm 2014", "groups_all": "Số nhóm",
    "expected_cells_under_5_pct": "Ô có tần số kỳ vọng dưới 5 (%)", "p_chi2_or_mwu": "p-value",
    "q_bh_14_tests": "q sau điều chỉnh 14 phép so sánh",
    "criterion": "Tiêu chí", "predeclared_acceptance": "Điều kiện chấp nhận đề xuất",
    "interpretation": "Cách diễn giải", "candidate": "Ứng viên", "reason_from_eda": "Lý do từ EDA",
    "proposed_controls": "Điều kiện thực hiện", "status": "Trạng thái",
    "evidence_in_report": "Bằng chứng trong báo cáo", "remaining_condition": "Điều kiện còn lại",
    "column": "Cột gốc", "meaning": "Ý nghĩa", "role": "Vai trò", "role_or_caution": "Lưu ý",
    "pandas_dtype": "Kiểu dữ liệu", "distinct_nonnull": "Số giá trị khác nhau không thiếu",
    "missing_n": "Số thiếu", "missing_pct": "Tỷ lệ thiếu (%)",
    "observed_domain_and_basis": "Miền giá trị và căn cứ", "in_train": "Có trong train", "in_test": "Có trong test",
    "booked_users": "Số có nhãn y=1", "valid_nonnegative_lags": "Số độ trễ không âm",
    "negative_lags": "Số độ trễ âm", "missing_or_unparsed_booked_dates": "Ngày đặt chỗ thiếu hoặc không đọc được",
    "median_days": "Trung vị (ngày)", "p75_days": "Phân vị 75% (ngày)", "p90_days": "Phân vị 90% (ngày)",
    "p95_days": "Phân vị 95% (ngày)", "max_days": "Lớn nhất (ngày)",
    "horizon_days": "Thời hạn (ngày)", "bookings_within_h": "Số đặt chỗ trong thời hạn",
    "denominator_valid_bookings": "Mẫu số · độ trễ hợp lệ", "pct_valid_bookings": "Trong số độ trễ hợp lệ (%)",
    "pct_all_observed_bookings": "Trong số người đã đặt chỗ (%)",
    "users": "Số người dùng", "users_with_sessions": "Số có nhật ký", "coverage_pct": "Độ phủ (%)",
    "proposed_use": "Mục đích đề xuất", "account_from": "Đăng ký từ ngày", "account_to": "Đăng ký đến ngày",
    "observed_bookings": "Số có nhãn y=1", "booking_pct": "Tỷ lệ đặt chỗ (%)",
    "component": "Thành phần", "value": "Giá trị", "issue": "Vấn đề", "evidence_or_limit": "Bằng chứng và giới hạn",
}


def display_header(value):
    if not isinstance(value, str):
        return value
    return DISPLAY_HEADERS.get(value, value.replace("_", " "))


def normalize_prose(value):
    value = normalize_text(value)
    value = re.sub(r"\bcohort\b", "nhóm đăng ký", value)
    value = re.sub(r"\bCohort\b", "Nhóm đăng ký", value)
    return value.replace("booking rate", "tỷ lệ đặt chỗ")


def human_title(value):
    for key in sorted(NAMES, key=len, reverse=True):
        value = re.sub(r"(?<!\w)" + re.escape(key) + r"(?!\w)", NAMES[key], value)
    return value.replace("cohort", "nhóm đăng ký").replace("Cohort", "Nhóm đăng ký")


def open_questions():
    from scripts.eda_diagnostics import section
    data = "[Mô tả dữ liệu](https://www.kaggle.com/competitions/airbnb-recruiting-new-user-bookings/data)"
    discussion = "[Thảo luận Kaggle](https://www.kaggle.com/competitions/airbnb-recruiting-new-user-bookings/discussion)"
    return section("open_questions", "Câu hỏi mở và cách xác minh", f"""
Ba câu hỏi dưới đây cần bằng chứng ngoài CSV. Vai trò phụ trách là đề xuất cho quy trình nghiên cứu, chưa phải xác nhận rằng cá nhân hoặc tổ chức đã nhận việc. Tác giả báo cáo giữ đầu mối theo dõi và lưu bằng chứng.

Nguồn cần tra cứu gồm {data}, {discussion} và hồ sơ của người cung cấp dữ liệu. Lần tra cứu ngày 2026-11-02 chưa đọc được nội dung trang dữ liệu và thảo luận qua công cụ web. Vì vậy, các liên kết này là nguồn có thể trả lời, không được ghi thành bằng chứng đã xác nhận. Chỉ đóng một câu hỏi khi lưu được liên kết hoặc tài liệu, đoạn giải thích liên quan, ngày đối chiếu và người duyệt.
""", [("Danh mục xác minh và quyết định khi thiếu bằng chứng", pd.DataFrame([
        ["Q1 · Hồ sơ tại t0", "Tuổi, tình trạng thiếu tuổi và các thuộc tính khác là dữ liệu lúc đăng ký hay đã cập nhật về sau?", data + "; " + discussion + "; mô tả trích xuất của người cung cấp dữ liệu", "Tác giả báo cáo tổng hợp; người cung cấp dữ liệu xác nhận cách trích xuất; người hướng dẫn duyệt phạm vi", "Đối chiếu từ điển gốc và lịch sử cập nhật hoặc mô tả truy vấn trích xuất cho từng thuộc tính.", "Lưu bằng chứng về thời điểm có sẵn của từng cột, gồm cả cờ thiếu. Cột chưa có bằng chứng không được coi là đầu vào hợp lệ tại t0.", "Mở · chưa có lịch sử hồ sơ"],
        ["Q2 · 29 ngoại lệ ngày đặt chỗ", "Vì sao ngày đặt chỗ có trước ngày tạo tài khoản?", data + "; " + discussion + "; giải thích các mốc thời gian từ người cung cấp dữ liệu", "Tác giả báo cáo kiểm tra tổng hợp; người cung cấp dữ liệu giải thích; người hướng dẫn duyệt quy tắc xử lý", "Đối chiếu ngày hoạt động đầu tiên, quy ước múi giờ, định nghĩa tạo tài khoản và sự kiện đặt chỗ. Lưu bảng kiểm tra tổng hợp, không công bố định danh.", "Có giải thích được dẫn nguồn và quyết định giữ hoặc loại có người duyệt. Trong EDA vẫn giữ nguyên dữ liệu và báo riêng 29 trường hợp.", "Mở · chưa giải thích được ngoại lệ"],
        ["Q3 · Kết thúc theo dõi", "Nhãn y=0 đã được theo dõi đến ngày nào, và vì sao độ trễ lớn nhất là 365 ngày?", data + "; " + discussion + "; quy trình tạo nhãn và ngày kết thúc theo dõi từ người cung cấp dữ liệu", "Tác giả báo cáo tổng hợp; người cung cấp dữ liệu xác nhận quy trình tạo nhãn; người hướng dẫn duyệt bài toán", "Tìm định nghĩa NDF và quy tắc cắt thời gian. Cần ngày kết thúc theo dõi từng người hoặc quy tắc chung có thể kiểm chứng.", "Xác định người được theo dõi đủ 90 ngày và thời điểm nhãn có sẵn. Nếu thiếu bằng chứng, giữ bài toán nhãn y hiện có và chưa triển khai mục tiêu 90 ngày.", "Mở · chưa xác nhận thời gian theo dõi"],
    ], columns=["Câu hỏi", "Thông tin cần làm rõ", "Nguồn có thể trả lời", "Vai trò phụ trách đề xuất", "Cách xác minh", "Điều kiện kết thúc và quyết định", "Trạng thái"]))])


def apply_stage_one(report):
    by_key = {item["key"]: item for item in walk_sections(report.sections)}
    by_key["source"]["text"] = by_key["source"]["text"].replace(
        "Thông tin nào chưa được lưu hoặc chưa xác minh được được ghi rõ, không điền bằng giả định.",
        "Báo cáo ghi rõ những thông tin chưa được lưu hoặc chưa xác minh.")
    by_key["glossary"]["text"] += "\n\nQuy ước số: dấu chấm biểu diễn phần thập phân; dấu phẩy phân tách hàng nghìn. Tên cột gốc chỉ dùng khi cần đối chiếu dữ liệu."
    signal = by_key["signal"]
    signal["text"] = """Phân tích xem xét 13 cột ứng viên và bổ sung góc nhìn về tình trạng thiếu tuổi, tổng cộng 14 phép so sánh. Cramér V đo độ mạnh liên hệ giữa biến phân loại và nhãn y trên thang 0–1. Hệ số của toàn bộ train được đối chiếu với kết quả riêng năm 2014 để kiểm tra ảnh hưởng của thành phần năm đăng ký.

Giới tính khai báo có V=0.207 trên toàn kỳ và 0.251 trong năm 2014. Ứng dụng đăng ký có V tương ứng 0.109 và 0.156, thể hiện liên hệ yếu hơn trong cả hai phạm vi. Đây là mô tả từng biến, không phải điểm chất lượng mô hình. Tuổi trong dải 16–100 dùng rank-biserial trên thang −1 đến 1. Giá trị −0.005 trong năm 2014 cho thấy khác biệt thứ hạng tuổi giữa hai nhóm nhãn rất nhỏ.

Công thức, giả định kiểm định và điều chỉnh nhiều phép so sánh nằm ở mục Tái lập và kiểm soát phạm vi. Báo cáo chưa đưa AUC vì chưa huấn luyện mô hình. [Phương pháp Cramér V](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.contingency.association.html) và [Mann–Whitney](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html) được đối chiếu từ tài liệu SciPy."""
    association = report.airbnb_evidence["association"].set_index("variable")
    for key, row in association.iterrows():
        if key == "gender":
            signal["text"] = signal["text"].replace("V=0.207", f"V={row.effect_all:.3f}").replace("và 0.251", f"và {row.effect_2014:.3f}")
        elif key == "signup_app":
            signal["text"] = signal["text"].replace("0.109 và 0.156", f"{row.effect_all:.3f} và {row.effect_2014:.3f}")
        elif key.startswith("age: chỉ"):
            signal["text"] = signal["text"].replace("−0.005", f"{row.effect_2014:.3f}")
    by_key["risks"].setdefault("blocks", []).append(open_questions())
    scopes = {
        "booking_delay.png": "Người đã đặt chỗ và có độ trễ không âm. Các tỷ lệ không đại diện cho toàn bộ người dùng.",
        "users_distributions.png": "Toàn bộ người dùng train. Biểu đồ tuổi giới hạn hiển thị 16–100; bảng chi tiết giữ tuổi thiếu và ngoài dải.",
        "categories_and_target.png": "Toàn bộ người dùng train. Số lượng dùng mẫu số toàn tập; tỷ lệ dùng mẫu số từng ứng dụng.",
        "missing_patterns.png": "Bảng tỷ lệ dùng toàn bộ train; hình mẫu thiếu chỉ hiển thị tối đa 300 dòng, seed=42.",
        "outliers_and_target.png": "Tuổi không thiếu trong train. Dải ngoại lai là quy tắc mô tả; dữ liệu gốc được giữ nguyên.",
        "cohort_strata.png": "Người dùng train, tách theo năm đăng ký. Ô có n<100 được đánh dấu; khoảng Wilson ở phụ lục.",
        "multivariate.png": "Người đăng ký năm 2014. Mẫu số là người trong từng ô kết hợp; dấu * là n<100.",
        "session_coverage.png": "Người dùng trong từng tập và năm đăng ký. Có nhật ký chưa xác định nhật ký có trước t0.",
        "account_cohorts.png": "Người dùng train theo tháng đăng ký. Khoảng Wilson 95% giả định người dùng độc lập.",
    }
    for name, text in list(report.figure_notes.items()):
        report.figure_notes[name] = "**Quan sát:** " + text.removeprefix("Nhận xét: ") + "\n\n**Phạm vi và cách đọc:** " + scopes.get(name, "Phạm vi ghi trên hình và bảng đi kèm.")
    for item in walk_sections(report.sections):
        item["title"] = human_title(item["title"])
        item["tables"] = [(human_title(label), table) for label, table in item["tables"]]


def variable_name(value):
    aliases = {
        "age: cờ thiếu (EDA)": "Tình trạng thiếu tuổi",
        "age: chỉ cửa sổ 16–100 (EDA)": "Tuổi trong dải 16–100",
        "date_account_created: tháng (EDA)": "Tháng tạo tài khoản",
        "timestamp_first_active: tháng (EDA)": "Tháng hoạt động đầu tiên",
    }
    return aliases.get(value, NAMES.get(value, value))


def apply_stage_two(report):
    from scripts.airbnb_deep_dive import grouped_rates
    from scripts.eda_diagnostics import section
    by_key = {item["key"]: item for item in walk_sections(report.sections)}
    appendix = by_key["appendix"]["blocks"]
    association = report.airbnb_evidence["association"]
    categorical = association[association.effect_metric.eq("Cramér V")].sort_values("effect_2014")
    age = association[association.effect_metric.eq("Rank-biserial")].iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(14, 7.2), gridspec_kw={"width_ratios": [2.8, 1.4]})
    y = np.arange(len(categorical))
    for offset, field, label, color in [(-.12, "effect_all", "Toàn bộ train", "#245D80"),
                                         (.12, "effect_2014", "Đăng ký năm 2014", "#C76A37")]:
        axes[0].scatter(categorical[field], y + offset, label=label, color=color, s=35)
    axes[0].set_yticks(y, [variable_name(value) for value in categorical.variable])
    axes[0].set(xlabel="Cramér V (0–1)", xlim=(0, 1), title="Liên hệ của biến phân loại với nhãn y")
    axes[0].grid(axis="x", alpha=.2)
    axes[0].legend(loc="lower right")
    axes[1].scatter([age.effect_all, age.effect_2014], [1, 0], color=["#245D80", "#C76A37"], s=45)
    for value, pos in [(age.effect_all, 1), (age.effect_2014, 0)]:
        axes[1].annotate(f"{value:.3f}", (value, pos), xytext=(10, 12), textcoords="offset points")
    axes[1].axvline(0, color="#aab6bc", linestyle="--")
    axes[1].set_yticks([0, 1], ["Năm 2014", "Toàn bộ train"])
    axes[1].set(xlim=(-1, 1), ylim=(-.5, 1.6), xlabel="Rank-biserial (−1 đến 1)", title="Tuổi trong dải 16–100")
    axes[1].set_xticks([-1, -.5, 0, .5, 1])
    fig.tight_layout(w_pad=3)
    path = report.savefig("association_strength", fig)
    report.figure_notes[path.name] = (
        "**Quan sát:** tình trạng thiếu tuổi có V lớn nhất trong các biến phân loại được khảo sát. Liên hệ của các mốc theo tháng giảm khi chỉ xét năm 2014. "
        f"Tuổi trong dải 16–100 có rank-biserial={age.effect_2014:.3f} trong năm 2014, gần 0.\n\n"
        "**Phạm vi và cách đọc:** V tính trên toàn bộ người dùng trong từng phạm vi, gồm giá trị thiếu như một nhóm. "
        "Rank-biserial chỉ tính trên tuổi 16–100 và được đặt trên trục riêng. Hai thước đo không dùng chung ngưỡng so sánh. "
        "Liên hệ của cờ thiếu cần được kiểm tra về thời điểm có sẵn tại t0."
    )
    by_key["signal"]["figures"] = [path]
    appendix.append(section("full_association", "Chi tiết độ mạnh liên hệ và kiểm định", "Bảng giữ đầy đủ 14 phép so sánh, cỡ mẫu, p-value, q sau điều chỉnh và tỷ lệ ô có tần số kỳ vọng nhỏ.", by_key["signal"]["tables"]))
    chosen = association.variable.isin(["gender", "signup_app", "signup_method", "age: cờ thiếu (EDA)", "age: chỉ cửa sổ 16–100 (EDA)"])
    compact = association.loc[chosen, ["variable", "effect_metric", "effect_all", "effect_2014"]].copy()
    compact.variable = compact.variable.map(variable_name)
    by_key["signal"]["tables"] = [("Các liên hệ chính cần kiểm tra trong thí nghiệm", compact)]

    target = by_key["target_rates"]
    appendix.append(section("full_group_rates", "Tỷ lệ đặt chỗ chi tiết theo hồ sơ", "Mỗi bảng dùng toàn bộ train. Mẫu số là người trong từng nhóm. Các bảng này giữ nguyên số liệu chi tiết làm căn cứ đối chiếu.", target["tables"]))
    frame = report.airbnb_context["frame"]
    recent = frame[report.airbnb_context["account"].dt.year.eq(2014)]
    columns = ["gender", "signup_app", "age_missing_eda"]
    rate_tables = []
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), layout="constrained")
    overall = recent.observed_booking.mean() * 100
    for ax, column in zip(axes, columns):
        table = grouped_rates(recent, [column])
        rows = table.assign(Đặc_điểm=NAMES[column]).rename(columns={column: "Nhóm", "Đặc_điểm": "Đặc điểm"})
        rate_tables.append(rows[["Đặc điểm", "Nhóm", "n", "positive", "rate_pct", "ci95_low_pct", "ci95_high_pct"]])
        positions = np.arange(len(table))
        errors = np.vstack([table.rate_pct - table.ci95_low_pct, table.ci95_high_pct - table.rate_pct])
        ax.errorbar(table.rate_pct, positions, xerr=errors, fmt="o", color="#245D80", capsize=4)
        ax.set_yticks(positions, [f"{name} (n={int(n):,})" for name, n in zip(table[column], table.n)])
        ax.axvline(overall, color="#C76A37", linestyle="--", label="Tỷ lệ chung năm 2014")
        ax.set(xlim=(0, 100), xlabel="Có lượt đặt chỗ đầu tiên (%)", title=NAMES[column])
        ax.grid(axis="x", alpha=.2)
    axes[1].legend(loc="upper center", bbox_to_anchor=(.5, -.18), fontsize=9, frameon=False)
    path = report.savefig("group_rates_wilson", fig)
    combined = pd.concat(rate_tables, ignore_index=True)
    target["title"] = "Tỷ lệ đặt chỗ và độ bất định theo các nhóm chính"
    target["text"] = "Ba nhóm đặc điểm dưới đây được so sánh trên cùng quần thể đăng ký năm 2014. Mỗi điểm là tỷ lệ có nhãn y=1 trong nhóm, thanh ngang là khoảng Wilson 95%. Bảng gom các nhóm vào cùng một cấu trúc để đọc đồng thời cỡ mẫu, tỷ lệ và độ bất định. Bảng toàn bộ train và các đặc điểm khác nằm ở phụ lục."
    target["tables"] = [("Tỷ lệ đặt chỗ theo nhóm · cùng năm đăng ký 2014", combined)]
    target["figures"] = [path]
    report.figure_notes[path.name] = (
        f"**Quan sát:** đường đứt đánh dấu tỷ lệ chung {overall:.2f}% của người đăng ký năm 2014. "
        "Khoảng rộng ở các nhóm ít người cho thấy tỷ lệ ước lượng kém chính xác hơn.\n\n"
        "**Phạm vi và cách đọc:** mẫu số của mỗi điểm là số người trong nhóm, được ghi cạnh tên. "
        "Khoảng Wilson 95% giả định người dùng độc lập. Mức chồng lấp khoảng tin cậy không thay thế kiểm định chênh lệch. "
        "Tuổi và tình trạng thiếu tuổi chỉ là ứng viên đầu vào sau khi xác minh tại t0."
    )
    report.facts["group_rate_figure_cohort"] = "2014"


def column_decisions(report):
    context = report.airbnb_context
    rows = []
    for column in context["train"].columns:
        if column == "id":
            role, decision, condition = "Khóa người dùng", "Dùng đối chiếu và ghép; loại khỏi đầu vào", "Kiểm tra tính duy nhất và giao nhau giữa các tập"
        elif column == "country_destination":
            role, decision, condition = "Cột xác định nhãn y", "Chỉ dùng tạo nhãn và đánh giá", "Xác minh phạm vi theo dõi · Q3"
        elif column == "date_first_booking":
            role, decision, condition = "Kết quả và kiểm tra thời gian", "Loại ngày và cờ thiếu khỏi đầu vào", "Giải thích 29 ngoại lệ · Q2"
        elif column == "age":
            role, decision, condition = "Thuộc tính hồ sơ", "Ứng viên có điều kiện; tuổi và cờ thiếu cần cùng được kiểm tra", "Xác minh hồ sơ tại t0 và ý nghĩa giá trị ngoài dải · Q1"
        elif column == "signup_flow":
            role, decision, condition = "Mã phân loại", "Ứng viên có điều kiện; không coi là đại lượng liên tục", "Xác minh thời điểm có sẵn · Q1; mã hóa chỉ học trên train"
        elif column in ["date_account_created", "timestamp_first_active"]:
            role, decision, condition = "Mốc thời gian", "Dùng kiểm tra và chia thời gian; cân nhắc đầu vào riêng", "Xác minh độ chính xác, múi giờ và thời điểm có sẵn · Q1"
        else:
            role, decision, condition = "Thuộc tính đăng ký", "Ứng viên có điều kiện", "Xác minh hồ sơ tại t0 · Q1; xử lý thiếu và nhóm mới trong từng tập train"
        rows.append(["Hồ sơ người dùng", column, variable_name(column), role, decision, condition])
    for column in ["user_id", "action", "action_type", "action_detail", "device_type", "secs_elapsed"]:
        rows.append(["Nhật ký hoạt động", column, NAMES.get(column, "Thiết bị ở sự kiện" if column == "device_type" else "Thời lượng"),
                     "Khóa ghép" if column == "user_id" else "Thuộc tính sự kiện",
                     "Dùng đối chiếu khóa" if column == "user_id" else "Loại khỏi đầu vào của thiết kế tại t0",
                     "Thiếu thời điểm sự kiện; thời lượng không xác định được phần có trước t0"])
    for file, label in [("countries.csv", "Thông tin quốc gia"), ("age_gender_bkts.csv", "Dân số theo tuổi và giới tính")]:
        for column in pd.read_csv(report.root / "data/raw/AIRBNB" / file, nrows=0).columns:
            rows.append([label, column, column.strip().replace("_", " "), "Thuộc tính tổng hợp hoặc khóa bảng phụ",
                         "Dùng làm bối cảnh; chưa ghép làm đầu vào", "Không ghép bằng điểm đến thật. Cần khóa biết tại t0 và căn cứ sử dụng bảng phụ."])
    return pd.DataFrame(rows, columns=["Bảng dữ liệu", "Cột gốc", "Ý nghĩa ngắn", "Vai trò", "Quyết định cho thiết kế chính", "Điều kiện và căn cứ"])


def relationship_figure(report):
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(14, 6.5))
    ax.set(xlim=(0, 14), ylim=(0, 6.5))
    ax.axis("off")
    def box(x, y, w, h, text, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15", facecolor=color, edgecolor="#93a9b4"))
        ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=11, linespacing=1.5)
    facts = report.facts
    box(.4, 3.5, 5, 2, f"HỒ SƠ NGƯỜI DÙNG\nTrain: {facts['rows']:,} · Test: {facts['test_rows']:,}\nMột dòng/người · khóa id\nTrain có cột điểm đến để xác định nhãn y", "#e9f1f6")
    box(8.0, 3.5, 5.3, 2, f"NHẬT KÝ HOẠT ĐỘNG\n{facts['sessions']:,} sự kiện · khóa user_id\nMỗi người có thể có nhiều sự kiện\nThiếu thời điểm sự kiện", "#e9f1f6")
    ax.annotate("", xy=(7.8, 4.5), xytext=(5.6, 4.5), arrowprops={"arrowstyle": "->", "color": "#245D80", "lw": 2})
    ax.text(6.7, 4.85, "id → user_id\n1 : nhiều", ha="center", fontsize=10)
    box(.4, .35, 5.0, 1.65, "THÔNG TIN QUỐC GIA\n10 dòng · khóa điểm đến\nThuộc tính địa lý và ngôn ngữ", "#fff4e8")
    box(8.0, .35, 5.3, 1.65, "DÂN SỐ THEO TUỔI VÀ GIỚI TÍNH\n420 dòng tổng hợp\nKhóa: quốc gia, nhóm tuổi, giới tính, năm", "#fff4e8")
    for x in [2.9, 10.65]:
        ax.annotate("", xy=(x, 2.2), xytext=(3, 3.3), arrowprops={"arrowstyle": "->", "linestyle": "--", "color": "#C76A37", "lw": 1.5})
    ax.text(7, 2.65, "Đường đứt: quan hệ mô tả có thể đối chiếu bằng điểm đến\nKhông dùng điểm đến thật để ghép đầu vào cho người dùng mới", ha="center", va="center", fontsize=10,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 5})
    fig.tight_layout()
    return report.savefig("table_relationships", fig)


def apply_stage_three(report):
    from scripts.eda_diagnostics import section
    by_key = {item["key"]: item for item in walk_sections(report.sections)}
    appendix = by_key["appendix"]["blocks"]
    decisions = column_decisions(report)
    appendix.append(section("column_decisions", "Quyết định sử dụng theo từng cột", "Bảng bao phủ toàn bộ cột của bốn loại bảng gốc. Đây là quyết định thiết kế, chưa thực hiện biến đổi hoặc loại dữ liệu.", [("Vai trò, quyết định và điều kiện cho từng cột", decisions)]))
    summary = decisions.groupby(["Bảng dữ liệu", "Quyết định cho thiết kế chính"], sort=False).size().reset_index(name="Số cột")
    by_key["quality_main"]["blocks"].append(section("column_decision_summary", "Vai trò dữ liệu trong thiết kế chính", "Bảng dưới tóm tắt quyết định theo nhóm cột. Bảng quyết định đầy đủ trong phụ lục chỉ rõ từng cột, điều kiện tại t0 và câu hỏi Q1–Q3 liên quan. Các cột hồ sơ có trạng thái ứng viên có điều kiện, chưa được xác nhận là khả dụng tại t0.", [("Tóm tắt quyết định sử dụng dữ liệu", summary)]))
    path = relationship_figure(report)
    by_key["overview"]["blocks"].append(section("relationships", "Quan hệ giữa các bảng", "Hồ sơ người dùng là đơn vị phân tích chính. Khi ghép nhật ký một–nhiều, phải tổng hợp về một dòng mỗi người trước khi xây dựng dữ liệu học. Hai bảng phụ mô tả điểm đến và dân số tổng hợp, nên cần phân biệt quan hệ có thể tra cứu với khóa đã biết tại thời điểm dự đoán.", figures=[path]))
    report.figure_notes[path.name] = f"**Quan sát:** hồ sơ có thể ghép với nhật ký qua định danh. Có {report.facts['sessions_missing_ids']:,} sự kiện thiếu định danh nên không ghép được về người dùng.\n\n**Phạm vi và cách đọc:** mũi tên liền chỉ quan hệ khóa 1:nhiều. Mũi tên đứt chỉ quan hệ bối cảnh, chưa phải phép ghép được chấp nhận cho mô hình. Các con số là quy mô bảng, không phải số khách hàng bổ sung."

    risks = by_key["risks"]
    suitability = by_key["conclusion_main"]["tables"][0][1].copy()
    mapping = {"Quần thể": "Khái quát hóa", "Nhóm nhỏ / bias": "Đủ cỡ mẫu", "Rò rỉ": "Không rò rỉ", "Giới hạn suy luận": "Đủ tín hiệu"}
    extras = []
    for row in risks["tables"][0][1].itertuples(index=False):
        if row.issue in mapping:
            mask = suitability.criterion.eq(mapping[row.issue])
            suitability.loc[mask, "remaining_condition"] += " " + row.evidence_or_limit
        else:
            extras.append([row.issue, row.evidence_or_limit, "Cần kiểm soát khi sử dụng", "Tác giả báo cáo rà soát quyền sử dụng và bảo vệ dữ liệu trước khi chia sẻ hoặc triển khai."])
    suitability = pd.concat([suitability, pd.DataFrame(extras, columns=suitability.columns)], ignore_index=True)
    risks["title"] = "6. Tổng hợp giới hạn và mức độ phù hợp"
    risks["text"] = by_key["conclusion_main"]["text"] + "\n\nBảng dưới gộp rủi ro và tiêu chí phù hợp vào cùng một nơi. Trạng thái hiện tại phân biệt mức đủ cho nghiên cứu với điều kiện cần trước khi triển khai. Các vấn đề chưa thể giải quyết bằng CSV được theo dõi trong mục Câu hỏi mở và cách xác minh."
    risks["tables"] = [("Giới hạn, mức độ phù hợp và điều kiện sử dụng", suitability)]
    implications = pd.DataFrame([
        ["Độ trễ tập trung trong 90 ngày", "Xem xét thời hạn 90 ngày", "Chỉ chuyển sang mục tiêu này sau khi giải quyết Q3", "Bảng mức bao phủ các thời hạn"],
        ["Cờ thiếu tuổi liên hệ rõ với nhãn y", "Đánh giá giá trị bổ sung của tình trạng thiếu hồ sơ", "Xác minh tuổi và cờ thiếu tại t0 · Q1", "Bảng độ mạnh liên hệ; bảng tỷ lệ theo nhóm"],
        ["Chênh lệch theo ứng dụng và kênh vẫn có trong năm 2014", "So sánh Logistic Regression và CatBoost", "Đánh giá theo thời gian; không suy ra tác động nhân quả", "Bảng phân tầng; bản đồ các nhóm kết hợp"],
        ["Ngày đặt chỗ tiết lộ hoàn toàn nhãn y", "Loại ngày đặt chỗ và cờ thiếu khỏi danh sách đầu vào", "Giữ cột để kiểm tra nhãn, độ trễ và Q2", "Bảng chéo ngày đặt chỗ và nhãn y"],
        ["Nhật ký thiếu thời điểm sự kiện", "Loại nhật ký khỏi thiết kế dự đoán ngay sau đăng ký", "Chỉ mở nghiên cứu hành vi khi có bằng chứng về thời gian", "Bảng rà soát hành động và độ phủ nhật ký"],
        ["Phân phối và tỷ lệ đặt chỗ thay đổi theo thời gian", "Dùng các cửa sổ kiểm định liên tiếp", "Kiểm tra nhãn đã có sẵn trước từng mốc đánh giá", "Bảng tháng đăng ký; bảng khác biệt phân phối"],
    ], columns=["Phát hiện", "Hàm ý cho bước sau", "Điều kiện cần", "Bằng chứng trong báo cáo"])
    risks["blocks"].insert(0, section("implications", "Phát hiện và hàm ý cho bước sau", "Mỗi hàm ý nối trực tiếp với quan sát EDA và điều kiện dữ liệu. Các bước mô hình hóa dưới đây là đề xuất cần được kiểm tra bằng thí nghiệm.", [("Từ quan sát đến quyết định nghiên cứu", implications)]))
    report.sections = [item for item in report.sections if item["key"] != "conclusion_main"]
    report.facts["columns_with_usage_decision"] = len(decisions)


def timeline_figure(report):
    import matplotlib.dates as mdates
    from matplotlib.patches import Patch
    protocol = report.airbnb_evidence["protocol"]
    fig, ax = plt.subplots(figsize=(14, 6.4))
    colors = ["#245D80", "#468477", "#245D80", "#468477", "#245D80", "#468477", "#245D80", "#C76A37", "#8A6598"]
    for pos, row in enumerate(protocol.itertuples(index=False)):
        start = pd.Timestamp(row.account_from)
        end = pd.Timestamp(row.account_to) + pd.Timedelta(days=1)
        left = mdates.date2num(start)
        width = mdates.date2num(end) - left
        ax.broken_barh([(left, width)], (pos-.32, .64), facecolors=colors[pos])
        ax.text(mdates.date2num(pd.Timestamp("2014-10-01")), pos, f"n={row.users:,}", va="center", fontsize=9)
    ax.set_yticks(np.arange(len(protocol)), protocol.proposed_use)
    ax.invert_yaxis()
    ax.set(xlim=(mdates.date2num(pd.Timestamp("2009-12-01")), mdates.date2num(pd.Timestamp("2015-04-01"))),
           xlabel="Ngày tạo tài khoản · cửa sổ đề xuất", title="Chọn cấu hình → huấn luyện lại → hiệu chỉnh → đánh giá cuối")
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    ax.grid(axis="x", alpha=.2)
    ax.legend(handles=[Patch(color=color, label=label) for color, label in
                       [("#245D80", "Huấn luyện"), ("#468477", "Kiểm định chọn cấu hình"),
                        ("#C76A37", "Hiệu chỉnh xác suất"), ("#8A6598", "Đánh giá cuối")]],
              loc="upper center", bbox_to_anchor=(.5, -.15), ncol=4, frameon=False)
    fig.tight_layout()
    return report.savefig("evaluation_timeline", fig)


def executive_sources(report, by_key):
    from scripts.eda_diagnostics import section
    context, facts = report.airbnb_context, report.facts
    train, test = context["train"], context["test"]
    frame, account = context["frame"], context["account"]
    recent = account.dt.year.eq(2014)
    evidence = report.airbnb_evidence
    association = evidence["association"].set_index("variable")
    session_rates = evidence["sessions_2014"].set_index("has_sessions")
    source = by_key["source"]
    size = pd.DataFrame([
        ["Train", len(train), int(frame.observed_booking.sum()), frame.observed_booking.mean()*100],
        ["Test", len(test), np.nan, np.nan],
    ], columns=["Tập dữ liệu", "Số người dùng", "Số có nhãn y=1", "Tỷ lệ y=1 (%)"])
    source["tables"].append(("B1 · Quy mô người dùng và nhãn y", size))
    by_key["booking_delay"]["tables"] = [
        (("B6 · " if i == 0 else "B2 · " if i == 1 else "") + title, table)
        for i, (title, table) in enumerate(by_key["booking_delay"]["tables"])]
    by_key["signal"]["tables"][0] = ("B3 · Các liên hệ chính cần kiểm tra", by_key["signal"]["tables"][0][1])
    missing = pd.DataFrame([{
        "Số người dùng thiếu tuổi": int(train.age.isna().sum()),
        "Tỷ lệ thiếu tuổi (%)": train.age.isna().mean()*100,
        "V cờ thiếu tuổi · 2014": association.loc["age: cờ thiếu (EDA)", "effect_2014"],
        "Rank-biserial tuổi 16–100 · 2014": association.loc["age: chỉ cửa sổ 16–100 (EDA)", "effect_2014"],
    }])
    by_key["column_decision_summary"]["tables"].append(("B4 · Tình trạng hồ sơ tuổi và liên hệ trong năm 2014", missing))
    train_recent_logs = facts["train_2014_session_users"]
    train_recent_n = int(recent.sum())
    train_coverage = train_recent_logs/train_recent_n*100
    test_coverage = facts["test_session_users"]/len(test)*100
    coverage = pd.DataFrame([
        ["Train toàn kỳ", len(train), facts["train_session_users"], facts["train_session_users"]/len(train)*100, np.nan, np.nan, np.nan],
        ["Train năm 2014", train_recent_n, train_recent_logs, train_coverage, 0., session_rates.loc[True, "rate_pct"], session_rates.loc[False, "rate_pct"]],
        ["Test năm 2014", len(test), facts["test_session_users"], test_coverage, test_coverage-train_coverage, np.nan, np.nan],
    ], columns=["Phạm vi", "Số người dùng", "Số có nhật ký", "Độ phủ (%)", "Chênh với train 2014 (điểm %)", "Tỷ lệ đặt chỗ · có nhật ký (%)", "Tỷ lệ đặt chỗ · thiếu nhật ký (%)"])
    by_key["sessions_evidence"]["tables"].insert(0, ("B5 · Độ phủ nhật ký và tỷ lệ đặt chỗ", coverage))
    by_key["evaluation"]["tables"][0] = ("B7 · Cửa sổ thời gian đề xuất và quy mô quan sát", evidence["protocol"])
    matches = train.date_first_booking.notna().eq(frame.observed_booking.astype(bool))
    leakage = pd.DataFrame([[int(matches.sum()), len(train), matches.mean()*100]],
                           columns=["Số trường hợp khớp", "Số người dùng train", "Tỷ lệ khớp (%)"])
    by_key["quality_main"]["blocks"][0]["tables"].append(("B8 · Mức khớp giữa tình trạng ngày đặt chỗ và nhãn y", leakage))
    rows = [
        ["Phát hiện 1", "B1", "Quy mô train, test, số và tỷ lệ nhãn y=1", "facts.rows; facts.test_rows; facts.positive; facts.rate"],
        ["Phát hiện 2", "B2; B6", "88,879 độ trễ hợp lệ; thời hạn và mức bao phủ 30/60/90 ngày", "facts.valid_booking_lags; facts.booking_coverage_30/60/90_pct"],
        ["Phát hiện 3", "B3", "V của giới tính và ứng dụng đăng ký, toàn kỳ và năm 2014", "association: gender/signup_app × effect_all/effect_2014"],
        ["Phát hiện 4", "B4", "Tỷ lệ thiếu tuổi, V cờ thiếu tuổi và rank-biserial tuổi 16–100", "missing tuổi từ train; association: hai dòng tuổi × effect_2014"],
        ["Phát hiện 5", "B5", "Độ phủ, chênh độ phủ, tỷ lệ đặt chỗ có/thiếu nhật ký; quy mô train 2014", "facts.train_2014_users; facts.train_2014_session_coverage_pct; sessions_2014"],
        ["Việc cần giải quyết 1", "B6; B2; Q3", "29 ngoại lệ, độ trễ lớn nhất 365 ngày và phương án 90 ngày", "facts.negative_booking_lags; facts.max_observed_booking_lag_days; facts.proposed_deployment_horizon_days"],
        ["Việc cần giải quyết 2", "B8; Q1", "Mức khớp 100% và điều kiện thông tin tại t0", "Tính trực tiếp từ ngày đặt chỗ có giá trị và nhãn y"],
        ["Việc cần giải quyết 3", "B7", "Hiệu chỉnh tháng 4/2014 và đánh giá tháng 5–6/2014", "protocol: account_from/account_to; đây là đề xuất, chưa chia tập"],
    ]
    provenance = pd.DataFrame(rows, columns=["Ý trong tóm tắt", "Bảng hoặc câu hỏi nguồn", "Số liệu và nội dung được đối chiếu", "Đường dẫn dữ liệu hoặc cách tính"])
    by_key["appendix"]["blocks"].append(section("executive_sources", "Truy vết số liệu trong tóm tắt", "Mã B1–B8 đứng trước tên các bảng tương ứng. Các số được làm tròn khi trình bày. Metadata giữ giá trị đầy đủ trong facts và dấu kiểm tra của các bảng thống kê. Các mốc chia thời gian là đề xuất nghiên cứu, không phải kết quả đã thực hiện.", [("Nguồn của từng phát hiện và việc cần giải quyết", provenance)]))
    text = by_key["executive"]["text"]
    sources = ["B1", "B2 và B6", "B3", "B4", "B5"]
    next_sources = ["B6, B2 và Q3", "B8 và Q1", "B7"]
    current = None
    parts = []
    for paragraph in text.split("\n\n"):
        if paragraph == "**Năm phát hiện chính**":
            current = sources
        elif paragraph == "**Ba việc cần giải quyết trước khi huấn luyện**":
            current = next_sources
        match = re.match(r"^(\d)\. \*\*", paragraph)
        if match and current:
            paragraph += f" (Nguồn: bảng {current[int(match.group(1))-1]}.)"
        parts.append(paragraph)
    by_key["executive"]["text"] = "\n\n".join(parts)
    report.executive_evidence = provenance.to_dict(orient="records")
    # Check every displayed number against cells/headers of the cited tables.
    from decimal import Decimal
    pattern = r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])"
    def numbers_in(text):
        return {str(Decimal(token.replace(",", "")).normalize())
                for token in re.findall(pattern, str(text))}
    tables = {"B1": size, "B2": evidence["horizons"], "B3": by_key["signal"]["tables"][0][1],
              "B4": missing, "B5": coverage, "B6": evidence["delay"], "B7": evidence["protocol"], "B8": leakage}
    citations = [["B1"], ["B2", "B6"], ["B3"], ["B4"], ["B5"], ["B6", "B2"], ["B8"], ["B7"]]
    paragraphs = [p for p in parts if re.match(r"^\d\. \*\*", p)]
    checks = []
    for paragraph, references in zip(paragraphs, citations):
        available = set()
        for reference in references:
            table = tables[reference]
            available |= numbers_in(" ".join(map(str, table.columns)).replace("_", " "))
            for row in table.itertuples(index=False, name=None):
                for value in row:
                    if isinstance(value, numbers.Real) and not pd.isna(value):
                        for digits in [0, 2, 3, 4]:
                            available |= numbers_in(f"{value:,.{digits}f}")
                    elif isinstance(value, str):
                        available |= numbers_in(value)
        used = numbers_in(re.sub(r"^\d\. ", "", paragraph))
        missing_numbers = used - available
        assert not missing_numbers, f"Summary numbers lack cited table: {missing_numbers} · {references}"
        checks.append({"sources": references, "displayed_numbers": sorted(used), "all_matched": True})
    report.executive_numeric_checks = checks


def apply_stage_four(report):
    from scripts.eda_diagnostics import section
    by_key = {item["key"]: item for item in walk_sections(report.sections)}
    path = timeline_figure(report)
    by_key["evaluation"]["figures"] = [path]
    report.figure_notes[path.name] = (
        "**Quan sát:** tập học mở rộng qua ba lượt kiểm định. Cấu hình được chọn trước khi huấn luyện lại đến hết tháng 3/2014. "
        "Tháng 4 dành cho hiệu chỉnh và tháng 5–6 dành cho đánh giá cuối.\n\n"
        "**Phạm vi và cách đọc:** các thanh biểu diễn khoảng ngày tạo tài khoản, không phải khoảng nhãn đã hoàn tất. "
        "Cỡ mẫu là số người quan sát trong cửa sổ, chưa phải số đủ điều kiện huấn luyện sau khi kiểm tra thời điểm có nhãn. "
        "Với mục tiêu 90 ngày, cần bổ sung điều kiện theo dõi đủ 90 ngày trước mỗi mốc dự đoán."
    )
    roles = pd.DataFrame([
        ["Huấn luyện và chọn cấu hình", "Các cửa sổ học/kiểm định liên tiếp", "Học xử lý dữ liệu trong từng tập học; chọn tham số, số vòng và phương pháp hiệu chỉnh bằng dữ liệu phát triển", "Không dùng nhãn xuất hiện sau mốc dự đoán; tập kiểm định không học thống kê tiền xử lý"],
        ["Huấn luyện lại", "Từ đầu dữ liệu đến hết 2014-03", "Cố định cấu hình rồi huấn luyện lại mô hình nền", "Không điều chỉnh thiết kế theo kết quả tháng 5–6"],
        ["Hiệu chỉnh xác suất", "Tháng 4/2014", "Học bộ hiệu chỉnh trên xác suất của mô hình nền đã cố định", "Không huấn luyện lại mô hình nền bằng dữ liệu hiệu chỉnh"],
        ["Đánh giá cuối", "Tháng 5–6/2014", "Tính log loss, Brier, AP, ROC-AUC, lift và độ ổn định theo tháng", "Dùng sau khi chốt mô hình và bộ hiệu chỉnh; nếu sửa thiết kế phải công bố đánh giá đã bị sử dụng"],
        ["Đối chiếu test Kaggle", "Tháng 7–9/2014", "Kiểm tra cấu trúc cột, nhóm giá trị mới và thay đổi phân phối", "Không tính chất lượng dự báo vì không có nhãn"],
    ], columns=["Giai đoạn", "Phạm vi", "Được thực hiện", "Điều kiện tách biệt"])
    by_key["evaluation"]["tables"].append(("Vai trò từng giai đoạn huấn luyện, hiệu chỉnh và đánh giá", roles))
    executive_sources(report, by_key)
    criteria = pd.DataFrame([
        ["0 · Sửa nội dung", "Đủ cảnh báo mẫu số và t0; số thập phân thống nhất; không lặp từ; mở đầu không có lệnh cài; ngày tải ghi đúng bằng chứng", "Kiểm tra văn bản, notebook và metadata"],
        ["1 · Chuẩn hóa", "Mỗi hình có quan sát và phạm vi; tiêu đề bảng dùng tên diễn giải; khái niệm có tên thống nhất; phương pháp chi tiết ở cuối", "Kiểm tra chú thích, tiêu đề và bảng thuật ngữ"],
        ["2 · Tổ chức EDA", "Có biểu đồ độ mạnh liên hệ với hai thang riêng; tỷ lệ nhóm có khoảng Wilson; bảng dài nằm ở phụ lục", "Kiểm tra hình, bảng và dấu kiểm tra thống kê"],
        ["3 · Hiểu dữ liệu", "Có quyết định cho toàn bộ 34 cột; sơ đồ quan hệ; phát hiện gắn hàm ý; rủi ro và phù hợp gộp một mục", "Đối chiếu số cột CSV, cấu trúc báo cáo và bảng quyết định"],
        ["4 · Thiết kế nghiên cứu", "Có sơ đồ thời gian và vai trò từng giai đoạn; mọi số trong tóm tắt có bảng nguồn; notebook chạy hết; số liệu khớp sau từng giai đoạn", "Đối chiếu B1–B8, nguồn số liệu, lịch sử kiểm tra và mã nguồn trong metadata"],
    ], columns=["Giai đoạn", "Điều kiện hoàn thành", "Cách kiểm tra"])
    by_key["reproducibility"]["tables"].append(("Điều kiện hoàn thành và kiểm tra sau từng giai đoạn", criteria))
    by_key["reproducibility"]["text"] += "\n\nMỗi giai đoạn 0–4 được dựng lại toàn bộ từ CSV bằng cùng notebook. Khi xuất báo cáo, chương trình đối chiếu các số liệu chính với metadata trước đó và kiểm tra SHA-256 của các bảng bằng chứng. Sau khi mọi ô chạy thành công, completed_stages trong metadata ghi kết quả của giai đoạn đó. Đây là lịch sử kiểm tra trong cùng bản báo cáo, không tạo bản sao, tag hay nhánh khác."


def walk_sections(sections):
    for item in sections:
        yield item
        yield from walk_sections(item.get("blocks", []))


def normalize_text(value):
    if not isinstance(value, str):
        return value
    value = value.replace("được được", "được")
    # Interval separators are punctuation, not decimal commas.
    value = re.sub(r"\[([−-]?\d+(?:\.\d+)?),\s*([−-]?\d+(?:\.\d+)?)\]", r"[\1; \2]", value)
    value = re.sub(r"(?<![\d.,])0,(\d+)(?![\d.,])", r"0.\1", value)
    # The report uses a decimal point and a comma for groups of three digits.
    return re.sub(r"(?<![\d.,])(\d+),(\d{1,2})(?![\d.,])", r"\1.\2", value)


def capture_evidence(report, tables):
    """Fingerprint computed evidence before any display-only transformations."""
    report.airbnb_evidence = tables
    serialized = json.dumps({key: table.to_json(orient="split", double_precision=15)
                             for key, table in sorted(tables.items())}, sort_keys=True)
    report.facts["statistical_fingerprint"] = hashlib.sha256(serialized.encode()).hexdigest()


def prepare_publication(report):
    if STAGE >= 1:
        apply_stage_one(report)
    if STAGE >= 2:
        apply_stage_two(report)
    if STAGE >= 3:
        apply_stage_three(report)
    if STAGE >= 4:
        apply_stage_four(report)
    for item in walk_sections(report.sections):
        item["title"] = normalize_text(item["title"])
        item["text"] = normalize_prose(item["text"])
        item["tables"] = [(normalize_text(label), table.map(normalize_text))
                          for label, table in item["tables"]]
        if STAGE >= 4:
            item["tables"] = [(label, table.rename(columns=display_header).rename_axis(display_header(table.index.name)))
                              for label, table in item["tables"]]
        if STAGE >= 1:
            assert all(not re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", label)
                       for label, _ in item["tables"] for key in NAMES), "Code name remains in table title"
    report.figure_notes = {key: normalize_prose(value) for key, value in report.figure_notes.items()}
    from scripts.build_descriptive_reports import md_table
    report.rendered_tables_sha256 = sorted(
        hashlib.sha256(md_table(table).encode()).hexdigest()
        for item in walk_sections(report.sections) for _, table in item["tables"])
    report.facts["completion_stage"] = STAGE
    report.facts["analysis_revision"] = "airbnb_completion_stages_0_to_4"
    previous = report.directory / "analysis_metadata.json"
    if previous.exists():
        previous_meta = json.loads(previous.read_text(encoding="utf-8"))
        report.completed_stages = previous_meta.get("completed_stages", [])
        old = previous_meta["facts"]
        for key, value in old.items():
            if key in report.facts and isinstance(value, numbers.Number) and key != "completion_stage":
                if value != report.facts[key]:
                    raise ValueError(f"Statistical fact changed: {key}")
        if "statistical_fingerprint" in old:
            assert old["statistical_fingerprint"] == report.facts["statistical_fingerprint"], "Evidence changed"
    for item in walk_sections(report.sections):
        for path in item["figures"]:
            assert path.name in report.figure_notes, f"Missing caption: {path.name}"


def verify_artifacts(root, notebook):
    path = root / "reports/AIRBNB/analysis_metadata.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    markdown = (path.parent / "README.md").read_text(encoding="utf-8")
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert all(cell.execution_count for cell in cells)
    assert not [out for cell in cells for out in cell.outputs if out.output_type == "error"]
    assert "pip install" not in notebook.cells[0].source
    assert "được được" not in markdown
    assert "người cung cấp xác nhận" not in markdown.lower()
    assert not re.search(r"(?<![\d.,])\d+,\d{1,2}(?![\d.,])", markdown)
    assert "[0.1]" not in markdown
    markdown_headings = re.findall(r"^## (.+)$", markdown, re.MULTILINE)
    notebook_headings = [cell.source.removeprefix("## ") for cell in notebook.cells
                         if cell.cell_type == "markdown" and cell.source.startswith("## ")]
    assert markdown_headings == notebook_headings, "Notebook/README section titles differ"
    rendered_hashes = []
    for cell in cells:
        for output in cell.outputs:
            text = output.get("data", {}).get("text/markdown", "")
            text = "".join(text) if isinstance(text, list) else text
            if text.startswith("| "):
                rendered_hashes.append(hashlib.sha256(text.encode()).hexdigest())
                assert text in markdown, "Notebook table differs from README"
    assert sorted(rendered_hashes) == meta["rendered_tables_sha256"], "Notebook tables missing or truncated"
    if STAGE >= 4:
        assert len(meta["executive_numeric_checks"]) == 8
        assert all(row["all_matched"] for row in meta["executive_numeric_checks"])
        assert "conclusion_main" not in meta["section_keys"]
        assert meta["facts"]["columns_with_usage_decision"] == 34
        assert {"association_strength.png", "group_rates_wilson.png", "table_relationships.png", "evaluation_timeline.png"} <= meta["figure_notes"].keys()
    for key, filename in [("script_sha256", "build_descriptive_reports.py"),
                          ("diagnostics_script_sha256", "eda_diagnostics.py"),
                          ("airbnb_deep_dive_script_sha256", "airbnb_deep_dive.py"),
                          ("presentation_script_sha256", "airbnb_report_presentation.py")]:
        assert meta[key] == hashlib.sha256((root / "scripts" / filename).read_bytes()).hexdigest()
    history = meta.get("completed_stages", [])
    history = [row for row in history if row["stage"] != STAGE]
    history.append({"stage": STAGE, "executed_cells": len(cells),
                    "statistical_fingerprint": meta["facts"]["statistical_fingerprint"],
                    "checks": "numeric facts, evidence, captions, notebook outputs, source hashes, decimals" + (", executive number provenance, column decisions, merged limitations, timeline" if STAGE >= 4 else "")})
    meta["completed_stages"] = sorted(history, key=lambda row: row["stage"])
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"AIRBNB stage {STAGE}: publication checks passed ({len(cells)} executed cells)", flush=True)
