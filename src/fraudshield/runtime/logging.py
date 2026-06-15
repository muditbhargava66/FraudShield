"""
Central logging bootstrap helpers for FraudShield entrypoints.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fraudshield.config.settings import LoggingSettings, RuntimeSettings, get_settings

STREAM_HANDLER_NAME = "fraudshield-stream"
FILE_HANDLER_NAME = "fraudshield-file"


def _resolve_level(level_name: str | None, fallback: str) -> int:
    candidate = (level_name or fallback).upper()
    resolved = logging.getLevelName(candidate)
    if isinstance(resolved, str):
        resolved = logging.getLevelName(fallback.upper())
    return int(resolved)


def _iter_fraudshield_handlers(root_logger: logging.Logger) -> list[logging.Handler]:
    return [handler for handler in root_logger.handlers if (handler.get_name() or "").startswith("fraudshield-")]


def _ensure_stream_handler(root_logger: logging.Logger, settings: LoggingSettings, level: int) -> None:
    if not settings.enable_console:
        return
    for handler in root_logger.handlers:
        if handler.get_name() == STREAM_HANDLER_NAME:
            handler.setLevel(level)
            handler.setFormatter(logging.Formatter(settings.format))
            return

    handler = logging.StreamHandler()
    handler.set_name(STREAM_HANDLER_NAME)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(settings.format))
    root_logger.addHandler(handler)


def _ensure_file_handler(root_logger: logging.Logger, settings: LoggingSettings, level: int, component: str) -> None:
    existing = next((handler for handler in root_logger.handlers if handler.get_name() == FILE_HANDLER_NAME), None)
    log_path = settings.directory / f"{component}.log"
    settings.directory.mkdir(parents=True, exist_ok=True)

    if existing is not None:
        existing_path = Path(getattr(existing, "baseFilename", ""))
        if existing_path == log_path:
            existing.setLevel(level)
            existing.setFormatter(logging.Formatter(settings.format))
            return
        root_logger.removeHandler(existing)
        existing.close()

    if not settings.enable_file:
        return

    handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.max_bytes,
        backupCount=settings.backup_count,
    )
    handler.set_name(FILE_HANDLER_NAME)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(settings.format))
    root_logger.addHandler(handler)


def configure_logging(
    settings: RuntimeSettings | None = None,
    *,
    component: str = "fraudshield",
    level: str | None = None,
    force: bool = False,
) -> logging.Logger:
    resolved = settings or get_settings()
    normalized_component = component.strip().replace(" ", "_").replace("/", "_") or "fraudshield"
    level_value = _resolve_level(level, resolved.logging.level)
    root_logger = logging.getLogger()

    if force:
        for handler in _iter_fraudshield_handlers(root_logger):
            root_logger.removeHandler(handler)
            handler.close()

    root_logger.setLevel(level_value)
    _ensure_stream_handler(root_logger, resolved.logging, level_value)
    _ensure_file_handler(root_logger, resolved.logging, level_value, normalized_component)
    return logging.getLogger(normalized_component)
