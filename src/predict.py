"""
predict.py
==========
Chấm điểm Propensity (Propensity Scoring) cho khách hàng mới.
Tự động tính xác suất, phân hạng Decile (Top 10% tiềm năng nhất) và xuất báo cáo Lift.
"""

import logging
from pathlib import Path
from typing import Optional, Union

import joblib
import numpy as np
import pandas as pd

from src.data_loader import load_config, load_data
from src.preprocessing import clean_raw_data, clip_outliers_iqr

logger = logging.getLogger(__name__)


def assign_deciles(scores: np.ndarray, num_deciles: int = 10) -> np.ndarray:
    """
    Phân chia điểm xác suất thành các phân vị (Deciles).
    Decile 1 đại diện cho nhóm khách hàng có xác suất (propensity) cao nhất (Top 10%).
    """
    ranks = pd.Series(scores).rank(ascending=False, method="first")
    deciles = pd.qcut(ranks, q=num_deciles, labels=list(range(1, num_deciles + 1)))
    return deciles.to_numpy()


def generate_decile_summary(df_scored: pd.DataFrame, score_col: str, decile_col: str) -> pd.DataFrame:
    """
    Tạo bảng tổng hợp theo Decile hỗ trợ đội ngũ Marketing nhắm mục tiêu chiến dịch.
    """
    summary = (
        df_scored.groupby(decile_col)
        .agg(
            customer_count=(score_col, "count"),
            min_propensity=(score_col, "min"),
            max_propensity=(score_col, "max"),
            avg_propensity=(score_col, "mean"),
        )
        .reset_index()
    )

    total_customers = len(df_scored)
    summary["customer_pct"] = summary["customer_count"] / total_customers
    summary["cum_customer_pct"] = summary["customer_pct"].cumsum()
    return summary


def score_new_customers(
    data_path: Union[str, Path],
    config_path: Union[str, Path] = "configs/config.yaml",
    output_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """
    Pipeline chấm điểm toàn diện cho tập khách hàng mới:
    1. Tải model, preprocessor, outlier bounds
    2. Tiền xử lý dữ liệu mới
    3. Dự đoán propensity score
    4. Gán phân vị Decile và nhãn theo threshold
    5. Xuất file kết quả
    """
    config = load_config(config_path)
    paths = config["paths"]
    schema = config["schema"]
    scoring_cfg = config["scoring"]

    # Kiểm tra sự tồn tại của mô hình
    model_path = Path(paths["model_path"])
    preprocessor_path = Path(paths["preprocessor_path"])
    outlier_bounds_path = Path(paths["model_dir"]) / "outlier_bounds.joblib"

    if not model_path.exists() or not preprocessor_path.exists():
        raise FileNotFoundError(
            f"Chưa tìm thấy model đã huấn luyện tại '{model_path}'. "
            "Vui lòng chạy `python -m src.train` trước khi chấm điểm."
        )

    logger.info("Đang nạp mô hình và preprocessor...")
    model = joblib.load(model_path)
    preprocessor = joblib.load(preprocessor_path)
    outlier_bounds = joblib.load(outlier_bounds_path) if outlier_bounds_path.exists() else None

    # Nạp dữ liệu mới
    df_new = load_data(data_path)
    df_features = clean_raw_data(
        df_new,
        target_col=None,
        drop_cols=schema.get("drop_columns", []),
        date_cols=schema.get("date_columns", []),
    )

    # Áp dụng outlier bounds
    num_cols = schema["numerical_features"]
    if outlier_bounds:
        df_features, _ = clip_outliers_iqr(df_features, numerical_cols=num_cols, bounds=outlier_bounds)

    # Transform qua preprocessor pipeline
    X_trans = preprocessor.transform(df_features)
    feature_names = preprocessor.get_feature_names_out()
    X_df = pd.DataFrame(X_trans, columns=feature_names)

    # Chấm điểm xác suất
    logger.info("Đang tính toán Propensity Scores...")
    propensity_scores = model.predict_proba(X_df)[:, 1]

    # Phân nhóm Deciles (1 = cao nhất, 10 = thấp nhất)
    deciles = assign_deciles(propensity_scores, num_deciles=scoring_cfg.get("num_deciles", 10))
    threshold = scoring_cfg.get("default_threshold", 0.5)
    binary_preds = (propensity_scores >= threshold).astype(int)

    # Đính kèm kết quả vào dataframe gốc
    df_result = df_new.copy()
    df_result["propensity_score"] = np.round(propensity_scores, 4)
    df_result["propensity_decile"] = deciles
    df_result["is_targeted"] = binary_preds

    # Tổng kết bảng Decile
    decile_summary = generate_decile_summary(
        df_result, score_col="propensity_score", decile_col="propensity_decile"
    )
    logger.info("\n=== BẢNG TỔNG HỢP THEO DECILE ===\n" + decile_summary.to_string(index=False))

    # Lưu kết quả
    save_dest = Path(output_path or paths["scored_data"])
    save_dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        if save_dest.suffix == ".parquet":
            df_result.to_parquet(save_dest, index=False)
        else:
            df_result.to_csv(save_dest, index=False)
    except Exception as e:
        csv_fallback = save_dest.with_suffix(".csv")
        logger.warning(f"Không thể lưu định dạng {save_dest.suffix} ({e}). Tự động lưu sang định dạng CSV: {csv_fallback}")
        df_result.to_csv(csv_fallback, index=False)
        save_dest = csv_fallback

    logger.info(f"Đã lưu kết quả chấm điểm khách hàng tại: {save_dest}")
    return df_result


if __name__ == "__main__":
    import sys

    input_file = sys.argv[1] if len(sys.argv) > 1 else "data/raw/customer_data.csv"
    try:
        score_new_customers(input_file)
    except Exception as e:
        logger.error(f"Lỗi khi thực thi chấm điểm: {e}")
