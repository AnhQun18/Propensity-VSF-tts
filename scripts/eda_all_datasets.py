"""THƯ VIỆN EDA TÁI SỬ DỤNG + ADAPTER HOTEL, AIRBNB, EXPEDIA.

DÙNG CHO BA BỘ DỮ LIỆU MỚI (không cần đổi mã nguồn):
    from scripts.eda_all_datasets import dataframe_report
    for name, frame in {"NEW_A": df_a, "NEW_B": df_b, "NEW_C": df_c}.items():
        dataframe_report(frame, name, root=".")

Có nhãn nhị phân, chọn cột và so sánh test:
    dataframe_report(df_a, "NEW_A", ".", target="converted",
                     numeric_columns=["income", "tenure"],
                     categorical_columns=["channel"], group_columns=["channel"],
                     meanings={"income": ("Thu nhập", "Xác minh đơn vị")}, test=df_a_test)
Không truyền target nếu chưa có nhãn. Không tự tạo nhãn từ giả định nghiệp vụ.
Nhãn thiếu bị loại khỏi mẫu số tỷ lệ; nhãn khác 0/1 cần được định nghĩa lại.
Các cột số/phân loại tự nhận diện theo dtype nếu không chỉ định; hãy loại ID
qua numeric_columns/categorical_columns. Hàm không thay thế dữ liệu gốc.

Tự xây báo cáo cho dataset bất kỳ:
    r = Report("NEW", "Báo cáo mới", root=".")
    r.add("overview", "Tổng quan", "Mô tả quần thể...",
          [("Thống kê", numeric_table(df, ["income"]))])
    r.publish()                  # không gọi adapter ba bộ cũ
    r.publish(prepare=my_hook)   # tùy chọn: my_hook(report)

CHẠY CSV MỚI BẰNG JSON, ví dụ eda_config.json (tự đặt tên bộ và tên cột):
    {"NEW_A": {"file": "train.csv", "target": "converted"},
     "NEW_B": {"file": "observations.csv", "plots": false},
     "NEW_C": {"file": "train.csv", "test_file": "test.csv"}}
Đường dẫn tương đối nằm trong data/raw/<tên_bộ>/; cũng nhận đường dẫn tuyệt đối.
    python scripts/eda_all_datasets.py --config eda_config.json
    python scripts/eda_all_datasets.py --config eda_config.json --dataset NEW_A
JSON nhận các tùy chọn của dataframe_report và read_csv_options (sep, encoding...).
Entry point này đọc CSV vào RAM; với dữ liệu lớn, viết adapter đọc chunk và dùng
TrainColumns(rows, numeric_columns, label_columns=["converted"]) hoặc
label_columns=() khi không có nhãn. full_missing_diagnostics nhận label_column
tùy chọn (None nếu không có nhãn); exact_spearman mặc định dùng numeric_columns.

Đăng ký adapter riêng bằng register_report(name, builder), trong đó builder(root)
trả về Report; chạy với build_report(name, root). Khi xuất notebook cho adapter
Python riêng, truyền notebook_setup là đoạn mã đăng ký lại adapter sau khi nạp
module dưới tên eda. register_csv_report tự lưu cấu hình vào notebook.

Các hàm hotel_report/airbnb_report/expedia_report, enrich_*, deepen_*, risks,
proposals, restructure và source_section vẫn dành cho schema ba bộ gốc.
Chúng không nằm trong luồng dataframe_report cho bộ mới.

File chứa phần triển khai của toàn bộ hàm/class trong 7 script phân tích
hiện có, gồm đọc raw CSV, từ điển biến, chất lượng dữ liệu, thống kê mô tả,
phân phối, missing, IQR/outlier, tương quan, tỷ lệ nhóm và Wilson 95%, drift,
kiểm tra nhãn/leakage, thời gian/cohort, sessions và dựng báo cáo/notebook.
Các hàm trùng tên được thêm tiền tố airbnb_, hotel_ hoặc hotel_expedia_.
Các thiết kế chia tập và nghiên cứu chỉ là mô tả, chưa huấn luyện mô hình.

CÁCH DÙNG (chạy tại thư mục gốc dự án):
    python scripts/eda_all_datasets.py --list-functions
    python scripts/eda_all_datasets.py --dataset HOTEL
    python scripts/eda_all_datasets.py --dataset AIRBNB
    python scripts/eda_all_datasets.py --dataset EXPEDIA
    python scripts/eda_all_datasets.py                 # chạy cả 3 bộ
    python scripts/eda_all_datasets.py --root "đường/dẫn/dự/án" --dataset HOTEL

Import vào notebook để dùng từng hàm, không tự đọc dữ liệu khi import:
    from scripts.eda_all_datasets import numeric_table, rate_table, iqr_table
    summary = numeric_table(df, ["lead_time", "adr"])
    rates = rate_table(df, "hotel", "is_canceled")
    outliers = iqr_table(df, ["adr"], "toàn bộ HOTEL")

PHỤ THUỘC: pandas, numpy, scipy, matplotlib; nbformat, IPython và tzdata
để dựng/xác minh notebook. Cần CSV đúng cấu trúc data/raw/{HOTEL,AIRBNB,EXPEDIA}/.
Không cần 7 script gốc để sử dụng file này. Đây là bản tổng hợp tại thời điểm
tạo; sửa script gốc sau này sẽ không tự cập nhật vào file này.

ĐẦU RA KHI CHẠY: reports/<DATASET>/README.md, figures/, analysis_metadata.json,
notebooks/<DATASET>/*_descriptive_report.ipynb; cập nhật reports/README.md khi
có đủ metadata cả ba bộ. Các file báo cáo tương ứng được ghi đè.
Raw CSV chỉ được đọc. Expedia dùng bộ đệm cột raw tạm trên đĩa và xóa sau
khi chạy, thống kê trên toàn bộ train; chỉ mẫu hiển thị được lấy mẫu.
Không tạo feature dataset hoặc huấn luyện mô hình.

MỤC LỤC HÀM/CLASS (theo nhóm nguồn):
  EDA chung: chất lượng, missing, outlier, tương quan:
    unit, role, dictionary_details, category_cardinality, section, subsection, combine, fig_note, source_section, iqr_table, missing_plot, correlation_scatter, category_panel, outlier_panel, risks, proposals, restructure, diagnostic_sections, enrich_hotel, enrich_airbnb, enrich_expedia
  EXPEDIA: thống kê chính xác toàn bộ train, đọc theo chunk:
    progress, working_directory, TrainColumns, full_numeric_statistics, exact_spearman, full_missing_diagnostics, correlation_plot
  AIRBNB: trình bày và kiểm tra tính nhất quán báo cáo:
    airbnb_display_header, normalize_prose, human_title, open_questions, apply_stage_one, variable_name, apply_stage_two, column_decisions, relationship_figure, apply_stage_three, timeline_figure, executive_sources, apply_stage_four, walk_sections, normalize_text, capture_evidence, airbnb_prepare_publication, airbnb_verify_artifacts
  AIRBNB: sessions, nhãn, liên hệ thống kê và cohort:
    session_action_counts, airbnb_grouped_rates, categorical_association, bh_qvalues, p_text, association_tables, booking_delay_tables, cohort_strata, compact_strata, heatmap_rates, session_audit, proposed_protocol, reproducibility_section, deepen_airbnb
  AIRBNB: nhãn 90 ngày, follow-up và mốc dự đoán:
    conditional_labels, protocol_90, profile_action_counts, rates_two_targets, profile_evidence, indirect_profile_evidence, followup_evidence, timeline_with_embargo, apply_research_revision, plot_profiles, plot_followup_and_cohorts, revise_research_design, research_roles, revise_executive
  HOTEL / EXPEDIA: liên hệ, thời gian và thiết kế nghiên cứu:
    walk, hotel_grouped_rates, categorical_effect, rank_effect, hotel_associations, standardize_hotels, hotel_temporal_protocol, effect_plot, deepen_hotel, expedia_protocol, deepen_expedia, glossary, usage_decisions, questions, proposed_design, design_figures, hotel_expedia_display_header, hotel_expedia_prepare_publication, hotel_expedia_verify_artifacts, walk_sections_from_metadata
  Đọc dữ liệu, thống kê mô tả và dựng báo cáo cả 3 bộ:
    pct, count, md_table, wilson, rate_table, numeric_table, categorical_table, drift_table, metadata_table, Report, show_section, manifest, hotel_report, airbnb_report, _combine_group, scan_expedia, expedia_report, _expedia_report, build_report, make_notebook, write_summary, main
"""
from __future__ import annotations

# Thiết lập backend trước mọi import pyplot, dùng được trên máy không có GUI.
import matplotlib
matplotlib.use("Agg")

# Mục lục để tra cứu bằng --list-functions; SHA-256 nhận diện bản nguồn.
FUNCTION_GROUPS = {'EDA chung: chất lượng, missing, outlier, tương quan': ['unit',
                                                         'role',
                                                         'dictionary_details',
                                                         'category_cardinality',
                                                         'section',
                                                         'subsection',
                                                         'combine',
                                                         'fig_note',
                                                         'source_section',
                                                         'iqr_table',
                                                         'missing_plot',
                                                         'correlation_scatter',
                                                         'category_panel',
                                                         'outlier_panel',
                                                         'risks',
                                                         'proposals',
                                                         'restructure',
                                                         'diagnostic_sections',
                                                         'enrich_hotel',
                                                         'enrich_airbnb',
                                                         'enrich_expedia'],
 'EXPEDIA: thống kê chính xác toàn bộ train, đọc theo chunk': ['progress',
                                                               'working_directory',
                                                               'TrainColumns',
                                                               'full_numeric_statistics',
                                                               'exact_spearman',
                                                               'full_missing_diagnostics',
                                                               'correlation_plot'],
 'AIRBNB: trình bày và kiểm tra tính nhất quán báo cáo': ['airbnb_display_header',
                                                          'normalize_prose',
                                                          'human_title',
                                                          'open_questions',
                                                          'apply_stage_one',
                                                          'variable_name',
                                                          'apply_stage_two',
                                                          'column_decisions',
                                                          'relationship_figure',
                                                          'apply_stage_three',
                                                          'timeline_figure',
                                                          'executive_sources',
                                                          'apply_stage_four',
                                                          'walk_sections',
                                                          'normalize_text',
                                                          'capture_evidence',
                                                          'airbnb_prepare_publication',
                                                          'airbnb_verify_artifacts'],
 'AIRBNB: sessions, nhãn, liên hệ thống kê và cohort': ['session_action_counts',
                                                        'airbnb_grouped_rates',
                                                        'categorical_association',
                                                        'bh_qvalues',
                                                        'p_text',
                                                        'association_tables',
                                                        'booking_delay_tables',
                                                        'cohort_strata',
                                                        'compact_strata',
                                                        'heatmap_rates',
                                                        'session_audit',
                                                        'proposed_protocol',
                                                        'reproducibility_section',
                                                        'deepen_airbnb'],
 'AIRBNB: nhãn 90 ngày, follow-up và mốc dự đoán': ['conditional_labels',
                                                    'protocol_90',
                                                    'profile_action_counts',
                                                    'rates_two_targets',
                                                    'profile_evidence',
                                                    'indirect_profile_evidence',
                                                    'followup_evidence',
                                                    'timeline_with_embargo',
                                                    'apply_research_revision',
                                                    'plot_profiles',
                                                    'plot_followup_and_cohorts',
                                                    'revise_research_design',
                                                    'research_roles',
                                                    'revise_executive'],
 'HOTEL / EXPEDIA: liên hệ, thời gian và thiết kế nghiên cứu': ['walk',
                                                                'hotel_grouped_rates',
                                                                'categorical_effect',
                                                                'rank_effect',
                                                                'hotel_associations',
                                                                'standardize_hotels',
                                                                'hotel_temporal_protocol',
                                                                'effect_plot',
                                                                'deepen_hotel',
                                                                'expedia_protocol',
                                                                'deepen_expedia',
                                                                'glossary',
                                                                'usage_decisions',
                                                                'questions',
                                                                'proposed_design',
                                                                'design_figures',
                                                                'hotel_expedia_display_header',
                                                                'hotel_expedia_prepare_publication',
                                                                'hotel_expedia_verify_artifacts',
                                                                'walk_sections_from_metadata'],
 'Đọc dữ liệu, thống kê mô tả và dựng báo cáo cả 3 bộ': ['pct',
                                                         'count',
                                                         'md_table',
                                                         'wilson',
                                                         'rate_table',
                                                         'numeric_table',
                                                         'categorical_table',
                                                         'drift_table',
                                                         'metadata_table',
                                                         'Report',
                                                         'show_section',
                                                         'manifest',
                                                         'hotel_report',
                                                         'airbnb_report',
                                                         '_combine_group',
                                                         'scan_expedia',
                                                         'expedia_report',
                                                         '_expedia_report',
                                                         'build_report',
                                                         'make_notebook',
                                                         'write_summary',
                                                         'main']}
SOURCE_SNAPSHOT_SHA256 = {'eda_diagnostics.py': '9e370009529921096180542336db80e9ba3c869d48ef9dce089cfba522e6c521',
 'expedia_full_train.py': '994a5145acaecd47ec450d0d808605762e91c7ffce1b1cc5d2a80ee7eb3964e3',
 'airbnb_report_presentation.py': '52d261b7a960b02eacd225c07eda9c3d34f49465cb0b00096b8717ec632c003f',
 'airbnb_deep_dive.py': '2a64165923cb92e5727a9f56ade846222f3f6bec3e94c1be86a3e2177aa8238a',
 'airbnb_research_revision.py': '4a896e24389d5ed410b809a308455d9597518649edd3a519039639007e317bd0',
 'hotel_expedia_research.py': '01c5377e5dc04287d984268a673a3db00562c544aadcaec0b724cdf421ba8d00',
 'build_descriptive_reports.py': '1ef214b0ac53762f579007756793286c9e22dcab070d3d048e04cafab0b74296'}


# ==============================================================================
# EDA chung: chất lượng, missing, outlier, tương quan
# Nguồn: eda_diagnostics.py — nội dung đã gộp, không cần import file gốc.
# ==============================================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SEED = 42
BLUE, ORANGE, GREEN = "#245D80", "#C76A37", "#468477"
SECTION_LAYOUT = [
    ("executive","Tóm tắt điều hành — dữ liệu là gì, đáng tin đến đâu, dùng cho việc gì"),
    ("overview","1. Tổng quan bộ dữ liệu"),
    ("quality_main","2. Chất lượng dữ liệu"),
    ("univariate","3. Phân tích đơn biến"),
    ("multivariate_main","4. Phân tích đa biến, thời gian và nhóm con"),
    ("risks","5. Hạn chế, rủi ro và quyền riêng tư"),
    ("conclusion_main","6. Kết luận và đề xuất bước tiếp theo"),
    ("appendix","Phụ lục — từ điển và bảng chi tiết"),
    ("reproducibility","Tái lập và kiểm soát phạm vi"),
]


def unit(name):
    if name in {"age"}: return "năm tuổi khai báo"
    if name in {"account_day","first_active_day"}: return "ngày từ mốc gốc trên biểu đồ"
    if name in {"lead_time","days_in_waiting_list","srch_booking_window"}: return "ngày"
    if name in {"adr"}: return "tiền/đêm; xác minh đồng tiền của bản CSV"
    if name in {"price_usd"}: return "USD; cần xác minh theo đêm/toàn kỳ"
    if name in {"visitor_hist_adr_usd","gross_bookings_usd"}: return "USD"
    if name.endswith("rate_percent_diff"): return "% theo định nghĩa nguồn"
    if name in {"stays_in_weekend_nights","stays_in_week_nights","srch_length_of_stay"}: return "đêm"
    if name in {"adults","children","babies","srch_adults_count","srch_children_count"}: return "người"
    if name in {"srch_room_count"}: return "phòng"
    if name in {"required_car_parking_spaces"}: return "chỗ đỗ xe"
    if name in {"previous_cancellations","previous_bookings_not_canceled","booking_changes","total_of_special_requests"}: return "lần/booking/yêu cầu theo tên biến"
    if name in {"prop_starrating","visitor_hist_starrating"}: return "sao"
    if name in {"prop_review_score","prop_location_score1","prop_location_score2","srch_query_affinity_score"}: return "điểm theo thang nguồn"
    if name in {"prop_log_historical_price"}: return "log giá; cơ số cần xác minh"
    if name in {"orig_destination_distance"}: return "khoảng cách; đơn vị cần xác minh"
    if name in {"date_account_created","date_first_booking","reservation_status_date","date_time","timestamp_first_active"}: return "ngày/giờ theo định dạng nguồn; timezone chưa xác minh"
    if name.startswith("arrival_date_"): return "thành phần lịch theo tên biến"
    if name in {"position"}: return "thứ hạng hiển thị"
    if name.endswith("_bool") or name in {"is_canceled","is_repeated_guest","promotion_flag"}: return "cờ 0/1"
    return "mã/nhãn phân loại, không có đơn vị vật lý"


def role(name):
    if name in {"is_canceled","country_destination","click_bool","booking_bool"}: return "đích"
    if name in {"date_first_booking","gross_bookings_usd","reservation_status","reservation_status_date"}: return "kết quả / nguy cơ rò rỉ đích"
    if name in {"id","srch_id","prop_id","agent","company"}: return "định danh / khóa nhóm, không phải số liên tục"
    if name=="position": return "metadata hiển thị, chỉ có train"
    return "đầu vào ứng viên; chưa xác nhận khả dụng tại t0"


