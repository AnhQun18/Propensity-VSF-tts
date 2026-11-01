"""
train.py
========
Huấn luyện, tuning hyperparameter, đánh giá toàn diện và lưu model.
Bao gồm các chỉ số vàng cho Propensity Modeling: ROC-AUC, PR-AUC, KS-statistic, Brier Score.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

from src.data_loader import load_config, load_data, validate_schema
from src.features import build_preprocessor_pipeline
from src.preprocessing import clean_raw_data, clip_outliers_iqr, split_data

logger = logging.getLogger(__name__)


def calculate_ks_statistic(y_true: np.ndarray, y_prob: np.ndarray) -> Tuple[float, float]:
    """
    Tính chỉ số Kolmogorov-Smirnov (KS Statistic) - thước đo chuẩn trong Credit & Propensity Scoring.
    KS càng cao (> 40%), khả năng phân tách nhóm phản ứng và không phản ứng càng tốt.
    """
    pos_probs = y_prob[y_true == 1]
    neg_probs = y_prob[y_true == 0]
    ks_res = ks_2samp(pos_probs, neg_probs)
    return float(ks_res.statistic), float(ks_res.pvalue)


def evaluate_propensity_model(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
    figures_dir: Optional[str] = "reports/figures",
    dataset_name: str = "Test",
) -> Dict[str, Any]:
    """
    Đánh giá chi tiết mô hình Propensity:
    - ROC-AUC & PR-AUC
    - KS Statistic
    - Brier Score
    - Precision, Recall, F1
    - Vẽ và lưu ROC Curve, PR Curve
    """
    y_pred = (y_prob >= threshold).astype(int)

    roc_auc = float(roc_auc_score(y_true, y_prob))
    pr_auc = float(average_precision_score(y_true, y_prob))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    brier = float(brier_score_loss(y_true, y_prob))
    ks_stat, _ = calculate_ks_statistic(y_true, y_prob)

    metrics = {
        "dataset": dataset_name,
        "sample_size": len(y_true),
        "positive_rate": float(np.mean(y_true)),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "ks_statistic": round(ks_stat, 4),
        "brier_score": round(brier, 4),
        "f1_score": round(f1, 4),
    }

    logger.info(
        f"[{dataset_name} Evaluation] ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f} | "
        f"KS: {ks_stat:.4f} | Brier: {brier:.4f} | F1: {f1:.4f}"
    )

    if figures_dir:
        Path(figures_dir).mkdir(parents=True, exist_ok=True)

        # 1. Vẽ ROC Curve
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        plt.figure(figsize=(6, 5))
        plt.plot(fpr, tpr, label=f"ROC curve (AUC = {roc_auc:.3f})", color="navy")
        plt.plot([0, 1], [0, 1], "r--")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title(f"ROC Curve - {dataset_name}")
        plt.legend(loc="lower right")
        plt.tight_layout()
        plt.savefig(f"{figures_dir}/roc_curve_{dataset_name.lower()}.png", dpi=150)
        plt.close()

        # 2. Vẽ PR Curve
        precision, recall, _ = precision_recall_curve(y_true, y_prob)
        plt.figure(figsize=(6, 5))
        plt.plot(recall, precision, label=f"PR curve (PR-AUC = {pr_auc:.3f})", color="darkgreen")
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.title(f"Precision-Recall Curve - {dataset_name}")
        plt.legend(loc="lower left")
        plt.tight_layout()
        plt.savefig(f"{figures_dir}/pr_curve_{dataset_name.lower()}.png", dpi=150)
        plt.close()

    return metrics


def get_model_instance(algorithm: str, params: Optional[Dict[str, Any]] = None):
    """
    Khởi tạo instance của mô hình dựa theo thuật toán chọn trong config.
    """
    params = params or {}
    algo = algorithm.lower()

    if algo == "lightgbm":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(**params)
    elif algo == "xgboost":
        from xgboost import XGBClassifier

        return XGBClassifier(**params)
    elif algo == "catboost":
        from catboost import CatBoostClassifier

        return CatBoostClassifier(**params, verbose=0)
    elif algo == "logistic_regression":
        return LogisticRegression(max_iter=1000, **params)
    else:
        raise ValueError(f"Thuật toán không được hỗ trợ: {algorithm}")


def run_pipeline(config_path: str = "configs/config.yaml"):
    """
    Chạy toàn bộ pipeline huấn luyện:
    1. Đọc config & nạp dữ liệu
    2. Kiểm tra schema & làm sạch thô
    3. Chia tập Train, Val, Test
    4. Fit Preprocessor (Tránh Data Leakage)
    5. Huấn luyện Model
    6. Đánh giá và lưu mô hình, biểu đồ, kết quả
    """
    config = load_config(config_path)
    paths = config["paths"]
    schema = config["schema"]
    model_cfg = config["model"]

    # 1. Nạp dữ liệu
    raw_path = paths["raw_data"]
    if not Path(raw_path).exists():
        logger.warning(
            f"Không tìm thấy file dữ liệu tại {raw_path}. "
            "Vui lòng đặt dữ liệu vào thư mục data/raw/ hoặc kiểm tra configs/config.yaml"
        )
        return

    df = load_data(raw_path)
    validate_schema(
        df,
        required_columns=[schema["target_column"]] + schema["numerical_features"] + schema["categorical_features"],
        id_column=schema["id_column"],
        target_column=schema["target_column"],
    )

    # 2. Làm sạch sơ bộ
    df_clean = clean_raw_data(
        df,
        target_col=schema["target_column"],
        drop_cols=schema.get("drop_columns", []),
        date_cols=schema.get("date_columns", []),
    )

    # 3. Chia tập dữ liệu TRƯỚC KHI transform
    train_df, val_df, test_df = split_data(
        df_clean,
        target_col=schema["target_column"],
        test_size=config["preprocessing"]["test_size"],
        val_size=config["preprocessing"]["val_size"],
        stratify=config["preprocessing"]["stratify"],
        random_state=config["project"]["random_seed"],
    )

    # 4. Outlier clipping trên train & áp dụng lên val/test
    num_cols = schema["numerical_features"]
    train_df, outlier_bounds = clip_outliers_iqr(train_df, numerical_cols=num_cols)
    if val_df is not None:
        val_df, _ = clip_outliers_iqr(val_df, numerical_cols=num_cols, bounds=outlier_bounds)
    test_df, _ = clip_outliers_iqr(test_df, numerical_cols=num_cols, bounds=outlier_bounds)

    # Tách X, y
    target = schema["target_column"]
    X_train, y_train = train_df.drop(columns=[target]), train_df[target].values
    X_val, y_val = (val_df.drop(columns=[target]), val_df[target].values) if val_df is not None else (None, None)
    X_test, y_test = test_df.drop(columns=[target]), test_df[target].values

    # 5. Lưu các tập dữ liệu đã chia (train/val/test) để phục vụ tái hiện và monitoring
    Path(paths["train_data"]).parent.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(paths["train_data"], index=False)
    test_df.to_csv(paths["test_data"], index=False)
    if val_df is not None:
        val_df.to_csv(paths["val_data"], index=False)

    # 6. Fit Feature Preprocessor
    cat_cols = schema["categorical_features"]
    preprocessor = build_preprocessor_pipeline(
        numerical_cols=num_cols,
        categorical_cols=cat_cols,
        rare_category_threshold=config["preprocessing"].get("rare_threshold", 0.02),
    )

    logger.info("Đang fit preprocessor trên tập train...")
    X_train_trans = preprocessor.fit_transform(X_train)
    X_test_trans = preprocessor.transform(X_test)
    X_val_trans = preprocessor.transform(X_val) if X_val is not None else None

    # Lấy tên đặc trưng để đảm bảo tương thích hoàn hảo giữa train và predict
    feature_names = preprocessor.get_feature_names_out()
    X_train_df = pd.DataFrame(X_train_trans, columns=feature_names)
    X_test_df = pd.DataFrame(X_test_trans, columns=feature_names)
    X_val_df = pd.DataFrame(X_val_trans, columns=feature_names) if X_val_trans is not None else None

    # 7. Khởi tạo và huấn luyện model
    algo_name = model_cfg["algorithm"]
    params = model_cfg.get(f"{algo_name}_params", {})
    logger.info(f"Đang huấn luyện mô hình {algo_name}...")
    model = get_model_instance(algo_name, params)
    model.fit(X_train_df, y_train)

    # 8. Đánh giá trên tập Test
    y_test_prob = model.predict_proba(X_test_df)[:, 1]
    metrics = evaluate_propensity_model(
        y_true=y_test,
        y_prob=y_test_prob,
        threshold=config["scoring"]["default_threshold"],
        figures_dir=paths["figures_dir"],
        dataset_name="Test",
    )

    # 9. Lưu model và artifact
    Path(paths["model_dir"]).mkdir(parents=True, exist_ok=True)
    Path(paths["metrics_dir"]).mkdir(parents=True, exist_ok=True)

    joblib.dump(model, paths["model_path"])
    joblib.dump(preprocessor, paths["preprocessor_path"])
    joblib.dump(outlier_bounds, Path(paths["model_dir"]) / "outlier_bounds.joblib")

    with open(Path(paths["metrics_dir"]) / "evaluation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)

    logger.info(f"Hoàn thành huấn luyện! Đã lưu model tại: {paths['model_path']}")


if __name__ == "__main__":
    run_pipeline()
