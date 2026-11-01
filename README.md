# 🎯 Propensity Modeling Project

Dự án xây dựng hệ thống **Propensity Modeling** (Mô hình hóa xu hướng hành vi khách hàng) chuẩn công nghiệp, phục vụ các bài toán Marketing Analytics, Tăng trưởng (Growth) và Quản trị Vòng đời Khách hàng (Customer Lifecycle Management).

---

## 📌 1. Giới thiệu Bài toán Propensity Modeling

### Khái niệm
**Propensity Modeling** là bài toán học máy phân loại nhị phân (Binary Classification) nhằm ước tính **xác suất** ($P \in [0, 1]$) mà một khách hàng cụ thể sẽ thực hiện một hành động mục tiêu trong một khoảng thời gian nhất định trong tương lai.

### Ứng dụng thực tế
- **Propensity to Buy / Convert:** Dự đoán khả năng khách hàng mua sản phẩm hoặc nâng cấp gói dịch vụ.
- **Propensity to Churn:** Dự đoán khả năng khách hàng rời bỏ dịch vụ để kích hoạt chương trình giữ chân (Retention).
- **Propensity to Engage / Click:** Dự đoán khả năng khách hàng phản hồi với chiến dịch Email/SMS/App Push Notification.
- **Cross-sell / Up-sell:** Phân nhóm khách hàng theo phân vị (Decile) để tối ưu chi phí tiếp thị (Marketing ROI).

---

## 🗂️ 2. Cấu trúc Thư mục Dự án

```text
propensity-modeling-project/
├── data/                         # Dữ liệu raw và processed (đưa vào .gitignore nếu file nặng)
│   ├── raw/
│   └── processed/
├── notebooks/                    # Chứa các file .ipynb làm EDA và thử nghiệm ban đầu
│   └── 01_eda_and_exploration.ipynb
├── src/                          # Source code chính đóng gói thành Python package
│   ├── __init__.py
│   ├── data_loader.py            # Đọc và kiểm tra schema dữ liệu
│   ├── preprocessing.py          # Làm sạch, xử lý missing, outlier
│   ├── features.py               # Các hàm/class Feature Engineering (Scikit-learn Pipeline)
│   ├── train.py                  # Huấn luyện, tuning hyperparameter và lưu model
│   ├── predict.py                # Chấm điểm propensity cho dữ liệu mới
│   └── monitoring.py             # Theo dõi chất lượng mô hình (Model Monitoring)
├── configs/                      # Các file cấu hình tham số (.yaml / .json)
│   └── config.yaml
├── reports/                      # Lưu biểu đồ EDA, kết quả đánh giá và Slide báo cáo
│   ├── figures/
│   ├── metrics/
│   └── README.md
├── setup.py                      # Cấu hình cài đặt package (pip install -e .)
├── pyproject.toml                # File cấu hình build package hiện đại
├── requirements.txt              # Danh sách thư viện và phiên bản
├── .gitignore                    # Bỏ qua dữ liệu nặng, checkpoints, logs, virtualenv
└── README.md                     # Mô tả bài toán, cấu trúc dữ liệu và hướng dẫn chạy
```

---

## 📋 3. Cấu trúc Dữ liệu Mẫu (Schema)

