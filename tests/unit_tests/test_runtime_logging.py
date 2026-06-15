import logging

from fraudshield.config.settings import get_settings
from fraudshield.runtime.logging import configure_logging


def _fraudshield_handlers() -> list[logging.Handler]:
    return [handler for handler in logging.getLogger().handlers if (handler.get_name() or "").startswith("fraudshield-")]


def test_configure_logging_writes_to_component_file(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    monkeypatch.setenv("FRAUDSHIELD_LOG_DIR", str(log_dir))
    monkeypatch.setenv("FRAUDSHIELD_LOG_LEVEL", "INFO")
    get_settings.cache_clear()

    configure_logging(component="unit_test_logging", force=True)
    logger = logging.getLogger("fraudshield.tests.logging")
    logger.info("runtime logging smoke test")

    for handler in _fraudshield_handlers():
        handler.flush()

    log_path = log_dir / "unit_test_logging.log"
    assert log_path.exists()
    assert "runtime logging smoke test" in log_path.read_text()


def test_configure_logging_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAUDSHIELD_LOG_DIR", str(tmp_path / "logs"))
    get_settings.cache_clear()

    configure_logging(component="idempotent", force=True)
    configure_logging(component="idempotent")

    handler_names = [handler.get_name() for handler in _fraudshield_handlers()]
    assert handler_names.count("fraudshield-stream") == 1
    assert handler_names.count("fraudshield-file") == 1
