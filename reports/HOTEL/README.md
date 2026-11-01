# HOTEL — Hiểu dữ liệu đặt phòng và kết quả hủy/no-show

> Phạm vi: EDA trên dữ liệu gốc. Không làm sạch/thay thế dữ liệu, không tạo tập feature, không huấn luyện mô hình.

Ngày phân tích: 2026-11-01. Đây không phải ngày thu thập dữ liệu.

## 1. Bối cảnh, quần thể và câu hỏi phân tích

Dữ liệu hiện có gồm **119,390 booking, 32 cột**, từ City Hotel và Resort Hotel. Mỗi dòng là một booking, không phải một khách hàng duy nhất. Không có booking ID hoặc customer ID để xác nhận danh tính, lịch sử khách hoặc nguyên nhân các dòng trùng.

**Bài toán phù hợp:** xác suất một booking có kết quả hủy/no-show. Không đồng nhất việc hủy một booking với customer churn. Mốc dự đoán (lúc tạo booking hay trước ngày đến) và tập booking còn có thể can thiệp chưa được xác lập; báo cáo chỉ đánh giá tính phù hợp dữ liệu, không ước lượng xác suất bằng mô hình.

Các câu hỏi EDA: nhãn thực sự gồm hành vi nào; khác biệt giữa hai khách sạn; mối liên hệ giữa nhãn và kênh/lead time; tác động của trùng lặp; độ phủ thời gian; biến nào tiết lộ kết quả hoặc chưa chứng minh có sẵn tại thời điểm dự đoán.

Nguồn nghiệp vụ: [Antonio, de Almeida & Nunes — Hotel booking demand datasets](https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/). Nguồn mô tả hai khách sạn tại Bồ Đào Nha và mốc trích xuất gắn với ngày trước ngày đến. Bản CSV trong dự án có thêm cột `hotel` để phân biệt hai cơ sở. Không suy rộng trực tiếp sang toàn ngành hoặc thị trường Việt Nam.

**Danh mục file gốc; data_lines đếm dòng sau header, đối chiếu số dòng pandas**

| file | data_lines | columns | bytes | sha256 |
| --- | --- | --- | --- | --- |
| hotel_bookings.csv | 119,390 | 32 | 16,855,599 | 7c2ae42a7353905ea136e5c2287f17c92c5435826598bfbb8491c6f0c7b1fc06 |

## 2. Từ điển dữ liệu và kiểu dữ liệu thực tế

Kiểu pandas không đồng nghĩa vai trò thống kê. `agent` và `company` được đọc như số nhưng là ID phân loại. Các cột lịch không phải các phép đo liên tục độc lập. Bảng dưới kiểm kê đủ 32 cột trên toàn bộ dữ liệu.

**Schema, độ đa dạng và missing**

