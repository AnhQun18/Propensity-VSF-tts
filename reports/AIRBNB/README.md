# AIRBNB — Hiểu người dùng mới, booking đầu và độ phủ hành vi

> Phạm vi: EDA trên dữ liệu gốc. Không làm sạch/thay thế dữ liệu, không tạo tập feature, không huấn luyện mô hình.

Ngày phân tích: 2026-11-01. Đây không phải ngày thu thập dữ liệu.

## 1. Bối cảnh, đơn vị quan sát và phạm vi nhãn

Train gồm **213,451 người dùng, 16 cột**, test gồm **62,096 người dùng, 15 cột**. Nhãn gốc là `country_destination` với 12 giá trị, gồm `NDF` và 11 điểm đến/nhóm điểm đến còn lại. Đối với propensity nhị phân, báo cáo chỉ thống kê hành vi **có booking được ghi nhận** khi nhãn khác NDF; không tạo tập nhãn huấn luyện mới.

Mục tiêu gốc là dự đoán điểm đến booking đầu, không trực tiếp cung cấp nhãn booking trong 30/60/90 ngày. `NDF` nghĩa không có booking theo nhãn của bộ dữ liệu; không khẳng định người dùng sẽ không bao giờ book. Chưa xác minh được ngày kết thúc theo dõi cho từng người dùng và độ trưởng thành nhãn ở mỗi cohort.