def dictionary_details(report,frame,full_stats=None,full_cat=None,full_domains=None):
    target=next(s for s in report.sections if s["key"]=="dictionary")
    stats=full_stats.set_index("column") if full_stats is not None else None
    label,table=target["tables"][0]
    table=table.copy();domains=[]
    for c in table.column:
        if c in {"id","srch_id","prop_id"}:
            domain="Khóa/mã; không in giá trị định danh cá nhân trong báo cáo"
        elif full_domains is not None and c in full_domains:
            domain=full_domains[c]
        elif stats is not None and c in stats.index:
            row=stats.loc[c];domain=f"Toàn file: [{row.full_min:g}, {row.full_max:g}]; NA thống kê riêng"
        elif full_cat is not None and c in full_cat:
            vals=full_cat[c][c].dropna().sort_values().astype(str).tolist()
            domain="Toàn file: "+", ".join(vals) if len(vals)<=12 else f"Toàn file: {len(vals)} mã khác nhau"
        elif c in frame:
            s=frame[c].dropna();n=s.nunique()
            prefix="Mẫu hash: " if full_stats is not None else "Toàn bảng: "
            if n<=12: domain=prefix+", ".join(repr(x) for x in sorted(s.unique(),key=str))
            elif pd.api.types.is_numeric_dtype(s): domain=prefix+f"[{s.min():g}, {s.max():g}], {n} giá trị phân biệt"
            elif c.startswith("date_"): domain=prefix+f"{s.min()}–{s.max()}"
            else: domain=prefix+f"{n} giá trị khác nhau; top category tại phụ lục"
        else:
            domain="Không kiểm kê đủ domain ở sample; xem mô tả nguồn và missing toàn file"
        domains.append(domain)
    table["role"]=table.column.map(role)
    table["unit"]=table.column.map(unit)
    table["observed_domain_and_basis"]=domains
    target["tables"][0]=(label,table)


def category_cardinality(frame,columns):
    rows=[]
    for c in columns:
        vc=frame[c].value_counts(dropna=False)
        rare=vc.lt(100)
        rows.append([c,len(vc),int(rare.sum()),int(vc[rare].sum()),vc[rare].sum()/len(frame)*100])
    return pd.DataFrame(rows,columns=["column","groups_including_na","groups_under_100","rows_in_rare_groups","pct_rows_rare"])

SOURCES = {
    "HOTEL": {
        "publisher": "Nuno Antonio, Ana de Almeida, Luis Nunes — Data in Brief; bản CSV gộp được phổ biến qua Kaggle",
        "year": "2018 online; Data in Brief tập 22, 2019",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/",
        "purpose": "Trích xuất PMS để nghiên cứu nhu cầu và kết quả hủy booking ở hai khách sạn Bồ Đào Nha.",
        "collection": "Dữ liệu vận hành PMS/SQL và booking change log; hai cơ sở ở Algarve và Lisbon. Không phải mẫu ngẫu nhiên toàn ngành.",
        "license": "Bài báo nguồn ghi CC BY (4.0). Nguồn tải/phiên bản của chính bản CSV gộp trên máy chưa được ghi lại; không suy giấy phép CSV chỉ từ giấy phép bài báo.",
        "terms_url": "https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand",
    },
    "AIRBNB": {
        "publisher": "Airbnb / Kaggle — Airbnb New User Bookings",
        "year": "Cuộc thi công bố 2015, kết thúc 2016",
        "url": "https://www.kaggle.com/c/airbnb-recruiting-new-user-bookings/data",
        "purpose": "Dự đoán quốc gia của lượt đặt chỗ đầu tiên cho người dùng mới để cá nhân hóa nội dung.",
        "collection": "Dữ liệu gồm hồ sơ đăng ký, nhật ký web/ứng dụng và các bảng tổng hợp của người dùng từ Mỹ. CSV chưa lưu chi tiết cách chọn người dùng và ngày kết thúc theo dõi của từng người.",
        "license": "Competition Rules, không phải giấy phép mở CC0/CC BY. Điều khoản DATA có giới hạn mục đích sử dụng và phân phối; phải đối chiếu rules trước khi tái sử dụng hoặc công bố dữ liệu.",
        "terms_url": "https://www.kaggle.com/competitions/airbnb-recruiting-new-user-bookings/rules",
    },
    "EXPEDIA": {
        "publisher": "Expedia / Kaggle — Personalize Expedia Hotel Searches, ICDM 2013",
        "year": "2013",
        "url": "https://www.kaggle.com/c/expedia-personalized-sort/data",
        "purpose": "Cá nhân hóa thứ tự khách sạn trong danh sách tìm kiếm dựa trên click/booking.",
        "collection": "Search logs, thông tin property, giá/đối thủ và thứ tự hiển thị. Cơ chế chọn search vào bản dữ liệu chưa được giải thích đầy đủ trong file local.",
        "license": "Điều khoản cuộc thi Expedia, không xác nhận có giấy phép dữ liệu mở. Phần License trong rules nói về winning entry, không đồng nghĩa giấy phép công bố lại raw data.",
        "terms_url": "https://storage.googleapis.com/kaggle-media/competitions/kaggle/3504/media/Expedia%20Personalized%20Sort%20Official%20Competition%20Rules%20Final.pdf",
    },
}


def section(key, title, text, tables=(), figures=()):
    return dict(key=key, title=title, text=text.strip(), tables=list(tables), figures=list(figures))


def subsection(s):
    copy = dict(s)
    # Inner titles retain descriptions without reusing the old chapter number.
    copy["title"] = s["title"].split(". ", 1)[-1] if s["title"][:1].isdigit() else s["title"]
    return copy


def combine(key, title, entries, text=""):
    s = section(key, title, text)
    s["blocks"] = [subsection(e) for e in entries]
    return s


def fig_note(report, path, text):
    report.figure_notes[path.name] = text


def source_section(report, coverage):
    src = SOURCES[report.dataset]
    inventory=next(s for s in report.sections if s["key"]=="scope")["tables"][0][1]
    rows = [
        ["Tên / nơi công bố", src["publisher"]], ["Năm công bố", src["year"]],
        ["Mục đích thu thập/công bố", src["purpose"]], ["Cách thu thập / quần thể", src["collection"]],
        ["Thời gian bao phủ quan sát được", coverage], ["Ngày tải raw", "Chưa được ghi lại; không dùng mtime/ctime để thay ngày tải"],
        ["Quy mô bảng train/chính",f"{report.facts['rows']:,} dòng × {report.facts['columns']} cột thô"],
        ["Dung lượng mọi CSV của bộ hiện có",f"{int(inventory.bytes.sum()):,} byte = {inventory.bytes.sum()/1024**2:,.2f} MiB; gồm cả bảng phụ/benchmark nếu có"],
        ["Phiên bản local", "Nhận diện bằng tên file, bytes, số dòng và SHA-256 tại phụ lục"],
        ["Giấy phép / điều khoản", src["license"]],
    ]
    return section("source", "Nguồn gốc và phạm vi thu thập", f"Nguồn công bố: [trang dữ liệu/nghiên cứu gốc]({src['url']}). [Giấy phép/điều khoản và trang phân phối]({src['terms_url']}). Thông tin nào chưa được lưu hoặc chưa xác minh được được ghi rõ, không điền bằng giả định.", [("Thông tin nguồn và phiên bản", pd.DataFrame(rows, columns=["item", "description"]))])


def iqr_table(frame, columns, population):
    rows=[]
    for c in columns:
        s=frame[c].dropna()
        q1,q3=s.quantile([.25,.75]); width=q3-q1
        lo,hi=q1-1.5*width,q3+1.5*width
        flagged=(s<lo)|(s>hi)
        rows.append([c,population,len(s),q1,q3,width,lo,hi,int(flagged.sum()),flagged.mean()*100,width==0])
    return pd.DataFrame(rows,columns=["column","population","nonnull_n","q1","q3","iqr","lower_fence","upper_fence","flagged_n","flagged_pct_nonnull","iqr_zero"])


def missing_plot(report, data, columns, group, group_name, sample_note, *, axis_labels=None):
    """Plot missingness for any dataset; override titles/axes with axis_labels."""
    axis_labels = axis_labels or {}
    chosen=[c for c in columns if c in data and data[c].isna().any()]
    rates=data[chosen].isna().mean().sort_values(ascending=False)
    chosen=list(rates.index[:12])
    if not chosen:
        raise ValueError("Missing plot requires at least one missing column")
    mask=data[chosen].isna()
    rows=mask.sample(n=min(300,len(mask)),random_state=SEED).sort_values(chosen,kind="stable")
    grouped=mask.groupby(pd.Series(group,index=data.index).fillna("<MISSING>"),dropna=False).mean()*100
    fig,axes=plt.subplots(1,2,figsize=(15,4.8),gridspec_kw={"width_ratios":[1.3,1]})
    axes[0].imshow(rows.to_numpy(dtype=int),aspect="auto",interpolation="nearest",cmap="Blues",vmin=0,vmax=1)
    axes[0].set(title=f"Missingness pattern: {len(rows)} displayed rows",ylabel="Descriptive row sample; sorted by pattern")
    axes[0].set_xticks(range(len(chosen)));axes[0].set_xticklabels(chosen,rotation=65,ha="right")
    axes[0].set(title=axis_labels.get("pattern_title", f"Missingness pattern: {len(rows)} displayed rows"),
                xlabel=axis_labels.get("xlabel", "Columns"),
                ylabel=axis_labels.get("pattern_ylabel", "Display sample; sorted by pattern"))
    im=axes[1].imshow(grouped.to_numpy(),aspect="auto",vmin=0,vmax=100,cmap="Blues")
    axes[1].set(title=f"Missing by {group_name} (%)",ylabel=group_name)
    axes[1].set_yticks(range(len(grouped)));axes[1].set_yticklabels(grouped.index.astype(str))
    axes[1].set_xticks(range(len(chosen)));axes[1].set_xticklabels(chosen,rotation=65,ha="right")
    axes[1].set(title=axis_labels.get("group_title", f"Missing by {group_name} (%)"),
                xlabel=axis_labels.get("xlabel", "Columns"),
                ylabel=axis_labels.get("group_ylabel", group_name))
    fig.colorbar(im,ax=axes[1],label=axis_labels.get("colorbar", "Missing (%)"),fraction=.035,pad=.03);fig.tight_layout()
    path=report.savefig("missing_patterns",fig)
    top=chosen[0]
    spread=grouped.max()-grouped.min();largest=spread.idxmax()
    note=f"Nhận xét: {top} thiếu {rates[top]*100:.2f}% trong {sample_note}; chênh lệch missing lớn nhất giữa các nhóm {group_name} là {spread[largest]:.2f} điểm phần trăm ở {largest}. Ô xanh là NA. Mẫu dòng hiển thị dùng seed={SEED}; việc sắp theo pattern chỉ để nhìn cụm thiếu, không phải thứ tự thời gian. Các khác biệt này không đủ kết luận cơ chế MCAR/MAR/MNAR."
    fig_note(report,path,note)
    group_table=grouped.reset_index().rename(columns={grouped.index.name or "index":group_name})
    return path,group_table,mask.corr().reset_index(names="column"),note


def correlation_scatter(report, data, cols, x, y, sample_name):
    corr=data[cols].corr(method="spearman")
    valid=data[[x,y]].dropna()
    plot=valid.sample(n=min(4000,len(valid)),random_state=SEED)
    fig,axes=plt.subplots(1,2,figsize=(15,6),gridspec_kw={"width_ratios":[1.2,1]})
    im=axes[0].imshow(corr,vmin=-1,vmax=1,cmap="RdBu_r")
    axes[0].set(title="Spearman correlation; pairwise complete")
    axes[0].set_xticks(range(len(cols)));axes[0].set_xticklabels(cols,rotation=65,ha="right",fontsize=8)
    axes[0].set_yticks(range(len(cols)));axes[0].set_yticklabels(cols,fontsize=8)
    fig.colorbar(im,ax=axes[0],label="Spearman rho",fraction=.03,pad=.03)
    axes[1].scatter(plot[x],plot[y],s=7,alpha=.15,color=BLUE,rasterized=True)
    axes[1].set(xlabel=f"{x}\n({unit(x)})",ylabel=f"{y}\n({unit(y)})",title=f"Scatter: {len(plot):,} displayed pairs")
    logarithmic=bool(valid[y].max()>20*max(float(valid[y].median()),1))
    if logarithmic: axes[1].set_yscale("symlog",linthresh=1)
    fig.tight_layout();path=report.savefig("multivariate",fig)
    pairs=[(a,b,corr.loc[a,b]) for i,a in enumerate(cols) for b in cols[i+1:] if pd.notna(corr.loc[a,b])]
    pairs=sorted(pairs,key=lambda z:-abs(z[2]))
    a,b,rho=pairs[0]
    note=f"Nhận xét: trong {sample_name}, cặp có |rho| lớn nhất của ma trận công bố là {a}–{b} (rho={rho:.3f}); riêng {x}–{y} có rho={corr.loc[x,y]:.3f}. Scatter chỉ hiển thị tối đa 4.000 cặp không thiếu, seed={SEED}; đơn vị từng biến xem từ điển. Heatmap dùng dữ liệu {sample_name}, không chỉ các điểm scatter. Tương quan cao là dấu hiệu chồng lặp để kiểm tra, không tự chứng minh đa cộng tuyến tuyến tính hoặc quan hệ nhân quả."
    if logarithmic: note+=" Trục y của scatter dùng thang symlog để đọc đuôi dài; giá trị raw không bị biến đổi/lưu lại."
    fig_note(report,path,note)
    return path,corr.reset_index(names="column"),note


def category_panel(report, data, column, target, population, *, axis_labels=None):
    axis_labels = axis_labels or {}
    validate_binary_target(data[target], target)
    table=data.groupby(column,dropna=False,observed=True)[target].agg(n="count",positive="sum").sort_values("n",ascending=False)
    total=len(table);rare=table.n.lt(100)
    shown=table.head(8).copy();shown["positive_pct"]=shown.positive/shown.n*100
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    labels=shown.index.astype(str)
    axes[0].bar(labels,shown.n,color=BLUE);axes[0].set(title=f"{column}: top groups",ylabel=f"{population} (count)")
    axes[1].bar(labels,shown.positive_pct,color=ORANGE);axes[1].set(title="Observed target rate within group",ylabel="Target = 1 (%)")
    for ax in axes: ax.tick_params(axis="x",rotation=35)
    axes[0].set(title=axis_labels.get("count_title", f"{column}: top groups"),
                xlabel=column, ylabel=axis_labels.get("count_ylabel", f"{population} (count)"))
    axes[1].set(title=axis_labels.get("rate_title", "Observed target rate within group"),
                xlabel=column, ylabel=axis_labels.get("rate_ylabel", f"{target} = 1 (%)"))
    fig.tight_layout();path=report.savefig("categories_and_target",fig)
    largest=shown.iloc[0];label=shown.index[0]
    na_note="bao gồm NA" if data[column].isna().any() else "không có NA"
    note=f"Nhận xét: {column} có {total} nhóm ({na_note}); {int(rare.sum())} nhóm dưới 100 quan sát. Nhóm lớn nhất {label} có {int(largest.n):,} quan sát, tỷ lệ nhãn 1 là {largest.positive_pct:.2f}%. Hai trục trả lời số lượng nhóm và tỷ lệ bên trong nhóm, không dùng lẫn mẫu số; phân tầng cohort được trình bày tại phần đa biến."
    fig_note(report,path,note)
    return path,table.reset_index(),note


def outlier_panel(report, frame, columns, target, population, *, units=None, axis_labels=None):
    validate_binary_target(frame[target], target)
    units = units or {}
    axis_labels = axis_labels or {}
    stats=iqr_table(frame,columns,population)
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    x=columns[0];y=columns[1] if len(columns)>1 else columns[0]
    axes[0].boxplot(frame[x].dropna(),showfliers=True,orientation="horizontal")
    axes[0].set(xlabel=f"{x}\n({units.get(x, 'đơn vị chưa cung cấp')})",title=f"{x}: raw boxplot",yticks=[])
    logarithmic=bool(frame[x].max()>20*max(float(frame[x].median()),1))
    if logarithmic: axes[0].set_xscale("symlog",linthresh=1)
    groups=[];labels=[]
    for value in sorted(frame[target].dropna().unique()):
        s=frame.loc[frame[target].eq(value),y].dropna()
        if len(s): groups.append(s);labels.append(str(value))
    if not groups:
        plt.close(fig)
        raise ValueError("Outlier panel requires nonmissing numeric values with observed labels")
    axes[1].boxplot(groups,tick_labels=labels,showfliers=False)
    axes[1].set(title=f"{y} by target; fliers hidden",xlabel=target,ylabel=f"{y}\n({units.get(y, 'đơn vị chưa cung cấp')})")
    axes[0].set(title=axis_labels.get("raw_title", f"{x}: raw boxplot"))
    axes[1].set(title=axis_labels.get("group_title", f"{y} by {target}; fliers hidden"))
    fig.tight_layout();path=report.savefig("outliers_and_target",fig)
    row=stats.iloc[0]
    med=frame.groupby(target)[y].median()
    note=f"Nhận xét: theo hàng rào Q1−1,5×IQR và Q3+1,5×IQR, {x} có {int(row.flagged_n):,}/{int(row.nonnull_n):,} giá trị bị gắn cờ ({row.flagged_pct_nonnull:.2f}%) trong {population}; đây là bất thường thống kê, chưa phải lỗi nhập liệu. Median {y} theo nhãn: "+", ".join(f"{k}={v:.2f}" for k,v in med.items())+". Boxplot bên phải ẩn các điểm ngoài whisker để đọc vùng giữa, không xóa chúng khỏi bảng hay raw. Đơn vị xem từ điển; IQR=0 ở biến rời rạc có thể gắn cờ nhiều giá trị thật."
    if logarithmic: note+=" Trục x boxplot raw dùng symlog; hàng rào IQR vẫn tính trên giá trị raw, không phải log."
    fig_note(report,path,note)
    return path,stats,note