| column | pandas_dtype | distinct_nonnull | missing_n | missing_pct | meaning | role_or_caution |
| --- | --- | --- | --- | --- | --- | --- |
| hotel | object | 2 | 0 | 0 | City Hotel / Resort Hotel | Phân khúc; chỉ hai cơ sở gốc, không đại diện toàn ngành |
| is_canceled | int64 | 2 | 0 | 0 | Nhãn kết quả booking, 0/1 | Target; dữ liệu hiện tại gộp Canceled và No-Show vào 1 |
| lead_time | int64 | 479 | 0 | 0 | Số ngày từ lúc nhập booking đến ngày đến | Kiểm tra mốc dự đoán và lịch sử thay đổi ngày đến |
| arrival_date_year | int64 | 3 | 0 | 0 | Năm đến dự kiến | Thời gian; không coi là đại lượng liên tục thông thường |
| arrival_date_month | object | 12 | 0 | 0 | Tháng đến dự kiến | Thời gian dạng tên tháng |
| arrival_date_week_number | int64 | 53 | 0 | 0 | Tuần của ngày đến | Thời gian, chồng lặp thông tin với ngày/tháng |
| arrival_date_day_of_month | int64 | 31 | 0 | 0 | Ngày trong tháng của ngày đến | Thời gian |
| stays_in_weekend_nights | int64 | 17 | 0 | 0 | Số đêm cuối tuần đặt/lưu trú | Số đếm; xác minh snapshot |
| stays_in_week_nights | int64 | 35 | 0 | 0 | Số đêm ngày thường đặt/lưu trú | Số đếm; xác minh snapshot |
| adults | int64 | 14 | 0 | 0 | Số người lớn | Kiểm tra 0 và số lượng lớn |
| children | float64 | 5 | 4 | 0.0034 | Số trẻ em | Có missing; không mặc định missing = 0 |
| babies | int64 | 5 | 0 | 0 | Số em bé | Số đếm |
| meal | object | 5 | 0 | 0 | Gói bữa ăn | Undefined/SC có thể có nghĩa không có gói ăn |
| country | object | 177 | 488 | 0.4087 | Quốc gia nguồn gốc khách | Mã phân loại; có thể cập nhật gần check-in |
| market_segment | object | 8 | 0 | 0 | Phân khúc thị trường | Biến phân loại |
| distribution_channel | object | 5 | 0 | 0 | Kênh phân phối | Biến phân loại; có liên hệ market_segment |
| is_repeated_guest | int64 | 2 | 0 | 0 | Khách quay lại, 0/1 | Đã tồn tại trong raw; không tạo lại feature |
| previous_cancellations | int64 | 15 | 0 | 0 | Số booking hủy trước booking hiện tại | Lịch sử; cần xác minh cách chốt thời gian |
| previous_bookings_not_canceled | int64 | 73 | 0 | 0 | Số booking trước không hủy | Lịch sử; cần xác minh cách chốt thời gian |
| reserved_room_type | object | 10 | 0 | 0 | Mã loại phòng đã đặt | Biến phân loại |
| assigned_room_type | object | 12 | 0 | 0 | Mã loại phòng được phân | Có thể cập nhật sau đặt; chưa chứng minh có sẵn tại t0 |
| booking_changes | int64 | 21 | 0 | 0 | Số lần sửa booking đến check-in/hủy | Biến tích lũy; nguy cơ dùng thông tin tương lai |
| deposit_type | object | 3 | 0 | 0 | Trạng thái đặt cọc từ thanh toán | Không mặc định đồng nghĩa chính sách đã biết lúc tạo booking |
| agent | float64 | 333 | 16,340 | 13.6862 | ID đại lý | Phân loại; NULL có thể là không áp dụng, không phải số liên tục |
| company | float64 | 352 | 112,593 | 94.3069 | ID công ty/thực thể trả tiền | Phân loại; NULL có thể là không áp dụng |
| days_in_waiting_list | int64 | 128 | 0 | 0 | Số ngày chờ trước xác nhận | Chỉ biết đầy đủ khi kết thúc chờ |
| customer_type | object | 4 | 0 | 0 | Contract / Group / Transient / Transient-Party | Biến phân loại |
| adr | float64 | 8,879 | 0 | 0 | Average Daily Rate, tiền/đêm | Theo nguồn là tổng giao dịch lưu trú / số đêm; xác minh thời điểm và đơn vị |
| required_car_parking_spaces | int64 | 5 | 0 | 0 | Số chỗ đỗ xe yêu cầu | Có thể cập nhật theo booking |
| total_of_special_requests | int64 | 6 | 0 | 0 | Số yêu cầu đặc biệt | Có thể cập nhật theo booking |
| reservation_status | object | 3 | 0 | 0 | Trạng thái cuối: Canceled / Check-Out / No-Show | Kết quả sau sự kiện; rò rỉ nhãn |
| reservation_status_date | object | 926 | 0 | 0 | Ngày thiết lập trạng thái cuối | Kết quả sau sự kiện; không dùng làm đầu vào dự đoán |

## 3. Chất lượng dữ liệu và định nghĩa nhãn

`is_canceled=1` có **44,224 booking (37.04%)**. Bảng chéo xác nhận nhãn này gồm cả `Canceled` và `No-Show`; nhãn 0 là `Check-Out`. Vì vậy tên mục tiêu trong báo cáo là **hủy/no-show**, thay vì chỉ hủy chủ động.

`reservation_status` tiết lộ hoàn toàn nhãn. `reservation_status_date` là ngày trạng thái cuối, cũng thuộc thông tin kết quả. Hai cột chỉ được dùng để hiểu dữ liệu.

`company`/`agent` có nhiều NULL; theo nghiên cứu gốc, NULL ở các cột này có thể nghĩa **không áp dụng**. Không coi các ID này là số liên tục hay mặc định thay NULL bằng trung vị. Với `children`/`country`, nguyên nhân thiếu chưa được xác minh từ CSV.

