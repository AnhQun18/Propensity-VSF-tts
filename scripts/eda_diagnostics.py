"""Descriptive diagnostics and editorial structure for the three EDA reports.

All temporary groupings and samples serve EDA only. This module never writes a
feature matrix, changes raw CSVs, fits preprocessing, or trains a model.
"""
from __future__ import annotations

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
        "purpose": "Dự đoán quốc gia của booking đầu cho người dùng mới, phục vụ cá nhân hóa nội dung.",
        "collection": "Hồ sơ đăng ký, web/app logs và các bảng tổng hợp; người dùng trong tập từ Mỹ. Quy trình chọn người dùng chi tiết và ngày đóng nhãn chưa được lưu trong CSV.",
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


def missing_plot(report, data, columns, group, group_name, sample_note):
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
    if report.dataset=="AIRBNB":
        from matplotlib.patches import Patch
        axes[0].set(title=f"Mẫu hình thiếu: {len(rows)} dòng hiển thị",xlabel="Cột dữ liệu",ylabel="Mẫu dòng, sắp theo mẫu hình thiếu")
        axes[0].legend(handles=[Patch(facecolor=plt.get_cmap("Blues")(0),edgecolor="gray",label="Có giá trị"),Patch(facecolor=plt.get_cmap("Blues")(1.),label="Thiếu (NA)")],loc="upper left",bbox_to_anchor=(0,1.22),ncol=2,fontsize=8)
    im=axes[1].imshow(grouped.to_numpy(),aspect="auto",vmin=0,vmax=100,cmap="Blues")
    axes[1].set(title=f"Missing by {group_name} (%)",ylabel=group_name)
    axes[1].set_yticks(range(len(grouped)));axes[1].set_yticklabels(grouped.index.astype(str))
    axes[1].set_xticks(range(len(chosen)));axes[1].set_xticklabels(chosen,rotation=65,ha="right")
    if report.dataset=="AIRBNB":
        axes[1].set(title="Tỷ lệ thiếu theo năm tạo tài khoản",xlabel="Cột dữ liệu",ylabel="Năm tạo tài khoản")
    fig.colorbar(im,ax=axes[1],label="Thiếu (%)" if report.dataset=="AIRBNB" else "Missing (%)",fraction=.035,pad=.03);fig.tight_layout()
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


def category_panel(report, data, column, target, population):
    table=data.groupby(column,dropna=False,observed=True)[target].agg(n="size",positive="sum").sort_values("n",ascending=False)
    total=len(table);rare=table.n.lt(100)
    shown=table.head(8).copy();shown["positive_pct"]=shown.positive/shown.n*100
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    labels=shown.index.astype(str)
    axes[0].bar(labels,shown.n,color=BLUE);axes[0].set(title=f"{column}: top groups",ylabel=f"{population} (count)")
    axes[1].bar(labels,shown.positive_pct,color=ORANGE);axes[1].set(title="Observed target rate within group",ylabel="Target = 1 (%)")
    for ax in axes: ax.tick_params(axis="x",rotation=35)
    if report.dataset=="AIRBNB":
        axes[0].set(title="Số người dùng theo ứng dụng đăng ký",xlabel=column,ylabel="Số người dùng train")
        axes[1].set(title="Tỷ lệ booking trong từng ứng dụng",xlabel=column,ylabel="Có booking được ghi nhận (%)")
    fig.tight_layout();path=report.savefig("categories_and_target",fig)
    largest=shown.iloc[0];label=shown.index[0]
    na_note="bao gồm NA" if data[column].isna().any() else "không có NA"
    note=f"Nhận xét: {column} có {total} nhóm ({na_note}); {int(rare.sum())} nhóm dưới 100 quan sát. Nhóm lớn nhất {label} có {int(largest.n):,} quan sát, tỷ lệ nhãn 1 là {largest.positive_pct:.2f}%. Hai trục trả lời số lượng nhóm và tỷ lệ bên trong nhóm, không dùng lẫn mẫu số; phân tầng cohort được trình bày tại phần đa biến."
    fig_note(report,path,note)
    return path,table.reset_index(),note


def outlier_panel(report, frame, columns, target, population):
    stats=iqr_table(frame,columns,population)
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    x=columns[0];y=columns[1] if len(columns)>1 else columns[0]
    axes[0].boxplot(frame[x].dropna(),showfliers=True,orientation="horizontal")
    axes[0].set(xlabel=f"{x}\n({unit(x)})",title=f"{x}: raw boxplot",yticks=[])
    logarithmic=bool(frame[x].max()>20*max(float(frame[x].median()),1))
    if logarithmic: axes[0].set_xscale("symlog",linthresh=1)
    groups=[];labels=[]
    for value in sorted(frame[target].dropna().unique()):
        s=frame.loc[frame[target].eq(value),y].dropna()
        if len(s): groups.append(s);labels.append(str(value))
    axes[1].boxplot(groups,tick_labels=labels,showfliers=False)
    axes[1].set(title=f"{y} by target; fliers hidden",xlabel=target,ylabel=f"{y}\n({unit(y)})")
    if report.dataset=="AIRBNB":
        axes[0].set(title="Tuổi raw: giữ toàn bộ giá trị ngoại lai",xlabel="Tuổi khai báo (năm; thang symlog)")
        axes[1].set(title="Tuổi theo nhãn: ẩn điểm ngoài whisker",xlabel="Có booking được ghi nhận (0/1)",ylabel="Tuổi khai báo (năm)")
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
    from scripts.build_descriptive_reports import pct,count
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


def enrich_airbnb(report,train,test,ids,account,per_user,transaction_counts):
    from scripts.build_descriptive_reports import count,pct
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
    from scripts.airbnb_deep_dive import deepen_airbnb
    deepen_airbnb(report,train,test,account,first,per_user,transaction_counts)


def enrich_expedia(report,train,test):
    from scripts.build_descriptive_reports import count,pct
    from scripts.expedia_full_train import full_missing_diagnostics,correlation_plot
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