Dự án đi kèm cấu hình mẫu trong [config.yaml](file:///c:/Users/admin/Documents/Thực tập VSF/Propensity/configs/config.yaml):

| Tên cột | Kiểu dữ liệu | Ý nghĩa |
| :--- | :--- | :--- |
| `customer_id` | String | Khóa định danh khách hàng duy nhất |
| `signup_date` | Date | Ngày đăng ký tài khoản |
| `last_active_date` | Date | Ngày hoạt động gần nhất |
| `age` | Integer | Độ tuổi khách hàng |
| `tenure_months` | Integer | Số tháng gắn bó |
| `total_spend` | Float | Tổng số tiền đã chi tiêu |
| `transaction_count_last_30d`| Integer | Số lượng giao dịch trong 30 ngày gần nhất |
| `avg_order_value` | Float | Giá trị trung bình của mỗi đơn hàng |
| `app_sessions_last_30d` | Integer | Số lần mở ứng dụng trong 30 ngày qua |
| `gender` | Categorical | Giới tính khách hàng |
| `acquisition_channel` | Categorical | Kênh tiếp cận (Organic, Facebook Ads, Google Search,...) |
| `loyalty_tier` | Categorical | Hạng thành viên (Bronze, Silver, Gold, Platinum) |
| `preferred_category` | Categorical | Danh mục hàng hóa ưa chuộng |
| **`converted`** (Target) | Integer (0/1) | **1: Chuyển đổi thành công**, **0: Không chuyển đổi** |

---

## ⚙️ 4. Hướng dẫn Cài đặt Môi trường

### Bước 1: Khởi tạo và kích hoạt môi trường ảo (Virtual Environment)
```bash
# Trên Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# Trên Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### Bước 2: Cài đặt các thư viện phụ thuộc
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 3: Cài đặt project dưới dạng package cục bộ (Editable mode)
```bash
pip install -e .
```
> Lệnh này cho phép bạn import các module trong `src` ở bất cứ đâu trong dự án (ví dụ: `from src.data_loader import load_data`) mà không lo lỗi `ModuleNotFoundError`.

---

## 🚀 5. Quy trình Vận hành Pipeline (Workflow Execution)

### Bước 1: Phân tích Khám phá Dữ liệu (EDA)
Mở Jupyter Notebook để phân tích trực quan hóa phân phối, phát hiện missing, outlier và kiểm tra độ mất cân bằng nhãn:
```bash
jupyter notebook notebooks/01_eda_and_exploration.ipynb
```

### Bước 2: Huấn luyện Mô hình (Model Training)
Chạy pipeline tiền xử lý, fit Scikit-learn transformer, huấn luyện thuật toán (LightGBM/XGBoost/CatBoost) và xuất báo cáo đánh giá:
```bash
python -m src.train
```
- **Kết quả xuất ra:**
  - Mô hình: `models/propensity_model.joblib`
  - Preprocessor: `models/preprocessor.joblib`
  - Biểu đồ: `reports/figures/roc_curve_test.png`, `reports/figures/pr_curve_test.png`
  - Chỉ số chi tiết: `reports/metrics/evaluation_metrics.json`

### Bước 3: Chấm điểm Khách hàng Mới (Propensity Scoring)
Áp dụng mô hình đã lưu để chấm điểm xác suất và phân vị Decile (Top 10% khách hàng tiềm năng nhất):
```bash
python -m src.predict
```
- File kết quả được ghi nhận tại `data/processed/scored_customers.parquet` chứa:
  - `propensity_score`: Xác suất chuyển đổi ($0.0000 - 1.0000$)
  - `propensity_decile`: Phân vị từ 1 (cao nhất) đến 10 (thấp nhất)
  - `is_targeted`: Nhãn dự đoán nhị phân theo ngưỡng cutoff threshold

### Bước 4: Giám sát Mô hình & Kiểm soát Trôi dạt (Model Monitoring & Drift)
Theo dõi độ ổn định của phân phối điểm số và đặc trưng đầu vào định kỳ:
```bash
python -m src.monitoring
```
- **Kết quả xuất ra:**
  - `reports/metrics/monitoring_report.json`
  - `reports/metrics/feature_drift_summary.csv`

---

## 📊 6. Bộ Chỉ số Đánh giá Chuyên sâu (Propensity Metrics)

Trong bài toán Propensity Modeling, nhãn mục tiêu thường có tỷ lệ xuất hiện thấp (từ 1% đến 10%). Dự án áp dụng bộ chỉ số toàn diện:

1. **ROC-AUC:** Đánh giá năng lực phân hạng tổng quát trên toàn bộ ngưỡng xác suất.
2. **PR-AUC (Precision-Recall AUC / Average Precision):** Thước đo cốt lõi cho dữ liệu mất cân bằng nghiêm trọng.
3. **Kolmogorov-Smirnov (KS) Statistic:** Đo khoảng cách tối đa giữa hàm phân phối tích lũy (CDF) của nhóm Positive và nhóm Negative:
   - $KS < 20\%$: Mô hình kém.
   - $20\% \le KS < 40\%$: Mô hình trung bình khá.
   - $KS \ge 40\%$: Mô hình tốt, khả năng phân tách cao.
4. **Brier Score:** Đo lường độ chuẩn xác của xác suất đầu ra (Probability Calibration).
5. **Decile Table & Cumulative Lift:** Đo lường hiệu quả tiếp cận khi đội ngũ Marketing chỉ nhắm vào Top 10% hoặc Top 20% khách hàng có điểm cao nhất.
6. **Population Stability Index (PSI):**
   - $PSI < 0.10$: Dữ liệu ổn định.
   - $0.10 \le PSI < 0.25$: Cảnh báo có dịch chuyển phân phối nhẹ.
   - $PSI \ge 0.25$: Cần lập tức huấn luyện lại mô hình (Retraining).

---

## 🛡️ 7. Nguyên tắc Phòng chống Rò rỉ Dữ liệu (Anti Data-Leakage)

- **Nguyên tắc phân chia:** Luôn chia dữ liệu thành tập Train, Val, Test **trước khi** thực hiện bất kỳ phép biến đổi nào (Scaling, Imputation, Rare Category Encoding, Outlier Clipping).
- **Bộ tiền xử lý:** Các tham số tiền xử lý (mean, median, IQR bounds, frequency) chỉ được học trên tập Train (`fit`) và áp dụng độc lập lên tập Val/Test/Production (`transform`).