Nếu giả định loại tất cả dòng trùng, tỷ lệ nhãn 1 đổi từ **37.04%** thành **27.49%**. Đây là độ nhạy đáng kể, không phải chỉ định phải deduplicate. Không có khóa booking nên chưa phân biệt được lỗi lặp với các booking thật có cùng thuộc tính. Các dòng gốc vẫn được giữ nguyên.

ADR âm/cao hoặc booking 0 đêm/0 khách là trường hợp cần xác minh. CSV không chứng minh nguyên nhân là hoàn tiền, voucher hay nhập sai; không clipping hay xóa trong báo cáo.

**Kiểm tra bất thường (các điều kiện có thể chồng lặp)**

| check | n | pct_all_bookings |
| --- | --- | --- |
| Dòng trùng hoàn toàn; giữ lần xuất hiện đầu để đếm | 31,994 | 26.7979 |
| Tổng số khách bằng 0 sau quy ước missing children=0 chỉ để kiểm tra | 180 | 0.1508 |
| Tổng số đêm bằng 0 | 715 | 0.5989 |
| ADR âm | 1 | 0.0008 |
| ADR bằng 0 | 1,959 | 1.6408 |
| ADR > 1.000 (ngưỡng kiểm tra, không phải kết luận lỗi) | 1 | 0.0008 |
| Ngày đến không parse được | 0 | 0 |
| Nhãn ngoài {0,1} hoặc thiếu | 0 | 0 |

**Trạng thái cuối × nhãn**

| reservation_status | 0 | 1 |
| --- | --- | --- |
| Canceled | 0 | 43,017 |
| Check-Out | 75,166 | 0 |
| No-Show | 0 | 1,207 |

**Độ nhạy theo giả định về duplicate**

| scenario | n | positive | positive_pct |
| --- | --- | --- | --- |
| Raw: giữ nguyên | 119,390 | 44,224 | 37.0416 |
| Giả định bỏ mọi dòng trùng (chỉ phân tích độ nhạy) | 87,396 | 24,025 | 27.4898 |

## 4. Phân phối đơn biến và mức độ bao phủ

Thống kê định lượng dùng toàn bộ dữ liệu, bỏ NA riêng ở từng cột. p1/p95/p99 cho thấy phần đuôi mà mean/median có thể che khuất. Bảng category hiển thị top 8 mỗi biến, tỷ lệ luôn chia cho toàn bộ booking (kể cả missing), nên tổng top 8 có thể nhỏ hơn 100%. ADR trên biểu đồ chỉ giới hạn vùng nhìn; dữ liệu và thống kê không bị cắt.

**Thống kê định lượng toàn bộ**

| column | count | mean | std | min | 1% | 25% | 50% | 75% | 95% | 99% | max | missing_pct | skewness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lead_time | 119,390 | 104.0114 | 106.8631 | 0 | 0 | 18 | 69 | 160 | 320 | 444 | 737 | 0 | 1.3465 |
| stays_in_weekend_nights | 119,390 | 0.9276 | 0.9986 | 0 | 0 | 0 | 1 | 2 | 2 | 4 | 19 | 0 | 1.38 |
| stays_in_week_nights | 119,390 | 2.5003 | 1.9083 | 0 | 0 | 1 | 2 | 3 | 5 | 10 | 50 | 0 | 2.8622 |
| adults | 119,390 | 1.8564 | 0.5793 | 0 | 1 | 2 | 2 | 2 | 3 | 3 | 55 | 0 | 18.3178 |
| children | 119,386 | 0.1039 | 0.3986 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 10 | 0.0034 | 4.1126 |
| babies | 119,390 | 0.0079 | 0.0974 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 | 24.6465 |
| previous_cancellations | 119,390 | 0.0871 | 0.8443 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 26 | 0 | 24.458 |
| previous_bookings_not_canceled | 119,390 | 0.1371 | 1.4974 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 72 | 0 | 23.5398 |
| booking_changes | 119,390 | 0.2211 | 0.6523 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 21 | 0 | 6.0003 |
| days_in_waiting_list | 119,390 | 2.3211 | 17.5947 | 0 | 0 | 0 | 0 | 0 | 0 | 75 | 391 | 0 | 11.9444 |
| adr | 119,390 | 101.8311 | 50.5358 | -6.38 | 0 | 69.29 | 94.575 | 126 | 193.5 | 252 | 5,400 | 0 | 10.5302 |
| required_car_parking_spaces | 119,390 | 0.0625 | 0.2453 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 8 | 0 | 4.1632 |
| total_of_special_requests | 119,390 | 0.5714 | 0.7928 | 0 | 0 | 0 | 0 | 1 | 2 | 3 | 5 | 0 | 1.3492 |

