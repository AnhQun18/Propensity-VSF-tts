"""
monitoring.py
=============
Theo dõi chất lượng mô hình (Model Monitoring & Drift Detection).
Bao gồm:
- Population Stability Index (PSI) cho điểm dự đoán (Prediction Drift).
- Characteristic Stability Index (CSI) cho từng đặc trưng đầu vào (Data Drift).
- Cảnh báo tự động khi mô hình bị suy giảm hiệu năng (Degradation / Concept Drift).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from src.data_loader import load_config, load_data

logger = logging.getLogger(__name__)


def calculate_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    num_bins: int = 10,
    epsilon: float = 1e-4,
) -> float:
    """
    Tính chỉ số Population Stability Index (PSI) giữa tập chuẩn (expected/baseline)
    và tập thực tế hiện tại (actual/production).

    Quy chuẩn diễn giải:
    - PSI < 0.10: Ổn định (Không có sự thay đổi đáng kể)
    - 0.10 <= PSI < 0.25: Cảnh báo (Có dịch chuyển nhẹ, cần chú ý theo dõi)
    - PSI >= 0.25: Nguy hiểm (Phân phối lệch đáng kể, CẦN HUẤN LUYỆN LẠI MÔ HÌNH)
    """
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Xác định các mốc bin dựa trên phân vị của expected
    quantiles = np.linspace(0, 100, num_bins + 1)
    bin_edges = np.percentile(expected, quantiles)
    bin_edges[0] -= 1e-5
    bin_edges[-1] += 1e-5

    # Đếm số lượng quan sát trong mỗi bin
    expected_counts, _ = np.histogram(expected, bins=bin_edges)
    actual_counts, _ = np.histogram(actual, bins=bin_edges)

    # Chuyển đổi thành tỷ lệ phần trăm
    expected_pct = expected_counts / len(expected)
    actual_pct = actual_counts / len(actual)

    # Thay thế 0 bằng epsilon để tránh lỗi chia cho 0 hoặc log(0)
    expected_pct = np.where(expected_pct == 0, epsilon, expected_pct)
    actual_pct = np.where(actual_pct == 0, epsilon, actual_pct)

    # Công thức PSI: sum((actual - expected) * ln(actual / expected))
    psi_value = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi_value)


def monitor_feature_drift(
    df_baseline: pd.DataFrame,
    df_current: pd.DataFrame,
    numerical_cols: List[str],
) -> pd.DataFrame:
    """
    Tính toán chỉ số trôi dạt (CSI / Feature PSI) cho từng biến đầu vào.
    """
    drift_records = []

    for col in numerical_cols:
        if col in df_baseline.columns and col in df_current.columns:
            psi_score = calculate_psi(
                expected=df_baseline[col].values,
                actual=df_current[col].values,
            )

            if psi_score < 0.10:
                status = "STABLE"
            elif psi_score < 0.25:
                status = "WARNING"
            else:
                status = "ACTION_REQUIRED"

            drift_records.append(
                {
                    "feature": col,
                    "psi": round(psi_score, 4),
                    "status": status,
                }
            )

    return pd.DataFrame(drift_records)


def run_model_monitoring(config_path: str = "configs/config.yaml") -> Dict[str, Any]:
    """
    Chạy quy trình kiểm tra sức khỏe và độ ổn định của mô hình định kỳ.
    """
    config = load_config(config_path)
    monitoring_cfg = config.get("monitoring", {})
    paths = config["paths"]
    schema = config["schema"]

    ref_path = Path(monitoring_cfg.get("reference_data_path", paths["train_data"]))
    cur_path = Path(monitoring_cfg.get("current_data_path", paths["scored_data"]))

    if not ref_path.exists() or not cur_path.exists():
        logger.warning(
            f"Không tìm thấy dữ liệu so sánh. Reference: '{ref_path}', Current: '{cur_path}'. "
            "Cần có dữ liệu train và dữ liệu chấm điểm gần nhất để chạy monitoring."
        )
        return {"status": "SKIPPED", "reason": "Missing comparison files"}

    df_ref = load_data(ref_path)
    df_cur = load_data(cur_path)

    # 1. Kiểm tra PSI của Propensity Score (nếu cả 2 tập đều có score)
    score_col = "propensity_score"
    score_psi = None
    if score_col in df_ref.columns and score_col in df_cur.columns:
        score_psi = calculate_psi(df_ref[score_col].values, df_cur[score_col].values)
        logger.info(f"Prediction Score PSI: {score_psi:.4f}")

    # 2. Kiểm tra Drift các biến đặc trưng (Feature Drift)
    num_cols = schema["numerical_features"]
    drift_df = monitor_feature_drift(df_ref, df_cur, num_cols)

    # 3. Tạo báo cáo
    metrics_dir = Path(paths["metrics_dir"])
    metrics_dir.mkdir(parents=True, exist_ok=True)

    csv_out = metrics_dir / "feature_drift_summary.csv"
    drift_df.to_csv(csv_out, index=False)

    report = {
        "prediction_psi": round(score_psi, 4) if score_psi is not None else "N/A",
        "features_evaluated": len(drift_df),
        "stable_features_count": int((drift_df["status"] == "STABLE").sum()) if not drift_df.empty else 0,
        "warning_features_count": int((drift_df["status"] == "WARNING").sum()) if not drift_df.empty else 0,
        "drifted_features_count": int((drift_df["status"] == "ACTION_REQUIRED").sum()) if not drift_df.empty else 0,
        "drift_summary_file": str(csv_out),
    }

    json_out = metrics_dir / "monitoring_report.json"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    logger.info(f"Báo cáo Model Monitoring đã lưu tại: {json_out}")
    return report


if __name__ == "__main__":
    run_model_monitoring()