def risks(report):
    specific={
        "HOTEL":[["Quyền riêng tư","Nguồn đã loại thông tin định danh trực tiếp; không có customer/booking ID để liên kết tin cậy. Quốc gia, ngày đến, cấu trúc đoàn vẫn là thông tin có thể kết hợp."],["Quần thể","Hai khách sạn ở Bồ Đào Nha và một giai đoạn lịch sử, không đại diện cho mọi khách sạn hoặc thị trường Việt Nam."],["Phụ thuộc / bias","Booking theo đoàn hoặc khách lặp không nhận diện được; duplicate có thể làm khoảng tin cậy quá hẹp."],["Rò rỉ","Trạng thái cuối và ngày trạng thái là kết quả; các biến cập nhật theo vòng đời cần lịch sử tại t0."]],
        "AIRBNB":[["Quyền riêng tư","ID là mã giả danh; age, gender, ngày hoạt động, device và log hành vi vẫn có thể là quasi-identifier. Không nêu ID cá nhân trong báo cáo."],["Quần thể","Users từ Mỹ, signup trong thời kỳ lịch sử; nhóm signup mới có thời gian theo dõi khác và độ phủ sessions khác."],["Nhóm nhỏ / bias","PT/AU và các category hiếm có ít quan sát; khác biệt theo giới/tuổi/kênh có thể bị cohort và missing chi phối."],["Rò rỉ","date_first_booking tiết lộ nhãn; log không có timestamp nên chưa xác nhận được cửa sổ trước t0."]],
        "EXPEDIA":[["Quyền riêng tư","Không có user ID trực tiếp trong schema; thời gian, vị trí quốc gia và hồ sơ lịch sử vẫn là thông tin hành vi. Không suy lại danh tính."],["Quần thể","Train không có search không click; xếp hạng, exposure và cách chọn mẫu làm tỷ lệ khác toàn bộ traffic."],["Phụ thuộc / bias","Nhiều property trong một search phụ thuộc nhau; chưa có user ID để kiểm soát searches lặp của cùng người."],["Rò rỉ","gross_bookings_usd là kết quả; position không có trong test; click tương lai không dùng để dự đoán trước click."]],
    }[report.dataset]
    specific += [["Đồng ý / quyền sử dụng","CSV không có biểu mẫu đồng ý hay hồ sơ pháp lý thu thập. Không suy dữ liệu công khai = đồng ý cho mọi mục đích; đọc điều khoản nguồn, không tự gán giấy phép mở."],["Giới hạn suy luận","EDA là mô tả, không phải kiểm định tác động can thiệp. Khoảng Wilson nếu có chỉ theo giả định độc lập; chưa đánh giá chất lượng mô hình hoặc tính công bằng của mô hình."]]
    return section("risks","5. Hạn chế, rủi ro và quyền riêng tư","Tách điều đã quan sát khỏi nguyên nhân chưa được chứng minh. Không diễn giải chênh lệch nhóm thành đặc điểm cố hữu của giới tính/tuổi/quốc gia và không thực hiện nhận diện lại cá nhân.",[("Rủi ro và giới hạn sử dụng",pd.DataFrame(specific,columns=["issue","evidence_or_limit"]))])


def proposals(report):
    rows={
        "HOTEL":[["Missing / ID","Agent/company có thể không áp dụng; children có NA","Đối chiếu nghĩa NULL; cân nhắc category không áp dụng, imputation chỉ học trên train nếu cần"],["Outlier / duplicate","Tỷ lệ nhãn nhạy với bỏ trùng; ADR/0 đêm cần xác minh","Xác minh khóa và nghiệp vụ, phân tích độ nhạy trước khi xóa/clipping"],["Mã hóa / chuẩn hóa","ID/category khác đại lượng số","Mã hóa phù hợp; chỉ cân nhắc scaling cho mô hình nhạy thang đo, không bắt buộc cho cây"],["Cân bằng lớp","Nhãn 1 khoảng 37%, chưa phải cực hiếm","Bắt đầu với phân phối gốc; không tự động SMOTE/weight"],["Feature engineering (đề xuất)","Có số đêm và lịch đến; nhiều cột cập nhật theo vòng đời","Có thể nghiên cứu cấu trúc lưu trú/lịch sau khi chốt t0; mọi tỷ lệ phải xử lý mẫu số 0"],["Hướng mô hình (đề xuất)","Target booking nhị phân","Baseline xác suất và mô hình nhị phân; đánh giá theo thời gian, calibration và chi phí vận hành sau khi kiểm soát leakage"]],
        "AIRBNB":[["Missing / tuổi","Tuổi thiếu, unknown và giá trị dạng năm sinh","Xác minh tuổi; cân nhắc missing category/median học trên train; không tự đổi mọi 19xx thành tuổi"],["Mã hóa / chuẩn hóa","Nhiều category hiếm và mã signup_flow","Mã hóa trong từng tập train; kiểm tra category mới; scaling chỉ theo nhu cầu mô hình"],["Cân bằng lớp","Binary booking khoảng 42%, nhưng destination có lớp rất nhỏ","Giữ baseline phân phối gốc; nếu dự đoán destination cần đánh giá từng lớp và n"],["Feature engineering (đề xuất)","Có user/session nhưng log thiếu timestamp","Chỉ nghiên cứu tổng hợp hành vi sau khi xác định cửa sổ logs; không tạo feature 'trước booking' khi chưa chứng minh được thời gian"],["Hướng mô hình (đề xuất)","User-level và 12 nhãn gốc","Chốt binary booking hoặc destination trước; có thể so sánh baseline/nhị phân/đa lớp ở giai đoạn sau; dùng cohort validation"]],
        "EXPEDIA":[["Missing / giá","Comp/history thiếu nhiều nhưng có quy luật","Thử chiến lược missing trên train sau khi hiểu nghĩa NA; không ép drop/giữ mọi cột chỉ từ missing rate"],["Mã hóa / chuẩn hóa","Nhiều ID; giá đuôi dài","Category encoding và xử lý giá chỉ trong train, xác minh đơn vị; scaling không mặc định với cây"],["Cân bằng lớp","Click/booking hiếm ở cấp cặp","Nếu thử sampling/weight, chỉ thực hiện trên train và kiểm tra lại calibration; giữ đủ group search"],["Feature engineering (đề xuất)","Thuộc tính property trong cùng search có quan hệ tương đối","Có thể nghiên cứu giá/vị trí tương đối trong tập ứng viên có sẵn tại t0; không dùng vị trí/booking sau sự kiện"],["Hướng mô hình (đề xuất)","Search-property với hai hành vi","So sánh baseline propensity hoặc learning-to-rank theo mục tiêu; chia theo srch_id và đánh giá thời gian/calibration, chưa chọn phương án cuối"]],
    }[report.dataset]
    return section("proposals","Đề xuất bước tiếp theo — chưa thực hiện","Các lựa chọn dưới đây là hướng nghiên cứu dựa trên EDA, không phải các phép tiền xử lý/feature/model đã được áp dụng. Chốt đối tượng, t0, thời hạn nhãn và tiêu chí kinh doanh trước; fit mọi phép biến đổi ở tập train sau khi thiết kế đánh giá.",[("Đề xuất và cơ sở dữ liệu",pd.DataFrame(rows,columns=["topic","eda_basis","proposal_only"]))])


def restructure(report, additions, insights, coverage):
    old={s["key"]:s for s in report.sections}
    # Full schema and exhaustive frequency/numeric tables belong in the appendix.
    append=[]
    append.append(old["dictionary"])
    scope=dict(old["scope"])
    append.append(section("inventory","Danh mục file, dung lượng và SHA-256", "Phiên bản local được xác định bằng các giá trị dưới đây; không suy ngày tải từ ngày sửa file.",scope["tables"]))
    scope["tables"]=[]
    if "auxiliary" in old: append.append(old["auxiliary"])
    distribution=dict(old["distributions"])
    append.append(section("raw_distributions","Bảng đơn biến đầy đủ","Các bảng thống kê dưới đây bổ sung cho các biểu đồ ở phần chính. Top category không phải toàn bộ domain; đối chiếu từ điển.",distribution["tables"]))
    distribution["tables"]=[]
    if "dependencies" in old:
        depend=dict(old["dependencies"])
        append.append(section("full_dependencies","Bảng phụ thuộc và bảng chéo chi tiết",depend["text"],depend["tables"]))
    overview=[source_section(report,coverage),scope]
    if "method" in old: overview.append(old["method"])
    quality=[old["quality"]]
    if "missing" in old: quality.append(old["missing"])
    quality += [additions["missing"],additions["outliers"]]
    target=dict(old["target"])
    target_tables=target["tables"]
    keep_words={"HOTEL":["theo hotel","Lead time"],"AIRBNB":["theo gender","theo signup_app"],"EXPEDIA":["prop_starrating","price_group","window_group"]}[report.dataset]
    target["tables"]=[(name,t) for name,t in target_tables if any(w in name for w in keep_words)]
    append.append(section("all_target_tables","Các bảng quan hệ với nhãn đầy đủ","Các nhóm n nhỏ đã được gắn cờ; bảng chuyển vào phụ lục để thân báo cáo tập trung vào phát hiện.",target_tables))
    multivariate=[target,additions["multivariate"]]
    if "position" in old: multivariate.append(old["position"])
    if "sessions" in old:
        sessions=dict(old["sessions"])
        append.append(section("session_details","Schema và phân phối sessions đầy đủ","Mẫu số sự kiện khác người dùng; không gộp log thành tập feature.",sessions["tables"]))
        sessions["tables"]=[(name,t) for name,t in sessions["tables"] if name.startswith("Độ phủ")]
        multivariate.append(sessions)
    time=dict(old["time"])
    append.append(section("calendar_tables","Các bảng thời gian và drift chi tiết",time["text"],time["tables"]))
    time["tables"]=[(name,t) for name,t in time["tables"] if "Khoảng thời gian" in name or "Khác biệt category" in name]
    multivariate.append(time)
    if "missing_corr" in additions: append.append(additions["missing_corr"])
    if "cardinality" in additions: append.append(additions["cardinality"])
    # Figure-specific observations are mandatory, including the original plots.
    for s in old.values():
        for path in s["figures"]:
            if path.name not in report.figure_notes:
                raise ValueError(f"Missing chart interpretation: {report.dataset}/{path.name}")
    summary="\n\n".join(f"{i}. {text}" for i,text in enumerate(insights,1))
    report.sections=[
        section("executive","Tóm tắt điều hành — dữ liệu là gì, đáng tin đến đâu, dùng cho việc gì",summary),
        combine("overview","1. Tổng quan bộ dữ liệu",overview),
        combine("quality_main","2. Chất lượng dữ liệu",quality),
        combine("univariate","3. Phân tích đơn biến",[distribution,additions["categories"]]),
        combine("multivariate_main","4. Phân tích đa biến, thời gian và nhóm con",multivariate),
        risks(report),
        combine("conclusion_main","6. Kết luận và đề xuất bước tiếp theo",[old["conclusions"],proposals(report)]),
        combine("appendix","Phụ lục — từ điển và bảng chi tiết",append),
    ]
    report.facts["figure_seed"]=SEED
    report.facts["download_date"]=None
    report.facts["rules_checked_on"]="2026-11-01"


def diagnostic_sections(report, frame, numeric, target, missing_columns, missing_group, group_name, population, cat, corr_cols, x, y):
    additions={}
    p,t,corr,note=missing_plot(report,frame,missing_columns,missing_group,group_name,population)
    additions["missing"]=section("missing_patterns","Missing có quy luật hay không?","Heatmap chọn tối đa 12 cột có NA. Chọn dòng để hiển thị với seed=42 và sắp theo pattern; bảng tỷ lệ theo nhóm dùng quần thể phân tích công bố, không chỉ các dòng hiển thị.",[(f"Missing (%) theo {group_name}; {population}",t)],[p])
    additions["missing_corr"]=section("missing_indicator_correlation","Tương quan giữa các chỉ báo thiếu","Đây là tương quan của các cờ NA để phát hiện cùng thiếu; không xác định MCAR/MAR/MNAR. Cờ dùng để EDA, không xuất thành feature.",[("Correlation các chỉ báo NA",corr)])
    p,t,note=outlier_panel(report,frame,numeric,target,population)
    additions["outliers"]=section("outliers","Ngoại lai: lượng hóa và phân biệt quy tắc với kết luận lỗi","Quy tắc 1,5×IQR chỉ gắn cờ để kiểm tra, không tự chứng minh lỗi. Mẫu số là số giá trị không thiếu của từng cột; bảng giữ rõ quần thể và trường hợp IQR=0.",[("Hàng rào IQR trên dữ liệu công bố",t)],[p])
    p,t,note=category_panel(report,frame,cat,target,"Observations")
    additions["categories"]=section("category_chart","Biến phân loại và nhãn","Biểu đồ hiển thị top 8 nhóm theo số lượng; bảng kiểm kê giữ cả các nhóm nhỏ. Nhóm hiếm được báo với ngưỡng mô tả n<100, chưa gộp category.",[(f"Tần suất đầy đủ của {cat}",t)],[p])
    p,t,note=correlation_scatter(report,frame,corr_cols,x,y,population)
    additions["multivariate"]=section("correlation_and_interaction","Tương quan, tương tác và chồng lặp thông tin","Ma trận Spearman dùng từng cặp không thiếu. Scatter lấy tối đa 4.000 điểm seed=42 để tránh che lấp, giữ nhãn trục và đơn vị. Chưa thực hiện kiểm định nhiều giả thuyết hay kết luận nhân quả; cấu trúc phụ thuộc quan sát và kích thước hiệu ứng cần được xét trước p-value.",[("Ma trận Spearman",t)],[p])
    return additions


def enrich_hotel(report,df,arrival):
    pass  # Hàm đã được định nghĩa trong cùng file.
    frame=df
    dictionary_details(report,df)
    additions=diagnostic_sections(report,frame,["adr","lead_time","adults","children","booking_changes"],"is_canceled",list(df.columns),df.is_canceled,"is_canceled","toàn bộ booking HOTEL","market_segment",["lead_time","adr","stays_in_week_nights","stays_in_weekend_nights","adults","children","booking_changes","total_of_special_requests"],"lead_time","adr")
    additions["cardinality"]=section("category_cardinality","Số nhóm và nhóm hiếm — toàn bộ HOTEL","Ngưỡng n<100 là cờ đọc báo cáo, không phải luật gộp category. NA là một nhóm riêng khi có.",[("Category cardinality",category_cardinality(df,["hotel","market_segment","distribution_channel","customer_type","deposit_type","meal","country","reserved_room_type","assigned_room_type","agent","company"]))])
    rates=df.groupby("hotel").is_canceled.mean()*100
    unique=df.drop_duplicates()
    out=iqr_table(df,["adr"],"full").iloc[0]
    fig_note(report,report.directory/"figures/distributions.png",f"Nhận xét: lead_time có median {df.lead_time.median():.0f} ngày so với mean {df.lead_time.mean():.2f}, thể hiện đuôi phải; ADR median {df.adr.median():.2f}, max {df.adr.max():.2f}. Biểu đồ ADR chỉ vẽ 0–500, có {int((~df.adr.between(0,500)).sum())} dòng ngoài vùng nhìn; thống kê vẫn giữ tất cả.")
    fig_note(report,report.directory/"figures/target_by_hotel.png",f"Nhận xét: tỷ lệ hủy/no-show City Hotel {rates['City Hotel']:.2f}% và Resort Hotel {rates['Resort Hotel']:.2f}%, chênh {rates['City Hotel']-rates['Resort Hotel']:.2f} điểm phần trăm. Đây là khác biệt giữa hai cơ sở có cơ cấu khách khác nhau, không phải tác động riêng của loại khách sạn.")
    timeline=df.groupby(arrival.dt.to_period("M")).is_canceled.agg(["size","mean"])
    fig_note(report,report.directory/"figures/calendar.png",f"Nhận xét: tỷ lệ nhãn theo tháng đến gộp hai cơ sở dao động {timeline['mean'].min()*100:.2f}–{timeline['mean'].max()*100:.2f}%; số booking và tỷ lệ hủy thay đổi theo thời gian và khách sạn. Các tháng có số năm bao phủ khác nhau, nên chưa kết luận mùa vụ lặp ổn định chỉ từ đường này.")
    insights=[
        f"**Đơn vị và độ phủ:** {count(len(df))} booking, 32 cột, ngày đến {arrival.min().date()}–{arrival.max().date()}, hai khách sạn. Xem mục 1 và danh mục SHA-256 ở phụ lục.",
        f"**Nhãn:** {count(df.is_canceled.sum())} booking hủy/no-show ({pct(df.is_canceled.mean())}); bảng trạng thái cuối ở mục 2 xác nhận gồm cả Canceled và No-Show.",
        f"**Duplicate có tác động lớn:** {count(df.duplicated().sum())} dòng trùng; giả định bỏ tất cả làm tỷ lệ nhãn từ {pct(df.is_canceled.mean())} xuống {pct(unique.is_canceled.mean())}. Đây là độ nhạy, chưa phải quyết định xóa.",
        f"**Khác biệt nhóm:** City {rates['City Hotel']:.2f}% so với Resort {rates['Resort Hotel']:.2f}% nhãn 1; xem biểu đồ hủy theo hotel ở mục 4. Chênh lệch chưa điều chỉnh theo kênh/cohort.",
        f"**Thiếu theo cấu trúc:** company thiếu {df.company.isna().mean()*100:.2f}%, agent {df.agent.isna().mean()*100:.2f}%; heatmap missing ở mục 2 và nguồn nghiệp vụ giúp phân biệt không áp dụng với thiếu thật.",
        f"**Đuôi giá:** quy tắc 1,5×IQR gắn cờ {int(out.flagged_n):,} ADR ({out.flagged_pct_nonnull:.2f}% số không thiếu); max {df.adr.max():.2f}. Xem boxplot và bảng outlier; chưa chứng minh đây là lỗi.",
        "**Tính phù hợp:** dùng cho cancellation/no-show ở cấp booking, với điều kiện loại thông tin kết quả và xác minh snapshot tại t0; chưa đủ để gọi là customer churn. Ma trận rủi ro và đề xuất ở mục 5–6 nêu các điểm cần giải quyết.",
    ]
    restructure(report,additions,insights,f"Arrival {arrival.min().date()}–{arrival.max().date()}")
    pass  # Hàm đã được định nghĩa trong cùng file.
    deepen_hotel(report, df, arrival)