**Phân bố phân loại — top 8/cột**

| column | value | n | pct_all_rows |
| --- | --- | --- | --- |
| hotel | City Hotel | 79,330 | 66.4461 |
| hotel | Resort Hotel | 40,060 | 33.5539 |
| market_segment | Online TA | 56,477 | 47.3046 |
| market_segment | Offline TA/TO | 24,219 | 20.2856 |
| market_segment | Groups | 19,811 | 16.5935 |
| market_segment | Direct | 12,606 | 10.5587 |
| market_segment | Corporate | 5,295 | 4.435 |
| market_segment | Complementary | 743 | 0.6223 |
| market_segment | Aviation | 237 | 0.1985 |
| market_segment | Undefined | 2 | 0.0017 |
| distribution_channel | TA/TO | 97,870 | 81.975 |
| distribution_channel | Direct | 14,645 | 12.2665 |
| distribution_channel | Corporate | 6,677 | 5.5926 |
| distribution_channel | GDS | 193 | 0.1617 |
| distribution_channel | Undefined | 5 | 0.0042 |
| deposit_type | No Deposit | 104,641 | 87.6464 |
| deposit_type | Non Refund | 14,587 | 12.2179 |
| deposit_type | Refundable | 162 | 0.1357 |
| customer_type | Transient | 89,613 | 75.0591 |
| customer_type | Transient-Party | 25,124 | 21.0436 |
| customer_type | Contract | 4,076 | 3.414 |
| customer_type | Group | 577 | 0.4833 |
| meal | BB | 92,310 | 77.318 |
| meal | HB | 14,463 | 12.1141 |
| meal | SC | 10,650 | 8.9203 |
| meal | Undefined | 1,169 | 0.9791 |
| meal | FB | 798 | 0.6684 |
| country | PRT | 48,590 | 40.6986 |
| country | GBR | 12,129 | 10.1591 |
| country | FRA | 10,415 | 8.7235 |
| country | ESP | 8,568 | 7.1765 |
| country | DEU | 7,287 | 6.1035 |
| country | ITA | 3,766 | 3.1544 |
| country | IRL | 3,375 | 2.8269 |
| country | BEL | 2,342 | 1.9616 |
| reserved_room_type | A | 85,994 | 72.0278 |
| reserved_room_type | D | 19,201 | 16.0826 |
| reserved_room_type | E | 6,535 | 5.4737 |
| reserved_room_type | F | 2,897 | 2.4265 |
| reserved_room_type | G | 2,094 | 1.7539 |
| reserved_room_type | B | 1,118 | 0.9364 |
| reserved_room_type | C | 932 | 0.7806 |
| reserved_room_type | H | 601 | 0.5034 |
| assigned_room_type | A | 74,053 | 62.0261 |
| assigned_room_type | D | 25,322 | 21.2095 |
| assigned_room_type | E | 7,806 | 6.5382 |
| assigned_room_type | F | 3,751 | 3.1418 |
| assigned_room_type | G | 2,553 | 2.1384 |
| assigned_room_type | C | 2,375 | 1.9893 |
| assigned_room_type | B | 2,163 | 1.8117 |
| assigned_room_type | H | 712 | 0.5964 |
| is_repeated_guest | 0 | 115,580 | 96.8088 |
| is_repeated_guest | 1 | 3,810 | 3.1912 |

![distributions](figures/distributions.png)

## 5. Mối liên hệ với nhãn và tương tác phân khúc

Mẫu số là booking trong từng nhóm; không phải tỷ trọng nhóm trong toàn dữ liệu. Các khoảng Wilson 95% là mô tả tham khảo dưới giả định quan sát độc lập; duplicate, booking theo đoàn và khách lặp có thể làm mức bất định thực tế lớn hơn. Nhóm dưới 100 quan sát được gắn cờ, không xếp hạng chắc chắn. Các liên hệ không phải tác động nhân quả của kênh, đặt cọc hoặc thời gian đặt trước. Bảng hotel × market_segment giúp kiểm tra việc khác cơ cấu khách giữa hai cơ sở.

