"""
FraudShield - Advanced Anomaly Detection Pipeline

This package provides the core functionality for the FraudShield fraud
detection system, integrating machine learning with optimized C++ backends.
It orchestrates data ingestion, preprocessing, training, and evaluation.

File: __init__.py
Author: Mudit Bhargava
License: MIT
"""
import os
from pathlib import Path

# Localize Airflow to the project root to prevent polluting the user's system
_project_root = Path(__file__).resolve().parent.parent.parent
_airflow_home = _project_root / ".airflow"
_airflow_db = _airflow_home / "airflow.db"

os.environ.setdefault("AIRFLOW_HOME", str(_airflow_home))
os.environ.setdefault("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", f"sqlite:///{_airflow_db}")
os.environ.setdefault("AIRFLOW__CORE__LOAD_EXAMPLES", "False")

if not _airflow_db.exists():
    import subprocess
    import sys

    _airflow_home.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [sys.executable, "-m", "airflow", "db", "migrate"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:  # pylint: disable=broad-exception-caught
        pass


__all__ = [
    "data_ingestion",
    "data_preprocessing",
    "feature_engineering",
    "model_training",
    "model_evaluation",
    "data_pipeline",
    "sql",
    "data_cleaning",
]

__version__ = "2.0.0"