def enrich_airbnb(report,train,test,ids,account,per_user,transaction_counts):
    pass  # Hàm đã được định nghĩa trong cùng file.
    frame=train.assign(observed_booking=train.country_destination.ne("NDF").astype(int))
    dictionary_details(report,train)
    first=pd.to_datetime(train.timestamp_first_active.astype(str),format="%Y%m%d%H%M%S",errors="coerce")
    # Two original time fields, represented as elapsed days only for a calendar scatter.
    diag=frame.assign(account_day=(account-account.min()).dt.days,first_active_day=(first-first.min()).dt.total_seconds()/86400)
    additions=diagnostic_sections(report,diag,["age"],"observed_booking",list(train.columns),account.dt.year,"account year","toàn bộ users train AIRBNB","signup_app",["age","account_day","first_active_day"],"account_day","first_active_day")
    # ID and source date columns are not numeric features: derived axes are EDA coordinates only.
    additions["multivariate"]["text"] += " account_day/first_active_day là tọa độ ngày từ mốc tối thiểu chỉ để vẽ và kiểm tra chồng lặp hai trường thời gian gốc, không phải feature đã tạo cho mô hình. signup_flow là mã phân loại nên không đưa vào ma trận số hoặc áp dụng IQR như một phép đo liên tục."
    additions["cardinality"]=section("category_cardinality","Số nhóm và nhóm hiếm — toàn bộ users train","Ngưỡng n<100 chỉ giúp phát hiện nhóm cần thận trọng; chưa gộp hoặc mã hóa category.",[("Category cardinality",category_cardinality(train,["gender","signup_method","signup_flow","language","affiliate_channel","affiliate_provider","first_affiliate_tracked","signup_app","first_device_type","first_browser"]))])
    coverage=len(set(train.id)&ids)/len(train);coverage_test=len(set(test.id)&ids)/len(test)
    aux=next(s for s in report.sections if s["key"]=="auxiliary")
    extra=[]
    for filename in ["countries.csv","age_gender_bkts.csv"]:
        raw=pd.read_csv(report.root/"data/raw/AIRBNB"/filename)
        for c in raw:
            s=raw[c].dropna()
            domain=", ".join(s.astype(str).unique()) if s.nunique()<=12 else f"{s.nunique()} giá trị; [{s.min()}, {s.max()}]"
            u={"lat_destination":"độ vĩ","lng_destination":"độ kinh","distance_km":"km","destination_km2":"km²","population_in_thousands":"nghìn theo nguồn","year":"năm","language_levenshtein_distance":"khoảng cách theo nguồn"}.get(c,"mã/nhóm phân loại")
            extra.append([filename,c,str(raw[c].dtype),u,domain,int(raw[c].isna().sum())])
    aux["tables"].insert(0,("Kiểu, đơn vị và domain của từng cột bảng phụ",pd.DataFrame(extra,columns=["table","column","dtype","unit","observed_domain","missing_n"])))
    age_bad=train.age.notna() & ~train.age.between(16,100)
    age_out=iqr_table(train,["age"],"full").iloc[0]
    fig_note(report,report.directory/"figures/users_distributions.png",f"Nhận xét: NDF chiếm {(train.country_destination.eq('NDF')).mean()*100:.2f}% toàn users; age thiếu {train.age.isna().mean()*100:.2f}% và có {int(age_bad.sum()):,} giá trị ngoài dải tham chiếu 16–100. Histogram chỉ vẽ tuổi 16–100, không thay đổi raw hoặc khẳng định mọi tuổi ngoài dải đều sai.")
    fig_note(report,report.directory/"figures/session_coverage.png",f"Nhận xét: độ phủ sessions train {coverage*100:.2f}% so với test {coverage_test*100:.2f}%; độ phủ của cohort 2010–2013 bằng 0 trong dữ liệu hiện có. Vì vậy thiếu log có quan hệ với thời kỳ thu thập, không đồng nghĩa không hoạt động.")
    cohort=frame.groupby(account.dt.year).observed_booking.agg(["size","mean"])
    fig_note(report,report.directory/"figures/account_cohorts.png",f"Nhận xét: booking rate theo năm signup trong train dao động {cohort['mean'].min()*100:.2f}–{cohort['mean'].max()*100:.2f}%. Cohort và thời gian có cơ hội quan sát cùng thay đổi; không gán toàn bộ chênh lệch cho chất lượng khách mới.")
    rates=frame.groupby("signup_app").observed_booking.agg(["size","mean"])
    biggest=rates.sort_values("size",ascending=False).iloc[0]
    insights=[
        f"**Đơn vị:** {count(len(train))} users train, {count(len(test))} users test; train signup {train.date_account_created.min()}–{train.date_account_created.max()}, test {test.date_account_created.min()}–{test.date_account_created.max()}. Xem mục 1.",
        f"**Nhãn:** {count(frame.observed_booking.sum())} users có booking ({pct(frame.observed_booking.mean())}); NDF là không có booking theo nhãn, chưa phải kết quả trong 30/60/90 ngày. Biểu đồ nhãn ở mục 3.",
        "**Leakage tuyệt đối:** presence date_first_booking khớp hoàn toàn nhãn có booking ở train; bảng chéo ở mục 2 chứng minh không dùng cột này/cờ thiếu để dự đoán first booking.",
        f"**Missing không chỉ là NA:** age thiếu {train.age.isna().mean()*100:.2f}%, gender '-unknown-' {train.gender.eq('-unknown-').mean()*100:.2f}%; heatmap và bảng sentinel ở mục 2 phân biệt hai khái niệm.",
        f"**Outlier cần xác minh:** {int(age_bad.sum()):,} tuổi ngoài [16,100]; quy tắc IQR gắn cờ {int(age_out.flagged_n):,} giá trị ({age_out.flagged_pct_nonnull:.2f}% không thiếu). Xem boxplot; không tự đổi năm sinh thành tuổi.",
        f"**Độ phủ log lệch mạnh:** train {coverage*100:.2f}%, test {coverage_test*100:.2f}%, chênh {(coverage_test-coverage)*100:.2f} điểm phần trăm. Biểu đồ sessions/cohort ở mục 4 cho thấy không thể diễn giải thiếu log là không hoạt động.",
        f"**Nhóm con:** app {rates.sort_values('size',ascending=False).index[0]} có {int(biggest['size']):,} users, booking rate {biggest['mean']*100:.2f}%; biểu đồ count/rate theo signup_app ở mục 3 cho phép đọc đúng mẫu số. Khác biệt app chưa điều chỉnh theo cohort.",
        "**Tính phù hợp:** first-booking propensity theo user là hướng phù hợp; destination là bài toán khác với 12 nhãn gốc. Sessions không có timestamp sự kiện nên khả năng dùng hành vi trước t0 chưa được chứng minh (mục 5–6).",
    ]
    restructure(report,additions,insights,f"Account train {train.date_account_created.min()}–{train.date_account_created.max()}; test {test.date_account_created.min()}–{test.date_account_created.max()}")
    pass  # Hàm đã được định nghĩa trong cùng file.
    deepen_airbnb(report,train,test,account,first,per_user,transaction_counts)


def enrich_expedia(report,train,test):
    pass  # Hàm đã được định nghĩa trong cùng file.
    pass  # Hàm đã được định nghĩa trong cùng file.
    store=train["store"]
    dictionary_details(report,pd.DataFrame(),train["stats"],train["cat"],
                       {"date_time":f"Toàn train: {train['min_date']}–{train['max_date']}"})
    additions={}
    p,t,missing_counts,corr=full_missing_diagnostics(report,train)
    additions["missing"]=section("missing_patterns","Pattern thiếu và tỷ lệ theo nhãn — toàn bộ train","Chọn 12 cột thiếu nhiều nhất theo toàn bộ train. Bảng tỷ lệ theo booking, số đếm và tương quan cờ NA dùng toàn bộ train; chỉ pattern bên trái hiển thị 300 dòng seed=42. Một booking bị thiếu gross được giữ trong số đếm, không làm tròn thành kết luận không có ngoại lệ.",[("Missing theo booking — toàn bộ train (%)",t),("Số missing theo nhãn và mẫu số nhóm — toàn bộ train",missing_counts)],[p])
    additions["missing_corr"]=section("missing_indicator_correlation","Đồng xuất hiện missing — toàn bộ train","Tương quan Pearson/phi của cờ NA cho 12 cột thiếu nhiều nhất dùng tất cả dòng train, kể cả các dòng không được hiển thị trong hình pattern. Correlation không xác định MCAR/MAR/MNAR; cờ chỉ dùng EDA.",[("Correlation cờ thiếu — toàn bộ train",corr)])
    numeric=["price_usd","srch_booking_window","srch_length_of_stay"]
    frame=store.frame(numeric+["booking_bool"])
    p,t,note=outlier_panel(report,frame,numeric,"booking_bool","toàn bộ train")
    additions["outliers"]=section("outliers","Ngoại lai: lượng hóa trên toàn bộ train","Q1/Q3, hàng rào 1,5×IQR, số đếm và tỷ lệ outlier dùng toàn bộ giá trị không thiếu của từng biến. Boxplot tính từ cùng quần thể đầy đủ; không kết luận giá trị sai chỉ vì vượt hàng rào. Giá trị raw không bị thay thế hoặc xóa.",[("Hàng rào IQR và outlier — toàn bộ train",t)],[p])
    del frame
    p=correlation_plot(report,train)
    additions["multivariate"]=section("correlation_and_interaction","Tương quan và tương tác — toàn bộ train","Ma trận Spearman của 9 biến dùng toàn bộ cặp không thiếu, xếp hạng lại riêng từng cặp. Số cặp hợp lệ có tại phụ lục. Chỉ scatter hiển thị tối đa 4.000 điểm seed=42. Chưa thực hiện kiểm định nhiều giả thuyết hoặc kết luận nhân quả/đa cộng tuyến từ tương quan.",[("Ma trận Spearman — toàn bộ train",train["correlation"].reset_index(names="column"))],[p])
    star=train["groups"]["prop_starrating"].sort_values("prop_starrating")
    fig,axes=plt.subplots(1,2,figsize=(12,4));axes[0].bar(star.prop_starrating.astype(str),star.n,color=BLUE);axes[0].set(title="Star rating: all train rows",xlabel="prop_starrating",ylabel="Search–property rows")
    axes[1].bar(star.prop_starrating.astype(str),star.booking_pct,color=ORANGE);axes[1].set(title="Booking rate within star-rating group",xlabel="prop_starrating",ylabel="Booking (%)");fig.tight_layout()
    path=report.savefig("categories_and_target",fig)
    best=star.loc[star.booking_pct.idxmax()]
    fig_note(report,path,f"Nhận xét: trong toàn bộ train, nhóm prop_starrating={int(best.prop_starrating)} có booking rate cao nhất trong bảng ({best.booking_pct:.2f}%, n={int(best.n):,}); các nhóm có quy mô khác nhau. Mã 0 cần xác minh nghĩa, không mặc định là chất lượng bằng 0; chênh lệch không được điều chỉnh theo giá/vị trí.")
    additions["categories"]=section("category_chart","Biến phân loại và nhãn trên toàn bộ train","Hai biểu đồ giữ riêng số cặp và tỷ lệ booking trong mỗi nhóm hạng sao, dùng toàn bộ train.",[("Hạng sao — toàn bộ train",star)],[path])
    cardinal=[]
    for c,t in train["cat"].items():
        low=t.n.lt(100)
        cardinal.append([c,len(t),int(low.sum()),int(t.loc[low,"n"].sum()),t.loc[low,"n"].sum()/train["rows"]*100])
    additions["cardinality"]=section("category_cardinality","Số nhóm và nhóm hiếm — các cột kiểm kê toàn file","Các ID/property/search không được coi là đại lượng liên tục; số thực thể/khóa trong phần kiểm tra cấu trúc nhóm. Bảng dưới kiểm kê các category được quét đầy đủ, không khẳng định đây là toàn bộ schema.",[("Category cardinality",pd.DataFrame(cardinal,columns=["column","groups","groups_under_100","rows_in_rare_groups","pct_rows_rare"]))])
    frame_corr=train["correlation"].loc["price_usd","prop_starrating"]
    price_row=train["stats"].set_index("column").loc["price_usd"]
    fig_note(report,report.directory/"figures/distributions.png",f"Nhận xét: trên toàn bộ train, giá có mean {price_row.full_mean:.2f} USD, median {price_row.full_p50:.2f} USD và max {price_row.full_max:.2f} USD, cho thấy đuôi phải lớn. Histogram đếm tất cả giá trong 0–1.000 USD; {train['high_price']:,} dòng trên 1.000 USD vẫn nằm trong thống kê/boxplot. Phân phối số ứng viên dùng đủ {len(train['queries']):,} searches.")
    pos=train["groups"]["random_bool_position"]
    first=pos[pos.position.eq(pos.position.min())]
    fig_note(report,report.directory/"figures/position.png","Nhận xét: tại vị trí nhỏ nhất quan sát được, "+"; ".join(f"random_bool={int(z.random_bool)}: click {z.click_pct:.2f}%, booking {z.booking_pct:.2f}%, n={int(z.n):,}" for z in first.itertuples())+". Chênh lệch giữa các cơ chế xếp hạng và sự phụ thuộc theo vị trí cho thấy CTR không chỉ phản ánh sở thích; đây chưa phải ước lượng nhân quả của thứ hạng.")
    time=train["groups"]["year_month"]
    fig_note(report,report.directory/"figures/calendar.png",f"Nhận xét: tỷ lệ click theo tháng dao động {time.click_pct.min():.2f}–{time.click_pct.max():.2f}%, booking {time.booking_pct.min():.2f}–{time.booking_pct.max():.2f}% trong train. Khoảng thời gian chưa đủ nhiều chu kỳ năm để khẳng định mùa vụ bền vững; quy mô dòng còn phụ thuộc số property/search.")
    out=additions["outliers"]["tables"][0][1].iloc[0]
    report.facts["full_train_price"]=price_row.to_dict()
    report.facts["full_train_outliers"]=additions["outliers"]["tables"][0][1].to_dict(orient="records")
    report.facts["full_train_price_star_spearman"]=float(frame_corr)
    report.facts["spearman_variables"]=list(train["correlation"].columns)
    rates=train["missing"]/train["rows"]
    insights=[
        f"**Đơn vị:** {count(train['rows'])} cặp search-property, 54 cột thuộc {count(len(train['queries']))} searches; test {count(test['rows'])} cặp, 50 cột. Mẫu số phải phân biệt dòng và search (mục 1).",
        f"**Nhãn toàn bộ train:** click {pct(report.facts['click_rate'])}, booking {pct(report.facts['booking_rate'])}, booking/click {pct(report.facts['booking_given_click'])}. Tử số/mẫu số cụ thể ở mục 2.",
        f"**Chọn mẫu:** có {report.facts['searches_without_click']:,} search hoàn toàn không click trong train hiện tại; không suy CTR/CVR toàn website từ các tỷ lệ này. Bảng cấu trúc nhóm ở mục 2.",
        f"**Missing khác theo đối thủ:** comp5_rate thiếu {rates['comp5_rate']*100:.2f}% nhưng comp1_rate {rates['comp1_rate']*100:.2f}%; không khái quát toàn bộ 24 cột đều >93%. Heatmap/pattern và bảng missing ở mục 2.",
        f"**Giá đuôi dài — toàn bộ train:** mean {price_row.full_mean:.2f} USD, median {price_row.full_p50:.2f} USD; hàng rào IQR gắn cờ {int(out.flagged_n):,} giá không thiếu ({out.flagged_pct_nonnull:.2f}%). Phân vị, hàng rào và số đếm đều tính trên toàn bộ train, xem boxplot ở mục 2.",
        f"**Tương quan và nhóm — toàn bộ train:** Spearman giá–hạng sao là {frame_corr:.3f}; booking rate theo sao và vị trí xem mục 3–4. Giá, sao và vị trí không phải các cơ chế độc lập đã được kiểm soát.",
        "**Leakage/schema:** gross_bookings_usd là kết quả sau booking; position chỉ có trong train; click thực tế không dùng để chấm trước click. Bảng schema và kiểm tra logic ở mục 2/phụ lục.",
        "**Tính phù hợp:** phù hợp nghiên cứu propensity/xếp hạng theo search, chưa phải marketing propensity theo user. Không có user ID và không có nhóm search không click nên giới hạn suy rộng phải được giữ trong kết luận (mục 5–6).",
    ]
    restructure(report,additions,insights,f"Search train {train['min_date']}–{train['max_date']}; test {test['min_date']}–{test['max_date']}")


