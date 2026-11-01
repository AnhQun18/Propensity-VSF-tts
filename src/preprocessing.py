"""
preprocessing.py
================
Làm sạch, xử lý missing, xử lý outlier và chia tập dữ liệu (Train/Val/Test).
QUAN TRỌNG: Chia tập dữ liệu TRƯỚC KHI fit bất kỳ transformer nào để tránh rò rỉ dữ liệu (Data Leakage).
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


def clean_raw_data(
    df: pd.DataFrame,
    target_col: Optional[str] = None,
    drop_cols: Optional[List[str]] = None,
    date_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Thực hiện tiền xử lý thô:
    - Loại bỏ bản ghi thiếu nhãn mục tiêu (target)
    - Định dạng kiểu dữ liệu ngày tháng
    - Loại bỏ các cột thừa/nhạy cảm
    """
    df_clean = df.copy()

    # 1. Loại bỏ các dòng thiếu target (nếu có cột target)
    if target_col and target_col in df_clean.columns:
        missing_target = df_clean[target_col].isnull().sum()
        if missing_target > 0:
            logger.info(f"Loại bỏ {missing_target:,} dòng thiếu giá trị mục tiêu '{target_col}'")
            df_clean = df_clean.dropna(subset=[target_col])

    # 2. Xử lý định dạng ngày tháng
    if date_cols:
        for col in date_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_datetime(df_clean[col], errors="coerce")

    # 3. Loại bỏ cột thừa
    if drop_cols:
        existing_drops = [c for c in drop_cols if c in df_clean.columns]
        if existing_drops:
            df_clean = df_clean.drop(columns=existing_drops)
            logger.info(f"Đã loại bỏ các cột không dùng: {existing_drops}")

    return df_clean


def clip_outliers_iqr(
    df: pd.DataFrame,
    numerical_cols: List[str],
    iqr_multiplier: float = 1.5,
    bounds: Optional[Dict[str, Tuple[float, float]]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Tuple[float, float]]]:
    """
    Xử lý outlier bằng phương pháp kẹp giá trị (Clipping) theo IQR.
    Nếu bounds=None (ở bước train), tính toán và trả về ngưỡng [lower_bound, upper_bound].
    Nếu bounds đã được cung cấp (ở bước test/inference), tái sử dụng ngưỡng để tránh Data Leakage.
    """
    df_clipped = df.copy()
    calculated_bounds = bounds.copy() if bounds else {}

    for col in numerical_cols:
        if col not in df_clipped.columns:
            continue

        if bounds and col in bounds:
            lower_bound, upper_bound = bounds[col]
        else:
            q25 = df_clipped[col].quantile(0.25)
            q75 = df_clipped[col].quantile(0.75)
            iqr = q75 - q25
            lower_bound = q25 - (iqr_multiplier * iqr)
            upper_bound = q75 + (iqr_multiplier * iqr)
            calculated_bounds[col] = (float(lower_bound), float(upper_bound))

        df_clipped[col] = df_clipped[col].clip(lower=lower_bound, upper=upper_bound)

    return df_clipped, calculated_bounds


def split_data(
    df: pd.DataFrame,
    target_col: str,
    test_size: float = 0.2,
    val_size: float = 0.1,
    stratify: bool = True,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
    """
    Chia dữ liệu thành Train, Validation và Test sets.
    Bảo đảm phân phối nhãn đồng đều qua tham số stratify.
    """
    logger.info(f"Bắt đầu chia tập dữ liệu: test_size={test_size}, val_size={val_size}")

    stratify_target = df[target_col] if stratify else None

    # Tách tập Test trước
    train_val_df, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_target,
    )

    val_df = None
    if val_size > 0:
        # Tỷ lệ validation trên tập còn lại
        adjusted_val_size = val_size / (1.0 - test_size)
        stratify_val = train_val_df[target_col] if stratify else None
        train_df, val_df = train_test_split(
            train_val_df,
            test_size=adjusted_val_size,
            random_state=random_state,
            stratify=stratify_val,
        )
    else:
        train_df = train_val_df

    logger.info(
        f"Kích thước tập dữ liệu sau khi chia - "
        f"Train: {train_df.shape[0]:,}, "
        f"Val: {val_df.shape[0] if val_df is not None else 0:,}, "
        f"Test: {test_df.shape[0]:,}"
    )

    return train_df, val_df, test_df
