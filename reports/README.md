# Báo cáo tổng hợp: mức độ phù hợp và hiểu sâu ba bộ dữ liệu

Ngày phân tích: 2026-11-02. Phạm vi là dữ liệu CSV hiện có trong dự án, không phải dữ liệu kinh doanh hiện tại. **Chưa feature engineering, chưa làm sạch/thay thế dữ liệu, chưa chia tập huấn luyện, chưa train mô hình.**

## Tóm tắt điều hành — 7 phát hiện có bằng chứng

1. **Ba đơn vị quan sát khác nhau:** HOTEL 119,390 booking; AIRBNB 213,451 users train; EXPEDIA 9,917,530 cặp search-property. Không so trực tiếp conversion rate giữa ba mẫu số.
2. **HOTEL nhạy với duplicate:** 31,994 dòng trùng; tỷ lệ hủy/no-show 37.04% ở raw so với 27.49% nếu giả định bỏ hết trùng. Bảng độ nhạy trong báo cáo HOTEL giải thích giới hạn.
3. **AIRBNB có leakage rõ:** presence `date_first_booking` khớp hoàn toàn nhãn có booking; không dùng ngày/cờ thiếu làm đầu vào. Xem bảng chéo và heatmap missing của AIRBNB.
4. **Độ phủ log AIRBNB cần so cùng cohort:** train 2014 96.53% so với test 2014 99.31%; tỷ lệ train toàn kỳ 34.58% thấp chủ yếu vì cohort 2010–2013 không có log. Sessions chưa được xác nhận trước t0.
5. **EXPEDIA thiếu quần thể không tương tác:** train có 399,344 searches và 0 search hoàn toàn không click; không coi CTR 4.47% là CTR toàn website.
6. **Đuôi giá và missing cần quy tắc rõ:** mỗi bộ đã có bảng hàng rào 1,5×IQR, tỷ lệ outlier, heatmap missing và ma trận tương quan. Expedia tính percentile, skewness, outlier, Spearman và missing theo nhãn trên toàn bộ train; chỉ scatter/pattern missing giới hạn số điểm hiển thị. Số liệu nằm cạnh hình ở từng báo cáo.
7. **Khả năng sử dụng có điều kiện:** HOTEL cho hủy/no-show, AIRBNB cho booking đầu ở cấp user, EXPEDIA cho search/ranking. Tất cả còn câu hỏi về t0/phạm vi áp dụng; ngày tải raw chưa được ghi nhận, giấy phép/điều khoản được trình bày tại nguồn của từng bộ, không gán mặc định quyền sử dụng mở.

Các báo cáo chi tiết cùng cấu trúc: tổng quan nguồn/phiên bản → chất lượng → đơn biến → đa biến/thời gian/nhóm con → rủi ro → kết luận và đề xuất; executive summary ở đầu, từ điển/bảng dài ở phụ lục. Mỗi hình có nhận xét định lượng ngay bên dưới. Đề xuất xử lý thiếu, mã hóa, feature engineering và mô hình chỉ là hướng cho giai đoạn sau, chưa thực hiện.

## 1. Kết luận phục vụ lựa chọn bài toán

Ba bộ dữ liệu phù hợp với ba hành vi và ba đơn vị dự đoán khác nhau. Propensity ở đây là xác suất hành vi; không phải propensity score nhận treatment hoặc ước lượng uplift. Chưa có thông tin can thiệp để kết luận tác động marketing.

| Bộ | Hành vi phù hợp | Đơn vị | Giới hạn quyết định |
| --- | --- | --- | --- |
| HOTEL | Hủy/no-show của booking | Booking | Không đồng nghĩa customer churn; cần xác minh snapshot tại thời điểm dự đoán |
| AIRBNB | Có booking đầu được ghi nhận; hoặc điểm đến đầu | Người dùng mới | Chưa có nhãn horizon 30/60/90 ngày chuẩn hóa; sessions thiếu timestamp và lệch độ phủ |
| EXPEDIA | Click/booking trong danh sách khách sạn | Cặp search-property | Phù hợp bối cảnh tìm kiếm/xếp hạng; không có ID khách để chấm CRM; thiếu search không click trong train |

