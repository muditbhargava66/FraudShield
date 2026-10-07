"""
FraudShield package metadata.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

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
    "__version__",
]

try:
    __version__ = _distribution_version("fraudshield")
except PackageNotFoundError as exc:
    raise RuntimeError("FraudShield distribution metadata is missing; install the project with `uv sync` first.") from exc
