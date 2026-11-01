# AIRBNB — Hiểu người dùng mới, booking đầu và độ phủ hành vi

> Phạm vi: EDA trên dữ liệu gốc. Không làm sạch/thay thế dữ liệu, không tạo tập feature, không huấn luyện mô hình.

Ngày phân tích: 2026-11-02. Đây không phải ngày thu thập dữ liệu.

## Tóm tắt điều hành

1. **Bài toán đã chọn:** xác suất user mới có booking đầu được ghi nhận, t0 thiết kế ngay sau tạo account; 213,451 user train và 62,096 test. Horizon nguồn chưa được xác nhận; xem phần 1.

2. **Nhãn và độ trễ:** 88,908 user có booking (41.65%); trong 88,879 độ trễ không âm, 30/60/90 ngày bao phủ 75.33%/80.26%/83.29%. Xem bảng độ trễ phần 5.

3. **Ngoại lệ nhãn:** 29 booking trước ngày account; max độ trễ ở mọi năm là 365 ngày. Đây là căn cứ điều tra cơ chế nhãn, chưa chứng minh NDF đã được theo dõi đủ một năm.

4. **Leakage đã chứng minh:** presence date_first_booking khớp 100% nhãn; giữ bảng chéo tại phần 3. Cột này và cờ thiếu không là đầu vào dự đoán.

5. **Liên hệ có định lượng:** gender có V=0.207 toàn kỳ và 0.251 trong 2014; signup_app tương ứng 0.109/0.156. Bảng đủ biến và phân tầng ở phần 5, chưa là chất lượng mô hình.

6. **So sessions cùng điều kiện:** train 2014 96.53% so với test 2014 99.31%, chênh 2.78 điểm phần trăm. 76,466 user train nằm trong phạm vi cohort có log; xem phần sessions.

7. **Có log không đồng nghĩa nhãn giống nhau:** trong 2014, booking rate có log 38.98%, không log 17.54%. Cần đọc cùng n/Wilson; không dùng presence log làm tín hiệu tại signup khi chưa chứng minh t0.

8. **Missing và tuổi:** age thiếu 41.22%; trong 2014, cờ thiếu tuổi có V=0.374, còn rank-biserial của tuổi 16–100 là -0.005. Hai thước đo khác nhau; kết quả nhấn mạnh cần kiểm tra tính đầy đủ hồ sơ và snapshot tại t0. Giữ riêng NA, unknown và untracked.

9. **Thiết kế tiếp theo đã cụ thể hóa:** baseline hằng/Logistic L2, CatBoost và calibration; rolling theo signup, calibration tháng 4/2014, đánh giá cuối tháng 5–6/2014. Đây là protocol đề xuất, chưa chia tập hay train.

## 1. Bài toán và lý do chọn dữ liệu

**Bối cảnh nghiệp vụ:** ưu tiên hỗ trợ onboarding/cá nhân hóa cho người dùng mới dựa trên khả năng phát sinh booking đầu. Điểm propensity mô tả xu hướng hành vi; chưa phải tác động tăng thêm do một chiến dịch.

**Phát biểu bài toán nghiên cứu đã chọn:** với một user mới, sử dụng thông tin đăng ký sẵn có tại t0 để ước lượng xác suất có booking đầu được ghi nhận trong nhãn nguồn. Đầu ra là một xác suất [0,1] cho mỗi user, phục vụ sắp ưu tiên; bài toán điểm đến 12 lớp được giữ làm bối cảnh EDA.

**t0 thiết kế:** ngay sau khi hoàn tất tạo tài khoản. date_account_created chỉ chính xác tới ngày nên không xác minh được thứ tự trong ngày. Nhãn nghiên cứu y=1 khi country_destination khác NDF; y=0 khi NDF, không diễn giải thành “không bao giờ book”. Các giá trị hồ sơ phải được xác minh là snapshot tại signup. 29 booking có ngày trước account chưa thỏa logic first-booking tương lai tại t0; đề xuất cách ly để xác minh ở giai đoạn sau, chưa xóa.

**Horizon:** phạm vi hiện tại là kết quả được ghi nhận theo cơ chế nhãn nguồn, không tự đổi thành nhãn 90 ngày. Horizon nghiệp vụ đề xuất là 90 ngày vì bao phủ 83.29% booking quan sát hợp lệ; muốn triển khai cần xác nhận ngày kết thúc theo dõi và nhãn âm. Nếu không xác minh được, chỉ được kết luận về bài toán nghiên cứu theo nhãn nguồn.

**Lý do chọn Airbnb so với hai bộ còn lại**

| dataset | unit | evidence | fit | decision |
| --- | --- | --- | --- | --- |
| AIRBNB | User mới | 213,451 user; 41.65% có booking | Đúng đối tượng chấm propensity khách hàng; có ID | Chọn cho nghiên cứu, còn điều kiện nhãn/t0 |
| HOTEL | Booking đã được tạo | Nhãn hủy/no-show; không quan sát đầy đủ người chưa đặt | Hợp cancellation propensity | Không trả lời trực tiếp ai sẽ tạo booking đầu |
| EXPEDIA | Cặp search–hotel | Tương tác trong danh sách; thiếu user ID và search không click | Hợp ranking/propensity trong search | Không ưu tiên cho propensity onboarding theo user |

## 2. Tổng quan bộ dữ liệu

### Nguồn gốc và phạm vi thu thập