**Tỷ lệ nhãn 1 theo hotel**

| hotel | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| City Hotel | 79,330 | 33,102 | 41.727 | 41.3842 | 42.0705 | 0 |
| Resort Hotel | 40,060 | 11,122 | 27.7634 | 27.327 | 28.204 | 0 |

**Tỷ lệ nhãn 1 theo market_segment**

| market_segment | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| Online TA | 56,477 | 20,739 | 36.7211 | 36.3245 | 37.1196 | 0 |
| Offline TA/TO | 24,219 | 8,311 | 34.316 | 33.7206 | 34.9164 | 0 |
| Groups | 19,811 | 12,097 | 61.062 | 60.381 | 61.7388 | 0 |
| Direct | 12,606 | 1,934 | 15.3419 | 14.7233 | 15.9816 | 0 |
| Corporate | 5,295 | 992 | 18.7347 | 17.7065 | 19.8082 | 0 |
| Complementary | 743 | 97 | 13.0552 | 10.8215 | 15.669 | 0 |
| Aviation | 237 | 52 | 21.9409 | 17.1427 | 27.6342 | 0 |
| Undefined | 2 | 2 | 100 | 34.238 | 100 | 1 |

**Tỷ lệ nhãn 1 theo distribution_channel**

| distribution_channel | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| TA/TO | 97,870 | 40,152 | 41.0259 | 40.718 | 41.3344 | 0 |
| Direct | 14,645 | 2,557 | 17.4599 | 16.8536 | 18.0832 | 0 |
| Corporate | 6,677 | 1,474 | 22.0758 | 21.0972 | 23.0865 | 0 |
| GDS | 193 | 37 | 19.171 | 14.2407 | 25.3046 | 0 |
| Undefined | 5 | 4 | 80 | 37.5535 | 96.3776 | 1 |

**Tỷ lệ nhãn 1 theo deposit_type**

| deposit_type | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| No Deposit | 104,641 | 29,694 | 28.377 | 28.1047 | 28.651 | 0 |
| Non Refund | 14,587 | 14,494 | 99.3624 | 99.2197 | 99.4792 | 0 |
| Refundable | 162 | 36 | 22.2222 | 16.5057 | 29.2256 | 0 |

**Tỷ lệ nhãn 1 theo customer_type**

| customer_type | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| Transient | 89,613 | 36,514 | 40.7463 | 40.425 | 41.0684 | 0 |
| Transient-Party | 25,124 | 6,389 | 25.4299 | 24.8952 | 25.9721 | 0 |
| Contract | 4,076 | 1,262 | 30.9617 | 29.5609 | 32.3984 | 0 |
| Group | 577 | 59 | 10.2253 | 8.0104 | 12.9663 | 0 |

**Tỷ lệ nhãn 1 theo is_repeated_guest**

| is_repeated_guest | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 115,580 | 43,672 | 37.7851 | 37.506 | 38.065 | 0 |
| 1 | 3,810 | 552 | 14.4882 | 13.4063 | 15.6416 | 0 |

**Tỷ lệ nhãn 1 theo country**

| country | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| PRT | 48,590 | 27,519 | 56.6351 | 56.194 | 57.0752 | 0 |
| GBR | 12,129 | 2,453 | 20.2243 | 19.5189 | 20.9485 | 0 |
| FRA | 10,415 | 1,934 | 18.5694 | 17.8342 | 19.3277 | 0 |
| ESP | 8,568 | 2,177 | 25.4085 | 24.4978 | 26.3412 | 0 |
| DEU | 7,287 | 1,218 | 16.7147 | 15.8756 | 17.5888 | 0 |
| ITA | 3,766 | 1,333 | 35.3956 | 33.884 | 36.9371 | 0 |
| IRL | 3,375 | 832 | 24.6519 | 23.2272 | 26.1342 | 0 |
| BEL | 2,342 | 474 | 20.2391 | 18.6612 | 21.9145 | 0 |
| BRA | 2,224 | 830 | 37.3201 | 35.3335 | 39.3505 | 0 |
| NLD | 2,104 | 387 | 18.3935 | 16.7962 | 20.1061 | 0 |
| USA | 2,097 | 501 | 23.8913 | 22.115 | 25.7631 | 0 |
| CHE | 1,730 | 428 | 24.7399 | 22.764 | 26.8277 | 0 |
| CN | 1,279 | 254 | 19.8593 | 17.7646 | 22.1345 | 0 |
| AUT | 1,263 | 230 | 18.2106 | 16.1796 | 20.4344 | 0 |
| SWE | 1,024 | 227 | 22.168 | 19.7305 | 24.8135 | 0 |