# ==============================================================================
# EXPEDIA: thống kê chính xác toàn bộ train, đọc theo chunk
# Nguồn: expedia_full_train.py — nội dung đã gộp, không cần import file gốc.
# ==============================================================================

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

    def __init__(self, rows, numeric_columns, label_columns=("click_bool", "booking_bool")):
        """Cache numeric columns and optional numeric labels, retaining NaN.

        Set label_columns=() for unlabelled data, or pass your own column names.
        The legacy defaults keep the existing Expedia entry point compatible.
        """
        self.rows = int(rows)
        if self.rows < 0:
            raise ValueError("rows must be nonnegative")
        self.numeric_columns = list(numeric_columns)
        self.label_columns = list(label_columns)
        self.columns = list(dict.fromkeys(self.numeric_columns + self.label_columns))
        if "_missing_bits" in self.columns:
            raise ValueError("_missing_bits is reserved for the missingness cache")
        self.arrays = {}
        self.offset = 0
        self.schema = None
        self.temporary = working_directory()

    def __enter__(self):
        self.directory = self.temporary.__enter__()
        for index, column in enumerate(self.columns):
            self.arrays[column] = np.lib.format.open_memmap(
                self.directory / f"column_{index}.npy", mode="w+",
                dtype=np.float64, shape=(self.rows,),
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
            raise ValueError("Schema changed between CSV chunks")
        end = self.offset + len(chunk)
        if end > self.rows:
            raise ValueError("CSV parser row count exceeds the raw-file inventory")
        for column in self.columns:
            self.arrays[column][self.offset:end] = chunk[column].to_numpy(dtype=np.float64, na_value=np.nan)
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


def exact_spearman(store, columns=None):
    """Rank each pair after its own NA removal, including average ranks for ties.

    Ranking the full columns once then dropping NA would produce the wrong
    pairwise-complete Spearman coefficient when missing patterns differ.
    """
    from scipy.stats import rankdata

    if columns is None:
        columns = getattr(store, "numeric_columns", [c for c in store.arrays if c != "_missing_bits"])
    columns = list(columns)
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


def full_missing_diagnostics(report, train, seed=42, *, label_column="booking_bool"):
    """All-row missing rates by label and exact binary-indicator correlations."""
    import matplotlib.pyplot as plt

    store = train["store"]
    if store.rows == 0:
        raise ValueError("Missing diagnostics require at least one row")
    label_values = ["ALL"] if label_column is None else [0, 1]
    if label_column is not None:
        labels = pd.Series(store.arrays[label_column], copy=False)
        validate_binary_target(labels, label_column)
        if labels.isna().any():
            label_values.append("<MISSING>")
    # The grouping label is represented by group counts (including NA), not
    # duplicated as a feature column with the same name as the output index.
    feature_missing = train["missing"].drop(labels=[label_column], errors="ignore")
    columns = list(feature_missing.sort_values(ascending=False).head(12).index)
    if not columns:
        raise ValueError("Missing diagnostics require at least one column")
    positions = [store.schema.index(c) for c in columns]
    groups = np.zeros((len(label_values), len(columns)), dtype=np.int64)
    denominators = np.zeros(len(label_values), dtype=np.int64)
    joint = np.zeros((len(columns), len(columns)), dtype=np.int64)
    for start in range(0, store.rows, 250_000):
        stop = min(start + 250_000, store.rows)
        mask = np.unpackbits(store.arrays["_missing_bits"][start:stop],
                             axis=1, count=len(store.schema), bitorder="little")[:, positions].astype(bool)
        labels = store.arrays[label_column][start:stop] if label_column is not None else None
        for index, label in enumerate(label_values):
            selection = (np.ones(stop-start, dtype=bool) if label_column is None else
                         np.isnan(labels) if label == "<MISSING>" else labels == label)
            denominators[index] += int(selection.sum())
            groups[index] += mask[selection].sum(axis=0)
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
    rates = pd.DataFrame(np.divide(groups * 100., denominators[:, None],
                         out=np.full(groups.shape, np.nan), where=denominators[:, None] != 0),
                         index=pd.Index(label_values, name=label_column or "population"), columns=columns)
    display_ids = np.random.default_rng(seed).choice(store.rows, min(300, store.rows), replace=False)
    display = pd.DataFrame(np.unpackbits(store.arrays["_missing_bits"][display_ids],
                           axis=1, count=len(store.schema), bitorder="little")[:, positions], columns=columns)
    display = display.sort_values(columns, kind="stable")
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1.3, 1]})
    axes[0].imshow(display, aspect="auto", interpolation="nearest", cmap="Blues", vmin=0, vmax=1)
    axes[0].set(title=f"Missingness: {len(display)} displayed train rows", ylabel="Display only; sorted by pattern")
    im = axes[1].imshow(rates, aspect="auto", vmin=0, vmax=100, cmap="Blues")
    axes[1].set(title=f"Missing by {label_column or 'population'}: all rows (%)", ylabel=label_column or "population")
    axes[1].set_yticks(range(len(label_values)), labels=[str(v) for v in label_values])
    for ax in axes:
        ax.set_xticks(range(len(columns)), labels=columns, rotation=65, ha="right")
    fig.colorbar(im, ax=axes[1], label="Missing (%)", fraction=.035, pad=.03)
    fig.tight_layout()
    path = report.savefig("missing_patterns", fig)
    differences = rates.max() - rates.min()
    largest = differences.idxmax()
    note = (
        f"Nhận xét: {columns[0]} thiếu {counts[0] / store.rows * 100:.2f}% trên toàn bộ train; "
        f"chênh lệch missing lớn nhất giữa các nhóm là {differences[largest]:.4f} điểm phần trăm "
        f"ở {largest}. Bảng tỷ lệ, số đếm và tương quan cờ thiếu dùng đủ {store.rows:,} dòng. "
        f"Chỉ hình pattern bên trái hiển thị {len(display)} dòng, seed={seed}, sắp theo pattern, không theo thời gian. "
        "Ô xanh là NA. Không suy cơ chế MCAR/MAR/MNAR từ hình; kiểm tra riêng nguy cơ rò rỉ nhãn của cờ thiếu."
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


# ==============================================================================
# AIRBNB: trình bày và kiểm tra tính nhất quán báo cáo
# Nguồn: airbnb_report_presentation.py — nội dung đã gộp, không cần import file gốc.
# ==============================================================================

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
    "age_missing": "Thiếu tuổi", "gender_unknown": "Không rõ giới tính",
}

DISPLAY_HEADERS = {
    **NAMES, "item": "Nội dung", "description": "Mô tả", "dataset": "Bộ dữ liệu",
    "account year": "Năm đăng ký", "year": "Năm",
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
    "observed_bookings": "Số có nhãn y90=1", "booking_pct": "Tỷ lệ y90=1 (%)",
    "eligible_90": "Mẫu hợp lệ y90", "prediction_origin": "Mốc dự đoán",
    "labels_ready_on": "Ngày nhãn cửa sổ sẵn có", "embargo_days": "Đệm (ngày lịch)",
    "gap_start": "Đệm từ ngày", "gap_end": "Đệm đến ngày",
    "source_rate": "Tỷ lệ nhãn y=1 (%)", "n90": "Mẫu hợp lệ y90", "positive90": "Số có nhãn y90=1",
    "rate90": "Tỷ lệ nhãn y90=1 (%)", "lower90": "Cận dưới 95% · y90 (%)", "upper90": "Cận trên 95% · y90 (%)",
    "train_from": "Đăng ký học từ", "train_to": "Đăng ký học đến", "train_n": "Mẫu học hợp lệ",
    "train_positive90": "Dương tính trong học", "train_rate90": "Tỷ lệ y90 trong học (%)",
    "calibration_from": "Mẫu OOF từ", "calibration_to": "Mẫu OOF đến", "calibration_n": "Mẫu nhãn cho hiệu chỉnh OOF",
    "evaluation_from": "Tháng dự đoán từ", "evaluation_to": "Tháng dự đoán đến", "evaluation_n": "Mẫu đánh giá",
    "evaluation_positive90": "Dương tính đánh giá", "evaluation_rate90": "Tỷ lệ y90 đánh giá (%)", "maturity_gap_days": "Nhãn chờ hoàn tất (ngày)",
    "within_method_pct": "Trong phương thức đăng ký (%)", "within_profile_pct": "Trong nhóm giao hai cờ (%)",
    "source": "Tập dữ liệu", "month": "Tháng đăng ký", "age_missing_pct": "Thiếu tuổi (%)", "gender_unknown_pct": "Không rõ giới tính (%)",
    "days_from_month_end_to_proxy_cutoff": "Ngày từ cuối tháng đến mốc lịch giả định",
    "component": "Thành phần", "value": "Giá trị", "issue": "Vấn đề", "evidence_or_limit": "Bằng chứng và giới hạn",
}


