# Dữ liệu của dự án

Thư mục `raw/` chứa dữ liệu gốc trên máy, được loại khỏi Git bằng `.gitignore`. Clone repo không tự tải các file CSV. Báo cáo và notebook có output nằm trong repo; chạy lại phân tích cần đặt dữ liệu vào đúng các thư mục dưới đây.

## Nguồn và cấu trúc

- **HOTEL:** [Hotel booking demand datasets — nghiên cứu gốc](https://pmc.ncbi.nlm.nih.gov/articles/PMC6297060/). File CSV đang dùng trong dự án là bản gộp hai khách sạn, có cột `hotel`.
- **AIRBNB:** [Airbnb New User Bookings](https://www.kaggle.com/c/airbnb-recruiting-new-user-bookings/data).
- **EXPEDIA:** [Personalize Expedia Hotel Searches — ICDM 2013](https://www.kaggle.com/c/expedia-personalized-sort/data).

Tải dữ liệu theo hướng dẫn của nguồn và đặt các file sau vào dự án:

```text
data/raw/
├── HOTEL/
│   └── hotel_bookings.csv
├── AIRBNB/
│   ├── train_users_2.csv
│   ├── test_users.csv
│   ├── sessions.csv
│   ├── countries.csv
│   ├── age_gender_bkts.csv
│   └── sample_submission_NDF.csv
└── EXPEDIA/
    ├── train.csv
    ├── test.csv
    ├── basicPythonBenchmark.csv
    ├── randomBenchmark.csv
    └── testOrderBenchmark.csv
```

Các file submission/benchmark không phải dữ liệu huấn luyện bổ sung. Danh mục, số dòng, kích thước chính xác theo byte và SHA-256 của dữ liệu đã phân tích được ghi trong [các báo cáo](../reports/README.md). Đối chiếu các thông tin này để tránh dùng nhầm phiên bản hoặc nhầm cuộc thi Expedia.

Sau khi có dữ liệu, chạy từ thư mục gốc:

```powershell
python scripts/build_descriptive_reports.py
```

Script chỉ thực hiện EDA và dựng báo cáo; không tạo tập feature hay huấn luyện mô hình.

## Khả năng đưa CSV lên GitHub

Kiểm tra ngày **2026-11-01**: 12 CSV có tổng dung lượng **4.815.050.232 byte**, khoảng **4,48 GiB**. Không thể push nguyên bộ bằng Git thường: GitHub chặn từng file lớn hơn **100 MiB**, bất kể chúng nằm trên nhánh `main` hay nhánh khác. Các file trên 50 MiB còn có cảnh báo dung lượng. [Giới hạn file GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)

| File | MiB, làm tròn | Git thường |
| --- | ---: | --- |
| `EXPEDIA/train.csv` | 2.248,87 | Vượt giới hạn |
| `EXPEDIA/test.csv` | 1.427,57 | Vượt giới hạn |
| `AIRBNB/sessions.csv` | 602,38 | Vượt giới hạn |
| Mỗi benchmark Expedia, 3 file | 88,68 | Dưới 100 MiB nhưng trên ngưỡng cảnh báo |
| `AIRBNB/train_users_2.csv` | 23,70 | Đáp ứng giới hạn kích thước |
| `HOTEL/hotel_bookings.csv` | 16,07 | Đáp ứng giới hạn kích thước |
| Các CSV còn lại | Dưới 7 | Đáp ứng giới hạn kích thước |

Git LFS đã có trên máy lúc kiểm tra, nhưng chưa cấu hình cho repo hoặc upload dữ liệu. GitHub quy định giới hạn LFS mỗi file theo gói: Free/Pro **2 GB**, Team **4 GB**, Enterprise Cloud **5 GB**. `EXPEDIA/train.csv` có **2.358.114.793 byte** (khoảng **2,20 GiB**), vượt giới hạn Free/Pro ngay cả khi dùng LFS. Chưa xác minh gói tài khoản và dung lượng/băng thông LFS còn lại, nên không khẳng định tài khoản hiện tại tải được toàn bộ dữ liệu. [Giới hạn Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)

**Cách dùng hiện tại:** lưu code, notebook, báo cáo và thông tin nguồn trên GitHub; giữ CSV gốc ngoài lịch sử Git, tải từ nguồn khi cần tái lập. Nếu sau này cần lưu cả dữ liệu trên GitHub, phải thiết kế phương án LFS/nén/chia file phù hợp và kiểm tra quota trước; bản cập nhật này chưa thực hiện các thay đổi đó.
