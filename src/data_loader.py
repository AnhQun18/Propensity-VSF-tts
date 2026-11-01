"""
data_loader.py
==============
Đọc và kiểm tra schema dữ liệu (Schema Validation & Data Ingestion).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_config(config_path: Union[str, Path] = "configs/config.yaml") -> Dict[str, Any]:
    """
    Đọc file cấu hình YAML của dự án.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình tại: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logger.info(f"Đã nạp file cấu hình từ {path}")
    return config


def load_data(file_path: Union[str, Path], **kwargs) -> pd.DataFrame:
    """
    Đọc dữ liệu từ file csv, parquet hoặc excel.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Tập dữ liệu không tồn tại: {path}")

    suffix = path.suffix.lower()
    logger.info(f"Đang đọc dữ liệu từ: {path} (định dạng: {suffix})")

    if suffix in [".csv", ".txt"]:
        df = pd.read_csv(path, **kwargs)
    elif suffix in [".parquet", ".pq"]:
        df = pd.read_parquet(path, **kwargs)
    elif suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(path, **kwargs)
    else:
        raise ValueError(f"Định dạng file không hỗ trợ: {suffix}")

    logger.info(f"Nạp dữ liệu thành công! Kích thước: {df.shape[0]:,} dòng, {df.shape[1]} cột")
    return df


def validate_schema(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    id_column: Optional[str] = None,
    target_column: Optional[str] = None,
    max_missing_ratio: float = 0.5,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Kiểm tra tính hợp lệ của schema dữ liệu:
    - Sự hiện diện của các cột bắt buộc
    - Kiểm tra trùng lặp khóa chính (ID)
    - Kiểm tra nhãn mục tiêu (target)
    - Tỷ lệ dữ liệu bị thiếu (missing values)
    """
    validation_report = {
        "is_valid": True,
        "missing_columns": [],
        "duplicate_id_count": 0,
        "high_missing_columns": [],
        "target_distribution": None,
    }

    # 1. Kiểm tra các cột bắt buộc
    if required_columns:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            validation_report["missing_columns"] = missing_cols
            validation_report["is_valid"] = False
            logger.error(f"Thiếu các cột bắt buộc trong schema: {missing_cols}")

    # 2. Kiểm tra trùng lặp ID
    if id_column and id_column in df.columns:
        duplicate_count = df.duplicated(subset=[id_column]).sum()
        validation_report["duplicate_id_count"] = int(duplicate_count)
        if duplicate_count > 0:
            logger.warning(f"Phát hiện {duplicate_count:,} bản ghi trùng lặp '{id_column}'")

    # 3. Kiểm tra cột target
    if target_column and target_column in df.columns:
        target_dist = df[target_column].value_counts(dropna=False, normalize=True).to_dict()
        validation_report["target_distribution"] = target_dist
        logger.info(f"Phân phối nhãn mục tiêu '{target_column}': {target_dist}")

    # 4. Kiểm tra missing values
    missing_ratio = df.isnull().mean()
    high_missing = missing_ratio[missing_ratio > max_missing_ratio].to_dict()
    if high_missing:
        validation_report["high_missing_columns"] = high_missing
        logger.warning(f"Các cột có tỷ lệ missing > {max_missing_ratio*100}%: {high_missing}")

    return validation_report["is_valid"], validation_report


if __name__ == "__main__":
    # Test thử load config
    try:
        cfg = load_config()
        print("Cấu hình dự án:", cfg.get("project"))
    except Exception as e:
        logger.warning(f"Chưa chạy được test: {e}")