def airbnb_display_header(value):
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
    pass  # Hàm đã được định nghĩa trong cùng file.
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
    grouped_rates = airbnb_grouped_rates
    pass  # Hàm đã được định nghĩa trong cùng file.
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
    pass  # Hàm đã được định nghĩa trong cùng file.
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
    pass  # Hàm đã được định nghĩa trong cùng file.
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
    protocol_main = evidence["protocol"][["prediction_origin", "role", "train_to", "train_n", "evaluation_n", "evaluation_positive90", "evaluation_rate90", "labels_ready_on"]]
    by_key["evaluation"]["tables"][0] = ("B7 · Các mốc tháng, lịch sử có nhãn và quy mô đánh giá", protocol_main)
    protocol_details = evidence["protocol"][["prediction_origin", "train_positive90", "train_rate90", "calibration_from", "calibration_to", "calibration_n", "evaluation_to"]]
    by_key["appendix"]["blocks"].append(section("monthly_protocol_details", "Chi tiết mẫu hiệu chỉnh tại từng mốc tháng", "Mọi mốc dùng lịch sử đăng ký từ đầu train. Mẫu nhãn hiệu chỉnh dưới đây phải đi kèm điểm OOF theo thời gian, chưa phải một tập dự đoán đã tạo. B7 giữ quy mô đánh giá chính.", [("Mẫu nhãn hiệu chỉnh OOF và tỷ lệ trong lịch sử học", protocol_details)]))
    matches = train.date_first_booking.notna().eq(frame.observed_booking.astype(bool))
    leakage = pd.DataFrame([[int(matches.sum()), len(train), matches.mean()*100]],
                           columns=["Số trường hợp khớp", "Số người dùng train", "Tỷ lệ khớp (%)"])
    by_key["quality_main"]["blocks"][0]["tables"].append(("B8 · Mức khớp giữa tình trạng ngày đặt chỗ và nhãn y", leakage))
    rows = [
        ["Phát hiện 1", "B1", "Quy mô train, test, số và tỷ lệ nhãn y=1", "facts.rows; facts.test_rows; facts.positive; facts.rate"],
        ["Phát hiện 2", "B9", "Số dương trong 90 ngày, tỷ lệ trên toàn bộ dòng và mẫu hợp lệ sau khi bỏ ngoại lệ", "facts.conditional_90_positive; facts.conditional_90_eligible; facts.conditional_90_rate_pct"],
        ["Phát hiện 3", "B10", "Bốn nhóm giao cờ có tỷ lệ y90 không đơn điệu và V giữa hai chỉ báo", "profile_summary: tỷ lệ y90 và V giữa chỉ báo đầu vào trong năm 2014"],
        ["Phát hiện 4", "B11", "Tỷ lệ y90 theo ứng dụng trong nhóm có tuổi và có khai báo giới tính", "profile_apps: age_missing=False; gender_unknown=False; rate90"],
        ["Phát hiện 5", "B5", "Độ phủ, chênh độ phủ, tỷ lệ đặt chỗ có/thiếu nhật ký; quy mô train 2014", "facts.train_2014_users; facts.train_2014_session_coverage_pct; sessions_2014"],
        ["Việc cần giải quyết 1", "B9; B15; B16; Q3", "Nghiên cứu y90 với giả định theo dõi tối thiểu 90 ngày, kiểm tra tháng và sai nhãn NDF", "conditional_labels và các kịch bản B16 giữ nguyên mẫu người dùng"],
        ["Việc cần giải quyết 2", "B8; B17; Q1", "Mức khớp 100%, nhánh chính tối thiểu và điều kiện thông tin tại t0", "Ngày đặt chỗ/nhãn y và bảng kiểm soát nhánh đầu vào"],
        ["Việc cần giải quyết 3", "B7", "Tại từng mốc đầu tháng học toàn bộ nhãn đã hoàn tất, hiệu chỉnh bằng điểm OOF lịch sử", "protocol: train_to, prediction_origin và mẫu hiệu chỉnh OOF theo thời gian"],
    ]
    provenance = pd.DataFrame(rows, columns=["Ý trong tóm tắt", "Bảng hoặc câu hỏi nguồn", "Số liệu và nội dung được đối chiếu", "Đường dẫn dữ liệu hoặc cách tính"])
    by_key["appendix"]["blocks"].append(section("executive_sources", "Truy vết số liệu trong tóm tắt", "Mã B1–B17 đứng trước tên các bảng tương ứng. Các số được làm tròn khi trình bày. Metadata giữ giá trị đầy đủ trong facts và dấu kiểm tra của các bảng thống kê. Các mốc chia thời gian là đề xuất nghiên cứu, không phải kết quả đã thực hiện.", [("Nguồn của từng phát hiện và việc cần giải quyết", provenance)]))
    text = by_key["executive"]["text"]
    sources = ["B1", "B9", "B10", "B11", "B5"]
    next_sources = ["B9, B15, B16 và Q3", "B8, B17 và Q1", "B7"]
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
        text = re.sub(r"\by(?:90)?\s*=\s*[01]\b", "", str(text))
        return {str(Decimal(token.replace(",", "")).normalize())
                for token in re.findall(pattern, text)}
    tables = {"B1": size, "B2": evidence["horizons"], "B3": by_key["signal"]["tables"][0][1],
              "B4": missing, "B5": coverage, "B6": evidence["delay"], "B7": evidence["protocol"], "B8": leakage,
              **report.research_tables}
    citations = [["B1"], ["B9"], ["B10"], ["B11"], ["B5"], ["B9","B15","B16"], ["B8","B17"], ["B7"]]
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
    pass  # Hàm đã được định nghĩa trong cùng file.
    by_key = {item["key"]: item for item in walk_sections(report.sections)}
    pass  # Hàm đã được định nghĩa trong cùng file.
    path = timeline_with_embargo(report)
    by_key["evaluation"]["figures"] = [path]
    report.figure_notes[path.name] = (
        "**Quan sát:** tại mỗi mốc tháng, tập học mở rộng đến mọi nhãn đã hoàn tất. Tháng 5/2014 học đến 2014-01-30, tháng 6/2014 học đến 2014-03-02.\n\n"
        "**Phạm vi và cách đọc:** vùng xanh là lịch sử có nhãn; gạch chéo là người chưa hoàn tất nhãn tại mốc dự đoán. Khung cam chỉ mẫu nhãn dùng học bộ hiệu chỉnh từ dự đoán OOF lịch sử, nằm trong tập học nền cuối. Việc trùng nhãn lịch sử chỉ hợp lệ khi điểm học bộ hiệu chỉnh là OOF theo thời gian. Đây là đặc tả đề xuất, chưa có dự đoán hoặc mô hình."
    )
    by_key["evaluation"]["tables"].append(("Vai trò từng giai đoạn huấn luyện, hiệu chỉnh và đánh giá", research_roles()))
    executive_sources(report, by_key)
    criteria = pd.DataFrame([
        ["0 · Sửa nội dung", "Đủ cảnh báo mẫu số và t0; số thập phân thống nhất; không lặp từ; mở đầu không có lệnh cài; ngày tải ghi đúng bằng chứng", "Kiểm tra văn bản, notebook và metadata"],
        ["1 · Chuẩn hóa", "Mỗi hình có quan sát và phạm vi; tiêu đề bảng dùng tên diễn giải; khái niệm có tên thống nhất; phương pháp chi tiết ở cuối", "Kiểm tra chú thích, tiêu đề và bảng thuật ngữ"],
        ["2 · Tổ chức EDA", "Có biểu đồ độ mạnh liên hệ với hai thang riêng; tỷ lệ nhóm có khoảng Wilson; bảng dài nằm ở phụ lục", "Kiểm tra hình, bảng và dấu kiểm tra thống kê"],
        ["3 · Hiểu dữ liệu", "Có quyết định cho toàn bộ 34 cột; sơ đồ quan hệ; phát hiện gắn hàm ý; rủi ro và phù hợp gộp một mục", "Đối chiếu số cột CSV, cấu trúc báo cáo và bảng quyết định"],
        ["4 · Thiết kế nghiên cứu", "Có sơ đồ thời gian và vai trò từng giai đoạn; mọi số trong tóm tắt có bảng nguồn; notebook chạy hết; số liệu khớp sau từng giai đoạn", "Đối chiếu B1–B17, nguồn số liệu, lịch sử kiểm tra và mã nguồn trong metadata"],
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


def airbnb_prepare_publication(report):
    if STAGE >= 1:
        apply_stage_one(report)
    if STAGE >= 2:
        apply_stage_two(report)
    if STAGE >= 3:
        apply_stage_three(report)
    if STAGE >= 4:
        pass  # Hàm đã được định nghĩa trong cùng file.
        apply_research_revision(report)
        apply_stage_four(report)
    for item in walk_sections(report.sections):
        item["title"] = normalize_text(item["title"])
        item["text"] = normalize_prose(item["text"])
        item["tables"] = [(normalize_text(label), table.map(normalize_text))
                          for label, table in item["tables"]]
        if STAGE >= 4:
            item["tables"] = [(label, table.rename(columns=airbnb_display_header).rename_axis(airbnb_display_header(table.index.name)))
                              for label, table in item["tables"]]
        if STAGE >= 1:
            assert all(not re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", label)
                       for label, _ in item["tables"] for key in NAMES), "Code name remains in table title"
    report.figure_notes = {key: normalize_prose(value) for key, value in report.figure_notes.items()}
    pass  # Hàm đã được định nghĩa trong cùng file.
    report.rendered_tables_sha256 = sorted(
        hashlib.sha256(md_table(table).encode()).hexdigest()
        for item in walk_sections(report.sections) for _, table in item["tables"])
    report.facts["completion_stage"] = STAGE
    report.facts["analysis_revision"] = report.facts.get("research_revision", "airbnb_completion_stages_0_to_4")
    previous = report.directory / "analysis_metadata.json"
    if previous.exists():
        previous_meta = json.loads(previous.read_text(encoding="utf-8"))
        report.completed_stages = previous_meta.get("completed_stages", [])
        old = previous_meta["facts"]
        for key, value in old.items():
            policy_revision = old.get("research_revision") == "airbnb_90day_embargo_profile_v2" and report.facts.get("research_revision") == "airbnb_asof_monthly_t0_branches_v3"
            allowed_policy_change = policy_revision and key == "followup_assumption_days" and value == 365 and report.facts[key] == 90
            if key in report.facts and isinstance(value, numbers.Number) and key != "completion_stage" and not allowed_policy_change:
                if value != report.facts[key]:
                    raise ValueError(f"Statistical fact changed: {key}")
        if "statistical_fingerprint" in old:
            if old["statistical_fingerprint"] != report.facts["statistical_fingerprint"]:
                if policy_revision:
                    assert old["base_evidence_fingerprint"] == report.facts["base_evidence_fingerprint"], "Underlying source evidence changed"
                else:
                    assert old["analysis_revision"] == "airbnb_completion_stages_0_to_4", "Evidence changed within revision"
                    assert old["statistical_fingerprint"] == report.facts["base_evidence_fingerprint"], "Underlying source evidence changed"
    for item in walk_sections(report.sections):
        for path in item["figures"]:
            assert path.name in report.figure_notes, f"Missing caption: {path.name}"


def airbnb_verify_artifacts(root, notebook):
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
        assert meta[key] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert meta["research_script_sha256"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    history = meta.get("completed_stages", [])
    history = [row for row in history if row["stage"] != STAGE]
    history.append({"stage": STAGE, "executed_cells": len(cells),
                    "revision": meta["facts"]["analysis_revision"],
                    "statistical_fingerprint": meta["facts"]["statistical_fingerprint"],
                    "checks": "numeric facts, evidence, captions, notebook outputs, source hashes, decimals" + (", executive number provenance, column decisions, merged limitations, timeline" if STAGE >= 4 else "")})
    meta["completed_stages"] = sorted(history, key=lambda row: row["stage"])
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"AIRBNB stage {STAGE}: publication checks passed ({len(cells)} executed cells)", flush=True)


# ==============================================================================
# AIRBNB: sessions, nhãn, liên hệ thống kê và cohort
# Nguồn: airbnb_deep_dive.py — nội dung đã gộp, không cần import file gốc.
# ==============================================================================

import hashlib
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

pass  # Hàm đã được định nghĩa trong cùng file.

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
pass  # Hàm đã được định nghĩa trong cùng file.
if STAGE >= 3:
    AIRBNB_LAYOUT = [(key, "6. Tổng hợp giới hạn và mức độ phù hợp" if key == "risks" else title)
                     for key, title in AIRBNB_LAYOUT if key != "conclusion_main"]


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


def airbnb_grouped_rates(frame, keys):
    pass  # Hàm đã được định nghĩa trong cùng file.
    result = frame.groupby(keys, observed=True, dropna=False).observed_booking.agg(n="size", positive="sum").reset_index()
    result["rate_pct"] = result.positive / result.n * 100
    result["ci95_low_pct"], result["ci95_high_pct"] = wilson(result.positive, result.n)
    result["n_under_100"] = result.n.lt(100)
    return result


def categorical_association(values, target):
    validate_binary_target(target)
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
    return airbnb_grouped_rates(rows, ["account_year", column])


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
    pass  # Hàm đã được định nghĩa trong cùng file.
    y = train.country_destination.ne("NDF").astype(int)
    is2014 = account.dt.year.eq(2014)
    frame = pd.DataFrame({"id": train.id, "observed_booking": y,
                          "has_sessions": train.id.isin(per_user.index), "account_year": account.dt.year})
    rates2014 = airbnb_grouped_rates(frame[is2014], ["has_sessions"])
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
Để chạy lại notebook, cần file eda_all_datasets.py và năm CSV train_users_2.csv, test_users.csv, sessions.csv, countries.csv, age_gender_bkts.csv tại data/raw/AIRBNB/. Notebook đã lưu kết quả để đọc trực tiếp. Dữ liệu gốc được lấy riêng theo hướng dẫn vì không được đính kèm kho mã.

Cài môi trường EDA từ thư mục gốc bằng lệnh dưới đây. Đây là hướng dẫn chuẩn bị, không phải ô phân tích dữ liệu:

```powershell
python -m pip install pandas==2.3.3 numpy==2.4.1 scipy==1.17.1 matplotlib==3.10.8 nbformat==5.10.4 ipython==9.9.0 tzdata
```

Từ thư mục gốc, chạy `python scripts/eda_all_datasets.py --dataset AIRBNB`. Cách khác là mở notebook bằng Jupyter, chọn Restart Kernel rồi Run All. Script đọc CSV gốc và xuất báo cáo Markdown, metadata JSON, hình và notebook có kết quả thực thi.

**Hồ sơ dự án chưa có bằng chứng về ngày tải và mã phiên bản Kaggle.** Báo cáo để trạng thái chưa xác định và nhận diện bản dữ liệu đang dùng bằng SHA-256 của từng file cùng danh mục file trong metadata. Ngày phân tích được ghi theo múi giờ Asia/Ho_Chi_Minh và không thay thế ngày tải.

Các bảng dùng toàn bộ người dùng hoặc toàn bộ sessions có khóa hợp lệ trong phạm vi ghi cạnh bảng. Hình về mẫu thiếu chỉ hiển thị tối đa 300 dòng với seed=42.

Phép tính Cramér V dùng chi-square không hiệu chỉnh Yates. Bảng báo p-value xấp xỉ và tỷ lệ ô có tần số kỳ vọng dưới 5 để kiểm tra độ phù hợp của xấp xỉ. Kiểm định Mann–Whitney hai phía dùng xấp xỉ có hiệu chỉnh các giá trị đồng hạng. Hệ số rank-biserial được tính bằng 2U/(n_y1 × n_y0) − 1. Trong công thức này, U là thống kê Mann–Whitney với nhóm y=1 đứng trước, còn n_y1 và n_y0 là cỡ mẫu hai nhóm.

Phương pháp Benjamini–Hochberg (BH) điều chỉnh p-value cho 14 phép kiểm định trên toàn kỳ và cho ra giá trị q trong bảng. Việc chọn biến sẽ được kiểm tra bằng thí nghiệm mô hình. Khoảng Wilson 95% giả định các người dùng độc lập. Khoảng này mô tả bất định của tỷ lệ, đồng thời cần xem xét riêng sai lệch chọn mẫu và khác biệt giữa các nhóm đăng ký.

Các kết quả được tính lại trong lần phân tích hiện tại. Bảng môi trường dưới đây và SHA-256 của file tổng hợp dựng báo cáo trong metadata nhận diện mã đã chạy. Thuật toán, cửa sổ chia dữ liệu, bootstrap và ngưỡng chấp nhận ở phần 7 là thiết kế cho giai đoạn tiếp theo.
""", [("Môi trường thực thi chính xác", environment)])


def deepen_airbnb(report, train, test, account, first, per_user, action_counts):
    pass  # Hàm đã được định nghĩa trong cùng file.
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
        interaction = airbnb_grouped_rates(frame[is2014], [a, b])
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
    source["tables"][0][1].loc[source["tables"][0][1]["item"].eq("Ngày tải raw"), "description"] = "Chưa có bằng chứng trong hồ sơ dự án về ngày tải hoặc mã phiên bản Kaggle. Bản dữ liệu được nhận diện bằng SHA-256."
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
        f"**Thời gian phát sinh đặt chỗ:** trong {len(values):,} lượt đặt chỗ có độ trễ không âm, {coverage_at(30):.2f}% xảy ra trong 30 ngày, {coverage_at(60):.2f}% trong 60 ngày và {coverage_at(90):.2f}% trong 90 ngày. Các tỷ lệ này chỉ tính trên người đã đặt chỗ và có độ trễ hợp lệ, không phải xác suất đặt chỗ của toàn bộ người dùng. Kết quả gợi ý xem xét thời hạn 90 ngày cho phương án triển khai.",
        f"**Liên hệ của hồ sơ đăng ký:** gender có V={v_by_name.loc['gender','effect_all']:.3f} trên toàn kỳ và {v_by_name.loc['gender','effect_2014']:.3f} trong năm 2014, được diễn giải ở mức yếu đến vừa trong báo cáo. signup_app có liên hệ yếu hơn, với V lần lượt là {v_by_name.loc['signup_app','effect_all']:.3f} và {v_by_name.loc['signup_app','effect_2014']:.3f}. Hai biến này là ứng viên để kiểm tra giá trị bổ sung trong mô hình.",
        f"**Độ đầy đủ của hồ sơ tuổi:** age thiếu ở {train.age.isna().mean()*100:.2f}% người dùng. Trong năm 2014, cờ thiếu tuổi có V={age_signal.effect_2014:.3f}, còn tuổi trong dải 16–100 có rank-biserial={age_rank.effect_2014:.3f}, gần 0. Mức độ đầy đủ của hồ sơ có liên hệ đáng chú ý với nhãn y, trong khi khác biệt thứ hạng tuổi giữa hai nhóm rất nhỏ. Chỉ được dùng tuổi và cờ thiếu tuổi nếu xác nhận chúng phản ánh hồ sơ tại t0, vì việc bổ sung hồ sơ sau đăng ký có thể làm lộ thông tin tương lai.",
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
        "download_date_status": "unknown_no_documentary_evidence",
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
    pass  # Hàm đã được định nghĩa trong cùng file.
    report.airbnb_context = {"train": train, "test": test, "frame": frame, "account": account, "first": first}
    capture_evidence(report, {
        "association": association, "delay": lag_summary, "horizons": horizons,
        "delay_cohorts": lag_cohorts, "followup_sensitivity": followup,
        "sessions_2014": s2014, "event_counts": event_summary, "actions": actions,
        "protocol": proposed_protocol(train, account),
        **{f"strata_{key}": value for key, value in strata.items()},
        **{f"rates_{key}": rate_table(frame, key, "observed_booking") for key in display_columns},
    })


# ==============================================================================
# AIRBNB: nhãn 90 ngày, follow-up và mốc dự đoán
# Nguồn: airbnb_research_revision.py — nội dung đã gộp, không cần import file gốc.
# ==============================================================================

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
    pass  # Hàm đã được định nghĩa trong cùng file.
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
    pass  # Hàm đã được định nghĩa trong cùng file.
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
    pass  # Hàm đã được định nghĩa trong cùng file.
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
    pass  # Hàm đã được định nghĩa trong cùng file.
    pass  # Hàm đã được định nghĩa trong cùng file.
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
    pass  # Hàm đã được định nghĩa trong cùng file.
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


# ==============================================================================
# HOTEL / EXPEDIA: liên hệ, thời gian và thiết kế nghiên cứu
# Nguồn: hotel_expedia_research.py — nội dung đã gộp, không cần import file gốc.
# ==============================================================================

import hashlib
import json
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

pass  # Hàm đã được định nghĩa trong cùng file.

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
HOTEL_BLUE, HOTEL_ORANGE = "#245D80", "#C76A37"
HOTEL_SOURCE = "https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/"
EXPEDIA_SOURCE = "https://www.kaggle.com/competitions/expedia-personalized-sort/data"
CALIBRATION = "https://scikit-learn.org/stable/modules/calibration.html"
RANKING = "https://lightgbm.readthedocs.io/en/stable/Parameters.html#objective"


def walk(sections):
    for item in sections:
        yield item
        yield from walk(item.get("blocks", []))


def hotel_grouped_rates(frame, keys, target="is_canceled"):
    pass  # Hàm đã được định nghĩa trong cùng file.
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
        tab = hotel_grouped_rates(pop, ["hotel"])
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
    strata = hotel_grouped_rates(frame, ["hotel", "market_segment"])
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
    ax.scatter(association.effect_click, y-.1, label="Click", color=HOTEL_BLUE)
    ax.scatter(association.effect_booking, y+.1, label="Booking", color=HOTEL_ORANGE)
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
        ax.add_patch(FancyBboxPatch((x, 1.2), 3.4, 1.4, boxstyle="round,pad=0.12", facecolor="#e9f1f6", edgecolor=HOTEL_BLUE))
        ax.text(x+1.7, 1.9, label, ha="center", va="center", fontsize=10)
        if i < 2:
            ax.annotate("", (x+3.95, 1.9), (x+3.55, 1.9), arrowprops={"arrowstyle": "->", "color": HOTEL_BLUE})
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
        ax.barh(i, (cutoff-xmin).days, left=mdates.date2num(xmin), color=HOTEL_BLUE, height=.45)
        if not hotel:
            ax.barh(i, 7, left=mdates.date2num(cutoff), color="#dddddd", hatch="///", height=.45)
        ax.barh(i, (origin+pd.offsets.MonthBegin(1)-origin).days, left=mdates.date2num(origin), color=HOTEL_ORANGE, height=.45)
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


def hotel_expedia_display_header(value, dataset):
    if value == "n":
        return "Số booking" if dataset == "HOTEL" else "Số cặp"
    if value in HEADERS:
        return HEADERS[value]
    if isinstance(value, str) and value.startswith("full_"):
        return "Toàn train · " + HEADERS.get(value[5:], value[5:].replace("_", " "))
    return value


def hotel_expedia_prepare_publication(report):
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
        s["tables"] = [(label, table.rename(columns=lambda c: hotel_expedia_display_header(c, report.dataset))) for label, table in s["tables"]]
    reproducibility = chosen["reproducibility"]
    reproducibility["text"] += "\n\nPhần nghiên cứu bổ sung do scripts/eda_all_datasets.py tạo từ cùng CSV. V tính từ bảng chéo K×2 không hiệu chỉnh; rank-biserial = 2U/(n1×n0)−1, với U của nhãn 1 và xử lý hòa hạng của SciPy. Không dùng kiểm định giả định các dòng độc lập để khẳng định ý nghĩa thống kê. Thống kê bổ sung Expedia dùng toàn bộ search và các bảng đếm toàn train. Các lịch chia tập chỉ là bảng quy mô, chưa sinh tập học hoặc dự đoán.\n\nChạy riêng: `python scripts/eda_all_datasets.py --dataset " + report.dataset + "`. Cần file eda_all_datasets.py, pandas, numpy, scipy, matplotlib, nbformat và IPython cùng dữ liệu raw tương ứng. SHA-256 từng CSV ở phụ lục; ngày tải và phiên bản chưa được ghi nhận. Không suy ngày tải từ timestamp file."
    fingerprint = json.dumps({k: v.to_json(orient="split", double_precision=15) for k, v in sorted(report.research_evidence.items())}, sort_keys=True)
    report.facts.update(research_revision="hotel_expedia_airbnb_structure_v1", research_evidence_sha256=hashlib.sha256(fingerprint.encode()).hexdigest())
    previous = report.directory/"analysis_metadata.json"
    if previous.exists():
        old = json.loads(previous.read_text(encoding="utf-8"))["facts"]
        for key in ["rows", "columns", "positive", "rate", "duplicates", "deduplicated_rows", "deduplicated_rate", "searches", "clicks", "bookings", "click_rate", "booking_rate"]:
            if key in old and old[key] != facts[key]:
                raise ValueError(f"Underlying raw fact changed: {report.dataset}/{key}")
    pass  # Hàm đã được định nghĩa trong cùng file.
    report.rendered_tables_sha256 = sorted(hashlib.sha256(md_table(t).encode()).hexdigest() for s in walk(report.sections) for _, t in s["tables"])


def hotel_expedia_verify_artifacts(root, dataset, notebook):
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


# ==============================================================================
# Đọc dữ liệu, thống kê mô tả và dựng báo cáo cả 3 bộ
# Nguồn: build_descriptive_reports.py — nội dung đã gộp, không cần import file gốc.
# ==============================================================================

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
        column_name = str(column).strip().lower()
        calendar_year = column_name in {"year", "account year", "năm"} or column_name.endswith("_year") or column_name.startswith("năm ")
        if calendar_year and isinstance(v, (int, float, np.integer, np.floating)) and float(v).is_integer():
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
    successes = np.asarray(successes, dtype=float)
    n, successes = np.broadcast_arrays(n, successes)
    if ((n < 0) | (successes < 0) | (successes > n)).any():
        raise ValueError("Wilson requires 0 <= successes <= n")
    # An empty group has an undefined rate/interval, never a zero-rate estimate.
    n = np.where(n > 0, n, np.nan)
    p = successes / n
    z = 1.959963984540054
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    half = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return (center-half)*100, (center+half)*100


def validate_binary_target(values, name="target"):
    """Require numeric/bool 0/1 labels; NA is unlabelled, not a negative."""
    if not values.dropna().isin([0, 1]).all():
        raise ValueError(f"{name} must contain only 0/1 (or bool) and missing values")


def rate_table(df, group, target, limit=None, ci=True):
    """Binary positive rate per group, using only observed labels as denominator."""
    validate_binary_target(df[target], target)
    key = df[group].astype("object").where(df[group].notna(), "<MISSING>")
    out = df.groupby(key, observed=True, dropna=False)[target].agg(n="count", positive="sum")
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
        a = train[col].astype(object).where(train[col].notna(), "<MISSING>").astype(str).value_counts(normalize=True)
        b = test[col].astype(object).where(test[col].notna(), "<MISSING>").astype(str).value_counts(normalize=True)
        idx = a.index.union(b.index)
        tv = (a.reindex(idx, fill_value=0)-b.reindex(idx, fill_value=0)).abs().sum()/2
        rows.append([col, tv, len(b.index.difference(a.index)), train[col].isna().mean()*100,
                     test[col].isna().mean()*100])
    return pd.DataFrame(rows, columns=["column", "total_variation_0_1", "test_only_categories",
                                        "train_missing_pct", "test_missing_pct"]).sort_values("total_variation_0_1", ascending=False)


def metadata_table(df, meanings=None):
    """Describe all columns; unspecified meaning/caution stays blank."""
    meanings = meanings or {}
    return pd.DataFrame([[c, str(df[c].dtype), int(df[c].nunique(dropna=True)),
                          int(df[c].isna().sum()), df[c].isna().mean()*100,
                          *meanings.get(c, ("", ""))] for c in df.columns],
                        columns=["column", "pandas_dtype", "distinct_nonnull", "missing_n",
                                 "missing_pct", "meaning", "role_or_caution"])


def _json_default(value):
    """Serialize numpy/pandas scalar facts without hiding unsupported objects."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if value is pd.NA or value is pd.NaT:
        return None
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


@dataclass
class Report:
    dataset: str
    title: str
    root: Path
    sections: list = field(default_factory=list)
    facts: dict = field(default_factory=dict)
    figure_notes: dict = field(default_factory=dict)
    prepare: object = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.root = Path(self.root)

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

    def publish(self, prepare=None):
        """Publish any dataset; an optional callback can prepare domain-specific sections.

        No Hotel/Airbnb/Expedia schema is required. Use prepare(report) either
        here or on the constructor; the per-call callback takes precedence.
        """
        hook = self.prepare if prepare is None else prepare
        if hook is not None:
            hook(self)
        environment = {"Python": platform.python_version(), "pandas": pd.__version__,
                       "numpy": np.__version__, "matplotlib": matplotlib.__version__}
        if not any(s["key"] == "reproducibility" for s in self.sections):
            self.add("reproducibility", "Tái lập và phạm vi",
                     "Thống kê mô tả trên dữ liệu được cung cấp. Các giá trị thiếu không "
                     "được thay thế; ngoại lai không bị xóa. Không tạo tập feature hoặc "
                     "huấn luyện mô hình. Nhãn, đơn vị và thời điểm quan sát do người dùng xác định.",
                     [("Môi trường", pd.DataFrame(environment.items(), columns=["component", "value"]))])
        parts = [f"# {self.title}",
                 "> Phạm vi: EDA và thống kê mô tả; không huấn luyện mô hình.",
                 f"Ngày phân tích: {datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date().isoformat()}."]

        def render(item, level=2):
            parts.append(f"{'#' * level} {item['title']}")
            if item["text"]:
                parts.append(item["text"])
            for label, table in item["tables"]:
                parts.extend([f"**{label}**", md_table(table)])
            for filename in item["figures"]:
                path = Path(filename)
                if path.name not in self.figure_notes:
                    raise ValueError(f"Chart lacks an interpretation: {path}")
                parts.extend([f"![{path.stem.replace('_', ' ')}](figures/{path.name})",
                              self.figure_notes[path.name]])
            for block in item.get("blocks", []):
                render(block, level + 1)

        for item in self.sections:
            render(item)
        metadata = {
            "dataset": self.dataset, "facts": self.facts,
            "analysis_date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "environment": environment, "section_keys": [s["key"] for s in self.sections],
            "figure_notes": self.figure_notes,
            "download_date": None,
            "download_date_note": "Chưa được cung cấp; không suy từ timestamp file.",
            **self.metadata,
        }
        serialized = json.dumps(metadata, ensure_ascii=False, indent=2, default=_json_default)
        (self.directory / "README.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")
        (self.directory / "analysis_metadata.json").write_text(serialized + "\n", encoding="utf-8")
        return self


def _prepare_builtin_report(report):
    """Opt-in adapter for the original three report schemas; never used by new datasets."""
    environment = pd.DataFrame([["Python", platform.python_version()], ["pandas", pd.__version__],
                                ["numpy", np.__version__], ["matplotlib", matplotlib.__version__],
                                ["Phương pháp", "Thống kê mô tả, không mô hình"],
                                ["Chunk CSV lớn", str(CHUNK_SIZE)]], columns=["component", "value"])
    if report.dataset == "AIRBNB":
        import scipy
        import nbformat
        import IPython
        environment = pd.concat([environment, pd.DataFrame(
            [["scipy", scipy.__version__], ["nbformat", nbformat.__version__], ["IPython", IPython.__version__]],
            columns=environment.columns)], ignore_index=True)
    sampling_note = ("Expedia tính thống kê trên toàn bộ train, gồm quantile tuyến tính, skewness không chệch theo pandas và Spearman xếp hạng trung bình cho ties, loại NA theo từng cặp. Chỉ scatter (tối đa 4.000 điểm) và hình pattern missing (300 dòng) lấy mẫu hiển thị với numpy default_rng, seed=42; các bảng và heatmap tổng hợp dùng toàn bộ train. Cột raw được đệm tạm trên đĩa để giới hạn RAM và xóa sau khi xuất báo cáo; không tạo tập processed. Test chỉ là đối chiếu schema/chất lượng và các phân phối tổng hợp, không dùng tính thống kê train. " if report.dataset == "EXPEDIA" else "Hình lấy mẫu hiển thị dùng seed=42. ")
    report.add("reproducibility", "Tái lập và kiểm soát phạm vi", "Chạy notebook theo thứ tự từ đầu, hoặc chạy `python scripts/eda_all_datasets.py --dataset " + report.dataset + "` tại thư mục gốc. Script chỉ đọc CSV raw, viết báo cáo/biểu đồ và lưu notebook trong notebooks/; không sửa raw, không ghi data/processed, không gọi pipeline huấn luyện. Các thời điểm phân tích dùng Asia/Ho_Chi_Minh. SHA-256 ở danh mục file nhận diện nguồn; số dòng theo CSV parser được đối chiếu với data_lines của file chính. Ngày tải raw chưa được ghi nhận; không suy từ mtime/ctime. " + sampling_note + "Script thực thi các cell bằng IPython trong cùng tiến trình và lưu output thật vào notebook; không khởi tạo kernel mạng. Phụ thuộc dựng báo cáo gồm pandas, numpy, scipy, matplotlib, nbformat và IPython; có thể mở notebook bằng Jupyter để Run All.", [("Môi trường thực thi", environment)])
    if report.dataset == "AIRBNB":
        pass  # Hàm đã được định nghĩa trong cùng file.
        report.sections[-1] = reproducibility_section(report, environment)
        prepare_publication = airbnb_prepare_publication
        prepare_publication(report)
    else:
        prepare_publication = hotel_expedia_prepare_publication
        prepare_publication(report)
    digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report.metadata.update(diagnostics_script_sha256=digest,
                           environment=dict(environment.itertuples(index=False, name=None)))
    if report.dataset == "AIRBNB":
        report.metadata.update(
            airbnb_deep_dive_script_sha256=digest, presentation_script_sha256=digest,
            research_script_sha256=digest,
            completed_stages=getattr(report, "completed_stages", []),
            executive_evidence=getattr(report, "executive_evidence", []),
            executive_numeric_checks=getattr(report, "executive_numeric_checks", []),
            rendered_tables_sha256=getattr(report, "rendered_tables_sha256", []),
            download_date="not_recorded",
        )
    else:
        report.metadata.update(research_script_sha256=digest,
                               rendered_tables_sha256=report.rendered_tables_sha256,
                               executive_evidence=report.executive_evidence)
    if report.dataset == "EXPEDIA":
        report.metadata["full_train_script_sha256"] = digest


def show_section(report, key):
    from IPython.display import Markdown, display, Image
    section = next(s for s in report.sections if s["key"] == key)
    def show(s, nested=False):
        if nested: display(Markdown(f"### {s['title']}"))
        if s["text"]: display(Markdown(s["text"]))
        for label, table in s["tables"]:
            display(Markdown(f"**{label}**"))
            display(Markdown(md_table(table)))
        for p in s["figures"]:
            display(Image(filename=str(p)))
            display(Markdown(report.figure_notes[p.name]))
        for block in s.get("blocks",[]): show(block,True)
    show(section)


def manifest(root, dataset):
    root = Path(root)
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
    r = Report("HOTEL", "HOTEL — Hiểu dữ liệu đặt phòng và kết quả hủy/no-show", root, prepare=_prepare_builtin_report)
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
    pass  # Hàm đã được định nghĩa trong cùng file.
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
    pass  # Hàm đã được định nghĩa trong cùng file.
    pass  # Hàm đã được định nghĩa trong cùng file.
    r = Report("AIRBNB", "AIRBNB — Hiểu người dùng mới, lượt đặt chỗ đầu tiên và độ phủ hành vi", root, prepare=_prepare_builtin_report)
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
    sess_rows=0; sess_missing=None; sess_unique={}; devices={}; actions={}; per_user=[]; transaction_parts=[]; profile_parts=[]
    elapsed_n=0; elapsed_sum=0.; elapsed_min=np.inf; elapsed_max=-np.inf; elapsed_zero=0; elapsed_negative=0
    for chunk in pd.read_csv(folder/"sessions.csv",chunksize=CHUNK_SIZE):
        transaction_parts.extend(session_action_counts(chunk))
        profile_parts.extend(profile_action_counts(chunk))
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
    r.profile_action_counts = pd.concat(profile_parts,ignore_index=True).groupby(["user_id","field","value"],observed=True,sort=False).event_n.sum().reset_index()
    r.session_user_ids = per_user.index
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
    pass  # Hàm đã được định nghĩa trong cùng file.
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
    pass  # Hàm đã được định nghĩa trong cùng file.
    rows=0; missing=None; dtypes={}; sums={}; squares={}; ns={}; mins={}; maxs={}
    query_parts=[]; pairs_a=[]; pairs_b=[]; properties=set(); query_ids=set()
    numeric_cols=EXPEDIA_NUM+[f"comp{i}_rate_percent_diff" for i in range(1,9)]+(["gross_bookings_usd"] if training else [])
    minimum="9999"; maximum=""; book_no_click=0; booking_missing_gross=0; nonbooking_gross=0; bad_labels=0
    zero_price=0; negative_price=0; high_price=0; very_high_price=0
    cat_cols=["site_id","visitor_location_country_id","prop_country_id","prop_starrating","prop_brand_bool",
              "promotion_flag","srch_saturday_night_bool","random_bool"]
    dictionary_categories=cat_cols+["srch_destination_id"]+[f"comp{i}_{kind}" for i in range(1,9) for kind in ["rate","inv"]]+(["position","click_bool","booking_bool"] if training else [])
    cat_parts={c:[] for c in dictionary_categories}
    group_parts={c:[] for c in cat_cols+["price_group","window_group","year_month","random_bool_position", "random_star", "random_price"]} if training else {}
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
            query_parts.append(query_diag.groupby("srch_id",sort=False).agg(n=("prop_id","size"),clicks=("click_bool","sum"),bookings=("booking_bool","sum"),date_min=("_date_ns","min"),date_max=("_date_ns","max"),random_min=("random_bool","min"),random_max=("random_bool","max")))
            for c in cat_cols:
                group_parts[c].append(chunk.groupby(c,dropna=False).agg(n=("srch_id","size"),clicks=("click_bool","sum"),bookings=("booking_bool","sum")).reset_index())
            price_group=pd.cut(chunk.price_usd,[-np.inf,0,50,100,150,250,500,1000,np.inf],labels=["<=0","(0,50]","(50,100]","(100,150]","(150,250]","(250,500]","(500,1000]",">1000"])
            window_group=pd.cut(chunk.srch_booking_window,[-np.inf,0,7,30,90,180,365,np.inf],labels=["<=0","1–7","8–30","31–90","91–180","181–365",">365"])
            for name,labels in [("price_group",price_group),("window_group",window_group),("year_month",chunk.date_time.str[:7])]:
                tmp=pd.DataFrame({name:labels,"click_bool":chunk.click_bool,"booking_bool":chunk.booking_bool,"srch_id":chunk.srch_id})
                group_parts[name].append(tmp.groupby(name,observed=True,dropna=False).agg(n=("srch_id","size"),clicks=("click_bool","sum"),bookings=("booking_bool","sum")).reset_index())
            group_parts["random_bool_position"].append(chunk.groupby(["random_bool","position"],dropna=False).agg(n=("srch_id","size"),clicks=("click_bool","sum"),bookings=("booking_bool","sum")).reset_index())
            group_parts["random_star"].append(chunk.groupby(["random_bool", "prop_starrating"],dropna=False).agg(n=("srch_id","size"),clicks=("click_bool","sum"),bookings=("booking_bool","sum")).reset_index())
            price_strata = chunk.assign(price_group=price_group)
            group_parts["random_price"].append(price_strata.groupby(["random_bool", "price_group"],observed=True,dropna=False).agg(n=("srch_id","size"),clicks=("click_bool","sum"),bookings=("booking_bool","sum")).reset_index())
        else:
            query_diag=chunk.assign(_date_ns=pd.to_datetime(chunk.date_time,format="%Y-%m-%d %H:%M:%S").astype("int64"))
            query_parts.append(query_diag.groupby("srch_id",sort=False).agg(n=("prop_id","size"),date_min=("_date_ns","min"),date_max=("_date_ns","max")))
    # Exact pair duplicate check, not a probabilistic hash duplicate count.
    pairs=pd.DataFrame({"srch_id":np.concatenate(pairs_a),"prop_id":np.concatenate(pairs_b)})
    duplicate_pairs=int(pairs.duplicated().sum())
    del pairs,pairs_a,pairs_b
    query=pd.concat(query_parts).groupby(level=0).agg({"n":"sum",**({"clicks":"sum","bookings":"sum", "random_min":"min", "random_max":"max"} if training else {}),"date_min":"min","date_max":"max"})
    stats=[]
    for c in numeric_cols:
        vns=ns[c]; mean=sums[c]/vns if vns else np.nan
        std=math.sqrt(max(0,(squares[c]-sums[c]*sums[c]/vns)/(vns-1))) if vns>1 else np.nan
        stats.append([c,vns,mean,std,mins.get(c,np.nan),maxs.get(c,np.nan)])
    stats=pd.DataFrame(stats,columns=["column","full_count_nonnull","full_mean","full_std","full_min","full_max"])
    if training:
        pass  # Hàm đã được định nghĩa trong cùng file.
        store.finish()
        stats=full_numeric_statistics(store,stats)
    cat={c:_combine_group(parts,[c]) for c,parts in cat_parts.items()}
    group_keys = {"random_bool_position": ["random_bool", "position"], "random_star": ["random_bool", "prop_starrating"], "random_price": ["random_bool", "price_group"]}
    groups={c:_combine_group(parts,group_keys.get(c,[c])) for c,parts in group_parts.items()}
    for g in groups.values():
        g["click_pct"]=g.clicks/g.n*100; g["booking_pct"]=g.bookings/g.n*100
    return dict(rows=rows,missing=missing,dtypes=dtypes,stats=stats,store=store,queries=query,
                query_ids=query_ids,properties=properties,cat=cat,groups=groups,min_date=minimum,max_date=maximum,
                duplicate_pairs=duplicate_pairs,book_no_click=book_no_click,booking_missing_gross=booking_missing_gross,
                nonbooking_gross=nonbooking_gross,bad_labels=bad_labels,zero_price=zero_price,negative_price=negative_price,
                high_price=high_price,very_high_price=very_high_price)


def expedia_report(root):
    pass  # Hàm đã được định nghĩa trong cùng file.
    inventory=manifest(root,"EXPEDIA")
    rows=int(inventory.set_index("file").loc["train.csv","data_lines"])
    numeric=EXPEDIA_NUM+[f"comp{i}_rate_percent_diff" for i in range(1,9)]+["gross_bookings_usd"]
    with TrainColumns(rows,numeric) as store:
        return _expedia_report(root,inventory,store)


def _expedia_report(root,inventory,store):
    r=Report("EXPEDIA","EXPEDIA — Hiểu tìm kiếm, click và booking ở cấp khách sạn hiển thị",root, prepare=_prepare_builtin_report)
    folder=root/"data/raw/EXPEDIA"
    train=scan_expedia(folder/"train.csv",True,store)
    test=scan_expedia(folder/"test.csv",False)
    pass  # Hàm đã được định nghĩa trong cùng file.
    train["correlation"],train["correlation_pairs"]=exact_spearman(store, CORRELATION_COLUMNS)
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
    pass  # Hàm đã được định nghĩa trong cùng file.
    enrich_expedia(r,train,test)
    pass  # Hàm đã được định nghĩa trong cùng file.
    deepen_expedia(r,train,test)
    return r.publish()


def dataframe_report(df, dataset, root, *, title=None, numeric_columns=None,
                     categorical_columns=None, target=None, group_columns=None,
                     meanings=None, test=None, drift_columns=None, prepare=None,
                     publish=True, plots=True):
    """EDA for an arbitrary DataFrame, with optional binary labels/test frame.

    Raw values are never changed. Numeric/categorical columns are inferred by
    dtype unless explicitly supplied; exclude IDs using the column parameters.
    No target is inferred or manufactured. Missing labels are excluded from
    rate denominators. Set publish=False to add your own sections first.
    This entry point holds the DataFrame in RAM; TrainColumns is available for
    custom chunked analyses of larger data.
    """
    if not df.columns.is_unique:
        raise ValueError("EDA requires unique column names")
    numeric = ([c for c in df.select_dtypes(include="number").columns if c != target]
               if numeric_columns is None else list(numeric_columns))
    categorical = ([c for c in df.columns if c != target and
                    (not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]))
                    and not pd.api.types.is_datetime64_any_dtype(df[c])]
                   if categorical_columns is None else list(categorical_columns))
    groups = list(group_columns or [])
    requested = numeric + categorical + groups + ([] if target is None else [target])
    missing = [c for c in requested if c not in df.columns]
    if missing:
        raise ValueError(f"Columns not found: {missing}")
    if any(not pd.api.types.is_numeric_dtype(df[c]) for c in numeric):
        raise ValueError("numeric_columns must refer to numeric dtypes")
    if target is not None:
        validate_binary_target(df[target], target)
    report = Report(dataset, title or f"{dataset} — EDA và thống kê mô tả", root, prepare=prepare)
    report.facts.update(rows=len(df), columns=len(df.columns), duplicates=int(df.duplicated().sum()),
                        target=target, numeric_columns=numeric, categorical_columns=categorical)
    report.add("overview", "Tổng quan", "Mỗi dòng là một quan sát theo định nghĩa của người cung cấp dữ liệu.",
               [("Quy mô", pd.DataFrame([report.facts], columns=["rows", "columns", "duplicates"]))])
    report.add("dictionary", "Từ điển và chất lượng dữ liệu", "Ô mô tả trống là thông tin chưa được cung cấp.",
               [("Thông tin cột", metadata_table(df, meanings))])
    if numeric:
        report.add("numeric", "Thống kê biến số", "Phân vị, độ lệch và hàng rào IQR dùng các giá trị không thiếu của từng cột; không xóa ngoại lai.",
                   [("Thống kê mô tả", numeric_table(df, numeric)),
                    ("Ngoại lai 1,5×IQR", iqr_table(df, numeric, dataset))])
        usable = [c for c in numeric if df[c].notna().any()]
        if plots and usable:
            fig, axes = plt.subplots(len(usable), 1, figsize=(9, 3 * len(usable)), squeeze=False)
            for ax, column in zip(axes.flat, usable):
                values = df[column].dropna()
                finite = values[np.isfinite(values)]
                ax.hist(finite, bins=30, color=BLUE)
                ax.set(title=f"{column}: {len(finite):,} finite values; {len(values)-len(finite):,} infinite excluded from plot",
                       xlabel=column, ylabel="Observations")
            fig.tight_layout()
            path = report.savefig("numeric_distributions", fig)
            fig_note(report, path, "Histogram dùng mọi giá trị hữu hạn không thiếu, không cắt đuôi ngoại lai. Giá trị vô hạn chỉ được loại khỏi hình, không sửa raw hoặc bảng thống kê.")
            report.sections[-1]["figures"].append(path)
        if len(numeric) >= 2:
            corr = df[numeric].corr(method="spearman")
            report.add("correlation", "Tương quan Spearman", "Loại NA theo từng cặp, không suy quan hệ nhân quả.",
                       [("Spearman", corr.reset_index(names="column"))])
    if categorical:
        report.add("categorical", "Thống kê biến phân loại", "Tỷ lệ trên tất cả dòng; nhóm thiếu được hiển thị riêng.",
                   [("Nhóm phổ biến", categorical_table(df, categorical)),
                    ("Số nhóm và nhóm hiếm", category_cardinality(df, categorical))])
    if target is not None:
        report.facts.update(labelled_rows=int(df[target].notna().sum()), missing_labels=int(df[target].isna().sum()))
        counts = df[target].value_counts(dropna=False).rename_axis(target).reset_index(name="n")
        report.add("target", "Phân phối nhãn", "Chỉ dùng nhãn 0/1 được cung cấp. NA là chưa có nhãn, không phải âm tính.",
                   [("Số lượng nhãn", counts)] +
                   [(f"Tỷ lệ theo {c}", rate_table(df, c, target)) for c in groups])
    elif groups:
        raise ValueError("group_columns for target rates requires an explicit target")
    if test is not None:
        schema = pd.DataFrame({"column": df.columns.union(test.columns, sort=False)})
        schema["in_train"] = schema.column.isin(df.columns)
        schema["in_test"] = schema.column.isin(test.columns)
        comparisons = [("Schema train/test", schema)]
        drift = ([c for c in categorical if c in test.columns] if drift_columns is None else list(drift_columns))
        if drift:
            comparisons.append(("Total variation phân loại (0–1)", drift_table(df, test, drift)))
        report.add("train_test", "Đối chiếu train/test", "So sánh mô tả; không fit phép biến đổi hoặc gộp hai tập.", comparisons)
    return report.publish() if publish else report