**Lead time — nhóm chỉ phục vụ thống kê EDA**

| lead_time_group | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| 31–90 | 29,553 | 11,141 | 37.6984 | 37.1475 | 38.2525 | 0 |
| 91–180 | 26,439 | 11,821 | 44.7105 | 44.112 | 45.3105 | 0 |
| 181–365 | 21,544 | 11,947 | 55.454 | 54.7894 | 56.1166 | 0 |
| 8–30 | 18,960 | 5,283 | 27.8639 | 27.2303 | 28.5065 | 0 |
| 1–7 | 13,401 | 1,472 | 10.9843 | 10.466 | 11.5249 | 0 |
| 0 | 6,345 | 430 | 6.777 | 6.1843 | 7.422 | 0 |
| >365 | 3,148 | 2,130 | 67.662 | 66.0073 | 69.2737 | 0 |

**Đối chiếu phân khúc trong từng khách sạn**

| hotel | market_segment | n | positive | positive_pct |
| --- | --- | --- | --- | --- |
| City Hotel | Aviation | 237 | 52 | 21.9409 |
| City Hotel | Complementary | 542 | 64 | 11.8081 |
| City Hotel | Corporate | 2,986 | 641 | 21.4668 |
| City Hotel | Direct | 6,093 | 1,056 | 17.3314 |
| City Hotel | Groups | 13,975 | 9,623 | 68.8587 |
| City Hotel | Offline TA/TO | 16,747 | 7,173 | 42.8316 |
| City Hotel | Online TA | 38,748 | 14,491 | 37.3981 |
| City Hotel | Undefined | 2 | 2 | 100 |
| Resort Hotel | Complementary | 201 | 33 | 16.4179 |
| Resort Hotel | Corporate | 2,309 | 351 | 15.2014 |
| Resort Hotel | Direct | 6,513 | 878 | 13.4807 |
| Resort Hotel | Groups | 5,836 | 2,474 | 42.392 |
| Resort Hotel | Offline TA/TO | 7,472 | 1,138 | 15.2302 |
| Resort Hotel | Online TA | 17,729 | 6,248 | 35.2417 |

![target by hotel](figures/target_by_hotel.png)

## 6. Thời gian, mùa vụ và giới hạn đánh giá

Ngày đến parse được nằm trong **2015-07-01–2017-08-31**. Đây là thời gian ngày đến, không phải thời gian tạo booking. Các tháng đầu/cuối không bao phủ đủ năm, nên không gộp số booking theo tên tháng rồi kết luận mùa vụ. Đồ thị dưới giữ năm–tháng và tách hai khách sạn. Chưa đủ cơ sở để chọn một cách chia tập cuối cùng: cần định nghĩa t0, nhãn đã trưởng thành và đối tượng còn có thể can thiệp; nếu đánh giá tương lai thì ưu tiên giữ trật tự thời gian, đồng thời kiểm tra duplicate qua các tập.

**Toàn bộ năm–tháng × khách sạn**