Nếu đề tài nhắm đến chuyển đổi khách hàng mới, AIRBNB phù hợp về đơn vị quan sát. Nếu nghiên cứu vận hành hủy booking, HOTEL rõ mục tiêu và nhẹ hơn. Nếu nghiên cứu tương tác với danh sách tìm kiếm, EXPEDIA phù hợp hơn. Không xếp một bộ là tốt nhất cho mọi mục tiêu và không coi mọi cột thô là feature hợp lệ.

## 2. Quy mô đã đối chiếu trực tiếp

| File | Quan sát | Cột thô | Ý nghĩa dòng |
| --- | ---: | ---: | --- |
| HOTEL/hotel_bookings.csv | 119,390 | 32 | Booking |
| AIRBNB/train_users_2.csv | 213,451 | 16 | User train |
| AIRBNB/test_users.csv | 62,096 | 15 | User test không có nhãn |
| AIRBNB/sessions.csv | 10,567,737 | 6 | Sự kiện, không phải thêm user |
| AIRBNB/countries.csv | 10 | 7 | Quốc gia |
| AIRBNB/age_gender_bkts.csv | 420 | 5 | Ô thống kê nhóm tuổi/giới tính/quốc gia |
| EXPEDIA/train.csv | 9,917,530 | 54 | Cặp search-property |
| EXPEDIA/test.csv | 6,622,629 | 50 | Cặp search-property không nhãn |

File submission Airbnb có 62.096 dòng × 2 cột; mỗi benchmark Expedia có 6.622.629 dòng × 2 cột. Đây là file định dạng/kết quả tham khảo, không phải dữ liệu huấn luyện bổ sung. Chi tiết file, dung lượng theo bytes và SHA-256 có trong từng báo cáo.

**Số cột ứng viên, chưa phải số feature cuối:** HOTEL có 31 cột ngoài target, còn 29 sau khi tách hai cột trạng thái cuối; các cột khác vẫn phải kiểm tra khả dụng tại t0. AIRBNB có 13 cột sau khi tách target, id và date_first_booking. EXPEDIA có 50 cột chung với test sau khi tách position, click_bool, booking_bool và gross_bookings_usd; nếu srch_id chỉ làm khóa nhóm còn 49 cột ứng viên. Chưa mã hóa, tạo feature hoặc chọn cột đầu vào cuối cùng.

## 3. Nhãn và mẫu số: không so sánh lẫn đơn vị

| Bộ / hành vi | Tử số | Mẫu số | Tỷ lệ trong dữ liệu |
| --- | ---: | ---: | ---: |
| HOTEL: hủy/no-show | 44,224 | 119,390 booking | 37.04% |
| AIRBNB: có booking được ghi nhận | 88,908 | 213,451 user train | 41.65% |
| EXPEDIA: click | 443,672 | 9,917,530 cặp | 4.47% |
| EXPEDIA: booking | 276,593 | 9,917,530 cặp | 2.79% |
| EXPEDIA: booking / click | 276,593 | 443,672 cặp đã click | 62.34% |

Tỷ lệ theo booking, user và cặp search-property trả lời các câu hỏi khác nhau. Không dùng chúng để kết luận nền tảng nào chuyển đổi tốt hơn. Tỷ số booking/click cao là liên hệ trong dữ liệu quan sát, không chứng minh click gây booking hoặc cải thiện ranking sẽ tạo mức tăng doanh thu tương ứng.

## 4. Các phát hiện thay đổi cách sử dụng dữ liệu

### HOTEL