[Mô tả cuộc thi Airbnb New User Bookings](https://www.kaggle.com/c/airbnb-recruiting-new-user-bookings/data) nêu người dùng trong tập đến từ Mỹ. Vì vậy tính đại diện về địa lý, thời kỳ và sản phẩm có giới hạn. Test công khai không có nhãn để tính chất lượng dự đoán hoặc so sánh booking rate với train.

**Danh mục đầy đủ; submission chỉ là định dạng kết quả, không phải dữ liệu người dùng bổ sung**

| file | data_lines | columns | bytes | sha256 |
| --- | --- | --- | --- | --- |
| age_gender_bkts.csv | 420 | 5 | 11,905 | ca101ff0d68112ac43083e5868ccf643a8701ede4dd0eaf90cd84bfff2998c6d |
| countries.csv | 10 | 7 | 632 | f6bc346fd3c51a237448860c9c77c16db2672d8e4799af11ef4d3b55560ec1cd |
| sample_submission_NDF.csv | 62,096 | 2 | 931,451 | 9cd8b164121586b8940ff1666dffce7fd44453628c0e4410e478ddb2dd61b769 |
| sessions.csv | 10,567,737 | 6 | 631,646,292 | 63d4a31cd7202468b120b6e88df4389f4e0bc0188a4ea683fcae50f7addc0f27 |
| test_users.csv | 62,096 | 15 | 6,763,170 | 17b25cbae6f3f6c95ff553ac108f145f0e3f0873bdae0c5f45f2f821ffd81384 |
| train_users_2.csv | 213,451 | 16 | 24,853,881 | 1d57dabe8b06534e51f86520ce6a66b6f67cce1704fb77a3fcfb596124858818 |

## 2. Từ điển users và quan hệ giữa các bảng

`id` là khóa users, ghép một–nhiều với `sessions.user_id`. Cần phân tích users trước và sau ghép mà không làm một người dùng bị nhân thành nhiều quan sát học. `countries` có khóa quốc gia; không ghép bằng điểm đến thật để dự đoán chính nhãn đó. `age_gender_bkts` là thống kê tổng hợp theo bucket/quốc gia/giới tính, không phải thêm 420 khách hàng.

**Schema đầy đủ của train users**

| column | pandas_dtype | distinct_nonnull | missing_n | missing_pct | meaning | role_or_caution |
| --- | --- | --- | --- | --- | --- | --- |
| id | object | 213,451 | 0 | 0 | Định danh người dùng | Khóa ghép sessions.user_id; không phải phép đo |
| date_account_created | object | 1,634 | 0 | 0 | Ngày tạo tài khoản | Mốc cohort; không tự xác định horizon nhãn |
| timestamp_first_active | int64 | 213,451 | 0 | 0 | Lần hoạt động đầu, dạng YYYYMMDDHHMMSS | Có thể trước ngày tạo tài khoản; cần parse theo định dạng |
| date_first_booking | object | 1,976 | 124,543 | 58.3473 | Ngày booking đầu được ghi nhận | Kết quả; presence tiết lộ nhãn có booking |
| gender | object | 4 | 0 | 0 | Giới tính khai báo | -unknown- là sentinel, không phải giá trị biết rõ |
| age | float64 | 127 | 87,990 | 41.2226 | Tuổi khai báo | Thiếu và giá trị ngoài dải tham chiếu; chưa sửa tuổi/năm sinh |
| signup_method | object | 3 | 0 | 0 | Phương thức đăng ký | Biến phân loại |
| signup_flow | int64 | 17 | 0 | 0 | Mã luồng/trang đăng ký | Mã phân loại dù pandas đọc số |
| language | object | 25 | 0 | 0 | Ngôn ngữ ưu tiên | Biến phân loại |
| affiliate_channel | object | 8 | 0 | 0 | Kênh marketing liên quan | Không tự chứng minh tác động nhân quả của kênh |
| affiliate_provider | object | 18 | 0 | 0 | Nhà cung cấp/kênh cụ thể | Biến phân loại |
| first_affiliate_tracked | object | 7 | 6,065 | 2.8414 | Tương tác affiliate đầu được theo dõi | NA và category untracked có nghĩa khác nhau |
| signup_app | object | 4 | 0 | 0 | Ứng dụng đăng ký | Không đại diện mọi thiết bị dùng về sau |
| first_device_type | object | 9 | 0 | 0 | Thiết bị đầu tiên | Khác device_type ở từng sự kiện sessions |
| first_browser | object | 52 | 0 | 0 | Trình duyệt đầu tiên | Có sentinel -unknown- |
| country_destination | object | 12 | 0 | 0 | Điểm đến booking đầu hoặc NDF | Target 12 lớp; 11 lớp khi chỉ xét có booking |

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

## 3. Chất lượng users, sentinel và rò rỉ nhãn

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

## 4. Nhãn, tuổi và phân phối kênh/thiết bị

Có booking được ghi nhận: **88,908/213,451 (41.65%)**. Nhóm NDF chiếm **58.35%**. Bảng điểm đến trình bày hai mẫu số riêng: toàn bộ người dùng và chỉ người có booking; không nhầm tỷ trọng US trong toàn bộ users với tỷ trọng US trong nhóm đã book.

Độ tuổi được trình bày cả raw và cửa sổ [16,100] để thấy tác động của giá trị cực đoan. Top category có mẫu số là toàn bộ users, kể cả NA. `signup_flow` là mã phân loại; không báo cáo mean của mã như một đặc điểm khách hàng.

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

![users distributions](figures/users_distributions.png)

## 5. Quan hệ giữa hồ sơ đăng ký và nhãn

Mỗi quan sát là một user train. Khoảng Wilson 95% chỉ phản ánh bất định nhị thức dưới giả định độc lập; không bao gồm sai lệch chọn mẫu, nhãn chưa trưởng thành hoặc khác thời gian theo dõi. Các nhóm n<100 cần thận trọng. Chênh lệch booking rate giữa kênh/app/thiết bị là liên hệ quan sát, không chứng minh kênh làm tăng booking. Phân nhóm tuổi phục vụ so sánh EDA, không tạo feature.

**Booking được ghi nhận theo gender**

| gender | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| -unknown- | 95,688 | 29,018 | 30.3256 | 30.0352 | 30.6177 | 0 |
| FEMALE | 63,041 | 31,993 | 50.7495 | 50.3592 | 51.1397 | 0 |
| MALE | 54,440 | 27,721 | 50.9203 | 50.5003 | 51.3401 | 0 |
| OTHER | 282 | 176 | 62.4113 | 56.6271 | 67.862 | 0 |

**Booking được ghi nhận theo signup_method**

| signup_method | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| basic | 152,897 | 65,051 | 42.5456 | 42.298 | 42.7936 | 0 |
| facebook | 60,008 | 23,756 | 39.5881 | 39.1975 | 39.98 | 0 |
| google | 546 | 101 | 18.4982 | 15.4653 | 21.9712 | 0 |

**Booking được ghi nhận theo signup_app**

| signup_app | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| Web | 182,717 | 80,021 | 43.795 | 43.5677 | 44.0227 | 0 |
| iOS | 19,019 | 5,511 | 28.9763 | 28.3359 | 29.6252 | 0 |
| Moweb | 6,261 | 2,143 | 34.2278 | 33.0625 | 35.4124 | 0 |
| Android | 5,454 | 1,233 | 22.6073 | 21.5167 | 23.7364 | 0 |

**Booking được ghi nhận theo affiliate_channel**

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

**Booking được ghi nhận theo first_device_type**

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

**Booking được ghi nhận theo first_affiliate_tracked**

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

**Tuổi theo nhãn — NA giữ là nhóm riêng**

| reported_age_group | n | positive | rate_pct | ci95_low_pct | ci95_high_pct | n_under_100 |
| --- | --- | --- | --- | --- | --- | --- |
| <MISSING> | 87,990 | 20,376 | 23.1572 | 22.8796 | 23.4371 | 0 |
| 25–34 | 55,694 | 32,054 | 57.5538 | 57.1428 | 57.9637 | 0 |
| 35–44 | 30,759 | 16,834 | 54.7287 | 54.1719 | 55.2843 | 0 |
| 45–54 | 14,521 | 7,149 | 49.2321 | 48.4193 | 50.0454 | 0 |
| 16–24 | 10,770 | 5,425 | 50.3714 | 49.4272 | 51.3154 | 0 |
| 55–64 | 7,599 | 3,904 | 51.3752 | 50.251 | 52.498 | 0 |
| 65–100 | 3,708 | 1,828 | 49.2988 | 47.6912 | 50.9079 | 0 |
| >100 | 2,345 | 1,321 | 56.3326 | 54.3165 | 58.3281 | 0 |
| 1–15 | 65 | 17 | 26.1538 | 17.0182 | 37.9508 | 1 |

## 6. Sessions: độ phủ, khóa ghép và giới hạn thời gian

Đã quét **toàn bộ 10,567,737 sự kiện**, không dùng 500.000 dòng đầu. Có **135,483 user_id khác nhau không thiếu**, gồm **73,815 train** và **61,668 test**; **0 ID** không thuộc cả hai bảng users. Có **34,496 sự kiện thiếu user_id**, không gán được về người dùng.

Độ phủ train **34.58%**, test **99.31%** khác nhau rất mạnh. Bảng cohort cho thấy độ phủ gắn với năm tạo account; không diễn giải không có log thành không có hoạt động. Tỷ lệ thiết bị dưới đây có mẫu số là **sự kiện**, không phải người dùng, nên người hoạt động nhiều có trọng số lớn hơn.

**Giới hạn quan trọng:** sáu cột sessions không có timestamp sự kiện. Không thể chứng minh từ file này rằng toàn bộ log thuộc cửa sổ trước t0/booking. Các tổng theo user chỉ là mô tả để hiểu độ phủ và mức độ lặp; không xuất thành feature và không kết luận predictive signal hợp lệ theo thời gian.

`secs_elapsed` có 10,431,706 giá trị không thiếu; trung bình 19,405.81, min 0.00, max 1,799,977.00; 104,624 giá trị 0 và 0 âm. Không đồng nhất tổng trường này với thời gian hoạt động độc lập liên tục hoặc thời điểm của hành động.

**Schema toàn bảng sessions**

| column | distinct_nonnull | missing_n | missing_pct | meaning | caution |
| --- | --- | --- | --- | --- | --- |
| user_id | 135,483 | 34,496 | 0.3264 | ID ghép users.id | Khóa; NA không ghép được |
| action | 359 | 79,626 | 0.7535 | Tên hành động | Không có timestamp sự kiện |
| action_type | 10 | 1,126,204 | 10.657 | Nhóm hành động | Có NA/sentinel; không suy ra thứ tự thời gian |
| action_detail | 155 | 1,126,204 | 10.657 | Chi tiết hành động | Có NA/sentinel |
| device_type | 14 | 0 | 0 | Thiết bị ở sự kiện | Tỷ trọng sự kiện khác tỷ trọng người dùng |
| secs_elapsed | không tính | 136,031 | 1.2872 | Trường thời lượng theo mô tả nguồn | Không phải timestamp; không dùng để cắt trước/sau booking |

**Độ phủ theo tập users**

| population | users | users_with_sessions | coverage_pct |
| --- | --- | --- | --- |
| train | 213,451 | 73,815 | 34.5817 |
| test | 62,096 | 61,668 | 99.3107 |

**Độ phủ theo năm account train**

| account_year | users | users_with_sessions | coverage_pct |
| --- | --- | --- | --- |
| 2,010 | 2,788 | 0 | 0 |
| 2,011 | 11,775 | 0 | 0 |
| 2,012 | 39,462 | 0 | 0 |
| 2,013 | 82,960 | 0 | 0 |
| 2,014 | 76,466 | 73,815 | 96.5331 |

**Độ phủ theo nhãn điểm đến (mô tả, không dùng suy luận nhân quả)**

| country_destination | users | users_with_sessions | coverage_pct |
| --- | --- | --- | --- |
| AU | 539 | 152 | 28.2004 |
| CA | 1,428 | 440 | 30.8123 |
| DE | 1,061 | 250 | 23.5627 |
| ES | 2,249 | 707 | 31.4362 |
| FR | 5,023 | 1,435 | 28.5686 |
| GB | 2,324 | 731 | 31.4544 |
| IT | 2,835 | 979 | 34.5326 |
| NDF | 124,543 | 45,041 | 36.165 |
| NL | 762 | 247 | 32.4147 |
| PT | 217 | 83 | 38.2488 |
| US | 62,376 | 20,095 | 32.2159 |
| other | 10,094 | 3,655 | 36.2096 |

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

![session coverage](figures/session_coverage.png)

## 7. Cohort thời gian và thay đổi train–test

Train và test nối tiếp theo ngày tạo account. Đồ thị booking rate theo cohort phản ánh cả thành phần khách và thời gian có cơ hội được quan sát; không kết luận cohort mới kém chất lượng chỉ từ nhãn. Total variation trong [0,1] so sánh phân phối category (kể cả NA); 0 là giống nhau, 1 là không giao nhau. Đây là mô tả drift, không phải ngưỡng tự động loại biến hoặc chọn mô hình.

**Khoảng thời gian account**

| population | account_min | account_max | users |
| --- | --- | --- | --- |
| train | 2010-01-01 | 2014-06-30 | 213,451 |
| test | 2014-07-01 | 2014-09-30 | 62,096 |

**Cohort theo tháng — toàn bộ train**

| account_month | users | booked | booked_pct |
| --- | --- | --- | --- |
| 2010-01 | 61 | 32 | 52.459 |
| 2010-02 | 102 | 55 | 53.9216 |
| 2010-03 | 163 | 106 | 65.0307 |
| 2010-04 | 157 | 91 | 57.9618 |
| 2010-05 | 227 | 128 | 56.3877 |
| 2010-06 | 222 | 109 | 49.0991 |
| 2010-07 | 307 | 180 | 58.6319 |
| 2010-08 | 312 | 180 | 57.6923 |
| 2010-09 | 371 | 218 | 58.7601 |
| 2010-10 | 309 | 191 | 61.8123 |
| 2010-11 | 286 | 164 | 57.3427 |
| 2010-12 | 271 | 149 | 54.9815 |
| 2011-01 | 316 | 189 | 59.8101 |
| 2011-02 | 362 | 215 | 59.3923 |
| 2011-03 | 491 | 326 | 66.3951 |
| 2011-04 | 577 | 372 | 64.4714 |
| 2011-05 | 744 | 468 | 62.9032 |
| 2011-06 | 822 | 506 | 61.5572 |
| 2011-07 | 993 | 644 | 64.854 |
| 2011-08 | 1,454 | 775 | 53.3012 |
| 2011-09 | 1,864 | 859 | 46.0837 |
| 2011-10 | 1,477 | 740 | 50.1016 |
| 2011-11 | 1,386 | 688 | 49.6392 |
| 2011-12 | 1,289 | 651 | 50.5043 |
| 2012-01 | 1,589 | 797 | 50.1573 |
| 2012-02 | 1,789 | 905 | 50.5869 |
| 2012-03 | 2,192 | 1,182 | 53.9234 |
| 2012-04 | 2,589 | 1,371 | 52.9548 |
| 2012-05 | 3,325 | 1,695 | 50.9774 |
| 2012-06 | 3,867 | 1,619 | 41.8671 |
| 2012-07 | 4,582 | 1,866 | 40.7246 |
| 2012-08 | 4,476 | 1,953 | 43.6327 |
| 2012-09 | 4,035 | 1,810 | 44.8575 |
| 2012-10 | 3,828 | 1,641 | 42.8683 |
| 2012-11 | 3,706 | 1,530 | 41.2844 |
| 2012-12 | 3,484 | 1,380 | 39.6096 |
| 2013-01 | 4,418 | 1,859 | 42.0779 |
| 2013-02 | 4,362 | 1,961 | 44.9564 |
| 2013-03 | 5,421 | 2,434 | 44.8995 |
| 2013-04 | 5,855 | 2,531 | 43.228 |
| 2013-05 | 6,721 | 2,910 | 43.2971 |
| 2013-06 | 6,765 | 2,879 | 42.5573 |
| 2013-07 | 7,950 | 3,340 | 42.0126 |
| 2013-08 | 8,369 | 3,474 | 41.5103 |
| 2013-09 | 9,125 | 3,365 | 36.8767 |
| 2013-10 | 7,862 | 3,153 | 40.1043 |
| 2013-11 | 7,751 | 2,906 | 37.4919 |
| 2013-12 | 8,361 | 3,072 | 36.742 |
| 2014-01 | 11,111 | 4,142 | 37.2784 |
| 2014-02 | 9,967 | 3,888 | 39.0087 |
| 2014-03 | 12,058 | 4,622 | 38.3314 |
| 2014-04 | 12,689 | 4,901 | 38.624 |
| 2014-05 | 14,895 | 5,754 | 38.6304 |
| 2014-06 | 15,746 | 5,932 | 37.6731 |

**Khác biệt category giữa train và test**

| column | total_variation_0_1 | test_only_categories | train_missing_pct | test_missing_pct |
| --- | --- | --- | --- | --- |
| first_device_type | 0.3121 | 0 | 0 | 0 |
| first_browser | 0.2595 | 3 | 0 | 0 |
| signup_app | 0.2569 | 0 | 0 | 0 |
| signup_flow | 0.2201 | 1 | 0 | 0 |
| affiliate_channel | 0.1574 | 0 | 0 | 0 |
| gender | 0.0959 | 0 | 0 | 0 |
| affiliate_provider | 0.092 | 0 | 0 | 0 |
| first_affiliate_tracked | 0.0798 | 0 | 2.8414 | 0.0322 |
| signup_method | 0.0419 | 1 | 0 | 0 |
| language | 0.0137 | 1 | 0 | 0 |

![account cohorts](figures/account_cohorts.png)

## 8. Bảng phụ: từ điển và khả năng ghép

Chỉ kiểm tra bảng và quan hệ; chưa thực hiện feature engineering. Các mã NDF/other trong users không nhất thiết có dòng tương ứng trong countries; việc thiếu đó không phải lỗi khóa của users. Bất kỳ cách dùng thống kê ngoài bảng users phải xác minh nguồn, mốc công bố và ngữ nghĩa trước khi ghép vào đầu vào dự đoán.

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

## 9. Kết luận và câu hỏi còn mở

**Đã kiểm chứng:** 41.65% users train có booking theo nhãn; date_first_booking tiết lộ nhãn; users và events có đơn vị khác nhau; độ phủ sessions chênh rất lớn giữa train/test và gắn với năm account; logs không có timestamp từng sự kiện.

**Mức độ phù hợp:** phù hợp cho nghiên cứu first-booking propensity ở cấp user nếu công bố rõ nhãn hiện tại là kết quả được quan sát, chưa phải một horizon chuẩn hóa. Bài toán điểm đến có 12 lớp khi gồm NDF; chỉ người có booking còn 11 giá trị điểm đến/other.

**Cần xác minh:** thời hạn nhãn và ngày kết thúc theo dõi; t0 chấm điểm; khoảng thời gian logs được thu thập và cắt log; ý nghĩa tuổi bất thường/unknown; thời điểm bảng phụ được công bố; khả năng áp dụng ngoài người dùng Mỹ và thời kỳ 2010–2014.

Chưa impute, sửa tuổi, encode, tổng hợp sessions thành tập feature, chọn feature, chia tập huấn luyện hay train model. Mọi bảng nhóm và nhãn nhị phân tạm thời trong code chỉ phục vụ thống kê EDA và không được xuất thành dữ liệu mô hình.

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