| year_month | hotel | n | positive | positive_pct |
| --- | --- | --- | --- | --- |
| 2015-07 | City Hotel | 1,398 | 939 | 67.1674 |
| 2015-07 | Resort Hotel | 1,378 | 320 | 23.2221 |
| 2015-08 | City Hotel | 2,480 | 1,232 | 49.6774 |
| 2015-08 | Resort Hotel | 1,409 | 366 | 25.9759 |
| 2015-09 | City Hotel | 3,529 | 1,543 | 43.7234 |
| 2015-09 | Resort Hotel | 1,585 | 551 | 34.7634 |
| 2015-10 | City Hotel | 3,386 | 1,321 | 39.0136 |
| 2015-10 | Resort Hotel | 1,571 | 411 | 26.1617 |
| 2015-11 | City Hotel | 1,235 | 301 | 24.3725 |
| 2015-11 | Resort Hotel | 1,105 | 185 | 16.7421 |
| 2015-12 | City Hotel | 1,654 | 668 | 40.3869 |
| 2015-12 | Resort Hotel | 1,266 | 305 | 24.0916 |
| 2016-01 | City Hotel | 1,364 | 438 | 32.1114 |
| 2016-01 | Resort Hotel | 884 | 119 | 13.4615 |
| 2016-02 | City Hotel | 2,371 | 930 | 39.224 |
| 2016-02 | Resort Hotel | 1,520 | 407 | 26.7763 |
| 2016-03 | City Hotel | 3,046 | 1,108 | 36.3756 |
| 2016-03 | Resort Hotel | 1,778 | 369 | 20.7537 |
| 2016-04 | City Hotel | 3,561 | 1,539 | 43.2182 |
| 2016-04 | Resort Hotel | 1,867 | 522 | 27.9593 |
| 2016-05 | City Hotel | 3,676 | 1,436 | 39.0642 |
| 2016-05 | Resort Hotel | 1,802 | 479 | 26.5816 |
| 2016-06 | City Hotel | 3,923 | 1,720 | 43.844 |
| 2016-06 | Resort Hotel | 1,369 | 376 | 27.4653 |
| 2016-07 | City Hotel | 3,131 | 1,043 | 33.312 |
| 2016-07 | Resort Hotel | 1,441 | 456 | 31.6447 |
| 2016-08 | City Hotel | 3,378 | 1,247 | 36.9153 |
| 2016-08 | Resort Hotel | 1,685 | 578 | 34.3027 |
| 2016-09 | City Hotel | 3,871 | 1,567 | 40.4805 |
| 2016-09 | Resort Hotel | 1,523 | 455 | 29.8752 |
| 2016-10 | City Hotel | 4,219 | 1,947 | 46.1484 |
| 2016-10 | Resort Hotel | 1,984 | 567 | 28.5786 |
| 2016-11 | City Hotel | 3,122 | 1,360 | 43.5618 |
| 2016-11 | Resort Hotel | 1,332 | 276 | 20.7207 |
| 2016-12 | City Hotel | 2,478 | 1,072 | 43.2607 |
| 2016-12 | Resort Hotel | 1,382 | 326 | 23.589 |
| 2017-01 | City Hotel | 2,372 | 1,044 | 44.0135 |
| 2017-01 | Resort Hotel | 1,309 | 206 | 15.7372 |
| 2017-02 | City Hotel | 2,594 | 971 | 37.4325 |
| 2017-02 | Resort Hotel | 1,583 | 388 | 24.5104 |
| 2017-03 | City Hotel | 3,412 | 1,278 | 37.456 |
| 2017-03 | Resort Hotel | 1,558 | 394 | 25.2888 |
| 2017-04 | City Hotel | 3,919 | 1,926 | 49.1452 |
| 2017-04 | Resort Hotel | 1,742 | 537 | 30.8266 |
| 2017-05 | City Hotel | 4,556 | 2,217 | 48.6611 |
| 2017-05 | Resort Hotel | 1,757 | 545 | 31.0188 |
| 2017-06 | City Hotel | 3,971 | 1,808 | 45.5301 |
| 2017-06 | Resort Hotel | 1,676 | 631 | 37.6492 |
| 2017-07 | City Hotel | 3,559 | 1,324 | 37.2015 |
| 2017-07 | Resort Hotel | 1,754 | 660 | 37.6283 |
| 2017-08 | City Hotel | 3,125 | 1,123 | 35.936 |
| 2017-08 | Resort Hotel | 1,800 | 693 | 38.5 |

![calendar](figures/calendar.png)

## 7. Phụ thuộc giữa các biến

Bảng Spearman là tương quan cặp giữa các biến số gốc, dùng các cặp không thiếu. Các phép đo nhiều giá trị 0, category được mã hóa bằng số và dữ liệu lặp có thể làm cách diễn giải khác thường. Không dùng bảng này để tự động loại biến. `market_segment` và `distribution_channel` có thể mô tả chồng lặp; bảng chéo bên dưới kiểm tra cấu trúc thay vì xem hai cột độc lập.