- Nhãn 1 bao gồm Canceled và No-Show. `reservation_status` xác định hoàn toàn nhãn; `reservation_status_date` cũng thuộc thông tin kết quả.
- Có 31,994 dòng trùng hoàn toàn. Nếu giả định bỏ mọi dòng trùng, còn 87,396 booking và tỷ lệ nhãn 1 thành 27.49%, so với 37.04% ở raw. Đây là phân tích độ nhạy, không phải quyết định xóa.
- Không có booking/customer ID để xác định nguyên nhân trùng hoặc nhận diện khách qua nhiều booking. Một booking bị hủy không chứng minh customer churn.
- Snapshot gốc không đồng nghĩa mọi cột có sẵn lúc tạo booking. Booking changes, phân phòng, đặt cọc, ADR và yêu cầu bổ sung cần được kiểm chứng theo t0.
- Phân tích năm–tháng tách theo khách sạn tránh nhầm số lần tháng được quan sát với mùa vụ.

### AIRBNB

- Presence của `date_first_booking` khớp hoàn toàn nhãn có booking trong train, nên không dùng nó hoặc cờ missing của nó làm đầu vào dự đoán hành vi đó.
- Có 135,483 user_id khác nhau không thiếu trong sessions, không phải tất cả thuộc train. So cùng cohort 2014: train 73,815/76,466 (96.53%), test 61,668/62,096 (99.31%). Tỷ lệ train toàn kỳ 34.58% chịu hiệu ứng thành phần cohort. Có 34,496 sự kiện thiếu user_id.
- Độ phủ sessions gắn với năm account; thiếu log không đồng nghĩa khách không hoạt động. Logs không có timestamp sự kiện để xác nhận trước t0/booking.
- NDF không có nghĩa không bao giờ book; chưa có horizon nhãn chung được xác nhận. Nhãn gốc có 12 giá trị, còn 11 giá trị điểm đến/other sau khi chỉ xét người có booking.
- Bảng quốc gia không được ghép bằng nhãn thật để dự đoán chính nhãn đó; bảng tuổi–giới tính là tổng hợp, không phải user bổ sung.

### EXPEDIA

- Đã quét toàn bộ 9,917,530 dòng train và 6,622,629 dòng test. Toàn bộ thống kê train, gồm percentile, skewness, outlier, missing theo nhãn và tương quan, dùng đầy đủ các dòng hợp lệ. Test chỉ đối chiếu schema/chất lượng và phân phối tổng hợp.
- Train có 399,344 searches, **0 search không click**. Không suy rộng tỷ lệ trong tập thành tỷ lệ tương tác của toàn website; cần xác minh cơ chế chọn mẫu.
- `gross_bookings_usd` là kết quả sau booking. `position` không có trong test; click tương lai không phải feature để chấm trước click.
- Nhóm đối thủ có 24 cột và mức thiếu khác nhau đáng kể, không phải toàn bộ đều thiếu 93–98%. Không khẳng định NA lịch sử = khách mới hoặc NA đối thủ = không có cạnh tranh.
- Các dòng cùng search phụ thuộc nhau. Báo cáo giữ cấu trúc nhóm, phân tích vị trí cùng random_bool và chưa thiết kế mô hình/chia tập.

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

Notebook chỉ lưu trong `notebooks/HOTEL`, `notebooks/AIRBNB`, `notebooks/EXPEDIA`; `reports` chứa báo cáo Markdown, biểu đồ và metadata cần để dựng báo cáo tổng hợp. Mỗi notebook đọc lại CSV qua cùng [script EDA](../scripts/build_descriptive_reports.py); các bảng Markdown và hình được sinh từ cùng kết quả tính, tránh số liệu viết tay lệch nhau.

Chạy tại thư mục gốc dự án:

```powershell
python scripts/build_descriptive_reports.py
# Hoặc chỉ dựng lại một bộ:
python scripts/build_descriptive_reports.py --dataset AIRBNB
```

Để chạy lại notebook độc lập, mở notebook và Run All; cell đầu quét dữ liệu và cập nhật bản Markdown/biểu đồ của bộ đó. Chạy script toàn bộ để cập nhật ba notebook và báo cáo tổng hợp. Môi trường và SHA-256 nguồn được ghi trong báo cáo chi tiết; không sửa raw hoặc pipeline dự án.
