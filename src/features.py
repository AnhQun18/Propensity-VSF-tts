"""
features.py
===========
Các hàm và class Feature Engineering đóng gói theo chuẩn Scikit-learn Pipeline.
Hỗ trợ chuyển đổi đặc trưng số (numeric), phân loại (categorical), và tạo đặc trưng mới.
"""

import logging
from typing import List, Optional

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler, StandardScaler

logger = logging.getLogger(__name__)


class RareCategoryEncoder(BaseEstimator, TransformerMixin):
    """
    Gộp các nhóm danh mục có tần suất xuất hiện quá thấp (< threshold) thành nhóm 'Other'.
    Giúp tránh overfitting và giải quyết vấn đề nhãn mới khi đưa vào production.
    """

    def __init__(self, threshold: float = 0.02, fill_value: str = "Other"):
        self.threshold = threshold
        self.fill_value = fill_value
        self.frequent_categories_: dict = {}

    def fit(self, X, y=None):
        X_df = pd.DataFrame(X)
        self.frequent_categories_ = {}
        for col in X_df.columns:
            freq = X_df[col].value_counts(normalize=True)
            frequent = freq[freq >= self.threshold].index.tolist()
            self.frequent_categories_[col] = frequent
        return self

    def transform(self, X):
        X_df = pd.DataFrame(X).copy()
        for col in X_df.columns:
            if col in self.frequent_categories_:
                frequent = self.frequent_categories_[col]
                X_df[col] = X_df[col].apply(lambda val: val if val in frequent else self.fill_value)
        return X_df

    def get_feature_names_out(self, input_features=None):
        if input_features is not None:
            return np.array(input_features, dtype=object)
        return np.array(list(self.frequent_categories_.keys()), dtype=object)


class DomainFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Tạo các chỉ số đặc trưng bổ sung đặc thù cho bài toán Propensity:
    - avg_spend_per_session = total_spend / (app_sessions + 1)
    - spend_per_tenure = total_spend / (tenure_months + 1)
    """

    def __init__(self):
        pass

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X_df = pd.DataFrame(X).copy()

        if "total_spend" in X_df.columns and "tenure_months" in X_df.columns:
            X_df["spend_per_tenure"] = X_df["total_spend"] / (X_df["tenure_months"] + 1)

        if "total_spend" in X_df.columns and "app_sessions_last_30d" in X_df.columns:
            X_df["spend_per_session"] = X_df["total_spend"] / (X_df["app_sessions_last_30d"] + 1)

        return X_df


def build_preprocessor_pipeline(
    numerical_cols: List[str],
    categorical_cols: List[str],
    scale_numeric: bool = True,
    numeric_scaler: str = "robust",  # 'robust' hoặc 'standard'
    rare_category_threshold: float = 0.02,
) -> ColumnTransformer:
    """
    Xây dựng Scikit-Learn ColumnTransformer chuẩn:
    - Numerical: Impute median -> [Tùy chọn RobustScaler/StandardScaler]
    - Categorical: Impute 'missing' -> RareCategoryEncoder -> OneHotEncoder
    """
    logger.info("Khởi tạo Scikit-learn Preprocessing Pipeline...")

    # Numerical Transformer
    num_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        scaler = RobustScaler() if numeric_scaler == "robust" else StandardScaler()
        num_steps.append(("scaler", scaler))
    num_pipeline = Pipeline(steps=num_steps)

    # Categorical Transformer
    cat_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
            ("rare_encoder", RareCategoryEncoder(threshold=rare_category_threshold)),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipeline, numerical_cols),
            ("cat", cat_pipeline, categorical_cols),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    return preprocessor


def get_feature_names_from_preprocessor(preprocessor: ColumnTransformer) -> List[str]:
    """
    Lấy danh sách tên đặc trưng sau khi qua ColumnTransformer.
    """
    try:
        return list(preprocessor.get_feature_names_out())
    except Exception:
        return []
