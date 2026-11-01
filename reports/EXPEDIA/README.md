# EXPEDIA — Hiểu tìm kiếm, click và booking ở cấp khách sạn hiển thị

> Phạm vi: EDA trên dữ liệu gốc. Không làm sạch/thay thế dữ liệu, không tạo tập feature, không huấn luyện mô hình.

Ngày phân tích: 2026-11-01. Đây không phải ngày thu thập dữ liệu.

## 1. Nguồn, đơn vị quan sát và câu hỏi propensity

Schema hiện có thuộc [Personalize Expedia Hotel Searches — ICDM 2013](https://www.kaggle.com/c/expedia-personalized-sort/data), khác cuộc thi Expedia Hotel Recommendations dự đoán hotel cluster. Train có **9,917,530 dòng, 54 cột**; test có **6,622,629 dòng, 50 cột**. Mỗi dòng là một cặp **search–property**, không phải một khách hàng hoặc một lượt search độc lập.

Hai nhãn là `click_bool` và `booking_bool`. Phù hợp với click/booking propensity trong ngữ cảnh danh sách tìm kiếm, hoặc nghiên cứu xếp hạng. Không có ID người dùng để trực tiếp hình thành bài toán CRM theo khách hàng; `srch_id` chỉ định danh lượt tìm kiếm.

Câu hỏi EDA: cấu trúc nhóm, quan hệ click–booking, khác biệt tỷ lệ theo ngữ cảnh/khách sạn/vị trí, thiếu dữ liệu theo nhóm cột, khác train–test, và giới hạn suy rộng tỷ lệ từ tập dữ liệu quan sát.

**Danh mục file; ba benchmark là thứ tự kết quả trên test, không phải dữ liệu train bổ sung**

| file | data_lines | columns | bytes | sha256 |
| --- | --- | --- | --- | --- |
| basicPythonBenchmark.csv | 6,622,629 | 2 | 92,985,279 | 7de0c115bd3a2a90bc9db65f4679233c0088a2b334868a6b06dde7af08d5a485 |
| randomBenchmark.csv | 6,622,629 | 2 | 92,985,279 | 5f28a62102d125a406cdd397181205b4b7af8ceb417e6e964ca16b13aeb01b5f |
| test.csv | 6,622,629 | 50 | 1,496,916,672 | be1d56681726315393c829f7c94f85d4f8c886748a903e6ec120bb8080538205 |
| testOrderBenchmark.csv | 6,622,629 | 2 | 92,985,279 | 42ecaf9f4bbca6ed62be0e3199523151e513584d39fa5d47adb752a5c7d76adf |
| train.csv | 9,917,530 | 54 | 2,358,114,793 | 84a53139ea92df1e9400f84852facbd78f3136f366a08440f4ab4518e71a49a9 |

## 2. Từ điển đủ 54 cột và schema train–test

Các ID được đọc thành số nhưng mang ý nghĩa phân loại. Nhóm đối thủ có **8 × 3 = 24 cột**, không phải 16. Bốn cột chỉ có ở train là position, click_bool, booking_bool, gross_bookings_usd. Sau khi tách bốn cột này, có 50 cột chung với test; đây là số cột schema, chưa phải số feature được phê duyệt sử dụng. Nếu srch_id chỉ làm khóa nhóm thì còn 49 cột ứng viên; prop_id vẫn cần quyết định cách dùng phù hợp ở giai đoạn sau.

**Schema và missing toàn bộ train**

| column | pandas_dtype | full_missing_n | full_missing_pct | in_test | meaning | role_or_caution |
| --- | --- | --- | --- | --- | --- | --- |
| srch_id | int64 | 0 | 0 | 1 | ID lượt tìm kiếm | Khóa nhóm, không phải ID người dùng |
| date_time | object | 0 | 0 | 1 | Thời điểm tìm kiếm | Thời gian, không giả định timezone không được công bố |
| site_id | int64 | 0 | 0 | 1 | ID website/điểm bán Expedia | Phân loại |
| visitor_location_country_id | int64 | 0 | 0 | 1 | ID quốc gia vị trí người tìm | Phân loại, không phải mã có thứ tự |
| visitor_hist_starrating | float64 | 9,412,233 | 94.905 | 1 | Mức sao trung bình trong lịch sử khách | NA không đủ chứng minh khách mới/chưa đăng nhập |
| visitor_hist_adr_usd | float64 | 9,409,918 | 94.8817 | 1 | ADR lịch sử của khách, USD | Cần xác minh cửa sổ lịch sử và cách tính |
| prop_country_id | int64 | 0 | 0 | 1 | ID quốc gia khách sạn | Phân loại |
| prop_id | int64 | 0 | 0 | 1 | ID khách sạn | Thực thể có thể lặp qua searches; không phải số liên tục |
| prop_starrating | int64 | 0 | 0 | 1 | Hạng sao khách sạn | 0 cần xác minh nghĩa; không tự xem là 0 sao chất lượng thấp |
| prop_review_score | float64 | 14,630 | 0.1475 | 1 | Điểm review khách sạn | 0 và NA là hai trường hợp cần phân biệt |
| prop_brand_bool | int64 | 0 | 0 | 1 | Cờ thuộc thương hiệu/chuỗi | Nhị phân; cố định nhãn 0/1 khi vẽ |
| prop_location_score1 | float64 | 0 | 0 | 1 | Điểm vị trí thứ nhất | Thước đo do nguồn cung cấp |
| prop_location_score2 | float64 | 2,178,380 | 21.9649 | 1 | Điểm vị trí thứ hai | Thước đo do nguồn cung cấp; có NA |
| prop_log_historical_price | float64 | 0 | 0 | 1 | Log giá lịch sử khách sạn | Không tự khôi phục tiền khi chưa biết cơ số/cách tính |
| position | int64 | 0 | 0 | 0 | Vị trí hiển thị quan sát được | Có trong train, không có trong test; có ảnh hưởng vị trí |
| price_usd | float64 | 0 | 0 | 1 | Giá hiển thị cho khách sạn trong search, USD | Cần xác minh đơn vị giá theo đêm/toàn kỳ; có đuôi cực lớn |
| promotion_flag | int64 | 0 | 0 | 1 | Cờ hiển thị khuyến mãi | Liên hệ quan sát không chứng minh tác động khuyến mãi |
| srch_destination_id | int64 | 0 | 0 | 1 | ID điểm đến tìm kiếm | Phân loại |
| srch_length_of_stay | int64 | 0 | 0 | 1 | Số đêm lưu trú tìm kiếm | Số đếm |
| srch_booking_window | int64 | 0 | 0 | 1 | Số ngày từ search đến ngày đến | Đơn vị ngày |
| srch_adults_count | int64 | 0 | 0 | 1 | Số người lớn trong search | Số đếm |
| srch_children_count | int64 | 0 | 0 | 1 | Số trẻ em trong search | Số đếm |
| srch_room_count | int64 | 0 | 0 | 1 | Số phòng trong search | Số đếm |
| srch_saturday_night_bool | int64 | 0 | 0 | 1 | Cờ kỳ lưu trú có đêm thứ Bảy | Nhị phân |
| srch_query_affinity_score | float64 | 9,281,966 | 93.5915 | 1 | Điểm liên quan query–property do nguồn cung cấp | Cần xác minh cách sinh và tính sẵn có |
| orig_destination_distance | float64 | 3,216,461 | 32.4321 | 1 | Khoảng cách nguồn–điểm đến theo nguồn | Đơn vị cần xác minh; không tự gán km |
| random_bool | int64 | 0 | 0 | 1 | Cờ danh sách được sắp ngẫu nhiên | Phân tích ảnh hưởng vị trí; không tự suy ra exposure propensity |
| comp1_rate | float64 | 9,681,724 | 97.6223 | 1 | So sánh giá với đối thủ 1, mã phân loại | Không coi mã -1/0/1 là giá; xác minh hướng so sánh theo nguồn |
| comp1_inv | float64 | 9,663,097 | 97.4345 | 1 | So sánh tồn phòng với đối thủ 1 | Mã phân loại; NA không phải không có đối thủ |
| comp1_rate_percent_diff | float64 | 9,732,623 | 98.1356 | 1 | Chênh lệch giá phần trăm đối thủ 1 | NA có thể theo điều kiện sinh dữ liệu; xác minh mẫu số/hướng |
| comp2_rate | float64 | 5,876,897 | 59.2577 | 1 | So sánh giá với đối thủ 2, mã phân loại | Không coi mã -1/0/1 là giá; xác minh hướng so sánh theo nguồn |
| comp2_inv | float64 | 5,665,992 | 57.1311 | 1 | So sánh tồn phòng với đối thủ 2 | Mã phân loại; NA không phải không có đối thủ |
| comp2_rate_percent_diff | float64 | 8,807,683 | 88.8092 | 1 | Chênh lệch giá phần trăm đối thủ 2 | NA có thể theo điều kiện sinh dữ liệu; xác minh mẫu số/hướng |
| comp3_rate | float64 | 6,858,257 | 69.1529 | 1 | So sánh giá với đối thủ 3, mã phân loại | Không coi mã -1/0/1 là giá; xác minh hướng so sánh theo nguồn |
| comp3_inv | float64 | 6,625,309 | 66.804 | 1 | So sánh tồn phòng với đối thủ 3 | Mã phân loại; NA không phải không có đối thủ |
| comp3_rate_percent_diff | float64 | 8,973,523 | 90.4814 | 1 | Chênh lệch giá phần trăm đối thủ 3 | NA có thể theo điều kiện sinh dữ liệu; xác minh mẫu số/hướng |
| comp4_rate | float64 | 9,297,431 | 93.7474 | 1 | So sánh giá với đối thủ 4, mã phân loại | Không coi mã -1/0/1 là giá; xác minh hướng so sánh theo nguồn |
| comp4_inv | float64 | 9,225,059 | 93.0177 | 1 | So sánh tồn phòng với đối thủ 4 | Mã phân loại; NA không phải không có đối thủ |
| comp4_rate_percent_diff | float64 | 9,653,317 | 97.3359 | 1 | Chênh lệch giá phần trăm đối thủ 4 | NA có thể theo điều kiện sinh dữ liệu; xác minh mẫu số/hướng |
| comp5_rate | float64 | 5,473,236 | 55.1875 | 1 | So sánh giá với đối thủ 5, mã phân loại | Không coi mã -1/0/1 là giá; xác minh hướng so sánh theo nguồn |
| comp5_inv | float64 | 5,196,697 | 52.3991 | 1 | So sánh tồn phòng với đối thủ 5 | Mã phân loại; NA không phải không có đối thủ |
| comp5_rate_percent_diff | float64 | 8,236,524 | 83.0502 | 1 | Chênh lệch giá phần trăm đối thủ 5 | NA có thể theo điều kiện sinh dữ liệu; xác minh mẫu số/hướng |
| comp6_rate | float64 | 9,435,043 | 95.135 | 1 | So sánh giá với đối thủ 6, mã phân loại | Không coi mã -1/0/1 là giá; xác minh hướng so sánh theo nguồn |
| comp6_inv | float64 | 9,393,385 | 94.715 | 1 | So sánh tồn phòng với đối thủ 6 | Mã phân loại; NA không phải không có đối thủ |
| comp6_rate_percent_diff | float64 | 9,724,218 | 98.0508 | 1 | Chênh lệch giá phần trăm đối thủ 6 | NA có thể theo điều kiện sinh dữ liệu; xác minh mẫu số/hướng |
| comp7_rate | float64 | 9,286,453 | 93.6368 | 1 | So sánh giá với đối thủ 7, mã phân loại | Không coi mã -1/0/1 là giá; xác minh hướng so sánh theo nguồn |
| comp7_inv | float64 | 9,204,355 | 92.8089 | 1 | So sánh tồn phòng với đối thủ 7 | Mã phân loại; NA không phải không có đối thủ |
| comp7_rate_percent_diff | float64 | 9,639,692 | 97.1985 | 1 | Chênh lệch giá phần trăm đối thủ 7 | NA có thể theo điều kiện sinh dữ liệu; xác minh mẫu số/hướng |
| comp8_rate | float64 | 6,098,487 | 61.492 | 1 | So sánh giá với đối thủ 8, mã phân loại | Không coi mã -1/0/1 là giá; xác minh hướng so sánh theo nguồn |
| comp8_inv | float64 | 5,957,142 | 60.0668 | 1 | So sánh tồn phòng với đối thủ 8 | Mã phân loại; NA không phải không có đối thủ |
| comp8_rate_percent_diff | float64 | 8,691,823 | 87.641 | 1 | Chênh lệch giá phần trăm đối thủ 8 | NA có thể theo điều kiện sinh dữ liệu; xác minh mẫu số/hướng |
| click_bool | int64 | 0 | 0 | 0 | Khách sạn có click trong search, 0/1 | Target/biến kết quả; không dùng click tương lai dự đoán trước click |
| gross_bookings_usd | float64 | 9,640,938 | 97.2111 | 0 | Giá trị booking ghi nhận, USD | Kết quả sau booking; presence gần như tiết lộ nhãn |
| booking_bool | int64 | 0 | 0 | 0 | Khách sạn được book trong search, 0/1 | Target |

## 3. Phương pháp tính: toàn bộ dữ liệu và mẫu nhóm

**Toàn bộ train và test được quét theo chunk 250,000 dòng.** Số dòng/nhóm, missing, tỷ lệ nhãn, thống kê mean/std/min/max, phân bố category, bảng nhóm và chuỗi thời gian đều được cộng dồn trên toàn file; không thay toàn bộ dữ liệu bằng 500.000 dòng đầu.

**Chỉ các percentile và biểu đồ phân phối trên mẫu** dùng mẫu xác định bằng `hash_pandas_object(srch_id, index=False) % 20 == 0`, tỷ lệ mục tiêu khoảng 5%. Tất cả khách sạn cùng srch_id được giữ cùng nhau, kể cả khi nhóm vượt ranh giới chunk. Mẫu train thực tế có **493,340 dòng / 19,841 searches**. Đây là mẫu nhóm bằng hàm băm có thể tái lập, không khẳng định đại diện tuyệt đối hoặc là lấy mẫu ngẫu nhiên đơn từng dòng. Thuật toán hash phụ thuộc phiên bản pandas nên môi trường được ghi ở cuối báo cáo.

Giá trị `sample_p*` được gắn nhãn riêng, không trộn với thống kê `full_*`. Khóa ghép (srch_id,prop_id) được kiểm tra trùng bằng cặp ID thật, không dùng va chạm hash để kết luận duplicate. Danh mục file có SHA-256 để nhận diện đúng phiên bản nguồn.

**Đối chiếu mẫu nhóm với toàn bộ train**

| population | rows | searches | click_pct | booking_pct |
| --- | --- | --- | --- | --- |
| train: toàn bộ | 9,917,530 | 399,344 | 4.4736 | 2.7889 |
| train: mẫu hash theo nhóm | 493,340 | 19,841 | 4.4847 | 2.7802 |

## 4. Cấu trúc nhóm, nhãn và giới hạn quần thể

Train gồm **399,344 searches**, trung bình **24.83 khách sạn/search**. Có **0 search không click** trong tập train. Vì vậy tập đang phân tích không có nhóm search hoàn toàn không tương tác; không ước lượng tỷ lệ mọi người dùng trên website quyết định click từ tỷ lệ 4–5% trên các dòng này.

Trong raw, mọi booking đều có click ở cùng cặp search–property; tỷ số bookings/clicks là thống kê có điều kiện đúng trên tập hiện tại. Nó không chứng minh việc làm tăng click sẽ gây tăng booking, không tự xác lập chiến lược marketing hay hiệu quả triển khai.

`gross_bookings_usd` là thông tin sau booking. Giá trị hiện diện chỉ ở dòng có booking; có 1 booking bị thiếu gross. Không impute cột kết quả này thành feature. `position` là vị trí hiển thị quan sát được và không có trong test. Click thực tế không phải đầu vào hợp lệ của mô hình dự đoán trước click.

Các dòng trong một search phụ thuộc nhau. Vì vậy không đưa khoảng tin cậy nhị thức giả định mọi impression độc lập; nếu cần suy luận ở giai đoạn sau, phải xét cấu trúc nhóm. Nhóm khóa không trùng không đồng nghĩa người dùng độc lập vì không có user ID.

**Kích thước danh sách theo search**

| population | searches | mean_properties | median_properties | min_properties | max_properties | searches_multiple_timestamps |
| --- | --- | --- | --- | --- | --- | --- |
| train | 399,344 | 24.8346 | 29 | 5 | 38 | 0 |
| test | 266,230 | 24.8756 | 29 | 5 | 37 | 0 |

**Kiểm tra khóa và tính nhất quán kết quả**

| check | n |
| --- | --- |
| Train: cặp srch_id-prop_id trùng (beyond first) | 0 |
| Test: cặp srch_id-prop_id trùng | 0 |
| srch_id xuất hiện cả train và test | 0 |
| prop_id xuất hiện cả train và test | 128,953 |
| Train: search không click | 0 |
| Train: search có >1 booking | 0 |
| Train: booking=1 nhưng click=0 | 0 |
| Train: booking=1 nhưng gross thiếu | 1 |
| Train: booking=0 nhưng gross có giá trị | 0 |
| Train: nhãn ngoài {0,1} hoặc thiếu | 0 |

**Tỷ lệ với tử số/mẫu số cụ thể — toàn bộ train**

| metric | numerator | denominator | pct |
| --- | --- | --- | --- |
| Click / cặp search-property | 443,672 | 9,917,530 | 4.4736 |
| Booking / cặp search-property | 276,593 | 9,917,530 | 2.7889 |
| Booking / cặp đã click | 276,593 | 443,672 | 62.3418 |
| Search có booking / toàn bộ search train | 276,593 | 399,344 | 69.2618 |

## 5. Missing, giá trị đặc biệt và chất lượng giá

Missing được trình bày đủ các cột ở phần schema, với so sánh train–test bên dưới. Nhóm comp có mức thiếu rất khác nhau theo đối thủ và loại thuộc tính; không suy từ top 15 cột thiếu nhiều nhất rằng cả nhóm đều thiếu >93%. Không có dữ liệu đối thủ không chứng minh khách sạn không có đối thủ. Thiếu lịch sử khách không đủ để kết luận khách mới/chưa đăng nhập. Giá 0 và giá cực lớn được định lượng bằng ngưỡng kiểm tra công bố trước; không tự kết luận lỗi, đổi đơn vị hoặc clipping. Định nghĩa giá theo đêm/toàn kỳ chưa được xác minh từ CSV.

**Toàn bộ 24 cột đối thủ — missing theo tập**

| column | train_missing_pct | test_missing_pct |
| --- | --- | --- |
| comp1_rate | 97.6223 | 97.6586 |
| comp1_inv | 97.4345 | 97.4743 |
| comp1_rate_percent_diff | 98.1356 | 98.156 |
| comp2_rate | 59.2577 | 59.2359 |
| comp2_inv | 57.1311 | 57.1107 |
| comp2_rate_percent_diff | 88.8092 | 88.7749 |
| comp3_rate | 69.1529 | 69.3113 |
| comp3_inv | 66.804 | 66.9643 |
| comp3_rate_percent_diff | 90.4814 | 90.5214 |
| comp4_rate | 93.7474 | 93.6915 |
| comp4_inv | 93.0177 | 92.9642 |
| comp4_rate_percent_diff | 97.3359 | 97.3044 |
| comp5_rate | 55.1875 | 55.0628 |
| comp5_inv | 52.3991 | 52.2728 |
| comp5_rate_percent_diff | 83.0502 | 83.0126 |
| comp6_rate | 95.135 | 95.0981 |
| comp6_inv | 94.715 | 94.668 |
| comp6_rate_percent_diff | 98.0508 | 98.0237 |
| comp7_rate | 93.6368 | 93.5586 |
| comp7_inv | 92.8089 | 92.7243 |
| comp7_rate_percent_diff | 97.1985 | 97.1561 |
| comp8_rate | 61.492 | 61.5682 |
| comp8_inv | 60.0668 | 60.1375 |
| comp8_rate_percent_diff | 87.641 | 87.6574 |

**Missing các cột ngoài comp**

| column | train_missing_pct | test_missing_pct |
| --- | --- | --- |
| srch_id | 0 | 0 |
| date_time | 0 | 0 |
| site_id | 0 | 0 |
| visitor_location_country_id | 0 | 0 |
| visitor_hist_starrating | 94.905 | 94.8589 |
| visitor_hist_adr_usd | 94.8817 | 94.8282 |
| prop_country_id | 0 | 0 |
| prop_id | 0 | 0 |
| prop_starrating | 0 | 0 |
| prop_review_score | 0.1475 | 0.1442 |
| prop_brand_bool | 0 | 0 |
| prop_location_score1 | 0 | 0 |
| prop_location_score2 | 21.9649 | 21.9689 |
| prop_log_historical_price | 0 | 0 |
| position | 0 | — |
| price_usd | 0 | 0 |
| promotion_flag | 0 | 0 |
| srch_destination_id | 0 | 0 |
| srch_length_of_stay | 0 | 0 |
| srch_booking_window | 0 | 0 |
| srch_adults_count | 0 | 0 |
| srch_children_count | 0 | 0 |
| srch_room_count | 0 | 0 |
| srch_saturday_night_bool | 0 | 0 |
| srch_query_affinity_score | 93.5915 | 93.5774 |
| orig_destination_distance | 32.4321 | 32.4334 |
| random_bool | 0 | 0 |
| click_bool | 0 | — |
| gross_bookings_usd | 97.2111 | — |
| booking_bool | 0 | — |

**Kiểm tra đuôi giá trên toàn bộ dữ liệu**

| population | rows | price_zero | price_negative | price_above_1000 | price_above_10000 |
| --- | --- | --- | --- | --- | --- |
| train | 9,917,530 | 54 | 0 | 27,018 | 3,936 |
| test | 6,622,629 | 80 | 0 | 17,251 | 2,628 |

## 6. Phân phối định lượng và phân loại

Các cột full_* dùng toàn bộ dữ liệu. Các cột sample_p* là percentile trên mẫu nhóm đã mô tả, không phải percentile chính xác toàn bộ file. Mean/std có thể rất nhạy với giá cực lớn; đọc cùng median/p95/p99 trên mẫu và full max. Tỷ trọng category dưới đây tính theo cặp search-property, không phải tỷ trọng khách hoặc tỷ trọng search; search có nhiều khách sạn đóng góp nhiều dòng hơn.

**Train: thống kê toàn bộ và percentile mẫu có nhãn riêng**

| column | full_count_nonnull | full_mean | full_std | full_min | full_max | sample_p1 | sample_p25 | sample_p50 | sample_p75 | sample_p95 | sample_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| visitor_hist_starrating | 505,297 | 3.3746 | 0.6922 | 1 | 5 | 2 | 2.83 | 3.44 | 3.93 | 4.49 | 5 |
| visitor_hist_adr_usd | 507,612 | 176.5885 | 108.4348 | 0 | 2,768.93 | 47.21 | 112.76 | 150.93 | 207.8 | 358.75 | 579.1 |
| prop_starrating | 9,917,530 | 3.1815 | 1.0502 | 0 | 5 | 0 | 3 | 3 | 4 | 5 | 5 |
| prop_review_score | 9,902,900 | 3.7777 | 1.0508 | 0 | 5 | 0 | 3.5 | 4 | 4.5 | 4.5 | 5 |
| prop_location_score1 | 9,917,530 | 2.876 | 1.5321 | 0 | 6.98 | 0 | 1.79 | 2.77 | 4.06 | 5.58 | 6.32 |
| prop_location_score2 | 7,739,150 | 0.1304 | 0.1595 | 0 | 1 | 0.0003 | 0.019 | 0.0689 | 0.1787 | 0.4775 | 0.7194 |
| prop_log_historical_price | 9,917,530 | 4.3168 | 1.8362 | 0 | 6.21 | 0 | 4.45 | 4.92 | 5.32 | 5.93 | 6.21 |
| price_usd | 9,917,530 | 241.7825 | 14,341.8095 | 0 | 19,726,328 | 33.44 | 85 | 122 | 185.8 | 356 | 597 |
| srch_length_of_stay | 9,917,530 | 2.39 | 2.0668 | 1 | 59 | 1 | 1 | 2 | 3 | 6 | 10 |
| srch_booking_window | 9,917,530 | 37.6238 | 52.108 | 0 | 498 | 0 | 4 | 17 | 50 | 155 | 244 |
| srch_adults_count | 9,917,530 | 1.9726 | 0.8591 | 1 | 9 | 1 | 2 | 2 | 2 | 4 | 5 |
| srch_children_count | 9,917,530 | 0.3487 | 0.7297 | 0 | 9 | 0 | 0 | 0 | 0 | 2 | 3 |
| srch_room_count | 9,917,530 | 1.1108 | 0.4241 | 1 | 8 | 1 | 1 | 1 | 1 | 2 | 3 |
| srch_query_affinity_score | 635,564 | -24.3028 | 15.808 | -326.5675 | -2.4941 | -76.0285 | -31.221 | -20.4839 | -13.6876 | -8.2257 | -4.9802 |
| orig_destination_distance | 6,701,069 | 1,307.018 | 2,030.2826 | 0.01 | 11,692.98 | 1.02 | 143.81 | 402.49 | 1,580.85 | 5,960.08 | 9,732.262 |

**Test: cùng phương pháp thống kê**

| column | full_count_nonnull | full_mean | full_std | full_min | full_max | sample_p1 | sample_p25 | sample_p50 | sample_p75 | sample_p95 | sample_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| visitor_hist_starrating | 340,476 | 3.3564 | 0.6912 | 1 | 5 | 2 | 2.88 | 3.33 | 3.86 | 4.5 | 5 |
| visitor_hist_adr_usd | 342,511 | 174.5589 | 106.9481 | 0 | 1,654.92 | 29.95 | 105.65 | 148.8 | 210.38 | 351.31 | 632.18 |
| prop_starrating | 6,622,629 | 3.1824 | 1.0484 | 0 | 5 | 0 | 3 | 3 | 4 | 5 | 5 |
| prop_review_score | 6,613,080 | 3.78 | 1.0479 | 0 | 5 | 0 | 3.5 | 4 | 4.5 | 4.5 | 5 |
| prop_location_score1 | 6,622,629 | 2.8814 | 1.5332 | 0 | 6.98 | 0 | 1.79 | 2.77 | 4.04 | 5.58 | 6.31 |
| prop_location_score2 | 5,167,707 | 0.1305 | 0.1595 | 0 | 1 | 0.0003 | 0.0192 | 0.0691 | 0.1779 | 0.4703 | 0.7148 |
| prop_log_historical_price | 6,622,629 | 4.3164 | 1.8355 | 0 | 6.21 | 0 | 4.45 | 4.91 | 5.32 | 5.93 | 6.21 |
| price_usd | 6,622,629 | 213.0988 | 8,332.4874 | 0 | 5,513,008 | 34.9284 | 85 | 121.61 | 184 | 352 | 589 |
| srch_length_of_stay | 6,622,629 | 2.3845 | 2.0462 | 1 | 50 | 1 | 1 | 2 | 3 | 6 | 10 |
| srch_booking_window | 6,622,629 | 37.5551 | 51.9371 | 0 | 498 | 0 | 4 | 16 | 48 | 151 | 244 |
| srch_adults_count | 6,622,629 | 1.9732 | 0.863 | 1 | 9 | 1 | 2 | 2 | 2 | 4 | 5 |
| srch_children_count | 6,622,629 | 0.3456 | 0.7262 | 0 | 9 | 0 | 0 | 0 | 0 | 2 | 3 |
| srch_room_count | 6,622,629 | 1.1113 | 0.4294 | 1 | 8 | 1 | 1 | 1 | 1 | 2 | 3 |
| srch_query_affinity_score | 425,344 | -24.0337 | 15.3296 | -307.9764 | -2.4941 | -83.8874 | -30.8649 | -20.7264 | -13.4135 | -7.1886 | -4.5398 |
| orig_destination_distance | 4,474,686 | 1,302.1814 | 2,030.6995 | 0.01 | 12,047.99 | 0.8 | 136.445 | 374.33 | 1,441.755 | 5,906.107 | 9,533.6638 |

**Top 12 category/cột — toàn bộ train**

| column | value | n | pct_all_rows |
| --- | --- | --- | --- |
| site_id | 5 | 6,164,803 | 62.1607 |
| site_id | 14 | 964,105 | 9.7212 |
| site_id | 15 | 618,620 | 6.2376 |
| site_id | 24 | 475,893 | 4.7985 |
| site_id | 32 | 355,805 | 3.5876 |
| site_id | 18 | 258,751 | 2.609 |
| site_id | 16 | 181,436 | 1.8294 |
| site_id | 12 | 148,636 | 1.4987 |
| site_id | 19 | 82,566 | 0.8325 |
| site_id | 9 | 82,298 | 0.8298 |
| site_id | 22 | 82,135 | 0.8282 |
| site_id | 11 | 69,698 | 0.7028 |
| visitor_location_country_id | 219 | 5,778,805 | 58.2686 |
| visitor_location_country_id | 100 | 990,487 | 9.9872 |
| visitor_location_country_id | 55 | 580,072 | 5.849 |
| visitor_location_country_id | 216 | 434,568 | 4.3818 |
| visitor_location_country_id | 220 | 350,433 | 3.5335 |
| visitor_location_country_id | 129 | 250,828 | 2.5291 |
| visitor_location_country_id | 31 | 185,743 | 1.8729 |
| visitor_location_country_id | 99 | 137,151 | 1.3829 |
| visitor_location_country_id | 59 | 123,412 | 1.2444 |
| visitor_location_country_id | 92 | 93,280 | 0.9406 |
| visitor_location_country_id | 158 | 86,076 | 0.8679 |
| visitor_location_country_id | 103 | 71,313 | 0.7191 |
| prop_country_id | 219 | 6,052,976 | 61.0331 |
| prop_country_id | 100 | 622,810 | 6.2799 |
| prop_country_id | 55 | 376,219 | 3.7935 |
| prop_country_id | 31 | 309,434 | 3.1201 |
| prop_country_id | 99 | 268,393 | 2.7062 |
| prop_country_id | 129 | 185,182 | 1.8672 |
| prop_country_id | 215 | 161,447 | 1.6279 |
| prop_country_id | 220 | 141,443 | 1.4262 |
| prop_country_id | 59 | 138,254 | 1.394 |
| prop_country_id | 216 | 123,954 | 1.2498 |
| prop_country_id | 98 | 113,229 | 1.1417 |
| prop_country_id | 158 | 81,817 | 0.825 |
| prop_starrating | 3 | 3,897,419 | 39.2983 |
| prop_starrating | 4 | 3,045,848 | 30.7118 |
| prop_starrating | 2 | 1,788,994 | 18.0387 |
| prop_starrating | 5 | 812,961 | 8.1972 |
| prop_starrating | 0 | 337,794 | 3.406 |
| prop_starrating | 1 | 34,514 | 0.348 |
| prop_brand_bool | 1 | 6,290,731 | 63.4304 |
| prop_brand_bool | 0 | 3,626,799 | 36.5696 |
| promotion_flag | 0 | 7,777,708 | 78.4238 |
| promotion_flag | 1 | 2,139,822 | 21.5762 |
| srch_saturday_night_bool | 1 | 4,961,307 | 50.0256 |
| srch_saturday_night_bool | 0 | 4,956,223 | 49.9744 |
| random_bool | 0 | 6,977,878 | 70.359 |
| random_bool | 1 | 2,939,652 | 29.641 |

![distributions](figures/distributions.png)

## 7. Mối liên hệ với click/booking theo nhóm

Tất cả bảng dùng toàn bộ train. Phân nhóm giá và booking window chỉ là công cụ đọc bảng EDA; không xuất feature. Tỷ lệ có thể phản ánh vị trí hiển thị, thành phần search, thương hiệu, thời gian và cơ chế chọn mẫu cùng lúc. Không coi chênh lệch promotion_flag là uplift từ khuyến mãi. Bảng không kiểm định nhiều giả thuyết hoặc khẳng định quan hệ nhân quả.

**Tỷ lệ click/booking theo prop_starrating; mẫu số là số cặp trong nhóm**

| prop_starrating | n | clicks | bookings | click_pct | booking_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 337,794 | 9,792 | 5,582 | 2.8988 | 1.6525 | 0 |
| 1 | 34,514 | 965 | 439 | 2.796 | 1.2719 | 0 |
| 2 | 1,788,994 | 60,596 | 38,892 | 3.3872 | 2.174 | 0 |
| 3 | 3,897,419 | 170,869 | 109,049 | 4.3842 | 2.798 | 0 |
| 4 | 3,045,848 | 164,118 | 101,691 | 5.3883 | 3.3387 | 0 |
| 5 | 812,961 | 37,332 | 20,940 | 4.5921 | 2.5758 | 0 |

**Tỷ lệ click/booking theo prop_brand_bool; mẫu số là số cặp trong nhóm**

| prop_brand_bool | n | clicks | bookings | click_pct | booking_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 3,626,799 | 160,997 | 92,903 | 4.4391 | 2.5616 | 0 |
| 1 | 6,290,731 | 282,675 | 183,690 | 4.4935 | 2.92 | 0 |

**Tỷ lệ click/booking theo promotion_flag; mẫu số là số cặp trong nhóm**

| promotion_flag | n | clicks | bookings | click_pct | booking_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 7,777,708 | 314,417 | 192,672 | 4.0425 | 2.4772 | 0 |
| 1 | 2,139,822 | 129,255 | 83,921 | 6.0405 | 3.9219 | 0 |

**Tỷ lệ click/booking theo srch_saturday_night_bool; mẫu số là số cặp trong nhóm**

| srch_saturday_night_bool | n | clicks | bookings | click_pct | booking_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 4,956,223 | 220,576 | 133,726 | 4.4505 | 2.6981 | 0 |
| 1 | 4,961,307 | 223,096 | 142,867 | 4.4967 | 2.8796 | 0 |

**Tỷ lệ click/booking theo site_id; mẫu số là số cặp trong nhóm**

| site_id | n | clicks | bookings | click_pct | booking_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 22,298 | 1,115 | 596 | 5.0004 | 2.6729 | 0 |
| 2 | 11,875 | 569 | 296 | 4.7916 | 2.4926 | 0 |
| 3 | 7,015 | 363 | 184 | 5.1746 | 2.623 | 0 |
| 4 | 27,243 | 1,327 | 644 | 4.871 | 2.3639 | 0 |
| 5 | 6,164,803 | 267,356 | 173,575 | 4.3368 | 2.8156 | 0 |
| 6 | 4,807 | 292 | 120 | 6.0745 | 2.4964 | 0 |
| 7 | 64,157 | 2,948 | 2,237 | 4.595 | 3.4868 | 0 |
| 8 | 62 | 2 | 1 | 3.2258 | 1.6129 | 1 |
| 9 | 82,298 | 3,949 | 1,934 | 4.7984 | 2.35 | 0 |
| 10 | 19,346 | 888 | 421 | 4.5901 | 2.1762 | 0 |
| 11 | 69,698 | 3,187 | 1,886 | 4.5726 | 2.706 | 0 |
| 12 | 148,636 | 7,216 | 3,702 | 4.8548 | 2.4906 | 0 |
| 13 | 17,372 | 918 | 423 | 5.2844 | 2.435 | 0 |
| 14 | 964,105 | 42,664 | 26,830 | 4.4252 | 2.7829 | 0 |
| 15 | 618,620 | 28,000 | 17,451 | 4.5262 | 2.821 | 0 |
| 16 | 181,436 | 8,535 | 4,494 | 4.7041 | 2.4769 | 0 |
| 17 | 12,377 | 698 | 296 | 5.6395 | 2.3915 | 0 |
| 18 | 258,751 | 12,719 | 6,713 | 4.9155 | 2.5944 | 0 |
| 19 | 82,566 | 4,798 | 1,706 | 5.8111 | 2.0662 | 0 |
| 20 | 248 | 11 | 10 | 4.4355 | 4.0323 | 0 |
| 21 | 7,471 | 346 | 197 | 4.6312 | 2.6369 | 0 |
| 22 | 82,135 | 4,165 | 2,247 | 5.0709 | 2.7357 | 0 |
| 23 | 24,128 | 1,168 | 658 | 4.8408 | 2.7271 | 0 |
| 24 | 475,893 | 22,953 | 14,354 | 4.8231 | 3.0162 | 0 |
| 25 | 24,764 | 1,182 | 585 | 4.7731 | 2.3623 | 0 |
| 26 | 33,291 | 1,668 | 882 | 5.0104 | 2.6494 | 0 |
| 27 | 9,669 | 461 | 395 | 4.7678 | 4.0852 | 0 |
| 28 | 8,988 | 485 | 178 | 5.3961 | 1.9804 | 0 |
| 29 | 59,011 | 2,760 | 1,572 | 4.6771 | 2.6639 | 0 |
| 30 | 7,047 | 372 | 190 | 5.2788 | 2.6962 | 0 |
| 31 | 50,009 | 2,402 | 2,188 | 4.8031 | 4.3752 | 0 |
| 32 | 355,805 | 17,058 | 9,098 | 4.7942 | 2.557 | 0 |
| 33 | 1,355 | 78 | 23 | 5.7565 | 1.6974 | 0 |
| 34 | 20,251 | 1,019 | 507 | 5.0319 | 2.5036 | 0 |

**Tỷ lệ click/booking theo price_group; mẫu số là số cặp trong nhóm**

| price_group | n | clicks | bookings | click_pct | booking_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| <=0 | 54 | 3 | 3 | 5.5556 | 5.5556 | 1 |
| (0,50] | 476,747 | 21,119 | 12,987 | 4.4298 | 2.7241 | 0 |
| (50,100] | 3,122,427 | 148,113 | 99,943 | 4.7435 | 3.2008 | 0 |
| (100,150] | 2,731,429 | 131,984 | 84,533 | 4.832 | 3.0948 | 0 |
| (150,250] | 2,326,363 | 101,679 | 59,608 | 4.3707 | 2.5623 | 0 |
| (250,500] | 1,089,425 | 36,566 | 18,092 | 3.3564 | 1.6607 | 0 |
| (500,1000] | 144,067 | 3,353 | 1,110 | 2.3274 | 0.7705 | 0 |
| >1000 | 27,018 | 855 | 317 | 3.1646 | 1.1733 | 0 |

**Tỷ lệ click/booking theo window_group; mẫu số là số cặp trong nhóm**

| window_group | n | clicks | bookings | click_pct | booking_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| <=0 | 556,154 | 24,235 | 19,161 | 4.3576 | 3.4453 | 0 |
| 1–7 | 2,833,346 | 126,553 | 89,579 | 4.4666 | 3.1616 | 0 |
| 8–30 | 2,950,085 | 131,739 | 82,929 | 4.4656 | 2.8111 | 0 |
| 31–90 | 2,345,949 | 105,136 | 58,437 | 4.4816 | 2.491 | 0 |
| 91–180 | 924,791 | 41,695 | 20,353 | 4.5086 | 2.2008 | 0 |
| 181–365 | 304,402 | 14,132 | 6,069 | 4.6425 | 1.9937 | 0 |
| >365 | 2,803 | 182 | 65 | 6.493 | 2.3189 | 0 |

## 8. Vị trí hiển thị và cơ chế tiếp xúc

`position` và `random_bool` cần được đọc cùng nhau: khách sạn được hiển thị ở vị trí khác nhau có cơ hội được xem/click khác nhau. Biểu đồ mô tả liên hệ trong từng giá trị cờ; không ước lượng tác động nhân quả của vị trí, xác suất exposure hoặc áp dụng hiệu chỉnh bias. Theo [nghiên cứu dùng dữ liệu Expedia](https://hamsabastani.github.io/proxies.pdf), random_bool=1 đánh dấu danh sách được sắp ngẫu nhiên; vẫn cần xác minh định nghĩa và quy trình tạo tập trước khi suy luận can thiệp. Không dùng position làm feature mặc định cho schema test hiện có.

**Toàn bộ random_bool × position, giữ số dòng mỗi ô**

| random_bool | position | n | clicks | bookings | click_pct | booking_pct |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 1 | 277,662 | 59,827 | 54,126 | 21.5467 | 19.4935 |
| 0 | 2 | 277,652 | 40,678 | 35,974 | 14.6507 | 12.9565 |
| 0 | 3 | 277,622 | 31,088 | 27,062 | 11.198 | 9.7478 |
| 0 | 4 | 266,073 | 24,500 | 21,057 | 9.208 | 7.914 |
| 0 | 5 | 16,672 | 321 | 199 | 1.9254 | 1.1936 |
| 0 | 6 | 277,308 | 19,837 | 16,885 | 7.1534 | 6.0889 |
| 0 | 7 | 271,435 | 16,238 | 13,657 | 5.9823 | 5.0314 |
| 0 | 8 | 265,486 | 13,722 | 11,479 | 5.1686 | 4.3238 |
| 0 | 9 | 259,865 | 11,499 | 9,527 | 4.425 | 3.6661 |
| 0 | 10 | 237,876 | 10,018 | 8,266 | 4.2114 | 3.4749 |
| 0 | 11 | 20,337 | 153 | 68 | 0.7523 | 0.3344 |
| 0 | 12 | 249,246 | 8,683 | 7,134 | 3.4837 | 2.8622 |
| 0 | 13 | 244,658 | 7,641 | 6,169 | 3.1231 | 2.5215 |
| 0 | 14 | 239,642 | 6,720 | 5,442 | 2.8042 | 2.2709 |
| 0 | 15 | 234,762 | 6,203 | 4,985 | 2.6423 | 2.1234 |
| 0 | 16 | 212,417 | 5,301 | 4,275 | 2.4956 | 2.0126 |
| 0 | 17 | 20,557 | 85 | 32 | 0.4135 | 0.1557 |
| 0 | 18 | 225,419 | 4,873 | 3,869 | 2.1618 | 1.7164 |
| 0 | 19 | 220,940 | 4,366 | 3,477 | 1.9761 | 1.5737 |
| 0 | 20 | 216,469 | 3,973 | 3,147 | 1.8354 | 1.4538 |
| 0 | 21 | 211,938 | 3,674 | 2,861 | 1.7335 | 1.3499 |
| 0 | 22 | 190,234 | 3,162 | 2,437 | 1.6622 | 1.2811 |
| 0 | 23 | 19,674 | 59 | 22 | 0.2999 | 0.1118 |
| 0 | 24 | 202,691 | 3,051 | 2,357 | 1.5052 | 1.1629 |
| 0 | 25 | 198,022 | 2,676 | 2,114 | 1.3514 | 1.0676 |
| 0 | 26 | 193,411 | 2,490 | 1,957 | 1.2874 | 1.0118 |
| 0 | 27 | 188,936 | 2,375 | 1,825 | 1.257 | 0.9659 |
| 0 | 28 | 184,559 | 2,090 | 1,619 | 1.1324 | 0.8772 |
| 0 | 29 | 179,912 | 1,865 | 1,430 | 1.0366 | 0.7948 |
| 0 | 30 | 174,730 | 1,737 | 1,321 | 0.9941 | 0.756 |
| 0 | 31 | 168,703 | 1,606 | 1,225 | 0.952 | 0.7261 |
| 0 | 32 | 159,192 | 1,427 | 1,071 | 0.8964 | 0.6728 |
| 0 | 33 | 150,677 | 1,294 | 1,005 | 0.8588 | 0.667 |
| 0 | 34 | 142,218 | 1,217 | 930 | 0.8557 | 0.6539 |
| 0 | 35 | 127,223 | 1,003 | 744 | 0.7884 | 0.5848 |
| 0 | 36 | 99,323 | 727 | 576 | 0.732 | 0.5799 |
| 0 | 37 | 55,520 | 401 | 315 | 0.7223 | 0.5674 |
| 0 | 38 | 16,424 | 119 | 96 | 0.7245 | 0.5845 |
| 0 | 39 | 2,293 | 16 | 12 | 0.6978 | 0.5233 |
| 0 | 40 | 100 | 1 | 1 | 1 | 1 |
| 1 | 1 | 120,907 | 17,171 | 2,227 | 14.2018 | 1.8419 |
| 1 | 2 | 120,814 | 13,056 | 1,749 | 10.8067 | 1.4477 |
| 1 | 3 | 120,862 | 10,962 | 1,505 | 9.0698 | 1.2452 |
| 1 | 4 | 120,354 | 9,414 | 1,202 | 7.8219 | 0.9987 |
| 1 | 5 | 1,928 | 108 | 14 | 5.6017 | 0.7261 |
| 1 | 6 | 120,792 | 8,446 | 1,036 | 6.9922 | 0.8577 |
| 1 | 7 | 117,788 | 7,223 | 885 | 6.1322 | 0.7513 |
| 1 | 8 | 114,876 | 6,298 | 718 | 5.4824 | 0.625 |
| 1 | 9 | 112,146 | 5,784 | 641 | 5.1576 | 0.5716 |
| 1 | 10 | 108,891 | 5,105 | 605 | 4.6882 | 0.5556 |
| 1 | 11 | 1,990 | 42 | 4 | 2.1106 | 0.201 |
| 1 | 12 | 107,088 | 4,621 | 544 | 4.3151 | 0.508 |
| 1 | 13 | 104,762 | 4,265 | 474 | 4.0711 | 0.4525 |
| 1 | 14 | 102,376 | 3,864 | 432 | 3.7743 | 0.422 |
| 1 | 15 | 100,146 | 3,596 | 386 | 3.5908 | 0.3854 |
| 1 | 16 | 96,956 | 3,418 | 328 | 3.5253 | 0.3383 |
| 1 | 17 | 1,941 | 13 | 0 | 0.6698 | 0 |
| 1 | 18 | 95,593 | 3,037 | 318 | 3.177 | 0.3327 |
| 1 | 19 | 93,463 | 2,854 | 278 | 3.0536 | 0.2974 |
| 1 | 20 | 91,379 | 2,806 | 261 | 3.0707 | 0.2856 |
| 1 | 21 | 89,204 | 2,505 | 231 | 2.8082 | 0.259 |
| 1 | 22 | 86,184 | 2,365 | 206 | 2.7441 | 0.239 |
| 1 | 23 | 1,781 | 19 | 2 | 1.0668 | 0.1123 |
| 1 | 24 | 84,954 | 2,197 | 219 | 2.5861 | 0.2578 |
| 1 | 25 | 82,742 | 1,999 | 179 | 2.4159 | 0.2163 |
| 1 | 26 | 80,651 | 1,992 | 200 | 2.4699 | 0.248 |
| 1 | 27 | 78,535 | 1,815 | 163 | 2.3111 | 0.2076 |
| 1 | 28 | 76,412 | 1,718 | 161 | 2.2483 | 0.2107 |
| 1 | 29 | 74,179 | 1,606 | 123 | 2.165 | 0.1658 |
| 1 | 30 | 71,690 | 1,544 | 114 | 2.1537 | 0.159 |
| 1 | 31 | 69,025 | 1,478 | 148 | 2.1413 | 0.2144 |
| 1 | 32 | 64,381 | 1,298 | 115 | 2.0161 | 0.1786 |
| 1 | 33 | 60,834 | 1,269 | 113 | 2.086 | 0.1858 |
| 1 | 34 | 56,515 | 1,117 | 94 | 1.9765 | 0.1663 |
| 1 | 35 | 48,503 | 939 | 80 | 1.936 | 0.1649 |
| 1 | 36 | 34,954 | 619 | 50 | 1.7709 | 0.143 |
| 1 | 37 | 18,293 | 316 | 29 | 1.7274 | 0.1585 |
| 1 | 38 | 4,952 | 65 | 9 | 1.3126 | 0.1817 |
| 1 | 39 | 781 | 12 | 2 | 1.5365 | 0.2561 |
| 1 | 40 | 30 | 0 | 0 | 0 | 0 |

![position](figures/position.png)

## 9. Thời gian và so sánh train–test

Khoảng thời gian và phân bố category được tính trực tiếp, không giả định test nằm sau train. Tháng đầu/cuối có thể không đầy đủ. Total variation so sánh phân phối category ở cấp dòng, không đại diện đầy đủ cho drift ở cấp search/user. Test không có nhãn nên không tính click/booking rate cho test. Bất kỳ đánh giá tương lai nào ở giai đoạn sau cần giữ nguyên srch_id trong một tập và thiết kế thời gian theo mục tiêu triển khai; chưa thực hiện chia tập ở đây.

**Khoảng thời gian toàn bộ mỗi tập**

| population | min_date_time | max_date_time | searches |
| --- | --- | --- | --- |
| train | 2012-11-01 00:01:37 | 2013-06-30 23:58:24 | 399,344 |
| test | 2012-11-01 00:03:24 | 2013-06-30 23:57:15 | 266,230 |

**Train: tỷ lệ theo tháng**

| year_month | n | clicks | bookings | click_pct | booking_pct |
| --- | --- | --- | --- | --- | --- |
| 2012-11 | 990,772 | 44,309 | 28,013 | 4.4722 | 2.8274 |
| 2012-12 | 957,195 | 42,372 | 26,708 | 4.4267 | 2.7902 |
| 2013-01 | 1,224,353 | 53,459 | 32,196 | 4.3663 | 2.6296 |
| 2013-02 | 1,177,863 | 52,119 | 32,580 | 4.4249 | 2.766 |
| 2013-03 | 1,400,821 | 62,848 | 38,738 | 4.4865 | 2.7654 |
| 2013-04 | 1,291,801 | 58,209 | 36,169 | 4.506 | 2.7999 |
| 2013-05 | 1,397,042 | 63,658 | 39,950 | 4.5566 | 2.8596 |
| 2013-06 | 1,477,683 | 66,698 | 42,239 | 4.5137 | 2.8585 |

**Khác biệt category train–test, toàn bộ dòng**

| column | total_variation_0_1 | test_only_categories |
| --- | --- | --- |
| prop_country_id | 0.0053 | 2 |
| visitor_location_country_id | 0.0048 | 5 |
| site_id | 0.0025 | 0 |
| srch_saturday_night_bool | 0.0014 | 0 |
| random_bool | 0.001 | 0 |
| prop_starrating | 0.0008 | 0 |
| prop_brand_bool | 0.0002 | 0 |
| promotion_flag | 0.0002 | 0 |

![calendar](figures/calendar.png)

## 10. Phụ thuộc giữa các biến trên mẫu nhóm

Tương quan Spearman dưới đây dùng mẫu hash theo search và các cặp không thiếu. Đây là kiểm tra mô tả cho một danh sách biến đã công bố, không phải chọn feature. Biến ngữ cảnh được lặp cho nhiều khách sạn cùng search, nên không diễn giải số dòng như số người độc lập. Giá, hạng sao, vị trí và giá lịch sử có thể chứa thông tin chồng lặp; chưa loại hoặc kết hợp cột.

**12 cặp có |rho| lớn nhất trên mẫu nhóm**

| column_a | column_b | sample_spearman_rho |
| --- | --- | --- |
| price_usd | prop_log_historical_price | 0.5773 |
| price_usd | prop_starrating | 0.5548 |
| prop_location_score1 | prop_location_score2 | 0.5292 |
| prop_starrating | prop_log_historical_price | 0.5019 |
| prop_starrating | prop_review_score | 0.4251 |
| price_usd | prop_review_score | 0.4208 |
| prop_review_score | prop_log_historical_price | 0.3472 |
| srch_length_of_stay | srch_booking_window | 0.3463 |
| prop_location_score1 | prop_log_historical_price | 0.3201 |
| prop_starrating | prop_location_score1 | 0.3196 |
| price_usd | prop_location_score1 | 0.3143 |
| price_usd | srch_booking_window | 0.1891 |

## 11. Kết luận và câu hỏi còn mở

**Đã kiểm chứng trên toàn bộ train:** 9,917,530 cặp search-property thuộc 399,344 searches; click 4.47%, booking 2.79%, booking/click 62.34%. Không có search hoàn toàn không click trong tập train hiện tại. Số cột đối thủ là 24 và tỷ lệ missing khác nhau mạnh theo đối thủ. Gross bookings là kết quả; position không có trong test.

**Mức độ phù hợp:** phù hợp nghiên cứu propensity/xếp hạng ở cấp khách sạn trong search, chưa phải propensity marketing theo user hoặc CTR/CVR toàn website. Two-stage click/booking là một khả năng định nghĩa bài toán, không phải kết luận bắt buộc từ tỷ số booking/click cao.

**Cần xác minh:** cơ chế đưa search vào dữ liệu và nhóm không click bị thiếu; tính sẵn có của từng điểm do Expedia sinh; nghĩa/đơn vị và cách hình thành giá; quy trình random_bool; khả năng nhận diện người dùng và lần tìm kiếm lặp; phạm vi áp dụng ngoài dữ liệu lịch sử.

Không class weighting, resampling, imputation, clipping, encoding, feature engineering hay train/rank model. Không tạo tập processed hoặc tự quyết định loại cột missing cao. Các câu hỏi và thống kê ở đây phục vụ hiểu dữ liệu trước giai đoạn tiếp theo.

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
