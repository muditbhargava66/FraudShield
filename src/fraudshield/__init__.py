"""
FraudShield package metadata.
"""

from fraudshield.config.settings import get_settings

__all__ = [
    "data_ingestion",
    "data_preprocessing",
    "feature_engineering",
    "model_training",
    "model_evaluation",
    "data_pipeline",
    "sql",
    "data_cleaning",
    "config",
    "runtime",
    "get_settings",
]

__version__ = "3.0.0"