Nguồn công bố: [trang dữ liệu/nghiên cứu gốc](https://www.kaggle.com/c/airbnb-recruiting-new-user-bookings/data). [Giấy phép/điều khoản và trang phân phối](https://www.kaggle.com/competitions/airbnb-recruiting-new-user-bookings/rules). Thông tin nào chưa được lưu hoặc chưa xác minh được được ghi rõ, không điền bằng giả định.

**Thông tin nguồn và phiên bản**

| item | description |
| --- | --- |
| Tên / nơi công bố | Airbnb / Kaggle — Airbnb New User Bookings |
| Năm công bố | Cuộc thi công bố 2015, kết thúc 2016 |
| Mục đích thu thập/công bố | Dự đoán quốc gia của booking đầu cho người dùng mới, phục vụ cá nhân hóa nội dung. |
| Cách thu thập / quần thể | Hồ sơ đăng ký, web/app logs và các bảng tổng hợp; người dùng trong tập từ Mỹ. Quy trình chọn người dùng chi tiết và ngày đóng nhãn chưa được lưu trong CSV. |
| Thời gian bao phủ quan sát được | Account train 2010-01-01–2014-06-30; test 2014-07-01–2014-09-30 |
| Ngày tải raw | Không được lưu; người cung cấp xác nhận 2026-11-02. Mã phiên bản Kaggle chưa có bằng chứng; dùng snapshot SHA-256. |
| Quy mô bảng train/chính | 213,451 dòng × 16 cột thô |
| Dung lượng mọi CSV của bộ hiện có | 664,207,331 byte = 633.44 MiB; gồm cả bảng phụ/benchmark nếu có |
| Phiên bản local | Nhận diện bằng tên file, bytes, số dòng và SHA-256 tại phụ lục |
| Giấy phép / điều khoản | Competition Rules, không phải giấy phép mở CC0/CC BY. Điều khoản DATA có giới hạn mục đích sử dụng và phân phối; phải đối chiếu rules trước khi tái sử dụng hoặc công bố dữ liệu. |

### Bối cảnh, đơn vị quan sát và phạm vi nhãn

Train gồm **213,451 người dùng, 16 cột**, test gồm **62,096 người dùng, 15 cột**. Nhãn gốc là `country_destination` với 12 giá trị, gồm `NDF` và 11 điểm đến/nhóm điểm đến còn lại. Đối với propensity nhị phân, báo cáo chỉ thống kê hành vi **có booking được ghi nhận** khi nhãn khác NDF; không tạo tập nhãn huấn luyện mới.

Mục tiêu gốc là dự đoán điểm đến booking đầu, không trực tiếp cung cấp nhãn booking trong 30/60/90 ngày. `NDF` nghĩa không có booking theo nhãn của bộ dữ liệu; không khẳng định người dùng sẽ không bao giờ book. Phân tích độ trễ và độ nhạy horizon ở phần 5 phân biệt nhãn nguồn với nhãn triển khai theo thời hạn.

[Mô tả cuộc thi Airbnb New User Bookings](https://www.kaggle.com/c/airbnb-recruiting-new-user-bookings/data) nêu người dùng trong tập đến từ Mỹ. Vì vậy tính đại diện về địa lý, thời kỳ và sản phẩm có giới hạn. Test công khai không có nhãn để tính chất lượng dự đoán hoặc so sánh booking rate với train.

## 3. Chất lượng dữ liệu

### Chất lượng users, sentinel và rò rỉ nhãn

**Rò rỉ đã kiểm chứng:** presence của `date_first_booking` khớp nhãn có booking ở **100.00%** người dùng train. Không dùng ngày này, hoặc cờ thiếu ngày này, làm đầu vào dự đoán booking đầu. Đây là thiếu theo cấu trúc kết quả, không phải missing cần impute.

Tuổi ngoài [16,100] được gắn cờ cho EDA; đây là **dải tham chiếu**, không phải chính sách hợp lệ đã xác nhận. Giá trị dạng 19xx/20xx có thể là năm sinh nhưng CSV không chứng minh nguyên nhân của từng dòng; không đổi tuổi, xóa người dùng hay thay giá trị. Gender/browser có sentinel cần thống kê riêng với NA.

Ngày hoạt động đầu trước ngày tạo tài khoản được nguồn gốc cho phép vì có thể tìm kiếm trước khi đăng ký. Có **29** dòng ngày booking trước ngày account; đây là câu hỏi về định nghĩa mốc thời gian cần xác minh, không tự động kết luận lỗi rồi loại bỏ.

**Kiểm tra định danh và logic thời gian**

| check | n |
| --- | --- |
| ID train bị lặp (beyond first) | 0 |
| ID test bị lặp (beyond first) | 0 |
| ID xuất hiện ở cả train và test | 0 |
| date_first_booking.notna không khớp nhãn có booking | 0 |
| date_first_booking có giá trị trong test | 0 |
| Tuổi có giá trị nhưng ngoài [16,100] (quy ước mô tả) | 2,410 |
| Booking đầu trước ngày tạo tài khoản | 29 |
| Hoạt động đầu trước ngày tạo tài khoản | 178 |
| Ngày account không parse được | 0 |
| Timestamp hoạt động đầu không parse được | 0 |
| Ngày booking có giá trị nhưng không parse được | 0 |

**NA và giá trị đặc biệt là các khái niệm khác nhau**

| column | null_n | minus_unknown_n | untracked_n |
| --- | --- | --- | --- |
| gender | 0 | 95,688 | 0 |
| first_browser | 0 | 27,266 | 0 |
| first_affiliate_tracked | 6,065 | 0 | 109,232 |

**Ngày booking có/không × nhãn có/không booking**

| has_booking_date | False | True |
| --- | --- | --- |
| 0 | 124,543 | 0 |
| 1 | 0 | 88,908 |

### Missing có quy luật hay không?

Heatmap chọn tối đa 12 cột có NA. Chọn dòng để hiển thị với seed=42 và sắp theo pattern; bảng tỷ lệ theo nhóm dùng quần thể phân tích công bố, không chỉ các dòng hiển thị.

**Missing (%) theo account year; toàn bộ users train AIRBNB**

| account year | date_first_booking | age | first_affiliate_tracked |
| --- | --- | --- | --- |
| 2010 | 42.5036 | 38.8092 | 28.1564 |
| 2011 | 45.3673 | 34.7346 | 20.3227 |
| 2012 | 55.0226 | 34.8183 | 3.312 |
| 2013 | 59.1562 | 42.1287 | 0.9462 |
| 2014 | 61.7621 | 44.6316 | 1.0397 |

![missing patterns](figures/missing_patterns.png)

Nhận xét: date_first_booking thiếu 58.35% trong toàn bộ users train AIRBNB; chênh lệch missing lớn nhất giữa các nhóm account year là 27.21 điểm phần trăm ở first_affiliate_tracked. Ô xanh là NA. Mẫu dòng hiển thị dùng seed=42; việc sắp theo pattern chỉ để nhìn cụm thiếu, không phải thứ tự thời gian. Các khác biệt này không đủ kết luận cơ chế MCAR/MAR/MNAR.

### Ngoại lai: lượng hóa và phân biệt quy tắc với kết luận lỗi

Quy tắc 1,5×IQR chỉ gắn cờ để kiểm tra, không tự chứng minh lỗi. Mẫu số là số giá trị không thiếu của từng cột; bảng giữ rõ quần thể và trường hợp IQR=0.

**Hàng rào IQR trên dữ liệu công bố**

| column | population | nonnull_n | q1 | q3 | iqr | lower_fence | upper_fence | flagged_n | flagged_pct_nonnull | iqr_zero |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| age | toàn bộ users train AIRBNB | 125,461 | 28 | 43 | 15 | 5.5 | 65.5 | 5,594 | 4.4588 | 0 |

![outliers and target](figures/outliers_and_target.png)

Nhận xét: theo hàng rào Q1−1,5×IQR và Q3+1,5×IQR, age có 5,594/125,461 giá trị bị gắn cờ (4.46%) trong toàn bộ users train AIRBNB; đây là bất thường thống kê, chưa phải lỗi nhập liệu. Median age theo nhãn: 0=34.00, 1=33.00. Boxplot bên phải ẩn các điểm ngoài whisker để đọc vùng giữa, không xóa chúng khỏi bảng hay raw. Đơn vị xem từ điển; IQR=0 ở biến rời rạc có thể gắn cờ nhiều giá trị thật. Trục x boxplot raw dùng symlog; hàng rào IQR vẫn tính trên giá trị raw, không phải log.

## 4. Phân tích đơn biến

### Nhãn, tuổi và phân phối kênh/thiết bị

Có booking được ghi nhận: **88,908/213,451 (41.65%)**. Nhóm NDF chiếm **58.35%**. Bảng điểm đến trình bày hai mẫu số riêng: toàn bộ người dùng và chỉ người có booking; không nhầm tỷ trọng US trong toàn bộ users với tỷ trọng US trong nhóm đã book.

Độ tuổi được trình bày cả raw và cửa sổ [16,100] để thấy tác động của giá trị cực đoan. Top category có mẫu số là toàn bộ users, kể cả NA. `signup_flow` là mã phân loại; không báo cáo mean của mã như một đặc điểm khách hàng.

![users distributions](figures/users_distributions.png)

Nhận xét: NDF chiếm 58.35% toàn users; age thiếu 41.22% và có 2,410 giá trị ngoài dải tham chiếu 16–100. Histogram chỉ vẽ tuổi 16–100, không thay đổi raw hoặc khẳng định mọi tuổi ngoài dải đều sai.

### Biến phân loại và nhãn

Biểu đồ hiển thị top 8 nhóm theo số lượng; bảng kiểm kê giữ cả các nhóm nhỏ. Nhóm hiếm được báo với ngưỡng mô tả n<100, chưa gộp category.

**Tần suất đầy đủ của signup_app**

| signup_app | n | positive |
| --- | --- | --- |
| Web | 182,717 | 80,021 |
| iOS | 19,019 | 5,511 |
| Moweb | 6,261 | 2,143 |
| Android | 5,454 | 1,233 |

![categories and target](figures/categories_and_target.png)

Nhận xét: signup_app có 4 nhóm (không có NA); 0 nhóm dưới 100 quan sát. Nhóm lớn nhất Web có 182,717 quan sát, tỷ lệ nhãn 1 là 43.80%. Hai trục trả lời số lượng nhóm và tỷ lệ bên trong nhóm, không dùng lẫn mẫu số; phân tầng cohort được trình bày tại phần đa biến.

## 5. Nhãn, liên hệ đa biến, cohort và sessions

### Độ trễ booking và giới hạn định nghĩa nhãn

Độ trễ = date_first_booking − date_account_created, tính bằng ngày lịch; ngày booking chỉ dùng để kiểm tra nhãn. Có 88,879 độ trễ không âm và 29 độ trễ âm. Không diễn giải độ trễ âm là booking tương lai và không sửa chúng trong EDA.

**Cửa sổ 90 ngày bao phủ 83.29% booking quan sát có độ trễ hợp lệ**, còn khoảng 16.71% nằm sau 90 ngày. Các tỷ lệ dưới đây không phải xác suất booking 30/60/90 ngày của toàn bộ user.

Ngày booking lớn nhất là 2015-06-29. Độ trễ lớn nhất ở cả năm cohort là 365 ngày. Điều này phù hợp với giả thuyết nhãn có giới hạn khoảng một năm theo từng user, nhưng chưa chứng minh cơ chế đóng nhãn hoặc thời gian theo dõi của NDF. **Không thể kết luận NDF ở cohort mới chỉ là chưa kịp booking, cũng chưa thể bác bỏ khả năng đó.**

Nếu giả định mọi user đều được theo dõi tới ngày booking lớn nhất, toàn bộ train có khoảng cách lịch đủ 30/60/90 ngày. Đây là phân tích độ nhạy theo một giả định chưa kiểm chứng, không phải bằng chứng xác nhận NDF đã trưởng thành. Bài toán chính dùng nhãn nguồn; 90 ngày là horizon triển khai cần dữ liệu bổ sung để xác nhận nhãn âm.

**Phân phối độ trễ: mẫu số và ngoại lệ**

| booked_users | valid_nonnegative_lags | negative_lags | missing_or_unparsed_booked_dates | median_days | p75_days | p90_days | p95_days | max_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 88,908 | 88,879 | 29 | 0 | 3 | 29 | 189 | 278 | 365 |

**Mức bao phủ các horizon trên booking đã quan sát**

| horizon_days | bookings_within_h | denominator_valid_bookings | pct_valid_bookings | pct_all_observed_bookings |
| --- | --- | --- | --- | --- |
| 7 | 55,366 | 88,879 | 62.2937 | 62.2734 |
| 30 | 66,950 | 88,879 | 75.3271 | 75.3026 |
| 60 | 71,333 | 88,879 | 80.2586 | 80.2324 |
| 90 | 74,027 | 88,879 | 83.2896 | 83.2625 |
| 180 | 79,524 | 88,879 | 89.4745 | 89.4453 |
| 365 | 88,879 | 88,879 | 100 | 99.9674 |

**Độ trễ theo năm tạo tài khoản**

| account_year | users | valid_bookings | negative_lags | within_30_pct | within_60_pct | within_90_pct | max_lag_days | latest_booking |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2010 | 2,788 | 1,597 | 6 | 86.6625 | 90.3569 | 91.9224 | 365 | 2011-11-30 |
| 2011 | 11,775 | 6,422 | 11 | 80.5824 | 84.2884 | 86.4217 | 365 | 2012-12-09 |
| 2012 | 39,462 | 17,738 | 11 | 76.5024 | 81.4241 | 84.2541 | 365 | 2013-12-31 |
| 2013 | 82,960 | 33,883 | 1 | 74.4503 | 79.2492 | 82.3156 | 365 | 2014-12-30 |
| 2014 | 76,466 | 29,239 | 0 | 73.8568 | 79.2845 | 82.6738 | 365 | 2015-06-29 |

**Giả định chung ngày đóng nhãn: chỉ là độ nhạy**

| assumed_common_cutoff | horizon_days | users_with_calendar_gap_ge_h | pct_users | status |
| --- | --- | --- | --- | --- |
| 2015-06-29 | 30 | 213,451 | 100 | Chỉ đúng nếu mọi user thực sự được theo dõi tới mốc giả định |
| 2015-06-29 | 60 | 213,451 | 100 | Chỉ đúng nếu mọi user thực sự được theo dõi tới mốc giả định |
| 2015-06-29 | 90 | 213,451 | 100 | Chỉ đúng nếu mọi user thực sự được theo dõi tới mốc giả định |
| 2015-06-29 | 365 | 212,861 | 99.7236 | Chỉ đúng nếu mọi user thực sự được theo dõi tới mốc giả định |

![booking delay](figures/booking_delay.png)

Nhận xét: trong 88,879 booking có độ trễ không âm, 75.33% xảy ra trong 30 ngày, 80.26% trong 60 ngày và 83.29% trong 90 ngày. Đây là phân phối có điều kiện trên người đã book; chưa xác định thời gian theo dõi của NDF. 29 độ trễ âm được báo riêng, không xóa khỏi raw.

### Độ mạnh liên hệ với nhãn trên toàn bộ biến ứng viên

Phạm vi sàng lọc gồm 13 cột ứng viên gốc: 10 biến phân loại, age và hai mốc thời gian. Cờ thiếu tuổi là một góc nhìn EDA bổ sung, không được xuất thành feature. Ngày tạo account/hoạt động đầu được nhóm theo tháng chỉ để mô tả cohort. ID, nhãn và date_first_booking không được dùng để chứng minh tín hiệu đầu vào.

Cramér V = sqrt(chi-square / [n × min(r−1,c−1)]), trong [0,1]; càng lớn là liên hệ biên càng mạnh. Cột effect_2014 tính lại trên cohort 2014 để kiểm tra ảnh hưởng thành phần năm. Không áp một ngưỡng V chung để tuyên bố biến hữu ích cho mô hình. P-value nhỏ khi n lớn chưa đảm bảo hiệu ứng có giá trị; các category hiếm làm kiểm định chi-square xấp xỉ kém hơn.

Tuổi được kiểm định Mann–Whitney hai phía trong cửa sổ tham chiếu 16–100, kèm rank-biserial trong [−1,1]. Dấu dương nghĩa tuổi ở nhóm booked có xu hướng cao hơn NDF; trị tuyệt đối gần 0 là khác biệt nhỏ. Không so trực tiếp trị số rank-biserial với V như cùng một thang đo. Tuổi ngoài dải và NA vẫn được báo riêng.

Đây là bằng chứng **liên hệ thống kê trong mẫu**, thay cho việc bịa ra AUC ở giai đoạn chưa train; chưa chứng minh khả năng dự báo ngoài thời gian hoặc tác động nhân quả. Nguồn phương pháp: [Cramér V của SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.contingency.association.html), [Mann–Whitney của SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html).

**Độ mạnh liên hệ toàn kỳ và trong cohort 2014; nêu đủ 14 phép sàng lọc**

| variable | effect_metric | effect_all | effect_2014 | n_all | n_2014 | groups_all | expected_cells_under_5_pct | p_chi2_or_mwu | q_bh_14_tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gender | Cramér V | 0.2073 | 0.2507 | 213,451 | 76,466 | 4 | 0 | <1e-300 | <1e-300 |
| signup_method | Cramér V | 0.0359 | 0.0371 | 213,451 | 76,466 | 3 | 0 | 1.25e-60 | 1.35e-60 |
| signup_flow | Cramér V | 0.147 | 0.1526 | 213,451 | 76,466 | 17 | 17.6471 | <1e-300 | <1e-300 |
| language | Cramér V | 0.0425 | 0.0452 | 213,451 | 76,466 | 25 | 12 | 9.56e-67 | 1.12e-66 |
| affiliate_channel | Cramér V | 0.0907 | 0.107 | 213,451 | 76,466 | 8 | 0 | <1e-300 | <1e-300 |
| affiliate_provider | Cramér V | 0.0633 | 0.0495 | 213,451 | 76,466 | 18 | 11.1111 | 4.02e-171 | 5.12e-171 |
| first_affiliate_tracked | Cramér V | 0.0715 | 0.087 | 213,451 | 76,466 | 8 | 0 | 3.12e-231 | 4.37e-231 |
| signup_app | Cramér V | 0.1095 | 0.1559 | 213,451 | 76,466 | 4 | 0 | <1e-300 | <1e-300 |
| first_device_type | Cramér V | 0.1272 | 0.1758 | 213,451 | 76,466 | 9 | 0 | <1e-300 | <1e-300 |
| first_browser | Cramér V | 0.133 | 0.1833 | 213,451 | 76,466 | 52 | 52.8846 | <1e-300 | <1e-300 |
| age: cờ thiếu (EDA) | Cramér V | 0.3142 | 0.3737 | 213,451 | 76,466 | 2 | 0 | <1e-300 | <1e-300 |
| date_account_created: tháng (EDA) | Cramér V | 0.1093 | 0.0119 | 213,451 | 76,466 | 54 | 0 | <1e-300 | <1e-300 |
| timestamp_first_active: tháng (EDA) | Cramér V | 0.1096 | 0.024 | 213,451 | 76,466 | 59 | 8.4746 | <1e-300 | <1e-300 |
| age: chỉ cửa sổ 16–100 (EDA) | Rank-biserial | -0.0324 | -0.0049 | 123,051 | 41,605 | — | — | 9.53e-23 | 9.53e-23 |

### Tỷ lệ booking theo hồ sơ, kênh, thiết bị và missing tuổi

Mỗi mẫu số là user trong nhóm. Bảng có n, số booking, tỷ lệ và Wilson 95%; n<100 là cờ thận trọng. Giữ riêng NA, giá trị unknown và tuổi ngoài dải. Các chênh lệch ở đây là liên hệ biên, được đối chiếu với phân tầng năm ở phần tiếp theo.

**Booking theo gender — toàn bộ nhóm**

| gender | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| -unknown- | 95,688 | 29,018 | 30.3256 | 30.0352 | 30.6177 | 0 |
| FEMALE | 63,041 | 31,993 | 50.7495 | 50.3592 | 51.1397 | 0 |
| MALE | 54,440 | 27,721 | 50.9203 | 50.5003 | 51.3401 | 0 |
| OTHER | 282 | 176 | 62.4113 | 56.6271 | 67.862 | 0 |

**Booking theo signup_app — toàn bộ nhóm**

| signup_app | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| Web | 182,717 | 80,021 | 43.795 | 43.5677 | 44.0227 | 0 |
| iOS | 19,019 | 5,511 | 28.9763 | 28.3359 | 29.6252 | 0 |
| Moweb | 6,261 | 2,143 | 34.2278 | 33.0625 | 35.4124 | 0 |
| Android | 5,454 | 1,233 | 22.6073 | 21.5167 | 23.7364 | 0 |

**Booking theo signup_method — toàn bộ nhóm**

| signup_method | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| basic | 152,897 | 65,051 | 42.5456 | 42.298 | 42.7936 | 0 |
| facebook | 60,008 | 23,756 | 39.5881 | 39.1975 | 39.98 | 0 |
| google | 546 | 101 | 18.4982 | 15.4653 | 21.9712 | 0 |

**Booking theo affiliate_channel — toàn bộ nhóm**

| affiliate_channel | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| direct | 137,727 | 59,398 | 43.1273 | 42.866 | 43.3891 | 0 |
| sem-brand | 26,045 | 11,094 | 42.5955 | 41.9961 | 43.1971 | 0 |
| sem-non-brand | 18,844 | 7,150 | 37.9431 | 37.2528 | 38.6383 | 0 |
| other | 8,961 | 3,600 | 40.1741 | 39.1635 | 41.1931 | 0 |
| seo | 8,663 | 3,955 | 45.6539 | 44.6072 | 46.7045 | 0 |
| api | 8,167 | 2,785 | 34.1006 | 33.0802 | 35.136 | 0 |
| content | 3,948 | 558 | 14.1337 | 13.0819 | 15.2553 | 0 |
| remarketing | 1,096 | 368 | 33.5766 | 30.8424 | 36.4256 | 0 |

**Booking theo first_device_type — toàn bộ nhóm**

| first_device_type | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| Mac Desktop | 89,600 | 42,250 | 47.154 | 46.8273 | 47.481 | 0 |
| Windows Desktop | 72,716 | 30,152 | 41.4654 | 41.1078 | 41.824 | 0 |
| iPhone | 20,759 | 6,417 | 30.9119 | 30.2868 | 31.544 | 0 |
| iPad | 14,339 | 5,464 | 38.1059 | 37.3143 | 38.9038 | 0 |
| Other/Unknown | 10,667 | 2,875 | 26.9523 | 26.1187 | 27.8025 | 0 |
| Android Phone | 2,803 | 715 | 25.5084 | 23.9289 | 27.1549 | 0 |
| Android Tablet | 1,292 | 460 | 35.6037 | 33.039 | 38.2538 | 0 |
| Desktop (Other) | 1,199 | 550 | 45.8716 | 43.0687 | 48.7007 | 0 |
| SmartPhone (Other) | 76 | 25 | 32.8947 | 23.3793 | 44.0562 | 1 |

**Booking theo language — 10 nhóm đông nhất; phần còn lại ở phụ lục**

| language | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| en | 206,314 | 86,664 | 42.0059 | 41.793 | 42.219 | 0 |
| zh | 1,632 | 521 | 31.924 | 29.707 | 34.226 | 0 |
| fr | 1,172 | 399 | 34.0444 | 31.3875 | 36.8055 | 0 |
| es | 915 | 275 | 30.0546 | 27.1723 | 33.1038 | 0 |
| ko | 747 | 241 | 32.2624 | 29.0081 | 35.6981 | 0 |
| de | 732 | 270 | 36.8852 | 33.4669 | 40.4405 | 0 |
| it | 514 | 104 | 20.2335 | 16.9871 | 23.9215 | 0 |
| ru | 389 | 110 | 28.2776 | 24.0316 | 32.9485 | 0 |
| pt | 240 | 62 | 25.8333 | 20.7069 | 31.7212 | 0 |
| ja | 225 | 84 | 37.3333 | 31.2755 | 43.8164 | 0 |

**Booking theo age_group_eda — toàn bộ nhóm**

| age_group_eda | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| Thiếu tuổi | 87,990 | 20,376 | 23.1572 | 22.8796 | 23.4371 | 0 |
| 25–34 | 55,694 | 32,054 | 57.5538 | 57.1428 | 57.9637 | 0 |
| 35–44 | 30,759 | 16,834 | 54.7287 | 54.1719 | 55.2843 | 0 |
| 45–54 | 14,521 | 7,149 | 49.2321 | 48.4193 | 50.0454 | 0 |
| 16–24 | 10,770 | 5,425 | 50.3714 | 49.4272 | 51.3154 | 0 |
| 55–64 | 7,599 | 3,904 | 51.3752 | 50.251 | 52.498 | 0 |
| 65–100 | 3,708 | 1,828 | 49.2988 | 47.6912 | 50.9079 | 0 |
| Ngoài [16,100] | 2,410 | 1,338 | 55.5187 | 53.5274 | 57.4924 | 0 |

**Booking theo age_missing_eda — toàn bộ nhóm**

| age_missing_eda | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| Có tuổi | 125,461 | 68,532 | 54.6241 | 54.3485 | 54.8995 | 0 |
| Thiếu tuổi | 87,990 | 20,376 | 23.1572 | 22.8796 | 23.4371 | 0 |

### Tách thành phần cohort khỏi chênh lệch app, gender và kênh

Đọc theo từng cột năm để so sánh các nhóm trong cùng cohort. Một số ứng dụng không xuất hiện ở năm đầu nên không thể chuẩn hóa ngây thơ mọi nhóm theo cùng cơ cấu 2010–2014. Bảng tỷ lệ toàn kỳ không được dùng để kết luận app/kênh/giới tính gây tăng booking.

Ngay cả khi chênh lệch còn trong một năm, đó vẫn là liên hệ sau phân tầng năm, chưa phải ước lượng nhân quả hoặc đã kiểm soát mọi nhiễu. Bảng dài với Wilson 95% nằm ở phụ lục để kiểm tra các ô n nhỏ.

**signup_app × năm signup: tỷ lệ và n**

| signup_app | 2010 | 2011 | 2012 | 2013 | 2014 |
| --- | --- | --- | --- | --- | --- |
| Android | Không có user | Không có user | 64.00% (n=25) | 23.75% (n=1,621) | 21.85% (n=3,808) |
| Moweb | Không có user | Không có user | 41.61% (n=560) | 36.71% (n=3,084) | 29.73% (n=2,617) |
| Web | 57.50% (n=2,788) | 54.63% (n=11,775) | 45.02% (n=38,184) | 41.86% (n=72,428) | 42.53% (n=57,542) |
| iOS | Không có user | Không có user | 44.44% (n=693) | 35.16% (n=5,827) | 25.23% (n=12,499) |

**gender × năm signup: tỷ lệ và n**

| gender | 2010 | 2011 | 2012 | 2013 | 2014 |
| --- | --- | --- | --- | --- | --- |
| -unknown- | 53.68% (n=1,509) | 54.45% (n=4,617) | 35.75% (n=10,993) | 28.89% (n=38,799) | 26.54% (n=39,770) |
| FEMALE | 61.89% (n=732) | 55.51% (n=3,693) | 48.52% (n=15,535) | 51.05% (n=23,631) | 50.84% (n=19,450) |
| MALE | 62.02% (n=545) | 53.74% (n=3,439) | 48.50% (n=12,846) | 51.64% (n=20,436) | 50.95% (n=17,174) |
| OTHER | 100.00% (n=2) | 80.77% (n=26) | 57.95% (n=88) | 60.64% (n=94) | 62.50% (n=72) |

**affiliate_channel × năm signup: tỷ lệ và n**

| affiliate_channel | 2010 | 2011 | 2012 | 2013 | 2014 |
| --- | --- | --- | --- | --- | --- |
| api | Không có user | 100.00% (n=1) | 45.73% (n=1,813) | 33.76% (n=3,504) | 27.10% (n=2,849) |
| content | 49.47% (n=95) | 37.50% (n=296) | 15.97% (n=432) | 10.05% (n=1,482) | 11.08% (n=1,643) |
| direct | 61.98% (n=1,310) | 56.32% (n=6,578) | 47.71% (n=25,114) | 43.03% (n=55,522) | 38.63% (n=49,203) |
| other | 52.62% (n=650) | 52.35% (n=1,593) | 39.05% (n=3,201) | 32.43% (n=2,661) | 36.33% (n=856) |
| remarketing | Không có user | 50.00% (n=94) | 44.96% (n=129) | 28.18% (n=181) | 30.64% (n=692) |
| sem-brand | 59.46% (n=37) | 54.95% (n=777) | 41.97% (n=2,783) | 41.28% (n=9,755) | 42.94% (n=12,693) |
| sem-non-brand | 49.11% (n=395) | 52.06% (n=1,800) | 38.75% (n=4,872) | 35.02% (n=6,604) | 35.14% (n=5,173) |
| seo | 61.79% (n=301) | 58.33% (n=636) | 45.26% (n=1,118) | 43.25% (n=3,251) | 44.27% (n=3,357) |

![cohort strata](figures/cohort_strata.png)

Nhận xét: riêng năm 2014, Web có booking rate 42.53% so với iOS 25.23% và Android 21.85%; chênh lệch app vẫn hiện diện trong cùng năm. FEMALE đạt 50.84% so với gender unknown 26.54%. Nhóm OTHER chỉ có 72 user 2014 nên cần đọc Wilson ở phụ lục. Dấu * là n<100. Phân tầng năm chưa kiểm soát nhiễu theo tháng hoặc biến khác.

### Tương tác liên quan đến nhãn trong cohort 2014

Thay biểu đồ hai trục ngày gần trùng nhau bằng signup_app × affiliate_channel và missing tuổi × gender. Nhóm tuổi/cờ thiếu chỉ tồn tại để tính bảng và hình EDA; chưa xuất dữ liệu đầu vào. Không kiểm định tương tác hàng loạt hoặc tự chọn feature từ hình.

![multivariate](figures/multivariate.png)

Nhận xét: trong user Web năm 2014, nhóm direct có booking rate 45.18% (n=33,354), nhóm content 11.08% (n=1,642). Trong nhóm FEMALE cùng năm, có tuổi đạt 51.74% so với thiếu tuổi 32.41%. Dấu * là n<100. Liên hệ không chỉ do trộn các năm, nhưng vẫn chưa chứng minh quan hệ nhân quả hoặc mô hình phi tuyến sẽ thắng baseline.

### Sessions: so sánh cùng cohort và rà soát thông tin giao dịch

Đã quét toàn bộ 10,567,737 sự kiện. So sánh phù hợp hơn là **train cohort 2014: 73,815/76,466 (96.53%)** với **test cohort 2014: 99.31%**; chênh 2.78 điểm phần trăm. Tỷ lệ train toàn kỳ 34,58% chủ yếu phản ánh việc cohort 2010–2013 không có log, không phải bằng chứng user ít hoạt động.

**Về độ phủ, nghiên cứu sessions phải giới hạn cohort 2014 (76,466 user train), trong đó 73,815 có log.** Về thời điểm dự đoán, sessions vẫn chưa đủ điều kiện: không có timestamp nên không cắt được trước t0. Giới hạn cohort không tự loại được rò rỉ thời gian.

Bảng có/không có log dưới đây chỉ xét 2014. Bảng số sự kiện giữ cả user không có log với event_n=0 để không nhầm mẫu số. Thời lượng secs_elapsed không phải timestamp và tổng thời lượng không chứng minh thứ tự hành động.

Rà soát tên ứng viên giao dịch/xác minh theo regex **(?:^|_)(?:book[a-z]*|reserv[a-z]*|pay[a-z]*|checkout|receipt|itinerar[a-z]*|confirm[a-z]*|request[a-z]*|billing)(?:_|$)**, trước khi xem liên hệ với nhãn; khớp token phân cách bởi dấu gạch dưới và giữ đầy đủ action_type để đối chiếu. Nhóm confirm/request có thể liên quan xác minh tài khoản hoặc yêu cầu, chưa mặc định là booking hoàn tất. Đếm presence theo user sau khi gộp toàn bộ chunk, tránh một người bị đếm lặp vì nhiều sự kiện. Mẫu số của hai cột pct_booked/pct_ndf là người có sessions trong từng lớp, không phải toàn bộ train.

**Dấu hiệu đáng điều tra:** receipt có 101/102 user mang nhãn booked (99.02%); requested có 6,192/7,090 (87.33%). Tỷ lệ cao phù hợp với rủi ro log chứa bước sát hoặc sau kết quả, chưa chứng minh receipt luôn là hậu booking hoặc requested gây ra booking.

Tên như booking/payment/request là dấu hiệu cần điều tra. Hành động cũng có thể là yêu cầu thất bại, chuẩn bị thanh toán hoặc hoạt động sau booking; xuất hiện ở booked hay NDF chưa chứng minh thứ tự trước/sau kết quả. **Toàn bộ sessions bị loại khỏi phạm vi đầu vào của thiết kế chính tại signup**, cho tới khi có timestamp hoặc chứng cứ về cửa sổ log. Đây là quyết định phạm vi đề xuất, chưa tạo tập feature.

**Độ phủ năm account train**

| account_year | users | users_with_sessions | coverage_pct |
| --- | --- | --- | --- |
| 2010 | 2,788 | 0 | 0 |
| 2011 | 11,775 | 0 | 0 |
| 2012 | 39,462 | 0 | 0 |
| 2013 | 82,960 | 0 | 0 |
| 2014 | 76,466 | 73,815 | 96.5331 |

**Booking trong nhóm có/không sessions — chỉ cohort 2014**

| has_sessions | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 2,651 | 465 | 17.5406 | 16.1401 | 19.035 | 0 |
| 1 | 73,815 | 28,774 | 38.9812 | 38.63 | 39.3336 | 0 |

**Số sự kiện/user theo có log và nhãn — chỉ cohort 2014**

| has_sessions | observed_booking | users | mean_events | median_events | p90_events | p99_events | max_events |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 2,186 | 0 | 0 | 0 | 0 | 0 |
| 0 | 1 | 465 | 0 | 0 | 0 | 0 | 0 |
| 1 | 0 | 45,041 | 67.8873 | 33 | 167 | 485.6 | 2,323 |
| 1 | 1 | 28,774 | 86.1975 | 45 | 207 | 592 | 2,644 |

**Presence tên ứng viên giao dịch/xác minh × nhãn, trong user 2014 có log**

| field | value | users_with_action | booked_users | ndf_users | booking_rate_pct | ci95_low_pct | ci95_high_pct | pct_booked_users_with_action | pct_ndf_users_with_action | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| action | confirm_email | 30,986 | 15,611 | 15,375 | 50.3808 | 49.8241 | 50.9374 | 54.2538 | 34.1356 | 0 |
| action | requested | 7,090 | 6,192 | 898 | 87.3343 | 86.5398 | 88.0883 | 21.5194 | 1.9937 | 0 |
| action | payment_instruments | 3,804 | 1,395 | 2,409 | 36.6719 | 35.1547 | 38.2161 | 4.8481 | 5.3485 | 0 |
| action | request_new_confirm_email | 2,619 | 1,754 | 865 | 66.9721 | 65.1472 | 68.7473 | 6.0958 | 1.9205 | 0 |
| action | payment_methods | 1,901 | 859 | 1,042 | 45.1867 | 42.9615 | 47.4314 | 2.9853 | 2.3134 | 0 |
| action | apply_reservation | 1,344 | 889 | 455 | 66.1458 | 63.5731 | 68.6265 | 3.0896 | 1.0102 | 0 |
| action | payout_preferences | 933 | 386 | 547 | 41.3719 | 38.2534 | 44.5612 | 1.3415 | 1.2144 | 0 |
| action | tos_confirm | 899 | 287 | 612 | 31.9244 | 28.9594 | 35.0431 | 0.9974 | 1.3588 | 0 |
| action | recent_reservations | 796 | 365 | 431 | 45.8543 | 42.421 | 49.3274 | 1.2685 | 0.9569 | 0 |
| action | pay | 737 | 563 | 174 | 76.3908 | 73.1928 | 79.3151 | 1.9566 | 0.3863 | 0 |
| action | itinerary | 482 | 412 | 70 | 85.4772 | 82.0512 | 88.3421 | 1.4318 | 0.1554 | 0 |
| action | ajax_payout_options_by_country | 362 | 103 | 259 | 28.453 | 24.0504 | 33.3082 | 0.358 | 0.575 | 0 |
| action | ajax_payout_edit | 327 | 89 | 238 | 27.2171 | 22.6784 | 32.2849 | 0.3093 | 0.5284 | 0 |
| action | payout_update | 264 | 73 | 191 | 27.6515 | 22.6059 | 33.3382 | 0.2537 | 0.4241 | 0 |
| action | receipt | 102 | 101 | 1 | 99.0196 | 94.6542 | 99.8267 | 0.351 | 0.0022 | 0 |
| action | guest_booked_elsewhere | 75 | 75 | 0 | 100 | 95.1276 | 100 | 0.2607 | 0 | 1 |
| action | clear_reservation | 44 | 30 | 14 | 68.1818 | 53.4431 | 80.0007 | 0.1043 | 0.0311 | 1 |
| action | request_photography | 40 | 15 | 25 | 37.5 | 24.223 | 52.9676 | 0.0521 | 0.0555 | 1 |
| action | email_itinerary_colorbox | 37 | 37 | 0 | 100 | 90.5942 | 100 | 0.1286 | 0 | 1 |
| action | payoneer_account_redirect | 32 | 7 | 25 | 21.875 | 11.0238 | 38.755 | 0.0243 | 0.0555 | 1 |
| action | create_paypal | 25 | 7 | 18 | 28 | 14.2839 | 47.5766 | 0.0243 | 0.04 | 1 |
| action | update_reservation_requirements | 20 | 7 | 13 | 35 | 18.1192 | 56.7146 | 0.0243 | 0.0289 | 1 |
| action | payoneer_signup_complete | 18 | 2 | 16 | 11.1111 | 3.102 | 32.7998 | 0.007 | 0.0355 | 1 |
| action | reservation | 7 | 5 | 2 | 71.4286 | 35.8934 | 91.7781 | 0.0174 | 0.0044 | 1 |
| action | ajax_payout_split_edit | 5 | 0 | 5 | 0 | 0 | 43.4482 | 0 | 0.0111 | 1 |
| action | change_default_payout | 5 | 0 | 5 | 0 | 0 | 43.4482 | 0 | 0.0111 | 1 |
| action | payout_delete | 4 | 0 | 4 | 0 | 0 | 48.9891 | 0 | 0.0089 | 1 |
| action | guest_billing_receipt | 3 | 3 | 0 | 100 | 43.8503 | 100 | 0.0104 | 0 | 1 |
| action | booking | 2 | 1 | 1 | 50 | 9.4531 | 90.5469 | 0.0035 | 0.0022 | 1 |
| action | print_confirmation | 2 | 2 | 0 | 100 | 34.238 | 100 | 0.007 | 0 | 1 |
| action | confirmation | 1 | 0 | 1 | 0 | 0 | 79.3451 | 0 | 0.0022 | 1 |
| action_type | booking_request | 10,003 | 8,466 | 1,537 | 84.6346 | 83.9146 | 85.328 | 29.4224 | 3.4124 | 0 |
| action_type | booking_response | 2 | 1 | 1 | 50 | 9.4531 | 90.5469 | 0.0035 | 0.0022 | 1 |

![session coverage](figures/session_coverage.png)

Nhận xét: độ phủ train toàn kỳ 34,58% là hỗn hợp cohort; train 2014 đạt 96.53% so với test 2014 99.31%, chênh 2.78 điểm phần trăm. Không có log ở cohort 2010–2013. Độ phủ cao không chứng minh log được ghi trước thời điểm dự đoán.

### Cohort tháng có bất định và drift train–test

Train có account 2010-01–2014-06; test 2014-07–2014-09 và không có nhãn. Hình giữ từng tháng, thêm Wilson 95% và ranh giới 2014-01 khi bắt đầu có sessions. Tháng ít user có khoảng rộng hơn; đường lên/xuống chưa chứng minh chất lượng khách hoặc mùa vụ.

Total variation trong [0,1] chỉ so sánh phân phối từng biến. Hai cột toàn kỳ và chỉ train 2014 giúp thấy phần thay đổi do thành phần cohort; chưa loại được drift trong năm hoặc drift quan hệ với nhãn. Các bảng khoảng thời gian và drift xuất hiện duy nhất tại đây; phụ lục chỉ giữ số liệu cohort tháng.

**Khoảng thời gian account**

| population | account_min | account_max | users |
| --- | --- | --- | --- |
| train | 2010-01-01 | 2014-06-30 | 213,451 |
| test | 2014-07-01 | 2014-09-30 | 62,096 |

**Khác biệt category train–test: toàn kỳ và cùng năm 2014**

| column | tv_all_train_vs_test | test_only_categories | train_missing_pct | test_missing_pct | tv_train2014_vs_test |
| --- | --- | --- | --- | --- | --- |
| first_device_type | 0.3121 | 0 | 0 | 0 | 0.2337 |
| first_browser | 0.2595 | 3 | 0 | 0 | 0.1848 |
| signup_app | 0.2569 | 0 | 0 | 0 | 0.1534 |
| signup_flow | 0.2201 | 1 | 0 | 0 | 0.1372 |
| affiliate_channel | 0.1574 | 0 | 0 | 0 | 0.1119 |
| gender | 0.0959 | 0 | 0 | 0 | 0.0241 |
| affiliate_provider | 0.092 | 0 | 0 | 0 | 0.0944 |
| first_affiliate_tracked | 0.0798 | 0 | 2.8414 | 0.0322 | 0.0824 |
| signup_method | 0.0419 | 1 | 0 | 0 | 0.0237 |
| language | 0.0137 | 1 | 0 | 0 | 0.0105 |

![account cohorts](figures/account_cohorts.png)

Nhận xét: tháng 2010-01 chỉ có 61 user, booking rate 52.46% với Wilson 95% [40.16%; 64.47%]; vì vậy dao động ở cohort nhỏ cần đọc cùng bất định. Vạch đứt 2014-01 đánh dấu thay đổi độ phủ sessions, không phải bằng chứng về tác động riêng của thời gian đăng ký.

## 6. Hạn chế, rủi ro và quyền riêng tư

Tách điều đã quan sát khỏi nguyên nhân chưa được chứng minh. Không diễn giải chênh lệch nhóm thành đặc điểm cố hữu của giới tính/tuổi/quốc gia và không thực hiện nhận diện lại cá nhân.

**Rủi ro và giới hạn sử dụng**

| issue | evidence_or_limit |
| --- | --- |
| Quyền riêng tư | ID là mã giả danh; age, gender, ngày hoạt động, device và log hành vi vẫn có thể là quasi-identifier. Không nêu ID cá nhân trong báo cáo. |
| Quần thể | Users từ Mỹ trong giai đoạn lịch sử; thời gian theo dõi từng user chưa xác minh, sessions chỉ phủ cohort 2014. |
| Nhóm nhỏ / bias | PT/AU và các category hiếm có ít quan sát; khác biệt theo giới/tuổi/kênh có thể bị cohort và missing chi phối. |
| Rò rỉ | date_first_booking tiết lộ nhãn; log không có timestamp nên chưa xác nhận được cửa sổ trước t0. |
| Đồng ý / quyền sử dụng | CSV không có biểu mẫu đồng ý hay hồ sơ pháp lý thu thập. Không suy dữ liệu công khai = đồng ý cho mọi mục đích; đọc điều khoản nguồn, không tự gán giấy phép mở. |
| Giới hạn suy luận | EDA là mô tả, không phải kiểm định tác động can thiệp. Khoảng Wilson nếu có chỉ theo giả định độc lập; chưa đánh giá chất lượng mô hình hoặc tính công bằng của mô hình. |

## 7. Thuật toán và thiết kế đánh giá đề xuất

### Baseline, mô hình chính và xác suất

Chọn nhị phân first-booking theo nhãn nguồn làm bài toán chính. Binary 41,65%/58,35% không cần mặc định resampling hoặc class weight; lớp điểm đến hiếm không phải lý do cân bằng lại nhãn nhị phân.

CatBoost là ứng viên chính để kiểm tra, không phải kết luận đã thắng baseline. Tín hiệu EDA và tương tác chỉ là cơ sở đặt giả thuyết. Mọi quy tắc xử lý tuổi, NA/category hiếm và mọi thống kê dựa nhãn phải học riêng trong train của mỗi fold. ID và date_first_booking không làm đầu vào; sessions chưa thuộc thiết kế chính.

Nguồn thuật toán: [xử lý category của CatBoost](https://catboost.ai/docs/en/concepts/algorithm-main-stages_cat-to-numberic). Hiệu chỉnh phải tách khỏi dữ liệu fit; [scikit-learn về calibration](https://scikit-learn.org/stable/modules/calibration.html) cũng lưu ý Brier/log loss đánh giá cả calibration lẫn khả năng phân biệt.

**Ứng viên và lý do chọn — chưa thực hiện**

| candidate | reason_from_eda | proposed_controls | status |
| --- | --- | --- | --- |
| Baseline xác suất hằng | p bằng tỷ lệ booking trong phần train của từng fold | Mốc đối chứng log loss/Brier; không dùng tỷ lệ toàn bộ dữ liệu | Chưa chạy |
| Baseline Logistic Regression + L2 | Quan hệ cộng, dễ đối chiếu với liên hệ biên EDA | One-hot/nhóm hiếm và xử lý tuổi/missing chỉ học trên train; kiểm tra category mới | Chưa chạy |
| Mô hình chính đề xuất: CatBoost nhị phân | Nhiều category, missing có cấu trúc và các nhóm kết hợp có tỷ lệ khác nhau | Xử lý category bằng cơ chế của mô hình; numeric missing được hỗ trợ, categorical NA cần quy ước. Giới hạn độ sâu/L2 và early stopping | Chưa chạy |
| Hiệu chỉnh xác suất sigmoid | Propensity cần xác suất có ý nghĩa, không chỉ xếp hạng | Fit trên cohort calibration tách riêng; chỉ dùng isotonic như đối chứng nếu đủ dữ liệu và validation ủng hộ | Chưa chạy |

### Chia theo thời gian và kiểm soát đánh giá

Thiết kế dưới đây được đặt trước lần huấn luyện đầu tiên. Rolling validation dùng để chọn cấu hình; sau đó refit đến hết 2014-03, calibration trên 2014-04, đánh giá nội bộ cuối trên 2014-05–06. Mỗi user chỉ một dòng và một giai đoạn trong từng fold; các cửa sổ học tích lũy giữa fold là có chủ đích. Test Kaggle 2014-07–09 không có nhãn, chỉ dùng đối chiếu schema/drift.

Bảng chỉ kiểm kê quy mô các cửa sổ đề xuất, chưa tạo tập chia hoặc fit. Việc chia theo signup đánh giá thay đổi cohort, chưa mô phỏng đầy đủ một backtest tại thời điểm lịch: cần chứng minh nhãn train đã được đóng và có sẵn trước mỗi mốc dự đoán. Nếu sau này dùng horizon 90 ngày, phải thêm điều kiện trưởng thành nhãn trước origin; chưa được lấy booking tương lai để giả lập huấn luyện tại quá khứ.

Chọn tham số/early stopping bằng validation; chọn phương pháp calibration bằng dữ liệu phát triển, fit calibrator trên tháng 4. Giữ tập cuối cho một lần đánh giá sau khi khóa thiết kế. Các khoảng bootstrap đề xuất phải lấy mẫu theo user, seed=42; chưa chạy bootstrap.

**Cửa sổ thời gian đề xuất và quy mô quan sát**

| proposed_use | account_from | account_to | users | observed_bookings | booking_pct |
| --- | --- | --- | --- | --- | --- |
| Rolling 1: học | 2010-01-01 | 2012-12-31 | 54,025 | 25,785 | 47.7279 |
| Rolling 1: kiểm định | 2013-01-01 | 2013-06-30 | 33,542 | 14,574 | 43.45 |
| Rolling 2: học | 2010-01-01 | 2013-06-30 | 87,567 | 40,359 | 46.0893 |
| Rolling 2: kiểm định | 2013-07-01 | 2013-12-31 | 49,418 | 19,310 | 39.0748 |
| Rolling 3: học | 2010-01-01 | 2013-12-31 | 136,985 | 59,669 | 43.5588 |
| Rolling 3: kiểm định | 2014-01-01 | 2014-03-31 | 33,136 | 12,652 | 38.182 |
| Refit sau chọn cấu hình | 2010-01-01 | 2014-03-31 | 170,121 | 72,321 | 42.5115 |
| Hiệu chỉnh xác suất | 2014-04-01 | 2014-04-30 | 12,689 | 4,901 | 38.624 |
| Đánh giá nội bộ cuối | 2014-05-01 | 2014-06-30 | 30,641 | 11,686 | 38.1384 |

### Tiêu chí chấp nhận đặt trước

Các mức 2%, 10%, 1,20, 2/3 điểm phần trăm và ngân sách top 20% là quy ước nghiên cứu đề xuất, không phải chuẩn phổ quát hoặc cam kết hiệu quả kinh doanh. Khi có chi phí/lợi ích thực tế cần chốt lại trước huấn luyện và ghi phiên bản protocol. Tất cả trạng thái hiện tại là chưa đánh giá.

**Cổng chấp nhận cho giai đoạn mô hình hóa**

| criterion | predeclared_acceptance | interpretation |
| --- | --- | --- |
| Toàn vẹn và khả dụng | 0 ID trùng giữa các tập; 0 biến kết quả hoặc log chưa chứng minh trước t0; xử lý rõ 29 độ trễ âm | Điều kiện bắt buộc trước fit |
| Xác suất | Log loss giảm ít nhất 2% tương đối so với baseline hằng tính từ train | Đề xuất nghiên cứu; chưa có kết quả |
| Phân biệt | Average Precision cao hơn prevalence của tập đánh giá ít nhất 10% tương đối; báo thêm ROC-AUC | Đánh giá trên phân phối tự nhiên |
| Ưu tiên | Lift@20% ít nhất 1,20 và cận dưới bootstrap user 95% >1 | 20% là ngân sách nghiên cứu giả định, chưa phải ngân sách kinh doanh |
| Calibration | Sai lệch mean p so với booking rate ≤2 điểm phần trăm; ECE 10 bin đồng số mẫu ≤3 điểm, kèm reliability plot | Báo cả Brier; hai số này chưa đủ đánh giá calibration riêng lẻ |
| Độ bền thời gian | Log loss tốt hơn baseline hằng trong từng tháng của tập đánh giá cuối; báo n/CI cho nhóm n≥100 | Không chọn mô hình chỉ từ một tháng thuận lợi |

## 8. Bằng chứng về mức độ phù hợp

**Kết luận lựa chọn:** Airbnb phù hợp nhất trong ba bộ cho nghiên cứu propensity booking đầu ở cấp user. Có cỡ mẫu và liên hệ mô tả để tiếp tục thiết kế nghiên cứu. Chưa đủ bằng chứng xác nhận một mô hình triển khai tại signup với horizon 90 ngày.

Các điều kiện về t0, ngoại lệ nhãn và thời gian theo dõi là cổng dữ liệu cần giải quyết; không được biến thành giả định ngầm để đánh dấu mọi tiêu chí đều đạt. Chưa làm sạch, thay thế tuổi/NA, mã hóa, tạo feature, tạo tập chia hay huấn luyện mô hình. Các nhóm, cờ và tổng sessions chỉ dùng để tính bảng EDA trong bộ nhớ.

**Bảng kiểm mức độ phù hợp**

| criterion | evidence_in_report | status | remaining_condition |
| --- | --- | --- | --- |
| Đủ tín hiệu | 10 category được sàng lọc V; gender V=0.207, trong 2014=0.251; có bảng tương tác/cohort | Đạt ở mức EDA | Chưa chứng minh dự báo ngoài mẫu; không dùng p-value thay AUC |
| Đủ cỡ mẫu | 213,451 users; 88,908 booking; cohort 2014 76,466 | Đạt tổng thể | Một số category/ô tương tác ít user; dùng n và CI |
| Nhãn tin cậy | Presence ngày booking khớp 100%; 29 độ trễ âm; max độ trễ 365 ngày | Cần xác minh | Chưa xác nhận horizon/follow-up của NDF và ngoại lệ trước account |
| Không rò rỉ | date_first_booking và presence tiết lộ nhãn; sessions chứa tên giao dịch, thiếu timestamp | Chưa đạt với toàn bộ raw | Thiết kế chính loại các nguồn này; cần audit lại trước fit |
| Biến khả dụng tại t0 | t0 đã chọn: sau tạo account; raw không cung cấp lịch sử cập nhật hồ sơ | Cần xác minh | Xác nhận snapshot từng biến; ngày account không có giờ |
| Ổn định theo thời gian | Booking rate/cohort, độ phủ sessions và TV category thay đổi; đã có đối chiếu cùng năm 2014 | Chưa đạt giả định ổn định | Dùng kiểm định theo thời gian, không coi train/test là IID |
| Khái quát hóa | User từ Mỹ, giai đoạn lịch sử; test Kaggle không có nhãn; chưa có dữ liệu vận hành khác | Chưa được chứng minh | Chưa suy sang Việt Nam, thị trường hiện tại hoặc chiến dịch marketing |

## Phụ lục — từ điển và bảng bổ sung

### Từ điển users và quan hệ giữa các bảng

`id` là khóa users, ghép một–nhiều với `sessions.user_id`. Cần phân tích users trước và sau ghép mà không làm một người dùng bị nhân thành nhiều quan sát học. `countries` có khóa quốc gia; không ghép bằng điểm đến thật để dự đoán chính nhãn đó. `age_gender_bkts` là thống kê tổng hợp theo bucket/quốc gia/giới tính, không phải thêm 420 khách hàng.

**Schema đầy đủ của train users**

| column | pandas_dtype | distinct_nonnull | missing_n | missing_pct | meaning | role_or_caution | role | unit | observed_domain_and_basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | object | 213,451 | 0 | 0 | Định danh người dùng | Khóa ghép sessions.user_id; không phải phép đo | định danh / khóa nhóm, không phải số liên tục | mã/nhãn phân loại, không có đơn vị vật lý | Khóa/mã; không in giá trị định danh cá nhân trong báo cáo |
| date_account_created | object | 1,634 | 0 | 0 | Ngày tạo tài khoản | Mốc cohort; không tự xác định horizon nhãn | ứng viên hồ sơ tại signup; cần xác minh snapshot | ngày/giờ theo định dạng nguồn; timezone chưa xác minh | Toàn bảng: 2010-01-01–2014-06-30 |
| timestamp_first_active | int64 | 213,451 | 0 | 0 | Lần hoạt động đầu, dạng YYYYMMDDHHMMSS | Có thể trước ngày tạo tài khoản; cần parse theo định dạng | ứng viên hồ sơ tại signup; cần xác minh snapshot | ngày/giờ theo định dạng nguồn; timezone chưa xác minh | Toàn bảng: [2.00903e+13, 2.01406e+13], 213451 giá trị phân biệt |
| date_first_booking | object | 1,976 | 124,543 | 58.3473 | Ngày booking đầu được ghi nhận | Kết quả; presence tiết lộ nhãn có booking | kết quả; loại khỏi đầu vào tại signup | ngày/giờ theo định dạng nguồn; timezone chưa xác minh | Toàn bảng: 2010-01-02–2015-06-29 |
| gender | object | 4 | 0 | 0 | Giới tính khai báo | -unknown- là sentinel, không phải giá trị biết rõ | ứng viên hồ sơ tại signup; cần xác minh snapshot | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: '-unknown-', 'FEMALE', 'MALE', 'OTHER' |
| age | float64 | 127 | 87,990 | 41.2226 | Tuổi khai báo | Thiếu và giá trị ngoài dải tham chiếu; chưa sửa tuổi/năm sinh | ứng viên hồ sơ tại signup; cần xác minh snapshot | năm tuổi khai báo | Toàn bảng: [1, 2014], 127 giá trị phân biệt |
| signup_method | object | 3 | 0 | 0 | Phương thức đăng ký | Biến phân loại | ứng viên hồ sơ tại signup; cần xác minh snapshot | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: 'basic', 'facebook', 'google' |
| signup_flow | int64 | 17 | 0 | 0 | Mã luồng/trang đăng ký | Mã phân loại dù pandas đọc số | ứng viên hồ sơ tại signup; cần xác minh snapshot | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: [0, 25], 17 giá trị phân biệt |
| language | object | 25 | 0 | 0 | Ngôn ngữ ưu tiên | Biến phân loại | ứng viên hồ sơ tại signup; cần xác minh snapshot | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: 25 giá trị khác nhau; top category tại phụ lục |
| affiliate_channel | object | 8 | 0 | 0 | Kênh marketing liên quan | Không tự chứng minh tác động nhân quả của kênh | ứng viên hồ sơ tại signup; cần xác minh snapshot | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: 'api', 'content', 'direct', 'other', 'remarketing', 'sem-brand', 'sem-non-brand', 'seo' |
| affiliate_provider | object | 18 | 0 | 0 | Nhà cung cấp/kênh cụ thể | Biến phân loại | ứng viên hồ sơ tại signup; cần xác minh snapshot | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: 18 giá trị khác nhau; top category tại phụ lục |
| first_affiliate_tracked | object | 7 | 6,065 | 2.8414 | Tương tác affiliate đầu được theo dõi | NA và category untracked có nghĩa khác nhau | ứng viên hồ sơ tại signup; cần xác minh snapshot | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: 'linked', 'local ops', 'marketing', 'omg', 'product', 'tracked-other', 'untracked' |
| signup_app | object | 4 | 0 | 0 | Ứng dụng đăng ký | Không đại diện mọi thiết bị dùng về sau | ứng viên hồ sơ tại signup; cần xác minh snapshot | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: 'Android', 'Moweb', 'Web', 'iOS' |
| first_device_type | object | 9 | 0 | 0 | Thiết bị đầu tiên | Khác device_type ở từng sự kiện sessions | ứng viên hồ sơ tại signup; cần xác minh snapshot | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: 'Android Phone', 'Android Tablet', 'Desktop (Other)', 'Mac Desktop', 'Other/Unknown', 'SmartPhone (Other)', 'Windows Desktop', 'iPad', 'iPhone' |
| first_browser | object | 52 | 0 | 0 | Trình duyệt đầu tiên | Có sentinel -unknown- | ứng viên hồ sơ tại signup; cần xác minh snapshot | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: 52 giá trị khác nhau; top category tại phụ lục |
| country_destination | object | 12 | 0 | 0 | Điểm đến booking đầu hoặc NDF | Target 12 lớp; 11 lớp khi chỉ xét có booking | đích | mã/nhãn phân loại, không có đơn vị vật lý | Toàn bảng: 'AU', 'CA', 'DE', 'ES', 'FR', 'GB', 'IT', 'NDF', 'NL', 'PT', 'US', 'other' |

**So sánh schema train và test**

| column | in_train | in_test |
| --- | --- | --- |
| id | 1 | 1 |
| date_account_created | 1 | 1 |
| timestamp_first_active | 1 | 1 |
| date_first_booking | 1 | 1 |
| gender | 1 | 1 |
| age | 1 | 1 |
| signup_method | 1 | 1 |
| signup_flow | 1 | 1 |
| language | 1 | 1 |
| affiliate_channel | 1 | 1 |
| affiliate_provider | 1 | 1 |
| first_affiliate_tracked | 1 | 1 |
| signup_app | 1 | 1 |
| first_device_type | 1 | 1 |
| first_browser | 1 | 1 |
| country_destination | 1 | 0 |

### Danh mục file, dung lượng và SHA-256

Phiên bản local được xác định bằng các giá trị dưới đây; không suy ngày tải từ ngày sửa file.

**Danh mục đầy đủ; submission chỉ là định dạng kết quả, không phải dữ liệu người dùng bổ sung**

| file | data_lines | columns | bytes | sha256 |
| --- | --- | --- | --- | --- |
| age_gender_bkts.csv | 420 | 5 | 11,905 | ca101ff0d68112ac43083e5868ccf643a8701ede4dd0eaf90cd84bfff2998c6d |
| countries.csv | 10 | 7 | 632 | f6bc346fd3c51a237448860c9c77c16db2672d8e4799af11ef4d3b55560ec1cd |
| sample_submission_NDF.csv | 62,096 | 2 | 931,451 | 9cd8b164121586b8940ff1666dffce7fd44453628c0e4410e478ddb2dd61b769 |
| sessions.csv | 10,567,737 | 6 | 631,646,292 | 63d4a31cd7202468b120b6e88df4389f4e0bc0188a4ea683fcae50f7addc0f27 |
| test_users.csv | 62,096 | 15 | 6,763,170 | 17b25cbae6f3f6c95ff553ac108f145f0e3f0873bdae0c5f45f2f821ffd81384 |
| train_users_2.csv | 213,451 | 16 | 24,853,881 | 1d57dabe8b06534e51f86520ce6a66b6f67cce1704fb77a3fcfb596124858818 |

### Bảng phụ: từ điển và khả năng ghép

Chỉ kiểm tra bảng và quan hệ; chưa thực hiện feature engineering. Các mã NDF/other trong users không nhất thiết có dòng tương ứng trong countries; việc thiếu đó không phải lỗi khóa của users. Bất kỳ cách dùng thống kê ngoài bảng users phải xác minh nguồn, mốc công bố và ngữ nghĩa trước khi ghép vào đầu vào dự đoán.

**Kiểu, đơn vị và domain của từng cột bảng phụ**

| table | column | dtype | unit | observed_domain | missing_n |
| --- | --- | --- | --- | --- | --- |
| countries.csv | country_destination | object | mã/nhóm phân loại | AU, CA, DE, ES, FR, GB, IT, NL, PT, US | 0 |
| countries.csv | lat_destination | float64 | độ vĩ | -26.853388, 62.393303, 51.165707, 39.896027, 46.232193, 54.63322, 41.87399, 52.133057, 39.553444, 36.966427 | 0 |
| countries.csv | lng_destination | float64 | độ kinh | 133.27516, -96.818146, 10.452764, -2.4876945, 2.209667, -3.4322774, 12.564167, 5.29525, -7.839319, -95.84403 | 0 |
| countries.csv | distance_km | float64 | km | 15297.744, 2828.1333, 7879.568, 7730.724, 7682.945, 6883.659, 8636.631, 7524.3203, 7355.2534, 0.0 | 0 |
| countries.csv | destination_km2 | float64 | km² | 7741220.0, 9984670.0, 357022.0, 505370.0, 643801.0, 243610.0, 301340.0, 41543.0, 92090.0, 9826675.0 | 0 |
| countries.csv | destination_language  | object | mã/nhóm phân loại | eng, deu, spa, fra, ita, nld, por | 0 |
| countries.csv | language_levenshtein_distance | float64 | khoảng cách theo nguồn | 0.0, 72.61, 92.25, 92.06, 89.4, 63.22, 95.45 | 0 |
| age_gender_bkts.csv | age_bucket | object | mã/nhóm phân loại | 21 giá trị; [0-4, 95-99] | 0 |
| age_gender_bkts.csv | country_destination | object | mã/nhóm phân loại | AU, CA, DE, ES, FR, GB, IT, NL, PT, US | 0 |
| age_gender_bkts.csv | gender | object | mã/nhóm phân loại | male, female | 0 |
| age_gender_bkts.csv | population_in_thousands | float64 | nghìn theo nguồn | 381 giá trị; [0.0, 11601.0] | 0 |
| age_gender_bkts.csv | year | float64 | năm | 2015.0 | 0 |

**Từ điển bảng phụ (đủ các cột raw)**

| table | column_or_columns | meaning | caution |
| --- | --- | --- | --- |
| countries | country_destination | Mã quốc gia ứng viên/điểm đến | Khóa duy nhất phải được kiểm tra; không ghép theo nhãn thật |
| countries | lat_destination / lng_destination | Vĩ độ / kinh độ | Thuộc quốc gia, không phải địa chỉ user |
| countries | distance_km | Khoảng cách theo nguồn, km | Cần giữ định nghĩa gốc; không giả định khoảng cách từng user |
| countries | destination_km2 | Diện tích quốc gia, km² | Thống kê tổng hợp |
| countries | destination_language  | Ngôn ngữ quốc gia | Tên cột gốc có dấu cách cuối; chưa đổi tên raw |
| countries | language_levenshtein_distance | Khoảng cách ngôn ngữ theo nguồn | Định nghĩa cần tham chiếu nguồn |
| age_gender_bkts | age_bucket | Nhóm tuổi | Không nối trực tiếp age số mà không xác định quy tắc bucket |
| age_gender_bkts | country_destination / gender | Quốc gia và giới tính của ô tổng hợp | Khóa ghép tổng hợp; kiểm tra tính duy nhất |
| age_gender_bkts | population_in_thousands | Quy mô theo đơn vị nghìn của bảng nguồn | Không phải số users train; không tự coi là tỷ lệ booking |
| age_gender_bkts | year | Năm thống kê | Kiểm tra khả dụng tại t0 trước khi sử dụng |

**Kiểm tra khóa và missing bảng phụ**

| check | n |
| --- | --- |
| countries: số dòng | 10 |
| countries: khóa quốc gia trùng | 0 |
| countries: tổng ô NA | 0 |
| age_gender_bkts: khóa bucket-country-gender-year trùng | 0 |
| age_gender_bkts: tổng ô NA | 0 |

**Toàn bộ countries**

| country_destination | lat_destination | lng_destination | distance_km | destination_km2 | destination_language  | language_levenshtein_distance |
| --- | --- | --- | --- | --- | --- | --- |
| AU | -26.8534 | 133.2752 | 15,297.744 | 7,741,220 | eng | 0 |
| CA | 62.3933 | -96.8181 | 2,828.1333 | 9,984,670 | eng | 0 |
| DE | 51.1657 | 10.4528 | 7,879.568 | 357,022 | deu | 72.61 |
| ES | 39.896 | -2.4877 | 7,730.724 | 505,370 | spa | 92.25 |
| FR | 46.2322 | 2.2097 | 7,682.945 | 643,801 | fra | 92.06 |
| GB | 54.6332 | -3.4323 | 6,883.659 | 243,610 | eng | 0 |
| IT | 41.874 | 12.5642 | 8,636.631 | 301,340 | ita | 89.4 |
| NL | 52.1331 | 5.2953 | 7,524.3203 | 41,543 | nld | 63.22 |
| PT | 39.5534 | -7.8393 | 7,355.2534 | 92,090 | por | 95.45 |
| US | 36.9664 | -95.844 | 0 | 9,826,675 | eng | 0 |

**Độ phủ năm và category trong age_gender_bkts**

| column | value | n | pct_all_rows |
| --- | --- | --- | --- |
| year | 2015.0 | 420 | 100 |
| gender | male | 210 | 50 |
| gender | female | 210 | 50 |
| country_destination | AU | 42 | 10 |
| country_destination | CA | 42 | 10 |
| country_destination | DE | 42 | 10 |
| country_destination | ES | 42 | 10 |
| country_destination | FR | 42 | 10 |
| country_destination | GB | 42 | 10 |
| country_destination | IT | 42 | 10 |
| country_destination | NL | 42 | 10 |
| country_destination | PT | 42 | 10 |
| country_destination | US | 42 | 10 |

### Bảng đơn biến đầy đủ

Các bảng thống kê dưới đây bổ sung cho các biểu đồ ở phần chính. Top category không phải toàn bộ domain; đối chiếu từ điển.

**12 nhãn và hai mẫu số**

| country_destination | n | pct_all_users | pct_booked_users |
| --- | --- | --- | --- |
| NDF | 124,543 | 58.3473 | — |
| US | 62,376 | 29.2226 | 70.1579 |
| other | 10,094 | 4.729 | 11.3533 |
| FR | 5,023 | 2.3532 | 5.6497 |
| IT | 2,835 | 1.3282 | 3.1887 |
| GB | 2,324 | 1.0888 | 2.6139 |
| ES | 2,249 | 1.0536 | 2.5296 |
| CA | 1,428 | 0.669 | 1.6062 |
| DE | 1,061 | 0.4971 | 1.1934 |
| NL | 762 | 0.357 | 0.8571 |
| AU | 539 | 0.2525 | 0.6062 |
| PT | 217 | 0.1017 | 0.2441 |

**Tuổi raw và cửa sổ mô tả**

| sample | n | mean | median |
| --- | --- | --- | --- |
| Toàn bộ age không thiếu | 125,461 | 49.6683 | 34 |
| Chỉ age trong [16,100]; không thay đổi raw | 123,051 | 36.5606 | 34 |

**Thống kê tuổi raw**

| column | count | mean | std | min | 1% | 25% | 50% | 75% | 95% | 99% | max | missing_pct | skewness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| age | 125,461 | 49.6683 | 155.6666 | 1 | 19 | 28 | 34 | 43 | 64 | 105 | 2,014 | 41.2226 | 12.4226 |

**Phân phối category — top 8/cột**

| column | value | n | pct_all_rows |
| --- | --- | --- | --- |
| gender | -unknown- | 95,688 | 44.829 |
| gender | FEMALE | 63,041 | 29.5342 |
| gender | MALE | 54,440 | 25.5047 |
| gender | OTHER | 282 | 0.1321 |
| signup_method | basic | 152,897 | 71.631 |
| signup_method | facebook | 60,008 | 28.1132 |
| signup_method | google | 546 | 0.2558 |
| signup_flow | 0 | 164,739 | 77.1788 |
| signup_flow | 25 | 14,659 | 6.8676 |
| signup_flow | 12 | 9,329 | 4.3706 |
| signup_flow | 3 | 8,822 | 4.133 |
| signup_flow | 2 | 6,881 | 3.2237 |
| signup_flow | 24 | 4,328 | 2.0276 |
| signup_flow | 23 | 2,835 | 1.3282 |
| signup_flow | 1 | 1,047 | 0.4905 |
| language | en | 206,314 | 96.6564 |
| language | zh | 1,632 | 0.7646 |
| language | fr | 1,172 | 0.5491 |
| language | es | 915 | 0.4287 |
| language | ko | 747 | 0.35 |
| language | de | 732 | 0.3429 |
| language | it | 514 | 0.2408 |
| language | ru | 389 | 0.1822 |
| affiliate_channel | direct | 137,727 | 64.5239 |
| affiliate_channel | sem-brand | 26,045 | 12.2019 |
| affiliate_channel | sem-non-brand | 18,844 | 8.8283 |
| affiliate_channel | other | 8,961 | 4.1982 |
| affiliate_channel | seo | 8,663 | 4.0585 |
| affiliate_channel | api | 8,167 | 3.8262 |
| affiliate_channel | content | 3,948 | 1.8496 |
| affiliate_channel | remarketing | 1,096 | 0.5135 |
| affiliate_provider | direct | 137,426 | 64.3829 |
| affiliate_provider | google | 51,693 | 24.2177 |
| affiliate_provider | other | 12,549 | 5.8791 |
| affiliate_provider | craigslist | 3,471 | 1.6261 |
| affiliate_provider | bing | 2,328 | 1.0906 |
| affiliate_provider | facebook | 2,273 | 1.0649 |
| affiliate_provider | vast | 829 | 0.3884 |
| affiliate_provider | padmapper | 768 | 0.3598 |
| first_affiliate_tracked | untracked | 109,232 | 51.1743 |
| first_affiliate_tracked | linked | 46,287 | 21.6851 |
| first_affiliate_tracked | omg | 43,982 | 20.6052 |
| first_affiliate_tracked | tracked-other | 6,156 | 2.884 |
| first_affiliate_tracked | <MISSING> | 6,065 | 2.8414 |
| first_affiliate_tracked | product | 1,556 | 0.729 |
| first_affiliate_tracked | marketing | 139 | 0.0651 |
| first_affiliate_tracked | local ops | 34 | 0.0159 |
| signup_app | Web | 182,717 | 85.6014 |
| signup_app | iOS | 19,019 | 8.9102 |
| signup_app | Moweb | 6,261 | 2.9332 |
| signup_app | Android | 5,454 | 2.5552 |
| first_device_type | Mac Desktop | 89,600 | 41.9768 |
| first_device_type | Windows Desktop | 72,716 | 34.0668 |
| first_device_type | iPhone | 20,759 | 9.7254 |
| first_device_type | iPad | 14,339 | 6.7177 |
| first_device_type | Other/Unknown | 10,667 | 4.9974 |
| first_device_type | Android Phone | 2,803 | 1.3132 |
| first_device_type | Android Tablet | 1,292 | 0.6053 |
| first_device_type | Desktop (Other) | 1,199 | 0.5617 |
| first_browser | Chrome | 63,845 | 29.9108 |
| first_browser | Safari | 45,169 | 21.1613 |
| first_browser | Firefox | 33,655 | 15.7671 |
| first_browser | -unknown- | 27,266 | 12.7739 |
| first_browser | IE | 21,068 | 9.8702 |
| first_browser | Mobile Safari | 19,274 | 9.0297 |
| first_browser | Chrome Mobile | 1,270 | 0.595 |
| first_browser | Android Browser | 851 | 0.3987 |

### Schema và phân phối sessions đầy đủ

Mẫu số sự kiện khác người dùng; không gộp log thành tập feature.

**Schema toàn bảng sessions**

| column | distinct_nonnull | missing_n | missing_pct | meaning | caution |
| --- | --- | --- | --- | --- | --- |
| user_id | 135,483 | 34,496 | 0.3264 | ID ghép users.id | Khóa; NA không ghép được |
| action | 359 | 79,626 | 0.7535 | Tên hành động | Không có timestamp sự kiện |
| action_type | 10 | 1,126,204 | 10.657 | Nhóm hành động | Có NA/sentinel; không suy ra thứ tự thời gian |
| action_detail | 155 | 1,126,204 | 10.657 | Chi tiết hành động | Có NA/sentinel |
| device_type | 14 | 0 | 0 | Thiết bị ở sự kiện | Tỷ trọng sự kiện khác tỷ trọng người dùng |
| secs_elapsed | không tính | 136,031 | 1.2872 | Trường thời lượng theo mô tả nguồn | Không phải timestamp; không dùng để cắt trước/sau booking |

**Số sự kiện mỗi user có log; NA user_id không nằm trong mẫu số**

| column | count | mean | std | min | 1% | 25% | 50% | 75% | 95% | 99% | max | missing_pct | skewness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| event_n | 135,483 | 77.7459 | 112.5637 | 1 | 1 | 16 | 41 | 95 | 273 | 538 | 2,722 | 0 | 4.7397 |
| elapsed_nonnull | 135,483 | 76.7459 | 112.5637 | 0 | 0 | 15 | 40 | 94 | 272 | 537 | 2,721 | 0 | 4.7397 |
| elapsed_sum | 135,483 | 1,489,732.4021 | 1,892,922.7256 | 0 | 0 | 260,598 | 850,271 | 2,000,422.5 | 5,143,472.4 | 8,911,308.36 | 38,221,363 | 0 | 2.9604 |

**Thiết bị theo toàn bộ sự kiện**

| device_type | events | pct_all_events |
| --- | --- | --- |
| Mac Desktop | 3,594,286 | 34.0119 |
| Windows Desktop | 2,658,539 | 25.1571 |
| iPhone | 2,105,031 | 19.9194 |
| Android Phone | 839,637 | 7.9453 |
| iPad Tablet | 683,414 | 6.467 |
| Android App Unknown Phone/Tablet | 273,652 | 2.5895 |
| -unknown- | 211,279 | 1.9993 |
| Tablet | 139,886 | 1.3237 |
| Linux Desktop | 28,373 | 0.2685 |
| Chromebook | 22,348 | 0.2115 |
| iPodtouch | 8,198 | 0.0776 |
| Windows Phone | 2,047 | 0.0194 |
| Blackberry | 979 | 0.0093 |
| Opera Phone | 68 | 0.0006 |

**Top 20 action theo toàn bộ sự kiện**

| action | events | pct_all_events |
| --- | --- | --- |
| show | 2,768,278 | 26.1956 |
| index | 843,699 | 7.9837 |
| search_results | 725,226 | 6.8626 |
| personalize | 706,824 | 6.6885 |
| search | 536,057 | 5.0726 |
| ajax_refresh_subtotal | 487,744 | 4.6154 |
| update | 365,130 | 3.4551 |
| similar_listings | 364,624 | 3.4504 |
| social_connections | 339,000 | 3.2079 |
| reviews | 320,591 | 3.0337 |
| active | 188,036 | 1.7793 |
| similar_listings_v2 | 168,788 | 1.5972 |
| lookup | 162,041 | 1.5334 |
| create | 155,887 | 1.4751 |
| dashboard | 152,952 | 1.4473 |
| header_userpic | 141,830 | 1.3421 |
| collections | 124,417 | 1.1773 |
| edit | 109,083 | 1.0322 |
| campaigns | 105,028 | 0.9939 |
| track_page_view | 81,117 | 0.7676 |

### Tương quan giữa các chỉ báo thiếu

Đây là tương quan của các cờ NA để phát hiện cùng thiếu; không xác định MCAR/MAR/MNAR. Cờ dùng để EDA, không xuất thành feature.

**Correlation các chỉ báo NA**

| column | date_first_booking | age | first_affiliate_tracked |
| --- | --- | --- | --- |
| date_first_booking | 1 | 0.3142 | 0.0451 |
| age | 0.3142 | 1 | 0.0878 |
| first_affiliate_tracked | 0.0451 | 0.0878 | 1 |

### Số nhóm và nhóm hiếm — toàn bộ users train

Ngưỡng n<100 chỉ giúp phát hiện nhóm cần thận trọng; chưa gộp hoặc mã hóa category.

**Category cardinality**

| column | groups_including_na | groups_under_100 | rows_in_rare_groups | pct_rows_rare |
| --- | --- | --- | --- | --- |
| gender | 4 | 0 | 0 | 0 |
| signup_method | 3 | 0 | 0 | 0 |
| signup_flow | 17 | 6 | 74 | 0.0347 |
| language | 25 | 14 | 449 | 0.2104 |
| affiliate_channel | 8 | 0 | 0 | 0 |
| affiliate_provider | 18 | 5 | 107 | 0.0501 |
| first_affiliate_tracked | 8 | 1 | 34 | 0.0159 |
| signup_app | 4 | 0 | 0 | 0 |
| first_device_type | 9 | 1 | 76 | 0.0356 |
| first_browser | 52 | 41 | 496 | 0.2324 |

### Tỷ lệ nhãn cho nhóm bổ sung

Các bảng ở đây không lặp các nhóm đã công bố trong phần chính.

**Booking theo language — các nhóm còn lại**

| language | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| sv | 122 | 44 | 36.0656 | 28.0904 | 44.8915 | 0 |
| nl | 97 | 35 | 36.0825 | 27.2245 | 46.0008 | 1 |
| tr | 64 | 20 | 31.25 | 21.2311 | 43.3923 | 1 |
| da | 58 | 19 | 32.7586 | 22.0833 | 45.5759 | 1 |
| pl | 54 | 13 | 24.0741 | 14.6443 | 36.9475 | 1 |
| cs | 32 | 9 | 28.125 | 15.5646 | 45.3745 | 1 |
| no | 30 | 13 | 43.3333 | 27.3775 | 60.8027 | 1 |
| el | 24 | 6 | 25 | 11.9994 | 44.8994 | 1 |
| th | 24 | 4 | 16.6667 | 6.6787 | 35.8531 | 1 |
| id | 22 | 0 | 0 | 0 | 14.8655 | 1 |
| hu | 18 | 4 | 22.2222 | 9.0009 | 45.2146 | 1 |
| fi | 14 | 7 | 50 | 26.7992 | 73.2008 | 1 |
| ca | 5 | 2 | 40 | 11.7621 | 76.9276 | 1 |
| is | 5 | 2 | 40 | 11.7621 | 76.9276 | 1 |
| hr | 2 | 0 | 0 | 0 | 65.762 | 1 |

**Booking theo signup_flow — bổ sung**

| signup_flow | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 164,739 | 69,894 | 42.4271 | 42.1886 | 42.6659 | 0 |
| 25 | 14,659 | 3,958 | 27.0005 | 26.2879 | 27.7251 | 0 |
| 12 | 9,329 | 3,065 | 32.8545 | 31.9087 | 33.8145 | 0 |
| 3 | 8,822 | 5,615 | 63.6477 | 62.6382 | 64.6453 | 0 |
| 2 | 6,881 | 3,679 | 53.4661 | 52.2859 | 54.6424 | 0 |
| 24 | 4,328 | 1,515 | 35.0046 | 33.5974 | 36.4384 | 0 |
| 23 | 2,835 | 643 | 22.6808 | 21.1768 | 24.2586 | 0 |
| 1 | 1,047 | 169 | 16.1414 | 14.0372 | 18.493 | 0 |
| 6 | 301 | 164 | 54.485 | 48.8381 | 60.019 | 0 |
| 8 | 240 | 111 | 46.25 | 40.0507 | 52.5674 | 0 |
| 21 | 196 | 84 | 42.8571 | 36.1319 | 49.857 | 0 |
| 5 | 36 | 2 | 5.5556 | 1.537 | 18.1447 | 1 |
| 20 | 14 | 2 | 14.2857 | 4.0094 | 39.9414 | 1 |
| 16 | 11 | 2 | 18.1818 | 5.1368 | 47.6981 | 1 |
| 15 | 10 | 4 | 40 | 16.818 | 68.7326 | 1 |
| 10 | 2 | 1 | 50 | 9.4531 | 90.5469 | 1 |
| 4 | 1 | 0 | 0 | 0 | 79.3451 | 1 |

**Booking theo affiliate_provider — bổ sung**

| affiliate_provider | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| direct | 137,426 | 59,234 | 43.1025 | 42.8408 | 43.3645 | 0 |
| google | 51,693 | 20,779 | 40.1969 | 39.775 | 40.6203 | 0 |
| other | 12,549 | 4,663 | 37.1583 | 36.3169 | 38.0076 | 0 |
| craigslist | 3,471 | 1,616 | 46.5572 | 44.9025 | 48.2195 | 0 |
| bing | 2,328 | 833 | 35.7818 | 33.8594 | 37.751 | 0 |
| facebook | 2,273 | 792 | 34.8438 | 32.9121 | 36.8267 | 0 |
| vast | 829 | 271 | 32.69 | 29.5831 | 35.9566 | 0 |
| padmapper | 768 | 252 | 32.8125 | 29.5845 | 36.2116 | 0 |
| facebook-open-graph | 545 | 141 | 25.8716 | 22.3728 | 29.7081 | 0 |
| yahoo | 496 | 174 | 35.0806 | 31.0101 | 39.3805 | 0 |
| gsp | 453 | 37 | 8.1678 | 5.9836 | 11.0554 | 0 |
| meetup | 347 | 46 | 13.2565 | 10.0877 | 17.2299 | 0 |
| email-marketing | 166 | 37 | 22.2892 | 16.6255 | 29.2063 | 0 |
| naver | 52 | 18 | 34.6154 | 23.151 | 48.1964 | 1 |
| baidu | 29 | 10 | 34.4828 | 19.9407 | 52.6549 | 1 |
| yandex | 17 | 4 | 23.5294 | 9.555 | 47.2618 | 1 |
| wayn | 8 | 0 | 0 | 0 | 32.4408 | 1 |
| daum | 1 | 1 | 100 | 20.6549 | 100 | 1 |

**Booking theo first_affiliate_tracked — bổ sung**

| first_affiliate_tracked | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| untracked | 109,232 | 47,739 | 43.7042 | 43.4103 | 43.9986 | 0 |
| linked | 46,287 | 20,102 | 43.429 | 42.9781 | 43.8811 | 0 |
| omg | 43,982 | 16,425 | 37.3448 | 36.8939 | 37.798 | 0 |
| tracked-other | 6,156 | 2,290 | 37.1995 | 36.0004 | 38.4145 | 0 |
| <MISSING> | 6,065 | 1,738 | 28.6562 | 27.5321 | 29.8074 | 0 |
| product | 1,556 | 542 | 34.8329 | 32.5056 | 37.2349 | 0 |
| marketing | 139 | 63 | 45.3237 | 37.2849 | 53.6141 | 0 |
| local ops | 34 | 9 | 26.4706 | 14.6012 | 43.1171 | 1 |

**Booking theo first_browser — bổ sung**

| first_browser | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| Chrome | 63,845 | 29,877 | 46.7961 | 46.4093 | 47.1834 | 0 |
| Safari | 45,169 | 19,721 | 43.6605 | 43.2037 | 44.1184 | 0 |
| Firefox | 33,655 | 15,730 | 46.739 | 46.2063 | 47.2724 | 0 |
| -unknown- | 27,266 | 7,618 | 27.9396 | 27.4101 | 28.4752 | 0 |
| IE | 21,068 | 7,723 | 36.6575 | 36.0093 | 37.3105 | 0 |
| Mobile Safari | 19,274 | 7,181 | 37.2574 | 36.5775 | 37.9425 | 0 |
| Chrome Mobile | 1,270 | 408 | 32.126 | 29.615 | 34.7448 | 0 |
| Android Browser | 851 | 280 | 32.9025 | 29.8286 | 36.13 | 0 |
| AOL Explorer | 245 | 63 | 25.7143 | 20.6459 | 31.5325 | 0 |
| Opera | 188 | 64 | 34.0426 | 27.6492 | 41.075 | 0 |
| Silk | 124 | 43 | 34.6774 | 26.8748 | 43.4009 | 0 |
| Chromium | 73 | 43 | 58.9041 | 47.4492 | 69.4687 | 1 |
| BlackBerry Browser | 53 | 22 | 41.5094 | 29.2609 | 54.9056 | 1 |
| Maxthon | 46 | 16 | 34.7826 | 22.681 | 49.2299 | 1 |
| Apple Mail | 36 | 15 | 41.6667 | 27.1406 | 57.7997 | 1 |
| IE Mobile | 36 | 7 | 19.4444 | 9.7531 | 35.028 | 1 |
| Sogou Explorer | 33 | 9 | 27.2727 | 15.0674 | 44.2176 | 1 |
| Mobile Firefox | 30 | 13 | 43.3333 | 27.3775 | 60.8027 | 1 |
| RockMelt | 24 | 12 | 50 | 31.4274 | 68.5726 | 1 |
| SiteKiosk | 24 | 7 | 29.1667 | 14.9146 | 49.1677 | 1 |
| Iron | 17 | 9 | 52.9412 | 30.9632 | 73.8349 | 1 |
| IceWeasel | 13 | 8 | 61.5385 | 35.5229 | 82.2903 | 1 |
| Pale Moon | 12 | 4 | 33.3333 | 13.812 | 60.9378 | 1 |
| CometBird | 11 | 1 | 9.0909 | 1.6232 | 37.7358 | 1 |
| Yandex.Browser | 11 | 1 | 9.0909 | 1.6232 | 37.7358 | 1 |
| SeaMonkey | 11 | 4 | 36.3636 | 15.1665 | 64.6199 | 1 |
| Camino | 9 | 7 | 77.7778 | 45.2589 | 93.6775 | 1 |
| TenFourFox | 8 | 4 | 50 | 21.5216 | 78.4784 | 1 |
| CoolNovo | 6 | 3 | 50 | 18.7616 | 81.2384 | 1 |
| wOSBrowser | 6 | 3 | 50 | 18.7616 | 81.2384 | 1 |
| Opera Mini | 4 | 2 | 50 | 15.0039 | 84.9961 | 1 |
| Avant Browser | 4 | 1 | 25 | 4.5587 | 69.9358 | 1 |
| Mozilla | 3 | 1 | 33.3333 | 6.1492 | 79.234 | 1 |
| Comodo Dragon | 2 | 0 | 0 | 0 | 65.762 | 1 |
| Flock | 2 | 0 | 0 | 0 | 65.762 | 1 |
| Crazy Browser | 2 | 0 | 0 | 0 | 65.762 | 1 |
| OmniWeb | 2 | 0 | 0 | 0 | 65.762 | 1 |
| Opera Mobile | 2 | 0 | 0 | 0 | 65.762 | 1 |
| TheWorld Browser | 2 | 2 | 100 | 34.238 | 100 | 1 |
| SlimBrowser | 2 | 1 | 50 | 9.4531 | 90.5469 | 1 |
| Google Earth | 1 | 0 | 0 | 0 | 79.3451 | 1 |
| Epic | 1 | 0 | 0 | 0 | 79.3451 | 1 |
| Conkeror | 1 | 0 | 0 | 0 | 79.3451 | 1 |
| Arora | 1 | 0 | 0 | 0 | 79.3451 | 1 |
| NetNewsWire | 1 | 1 | 100 | 20.6549 | 100 | 1 |
| Googlebot | 1 | 1 | 100 | 20.6549 | 100 | 1 |
| IceDragon | 1 | 0 | 0 | 0 | 79.3451 | 1 |
| Kindle Browser | 1 | 1 | 100 | 20.6549 | 100 | 1 |
| PS Vita browser | 1 | 0 | 0 | 0 | 79.3451 | 1 |
| Outlook 2007 | 1 | 0 | 0 | 0 | 79.3451 | 1 |
| Palm Pre web browser | 1 | 1 | 100 | 20.6549 | 100 | 1 |
| Stainless | 1 | 1 | 100 | 20.6549 | 100 | 1 |

### Phân tầng và tương tác: Wilson 95% cho từng ô

Dùng để đọc độ bất định của các ô heatmap; không phải kết quả mô hình.

**signup_app × năm**

| account_year | signup_app | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2010 | Web | 2,788 | 1,603 | 57.4964 | 55.6523 | 59.3199 | 0 |
| 2011 | Web | 11,775 | 6,433 | 54.6327 | 53.7321 | 55.5303 | 0 |
| 2012 | Android | 25 | 16 | 64 | 44.5185 | 79.7521 | 1 |
| 2012 | Moweb | 560 | 233 | 41.6071 | 37.5954 | 45.7332 | 0 |
| 2012 | Web | 38,184 | 17,192 | 45.0241 | 44.5256 | 45.5236 | 0 |
| 2012 | iOS | 693 | 308 | 44.4444 | 40.7856 | 48.1646 | 0 |
| 2013 | Android | 1,621 | 385 | 23.7508 | 21.7427 | 25.8829 | 0 |
| 2013 | Moweb | 3,084 | 1,132 | 36.7056 | 35.022 | 38.4223 | 0 |
| 2013 | Web | 72,428 | 30,318 | 41.8595 | 41.5007 | 42.2192 | 0 |
| 2013 | iOS | 5,827 | 2,049 | 35.1639 | 33.9481 | 36.3993 | 0 |
| 2014 | Android | 3,808 | 832 | 21.8487 | 20.565 | 23.1892 | 0 |
| 2014 | Moweb | 2,617 | 778 | 29.7287 | 28.0083 | 31.5085 | 0 |
| 2014 | Web | 57,542 | 24,475 | 42.5341 | 42.1307 | 42.9386 | 0 |
| 2014 | iOS | 12,499 | 3,154 | 25.234 | 24.4802 | 26.003 | 0 |

**gender × năm**

| account_year | gender | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2010 | -unknown- | 1,509 | 810 | 53.6779 | 51.1559 | 56.1813 | 0 |
| 2010 | FEMALE | 732 | 453 | 61.8852 | 58.3135 | 65.3329 | 0 |
| 2010 | MALE | 545 | 338 | 62.0183 | 57.8729 | 65.9955 | 0 |
| 2010 | OTHER | 2 | 2 | 100 | 34.238 | 100 | 1 |
| 2011 | -unknown- | 4,617 | 2,514 | 54.4509 | 53.0113 | 55.8832 | 0 |
| 2011 | FEMALE | 3,693 | 2,050 | 55.5104 | 53.9027 | 57.1067 | 0 |
| 2011 | MALE | 3,439 | 1,848 | 53.7366 | 52.0669 | 55.3979 | 0 |
| 2011 | OTHER | 26 | 21 | 80.7692 | 62.1237 | 91.4929 | 1 |
| 2012 | -unknown- | 10,993 | 3,930 | 35.75 | 34.8592 | 36.6508 | 0 |
| 2012 | FEMALE | 15,535 | 7,538 | 48.5227 | 47.7372 | 49.3089 | 0 |
| 2012 | MALE | 12,846 | 6,230 | 48.4976 | 47.6339 | 49.3622 | 0 |
| 2012 | OTHER | 88 | 51 | 57.9545 | 47.5208 | 67.7229 | 1 |
| 2013 | -unknown- | 38,799 | 11,209 | 28.8899 | 28.441 | 29.343 | 0 |
| 2013 | FEMALE | 23,631 | 12,064 | 51.0516 | 50.4141 | 51.6887 | 0 |
| 2013 | MALE | 20,436 | 10,554 | 51.6442 | 50.9588 | 52.3289 | 0 |
| 2013 | OTHER | 94 | 57 | 60.6383 | 50.5311 | 69.9101 | 1 |
| 2014 | -unknown- | 39,770 | 10,555 | 26.5401 | 26.1084 | 26.9763 | 0 |
| 2014 | FEMALE | 19,450 | 9,888 | 50.838 | 50.1354 | 51.5404 | 0 |
| 2014 | MALE | 17,174 | 8,751 | 50.9549 | 50.2071 | 51.7023 | 0 |
| 2014 | OTHER | 72 | 45 | 62.5 | 50.9529 | 72.7808 | 1 |

**affiliate_channel × năm**

| account_year | affiliate_channel | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2010 | content | 95 | 47 | 49.4737 | 39.6376 | 59.3507 | 1 |
| 2010 | direct | 1,310 | 812 | 61.9847 | 59.3246 | 64.5747 | 0 |
| 2010 | other | 650 | 342 | 52.6154 | 48.7727 | 56.4273 | 0 |
| 2010 | sem-brand | 37 | 22 | 59.4595 | 43.486 | 73.6535 | 1 |
| 2010 | sem-non-brand | 395 | 194 | 49.1139 | 44.2162 | 54.0287 | 0 |
| 2010 | seo | 301 | 186 | 61.794 | 56.1889 | 67.1019 | 0 |
| 2011 | api | 1 | 1 | 100 | 20.6549 | 100 | 1 |
| 2011 | content | 296 | 111 | 37.5 | 32.1781 | 43.1422 | 0 |
| 2011 | direct | 6,578 | 3,705 | 56.3241 | 55.1222 | 57.5187 | 0 |
| 2011 | other | 1,593 | 834 | 52.354 | 49.8987 | 54.798 | 0 |
| 2011 | remarketing | 94 | 47 | 50 | 40.0927 | 59.9073 | 1 |
| 2011 | sem-brand | 777 | 427 | 54.955 | 51.4407 | 58.4204 | 0 |
| 2011 | sem-non-brand | 1,800 | 937 | 52.0556 | 49.7457 | 54.3566 | 0 |
| 2011 | seo | 636 | 371 | 58.3333 | 54.463 | 62.1036 | 0 |
| 2012 | api | 1,813 | 829 | 45.7253 | 43.4436 | 48.0251 | 0 |
| 2012 | content | 432 | 69 | 15.9722 | 12.8197 | 19.7246 | 0 |
| 2012 | direct | 25,114 | 11,981 | 47.7065 | 47.0891 | 48.3245 | 0 |
| 2012 | other | 3,201 | 1,250 | 39.0503 | 37.3743 | 40.7525 | 0 |
| 2012 | remarketing | 129 | 58 | 44.9612 | 36.6464 | 53.5675 | 0 |
| 2012 | sem-brand | 2,783 | 1,168 | 41.9691 | 40.1479 | 43.8125 | 0 |
| 2012 | sem-non-brand | 4,872 | 1,888 | 38.7521 | 37.3934 | 40.1284 | 0 |
| 2012 | seo | 1,118 | 506 | 45.2594 | 42.3629 | 48.1883 | 0 |
| 2013 | api | 3,504 | 1,183 | 33.7614 | 32.2142 | 35.3442 | 0 |
| 2013 | content | 1,482 | 149 | 10.054 | 8.6247 | 11.6898 | 0 |
| 2013 | direct | 55,522 | 23,892 | 43.0316 | 42.6202 | 43.4439 | 0 |
| 2013 | other | 2,661 | 863 | 32.4314 | 30.6792 | 34.2343 | 0 |
| 2013 | remarketing | 181 | 51 | 28.1768 | 22.1292 | 35.1314 | 0 |
| 2013 | sem-brand | 9,755 | 4,027 | 41.2814 | 40.308 | 42.2617 | 0 |
| 2013 | sem-non-brand | 6,604 | 2,313 | 35.0242 | 33.8827 | 36.1832 | 0 |
| 2013 | seo | 3,251 | 1,406 | 43.2482 | 41.5542 | 44.9582 | 0 |
| 2014 | api | 2,849 | 772 | 27.0972 | 25.4968 | 28.7593 | 0 |
| 2014 | content | 1,643 | 182 | 11.0773 | 9.6496 | 12.6866 | 0 |
| 2014 | direct | 49,203 | 19,008 | 38.6318 | 38.2025 | 39.0629 | 0 |
| 2014 | other | 856 | 311 | 36.3318 | 33.1775 | 39.6081 | 0 |
| 2014 | remarketing | 692 | 212 | 30.6358 | 27.316 | 34.1695 | 0 |
| 2014 | sem-brand | 12,693 | 5,450 | 42.9371 | 42.0782 | 43.8002 | 0 |
| 2014 | sem-non-brand | 5,173 | 1,818 | 35.144 | 33.8545 | 36.4556 | 0 |
| 2014 | seo | 3,357 | 1,486 | 44.2657 | 42.593 | 45.9515 | 0 |

**signup_app × affiliate_channel, chỉ cohort 2014**

| signup_app | affiliate_channel | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Android | api | 942 | 200 | 21.2314 | 18.7395 | 23.9571 | 0 |
| Android | direct | 2,832 | 622 | 21.9633 | 20.4771 | 23.5254 | 0 |
| Android | other | 6 | 1 | 16.6667 | 3.0053 | 56.3503 | 1 |
| Android | sem-brand | 20 | 7 | 35 | 18.1192 | 56.7146 | 1 |
| Android | sem-non-brand | 6 | 2 | 33.3333 | 9.6771 | 70.0007 | 1 |
| Android | seo | 2 | 0 | 0 | 0 | 65.762 | 1 |
| Moweb | api | 271 | 91 | 33.5793 | 28.2208 | 39.3969 | 0 |
| Moweb | direct | 2,212 | 655 | 29.6112 | 27.7453 | 31.5478 | 0 |
| Moweb | other | 29 | 8 | 27.5862 | 14.6988 | 45.7171 | 1 |
| Moweb | sem-brand | 55 | 10 | 18.1818 | 10.1877 | 30.3305 | 1 |
| Moweb | sem-non-brand | 24 | 8 | 33.3333 | 17.9722 | 53.2937 | 1 |
| Moweb | seo | 26 | 6 | 23.0769 | 11.0338 | 42.0516 | 1 |
| Web | api | 12 | 1 | 8.3333 | 1.4865 | 35.388 | 1 |
| Web | content | 1,642 | 182 | 11.084 | 9.6555 | 12.6943 | 0 |
| Web | direct | 33,354 | 15,071 | 45.185 | 44.6515 | 45.7196 | 0 |
| Web | other | 778 | 295 | 37.9177 | 34.5757 | 41.3785 | 0 |
| Web | remarketing | 692 | 212 | 30.6358 | 27.316 | 34.1695 | 0 |
| Web | sem-brand | 12,599 | 5,427 | 43.0748 | 42.2124 | 43.9415 | 0 |
| Web | sem-non-brand | 5,140 | 1,807 | 35.1556 | 33.8619 | 36.4716 | 0 |
| Web | seo | 3,325 | 1,480 | 44.5113 | 42.8293 | 46.2059 | 0 |
| iOS | api | 1,624 | 480 | 29.5567 | 27.3878 | 31.822 | 0 |
| iOS | content | 1 | 0 | 0 | 0 | 79.3451 | 1 |
| iOS | direct | 10,805 | 2,660 | 24.6182 | 23.8151 | 25.4394 | 0 |
| iOS | other | 43 | 7 | 16.2791 | 8.1166 | 29.9724 | 1 |
| iOS | sem-brand | 19 | 6 | 31.5789 | 15.3644 | 53.9896 | 1 |
| iOS | sem-non-brand | 3 | 1 | 33.3333 | 6.1492 | 79.234 | 1 |
| iOS | seo | 4 | 0 | 0 | 0 | 48.9891 | 1 |

**age_missing_eda × gender, chỉ cohort 2014**

| age_missing_eda | gender | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Có tuổi | -unknown- | 7,149 | 4,902 | 68.569 | 67.4832 | 69.635 | 0 |
| Có tuổi | FEMALE | 18,546 | 9,595 | 51.7362 | 51.0168 | 52.455 | 0 |
| Có tuổi | MALE | 16,576 | 8,552 | 51.5927 | 50.8316 | 52.353 | 0 |
| Có tuổi | OTHER | 67 | 44 | 65.6716 | 53.7327 | 75.911 | 1 |
| Thiếu tuổi | -unknown- | 32,621 | 5,653 | 17.3293 | 16.9224 | 17.7439 | 0 |
| Thiếu tuổi | FEMALE | 904 | 293 | 32.4115 | 29.4404 | 35.5314 | 0 |
| Thiếu tuổi | MALE | 598 | 199 | 33.2776 | 29.6182 | 37.1504 | 0 |
| Thiếu tuổi | OTHER | 5 | 1 | 20 | 3.6224 | 62.4465 | 1 |

### Rà soát sessions bổ sung

Mẫu số là user 2014 có log; action_type giữ toàn bộ, action_detail lọc bằng regex đã công bố. Các bảng không chứng minh thời điểm sự kiện.

**Toàn bộ action_type và action_detail được rà soát**

| field | value | users_with_action | booked_users | ndf_users | booking_rate_pct | ci95_low_pct | ci95_high_pct | pct_booked_users_with_action | pct_ndf_users_with_action | events | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| action_detail | confirm_email_link | 30,857 | 15,545 | 15,312 | 50.3775 | 49.8197 | 50.9353 | 54.0245 | 33.9957 | 34,449 | 0 |
| action_detail | reservations | 4,746 | 1,604 | 3,142 | 33.7969 | 32.4647 | 35.1552 | 5.5745 | 6.9759 | 14,551 | 0 |
| action_detail | post_checkout_action | 4,619 | 4,078 | 541 | 88.2875 | 87.3282 | 89.1832 | 14.1725 | 1.2011 | 5,742 | 0 |
| action_detail | payment_instruments | 3,764 | 1,384 | 2,380 | 36.7694 | 35.2432 | 38.3225 | 4.8099 | 5.2841 | 10,230 | 0 |
| action_detail | request_new_confirm_email | 2,619 | 1,754 | 865 | 66.9721 | 65.1472 | 68.7473 | 6.0958 | 1.9205 | 4,251 | 0 |
| action_detail | book_it | 1,773 | 642 | 1,131 | 36.2098 | 34.0048 | 38.4745 | 2.2312 | 2.511 | 4,716 | 0 |
| action_detail | account_payout_preferences | 933 | 386 | 547 | 41.3719 | 38.2534 | 44.5612 | 1.3415 | 1.2144 | 2,352 | 0 |
| action_detail | instant_book | 591 | 211 | 380 | 35.7022 | 31.9431 | 39.6459 | 0.7333 | 0.8437 | 1,220 | 0 |
| action_detail | guest_itinerary | 482 | 412 | 70 | 85.4772 | 82.0512 | 88.3421 | 1.4318 | 0.1554 | 922 | 0 |
| action_detail | request_to_book | 248 | 92 | 156 | 37.0968 | 31.3243 | 43.2629 | 0.3197 | 0.3464 | 843 | 0 |
| action_detail | your_reservations | 188 | 65 | 123 | 34.5745 | 28.1461 | 41.6206 | 0.2259 | 0.2731 | 390 | 0 |
| action_detail | confirm_email | 129 | 66 | 63 | 51.1628 | 42.6288 | 59.6295 | 0.2294 | 0.1399 | 131 | 0 |
| action_detail | guest_receipt | 102 | 101 | 1 | 99.0196 | 94.6542 | 99.8267 | 0.351 | 0.0022 | 192 | 0 |
| action_detail | complete_booking | 27 | 22 | 5 | 81.4815 | 63.3013 | 91.8193 | 0.0765 | 0.0111 | 49 | 1 |
| action_detail | alteration_request | 14 | 12 | 2 | 85.7143 | 60.0586 | 95.9906 | 0.0417 | 0.0044 | 23 | 1 |
| action_detail | create_alteration_request | 10 | 10 | 0 | 100 | 72.2467 | 100 | 0.0348 | 0 | 11 | 1 |
| action_detail | respond_to_alteration_request | 9 | 9 | 0 | 100 | 70.0855 | 100 | 0.0313 | 0 | 9 | 1 |
| action_detail | booking | 2 | 1 | 1 | 50 | 9.4531 | 90.5469 | 0.0035 | 0.0022 | 2 | 1 |
| action_type | submit | 68,915 | 27,342 | 41,573 | 39.675 | 39.3103 | 40.0408 | 95.0233 | 92.3003 | 357,371 | 0 |
| action_type | data | 68,139 | 27,246 | 40,893 | 39.9859 | 39.6187 | 40.3543 | 94.6897 | 90.7906 | 1,188,495 | 0 |
| action_type | view | 65,428 | 26,378 | 39,050 | 40.3161 | 39.9408 | 40.6925 | 91.673 | 86.6988 | 1,669,723 | 0 |
| action_type | click | 59,251 | 24,703 | 34,548 | 41.6921 | 41.2957 | 42.0896 | 85.8518 | 76.7034 | 1,064,436 | 0 |
| action_type | -unknown- | 56,216 | 23,277 | 32,939 | 41.4064 | 40.9998 | 41.8141 | 80.8959 | 73.1311 | 564,803 | 0 |
| action_type | <NA> | 52,680 | 20,986 | 31,694 | 39.8368 | 39.4195 | 40.2555 | 72.9339 | 70.367 | 619,860 | 0 |
| action_type | message_post | 27,919 | 16,048 | 11,871 | 57.4806 | 56.8997 | 58.0594 | 55.7726 | 26.356 | 55,567 | 0 |
| action_type | booking_request | 10,003 | 8,466 | 1,537 | 84.6346 | 83.9146 | 85.328 | 29.4224 | 3.4124 | 10,695 | 0 |
| action_type | partner_callback | 5,334 | 2,804 | 2,530 | 52.5684 | 51.227 | 53.9061 | 9.7449 | 5.6171 | 7,005 | 0 |
| action_type | booking_response | 2 | 1 | 1 | 50 | 9.4531 | 90.5469 | 0.0035 | 0.0022 | 2 | 1 |

### Cohort theo tháng và khoảng tin cậy

Số liệu đứng sau hình account_cohorts; không lặp lại bảng khoảng thời gian hoặc drift.

**Toàn bộ cohort tháng; Wilson 95%**

| account_month | users | booked | booked_pct | ci95_low_pct | ci95_high_pct |
| --- | --- | --- | --- | --- | --- |
| 2010-01 | 61 | 32 | 52.459 | 40.1572 | 64.4695 |
| 2010-02 | 102 | 55 | 53.9216 | 44.282 | 63.2765 |
| 2010-03 | 163 | 106 | 65.0307 | 57.4403 | 71.9289 |
| 2010-04 | 157 | 91 | 57.9618 | 50.1407 | 65.4025 |
| 2010-05 | 227 | 128 | 56.3877 | 49.8833 | 62.6794 |
| 2010-06 | 222 | 109 | 49.0991 | 42.5944 | 55.6344 |
| 2010-07 | 307 | 180 | 58.6319 | 53.0493 | 64.0012 |
| 2010-08 | 312 | 180 | 57.6923 | 52.1494 | 63.0481 |
| 2010-09 | 371 | 218 | 58.7601 | 53.6861 | 63.6545 |
| 2010-10 | 309 | 191 | 61.8123 | 56.2815 | 67.053 |
| 2010-11 | 286 | 164 | 57.3427 | 51.5507 | 62.94 |
| 2010-12 | 271 | 149 | 54.9815 | 49.0297 | 60.7941 |
| 2011-01 | 316 | 189 | 59.8101 | 54.3179 | 65.0667 |
| 2011-02 | 362 | 215 | 59.3923 | 54.2603 | 64.327 |
| 2011-03 | 491 | 326 | 66.3951 | 62.1041 | 70.4316 |
| 2011-04 | 577 | 372 | 64.4714 | 60.4823 | 68.269 |
| 2011-05 | 744 | 468 | 62.9032 | 59.3741 | 66.2997 |
| 2011-06 | 822 | 506 | 61.5572 | 58.1852 | 64.8216 |
| 2011-07 | 993 | 644 | 64.854 | 61.8324 | 67.761 |
| 2011-08 | 1,454 | 775 | 53.3012 | 50.7315 | 55.8536 |
| 2011-09 | 1,864 | 859 | 46.0837 | 43.8312 | 48.3523 |
| 2011-10 | 1,477 | 740 | 50.1016 | 47.5547 | 52.6479 |
| 2011-11 | 1,386 | 688 | 49.6392 | 47.0116 | 52.2688 |
| 2011-12 | 1,289 | 651 | 50.5043 | 47.7774 | 53.2281 |
| 2012-01 | 1,589 | 797 | 50.1573 | 47.7015 | 52.6124 |
| 2012-02 | 1,789 | 905 | 50.5869 | 48.2714 | 52.8999 |
| 2012-03 | 2,192 | 1,182 | 53.9234 | 51.8316 | 56.0014 |
| 2012-04 | 2,589 | 1,371 | 52.9548 | 51.0292 | 54.8716 |
| 2012-05 | 3,325 | 1,695 | 50.9774 | 49.2781 | 52.6745 |
| 2012-06 | 3,867 | 1,619 | 41.8671 | 40.321 | 43.4293 |
| 2012-07 | 4,582 | 1,866 | 40.7246 | 39.3103 | 42.1544 |
| 2012-08 | 4,476 | 1,953 | 43.6327 | 42.1859 | 45.0904 |
| 2012-09 | 4,035 | 1,810 | 44.8575 | 43.3285 | 46.3962 |
| 2012-10 | 3,828 | 1,641 | 42.8683 | 41.3085 | 44.4424 |
| 2012-11 | 3,706 | 1,530 | 41.2844 | 39.7091 | 42.8778 |
| 2012-12 | 3,484 | 1,380 | 39.6096 | 37.9979 | 41.2443 |
| 2013-01 | 4,418 | 1,859 | 42.0779 | 40.6296 | 43.5399 |
| 2013-02 | 4,362 | 1,961 | 44.9564 | 43.4853 | 46.4365 |
| 2013-03 | 5,421 | 2,434 | 44.8995 | 43.5795 | 46.2267 |
| 2013-04 | 5,855 | 2,531 | 43.228 | 41.9639 | 44.501 |
| 2013-05 | 6,721 | 2,910 | 43.2971 | 42.1167 | 44.4852 |
| 2013-06 | 6,765 | 2,879 | 42.5573 | 41.3836 | 43.7394 |
| 2013-07 | 7,950 | 3,340 | 42.0126 | 40.9317 | 43.1012 |
| 2013-08 | 8,369 | 3,474 | 41.5103 | 40.4588 | 42.5697 |
| 2013-09 | 9,125 | 3,365 | 36.8767 | 35.8925 | 37.872 |
| 2013-10 | 7,862 | 3,153 | 40.1043 | 39.026 | 41.1922 |
| 2013-11 | 7,751 | 2,906 | 37.4919 | 36.4207 | 38.5756 |
| 2013-12 | 8,361 | 3,072 | 36.742 | 35.7149 | 37.7813 |
| 2014-01 | 11,111 | 4,142 | 37.2784 | 36.3838 | 38.1817 |
| 2014-02 | 9,967 | 3,888 | 39.0087 | 38.0555 | 39.9704 |
| 2014-03 | 12,058 | 4,622 | 38.3314 | 37.4674 | 39.2028 |
| 2014-04 | 12,689 | 4,901 | 38.624 | 37.7804 | 39.4745 |
| 2014-05 | 14,895 | 5,754 | 38.6304 | 37.8515 | 39.4152 |
| 2014-06 | 15,746 | 5,932 | 37.6731 | 36.9193 | 38.4328 |

### Độ trễ trong các cohort tháng gần cuối train

So 2014-01 đến 2014-06 để xem khác biệt trong các booking đã quan sát. Không gán thời gian theo dõi cho NDF từ phân phối dương; tỷ lệ trong ba cột horizon có mẫu số valid_observed_bookings.

**Cohort 2014: NDF và mức bao phủ booking quan sát**

| account_month | users | ndf_users | valid_observed_bookings | within30_pct_of_observed | within60_pct_of_observed | within90_pct_of_observed | max_observed_lag_days |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2014-01 | 11,111 | 6,969 | 4,142 | 70.7388 | 76.7986 | 80.9754 | 365 |
| 2014-02 | 9,967 | 6,079 | 3,888 | 73.8426 | 78.8837 | 82.2274 | 365 |
| 2014-03 | 12,058 | 7,436 | 4,622 | 73.9074 | 79.4894 | 82.7997 | 365 |
| 2014-04 | 12,689 | 7,788 | 4,901 | 73.7605 | 79.6368 | 83.3095 | 365 |
| 2014-05 | 14,895 | 9,141 | 5,754 | 75.0782 | 80.0487 | 83.2986 | 365 |
| 2014-06 | 15,746 | 9,814 | 5,932 | 74.8989 | 80.091 | 82.9231 | 365 |

## Tái lập và kiểm soát phạm vi

Notebook cần package scripts/ và năm CSV train_users_2.csv, test_users.csv, sessions.csv, countries.csv, age_gender_bkts.csv tại data/raw/AIRBNB/. Chỉ nộp một file notebook thì xem được output lưu sẵn, chưa thể chạy lại độc lập. Ô mở đầu notebook ghi cấu trúc thư mục và cách cài đúng các thư viện EDA; raw không được đính kèm repo.

Từ thư mục gốc chạy: python scripts/build_descriptive_reports.py --dataset AIRBNB. Hoặc mở notebook bằng Jupyter, Restart Kernel và Run All. Script chỉ đọc CSV raw, xuất Markdown, JSON, hình và notebook có output thật; không tạo data/processed, tập feature, tập chia train/test hay mô hình.

Ngày tải **không được lưu**, đã được người cung cấp xác nhận ngày 2026-11-02. Mã phiên bản Kaggle cũng chưa có bằng chứng. Không điền một ngày giả định: snapshot local được định danh bằng SHA-256 từng file và hash danh mục có thứ tự ở metadata. Ngày phân tích theo Asia/Ho_Chi_Minh khác với ngày tải.

Mọi bảng dùng toàn bộ user hoặc toàn bộ sessions có khóa hợp lệ trong phạm vi ghi cạnh bảng. Chỉ mẫu hình thiếu hiển thị tối đa 300 dòng, seed=42. Cramér V dùng chi-square không hiệu chỉnh Yates; p chi-square là xấp xỉ, kèm tỷ lệ ô kỳ vọng dưới 5. Mann–Whitney hai phía dùng xấp xỉ có hiệu chỉnh ties; rank-biserial = 2U/(n_booked × n_NDF) − 1. BH điều chỉnh 14 phép sàng lọc toàn kỳ; không áp dụng ngưỡng p để tự động chọn feature. Wilson 95% giả định user độc lập và không bao gồm sai lệch chọn mẫu/cohort. Không bootstrap, fit, tối ưu tham số hay tính chất lượng mô hình trong lần chạy EDA.

Output được tính lại trong lần phân tích hiện tại; môi trường dưới đây và SHA-256 ba module dựng báo cáo trong metadata nhận diện code đã chạy. Các đề xuất thuật toán, cửa sổ chia tập và ngưỡng chấp nhận chưa được thực thi.

**Môi trường thực thi chính xác**

| component | value |
| --- | --- |
| Python | 3.14.2 |
| pandas | 2.3.3 |
| numpy | 2.4.1 |
| matplotlib | 3.10.8 |
| Phương pháp | Thống kê mô tả, không mô hình |
| Chunk CSV lớn | 250000 |
| scipy | 1.17.1 |
| nbformat | 5.10.4 |
| IPython | 9.9.0 |