def csv_report(root, *, dataset, file, test_file=None, read_csv_options=None, **options):
    """Read your CSV(s) and call dataframe_report; relative paths use data/raw/<dataset>/."""
    root = Path(root)
    def resolve(filename):
        path = Path(filename)
        return path if path.is_absolute() else root / "data" / "raw" / dataset / path
    reader = dict(read_csv_options or {})
    frame = pd.read_csv(resolve(file), **reader)
    test = pd.read_csv(resolve(test_file), **reader) if test_file is not None else None
    report = dataframe_report(frame, dataset, root, test=test, publish=False, **options)
    report.metadata["source_files"] = [str(resolve(file))] + ([] if test_file is None else [str(resolve(test_file))])
    return report.publish()


# Domain-specific code is opt-in through this registry. New datasets do not
# inherit the old sources, target definitions, presentation or verification.
REPORTS = {"HOTEL": hotel_report, "AIRBNB": airbnb_report, "EXPEDIA": expedia_report}
REPORT_LAYOUTS = {"HOTEL": LAYOUT, "AIRBNB": AIRBNB_LAYOUT, "EXPEDIA": LAYOUT}
REPORT_CONFIGS = {}
REPORT_NOTEBOOK_SETUP = {}


def register_report(dataset, builder, *, notebook_setup=None, layout=None):
    """Register builder(root) -> Report. notebook_setup is trusted Python code
    that repeats your registration when reopening a generated notebook.
    Programmatic builders need no notebook_setup when only using build_report.
    """
    if not isinstance(dataset, str) or not dataset or Path(dataset).name != dataset or dataset in {".", ".."}:
        raise ValueError("dataset must be a nonempty folder name")
    if not callable(builder):
        raise TypeError("builder must be callable")
    REPORTS[dataset] = builder
    REPORT_LAYOUTS[dataset] = layout
    REPORT_NOTEBOOK_SETUP[dataset] = notebook_setup
    REPORT_CONFIGS.pop(dataset, None)