**12 cặp số có |rho| lớn nhất trong danh sách công bố**

| column_a | column_b | spearman_rho |
| --- | --- | --- |
| lead_time | stays_in_week_nights | 0.2963 |
| adults | adr | 0.2798 |
| children | adr | 0.2655 |
| stays_in_weekend_nights | stays_in_week_nights | 0.2381 |
| adults | previous_bookings_not_canceled | -0.2096 |
| adr | total_of_special_requests | 0.1964 |
| lead_time | adults | 0.1922 |
| lead_time | previous_bookings_not_canceled | -0.1886 |
| lead_time | previous_cancellations | 0.1708 |
| lead_time | stays_in_weekend_nights | 0.1621 |
| adults | total_of_special_requests | 0.1616 |
| stays_in_week_nights | adults | 0.153 |

**Market segment × distribution channel**

| market_segment | Corporate | Direct | GDS | TA/TO | Undefined |
| --- | --- | --- | --- | --- | --- |
| Aviation | 227 | 0 | 0 | 10 | 0 |
| Complementary | 89 | 576 | 0 | 78 | 0 |
| Corporate | 4,788 | 172 | 0 | 335 | 0 |
| Direct | 90 | 12,276 | 1 | 237 | 2 |
| Groups | 1,228 | 1,472 | 0 | 17,111 | 0 |
| Offline TA/TO | 212 | 16 | 45 | 23,946 | 0 |
| Online TA | 43 | 133 | 147 | 56,153 | 1 |
| Undefined | 0 | 0 | 0 | 0 | 2 |

## 8. Kết luận và câu hỏi còn mở

**Kết luận đã kiểm chứng:** nhãn 1 chiếm 37.04%, gồm hủy và no-show; có 31,994 dòng trùng hoàn toàn; tỷ lệ thay đổi mạnh theo giả định bỏ trùng; hai cơ sở và các kênh có cơ cấu khác nhau. Thông tin trạng thái cuối không thể là đầu vào dự đoán.

**Mức độ phù hợp:** tốt cho nghiên cứu cancellation/no-show ở cấp booking. Chưa đủ để mô tả churn ở cấp khách hàng hoặc mô phỏng chấm điểm ngay lúc tạo booking một cách đáng tin cậy.

**Cần xác minh trước giai đoạn tiếp theo:** (1) thời điểm chấm điểm và tập booking còn hiệu lực; (2) lịch sử giá trị tại t0 cho từng biến, nhất là assigned_room_type, booking_changes, deposit_type, ADR và yêu cầu bổ sung; (3) định danh booking/nhóm để giải thích trùng; (4) ý nghĩa các booking 0 khách/0 đêm và ADR bất thường; (5) phạm vi áp dụng ngoài hai khách sạn.

Không xóa dòng, impute, clipping, encoding, tạo feature hoặc train model trong báo cáo này. Các phân nhóm ngày/tháng và lead time chỉ là bảng thống kê EDA; không được xuất thành tập huấn luyện.

## Tái lập và kiểm soát phạm vi

Chạy notebook theo thứ tự từ đầu, hoặc chạy `python scripts/build_descriptive_reports.py` tại thư mục gốc để dựng lại toàn bộ. Script chỉ đọc CSV raw, viết báo cáo/biểu đồ và lưu notebook trong notebooks/; không sửa raw, không ghi data/processed, không gọi pipeline huấn luyện. Các thời điểm phân tích dùng Asia/Ho_Chi_Minh. SHA-256 ở danh mục file nhận diện nguồn; số dòng theo CSV parser được đối chiếu với data_lines của file chính. Các bảng nhóm chỉ sống trong bộ nhớ để tính EDA. Script thực thi các cell bằng IPython trong cùng tiến trình và lưu output thật vào notebook; không khởi tạo kernel mạng. Phụ thuộc dựng báo cáo gồm pandas, numpy, matplotlib, nbformat và IPython; có thể mở notebook bằng Jupyter để Run All.

**Môi trường thực thi**

| component | value |
| --- | --- |
| Python | 3.14.2 |
| pandas | 2.3.3 |
| numpy | 2.4.1 |
| matplotlib | 3.10.8 |
| Phương pháp | Thống kê mô tả, không mô hình |
| Chunk CSV lớn | 250000 |