def register_csv_report(dataset, **config):
    """Register a serializable CSV configuration, usable from CLI and notebooks."""
    from functools import partial
    # Store a JSON copy so later mutation of the caller's lists cannot change it.
    config = json.loads(json.dumps(config))
    if "file" not in config:
        raise ValueError("CSV configuration requires 'file'")
    forbidden = {"dataset", "root", "publish", "prepare", "test"}.intersection(config)
    if forbidden:
        raise ValueError(f"Unsupported CSV configuration keys: {sorted(forbidden)}")
    register_report(dataset, partial(csv_report, dataset=dataset, **config))
    REPORT_CONFIGS[dataset] = config


def build_report(dataset, root):
    """Run a registered report builder, with a clear error for unknown names."""
    if dataset not in REPORTS:
        raise ValueError(f"Unknown dataset {dataset!r}; register_report/register_csv_report first. Available: {', '.join(REPORTS)}")
    return REPORTS[dataset](Path(root))


def make_notebook(root, dataset):
    """Tạo notebook chạy lại bằng duy nhất file eda_all_datasets.py và CSV raw."""
    import nbformat as nbf

    if dataset not in REPORTS:
        raise ValueError(f"Unknown dataset: {dataset!r}")
    layout = REPORT_LAYOUTS.get(dataset)
    registration = ""
    if dataset in REPORT_CONFIGS:
        registration = ("import json\n" + f"eda.register_csv_report({dataset!r}, **json.loads({json.dumps(REPORT_CONFIGS[dataset])!r}))\n")
    elif dataset in REPORT_NOTEBOOK_SETUP:
        registration = REPORT_NOTEBOOK_SETUP[dataset]
        if registration is None:
            raise ValueError("Custom builders need notebook_setup code to make a reproducible notebook; or use register_csv_report")
        registration += "\n"
    title = human_title if dataset == "AIRBNB" else str
    introduction = (
        f"# {dataset} — EDA, thống kê mô tả và tìm hiểu sơ bộ\n\n"
        "Phạm vi: đọc CSV gốc, kiểm tra chất lượng, nhãn và thống kê mô tả. "
        "Các đề xuất nghiên cứu chưa phải kết quả mô hình.\n\n"
        "Cần file scripts/eda_all_datasets.py (hoặc eda_all_datasets.py tại gốc) "
        "và dữ liệu trong data/raw/. Chạy các cell theo thứ tự để tái lập."
    )
    setup = """from pathlib import Path
import importlib.util
import sys

cwd = Path.cwd().resolve()
PROJECT_ROOT = globals().get('_EDA_ROOT')
if PROJECT_ROOT is None:
    PROJECT_ROOT = next((p for p in (cwd, *cwd.parents)
                         if (p / 'data' / 'raw').is_dir()), None)
if PROJECT_ROOT is None:
    raise FileNotFoundError('Không tìm thấy data/raw trong thư mục dự án.')
EDA_FILE = globals().get('_EDA_FILE')
if EDA_FILE is None:
    EDA_FILE = next((p for p in [PROJECT_ROOT / 'scripts' / 'eda_all_datasets.py',
                                PROJECT_ROOT / 'eda_all_datasets.py'] if p.is_file()), None)
if EDA_FILE is None:
    raise FileNotFoundError('Cần file eda_all_datasets.py tại gốc hoặc scripts/.')
spec = importlib.util.spec_from_file_location('eda_all_datasets', EDA_FILE)
eda = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = eda
spec.loader.exec_module(eda)
""" + registration + f"report = eda.build_report({dataset!r}, PROJECT_ROOT)\n" + "print('Đã tính EDA từ CSV raw:', report.facts)"
    cells = [nbf.v4.new_markdown_cell(introduction), nbf.v4.new_code_cell(setup)]
    for key, heading in layout or []:
        cells.extend([nbf.v4.new_markdown_cell(f"## {title(heading)}"),
                      nbf.v4.new_code_cell(f"eda.show_section(report, {key!r})")])
    if layout is None:
        cells.append(nbf.v4.new_code_cell(
            "from IPython.display import Markdown, display\n"
            "for item in report.sections:\n"
            "    display(Markdown('## ' + item['title']))\n"
            "    eda.show_section(report, item['key'])"))
    nb = nbf.v4.new_notebook(cells=cells)
    nb.metadata.update(
        kernelspec={"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"},
        language_info={"name": "python", "version": platform.python_version()},
    )
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

Các báo cáo chi tiết cùng cấu trúc: thuật ngữ → tóm tắt điều hành → bài toán → nguồn/phiên bản → chất lượng → đơn biến → nhãn/đa biến/thời gian/nhóm con → giới hạn → thuật toán và thiết kế đánh giá. Từ điển, quyết định từng cột, bảng dài và truy vết tóm tắt nằm ở phụ lục. Các lịch chia tập và ngưỡng chấp nhận là đề xuất; chưa tạo tập học hoặc huấn luyện mô hình.

HOTEL bổ sung liên hệ của 29 cột ứng viên, độ nhạy raw/bỏ trùng/từng khách sạn, chuẩn hóa cơ cấu phân khúc và quyết định vai trò cho đủ 32 cột. Thiết kế so sánh LR có tương tác với CatBoost; lịch theo tháng đến chỉ dùng chẩn đoán hồi cứu khi chưa có snapshot tại t0. EXPEDIA bổ sung liên hệ với hai nhãn, trọng số theo dòng/search, phân tầng giá/sao theo cơ chế hiển thị và quyết định vai trò đủ 54 cột. Thiết kế xác suất so sánh LR với LightGBM binary; LambdaRank là nhánh xếp hạng riêng. Khoảng đệm nhãn Expedia chưa được xác nhận; không coi lịch đề xuất là bằng chứng nhãn đã hoàn tất.

## 1. Kết luận phục vụ lựa chọn bài toán

Ba bộ dữ liệu phù hợp với ba hành vi và ba đơn vị dự đoán khác nhau. Propensity ở đây là xác suất hành vi; không phải propensity score nhận treatment hoặc ước lượng uplift. Chưa có thông tin can thiệp để kết luận tác động marketing.

| Bộ | Hành vi phù hợp | Đơn vị | Giới hạn quyết định |
| --- | --- | --- | --- |
| HOTEL | Hủy/no-show của booking | Booking | Không đồng nghĩa customer churn; cần xác minh snapshot tại thời điểm dự đoán |
| AIRBNB | Lượt đặt chỗ đầu tiên trong 90 ngày, dưới giả định NDF được theo dõi ít nhất 90 ngày | Người dùng mới | Nhánh chính không dùng cờ hồ sơ; các nhánh mở rộng cần bằng chứng tại t0; sessions thiếu timestamp |
| EXPEDIA | Click/booking trong danh sách khách sạn | Cặp search-property | Phù hợp bối cảnh tìm kiếm/xếp hạng; không có ID khách để chấm CRM; thiếu search không click trong train |

Nếu đề tài nhắm đến chuyển đổi khách hàng mới, AIRBNB phù hợp về đơn vị quan sát. Nếu nghiên cứu vận hành hủy booking, HOTEL rõ mục tiêu và nhẹ hơn. Nếu nghiên cứu tương tác với danh sách tìm kiếm, EXPEDIA phù hợp hơn. Không xếp một bộ là tốt nhất cho mọi mục tiêu và không coi mọi cột thô là feature hợp lệ.

Đối với AIRBNB, nhãn y90 có {a['conditional_90_positive']:,} trường hợp dương trên toàn bộ {a['rows']:,} dòng ({a['conditional_90_fraction_all_rows_pct']:.2f}%). Khi để {a['conditional_90_unassigned']:,} ngoại lệ ngày âm ở trạng thái chưa gán, mẫu nghiên cứu còn {a['conditional_90_eligible']:,} người, tỷ lệ dương {a['conditional_90_rate_pct']:.2f}%. Đây là mục tiêu nghiên cứu dưới giả định NDF được theo dõi ít nhất 90 ngày. Mỗi mốc dự đoán tháng dùng toàn bộ nhãn đã hoàn tất, với hiệu chỉnh từ điểm OOF theo thời gian. Nhánh chính tối thiểu chỉ dùng mốc tạo tài khoản; hai cờ hồ sơ bị chặn khi Q1 còn mở. Trong từng nhánh hợp lệ, CatBoost được so với Logistic Regression gồm cả tương tác cặp; mọi ứng viên phải đạt ngưỡng hiệu chỉnh tuyệt đối. Các tỷ lệ theo nhãn y gốc trong phần so sánh ba bộ vẫn được giữ riêng.

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
- Các dòng cùng search phụ thuộc nhau. Báo cáo giữ cấu trúc nhóm, phân tích vị trí cùng random_bool và đề xuất đánh giá theo thời gian/nhóm search; chưa tạo tập chia hoặc huấn luyện.

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

Notebook chỉ lưu trong `notebooks/HOTEL`, `notebooks/AIRBNB`, `notebooks/EXPEDIA`; `reports` chứa báo cáo Markdown, biểu đồ và metadata cần để dựng báo cáo tổng hợp. Mỗi notebook đọc lại CSV qua cùng [script EDA](../scripts/eda_all_datasets.py); các bảng Markdown và hình được sinh từ cùng kết quả tính, tránh số liệu viết tay lệch nhau.

Chạy tại thư mục gốc dự án:

```powershell
python scripts/eda_all_datasets.py
# Hoặc chỉ dựng lại một bộ:
python scripts/eda_all_datasets.py --dataset AIRBNB
```

Để chạy lại notebook độc lập, mở notebook và Run All; cell đầu quét dữ liệu và cập nhật bản Markdown/biểu đồ của bộ đó. Chạy script toàn bộ để cập nhật ba notebook và báo cáo tổng hợp. Môi trường và SHA-256 nguồn được ghi trong báo cáo chi tiết; không sửa raw hoặc pipeline dự án.
"""
    (root/"reports/README.md").write_text(text,encoding="utf-8")


FUNCTION_GROUPS["API tái sử dụng cho dữ liệu mới"] = [
    "dataframe_report", "csv_report", "register_report", "register_csv_report",
    "validate_binary_target",
]


def main(argv=None):
    import sys
    import nbformat
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output
    from traitlets.config import Config
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", help="Tên bộ dữ liệu đã đăng ký; bỏ trống để chạy các bộ trong --config, hoặc ba bộ cũ")
    parser.add_argument("--config", type=Path, help="JSON: {tên_bộ: {file: tên.csv, target: tên_nhãn, ...}}; target có thể bỏ trống")
    parser.add_argument("--root", type=Path, help="Thư mục dự án chứa data/raw (mặc định tự tìm từ vị trí file)")
    parser.add_argument("--list-functions", action="store_true", help="Liệt kê hàm/class, không đọc CSV hoặc ghi báo cáo")
    args=parser.parse_args(argv)
    if args.list_functions:
        for group, names in FUNCTION_GROUPS.items():
            print(group + ":")
            print("  " + ", ".join(names))
        return
    configured = []
    if args.config:
        configs = json.loads(args.config.read_text(encoding="utf-8-sig"))
        if not isinstance(configs, dict) or not configs:
            parser.error("--config phải là object JSON không rỗng chứa tên các bộ dữ liệu")
        for name, config in configs.items():
            register_csv_report(name, **config)
            configured.append(name)
    selected = [args.dataset] if args.dataset else (configured or list(REPORTS))
    unknown = [name for name in selected if name not in REPORTS]
    if unknown:
        parser.error(f"Bộ dữ liệu chưa đăng ký: {unknown}; dùng --config cho bộ mới")
    here = Path(__file__).resolve().parent
    root = args.root.resolve() if args.root else next(
        (p for p in (here, *here.parents) if (p / "data" / "raw").is_dir()), None)
    if root is None or not root.is_dir():
        parser.error("Không tìm thấy thư mục dự án; hãy truyền --root đường/dẫn/dự/án")
    if str(root) not in sys.path:
        sys.path.insert(0,str(root))
    shell_config=Config()
    shell_config.HistoryManager.hist_file=":memory:"
    shell=InteractiveShell.instance(config=shell_config)
    for dataset in selected:
        print(f"Executing {dataset} report notebook ...",flush=True)
        nb=make_notebook(root,dataset)
        shell.user_ns.clear()
        shell.init_user_ns()
        shell.user_ns["_EDA_ROOT"] = root
        shell.user_ns["_EDA_FILE"] = Path(__file__).resolve()
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
        if dataset in REPORT_CONFIGS or dataset in REPORT_NOTEBOOK_SETUP:
            # Generic/custom reports have no old-domain assertions.
            continue
        if dataset == "AIRBNB":
            verify_artifacts = airbnb_verify_artifacts
            verify_artifacts(root, nb)
        else:
            verify_artifacts = hotel_expedia_verify_artifacts
            verify_artifacts(root, dataset, nb)
    if any(d in {"HOTEL", "AIRBNB", "EXPEDIA"} and d not in REPORT_CONFIGS and d not in REPORT_NOTEBOOK_SETUP for d in selected) and all((root/"reports"/d/"analysis_metadata.json").exists() for d in ["HOTEL","AIRBNB","EXPEDIA"]):
        write_summary(root)
        print("Updated reports/README.md",flush=True)


if __name__=="__main__":
    main()
