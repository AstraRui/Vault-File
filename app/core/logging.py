import logging
import logging.handlers
from pathlib import Path

from app.core.config import Settings

LOG_DIR = Path("logs")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 5


def setup_logging(settings: Settings) -> None:
    """Настраивает корневой логгер: вывод в консоль (для Docker) и ротируемые файлы.

    app.log хранит все события от уровня settings.log_level и выше,
    error.log дублирует только ERROR/CRITICAL для быстрой диагностики сбоев.
    """
    LOG_DIR.mkdir(exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    app_file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    app_file_handler.setFormatter(formatter)

    error_file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "error.log",
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_file_handler.setFormatter(formatter)
    error_file_handler.setLevel(logging.ERROR)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(app_file_handler)
    root_logger.addHandler(error_file_handler)

    # uvicorn ведёт собственные логгеры поверх root — просто выравниваем уровень
    logging.getLogger("uvicorn").setLevel(settings.log_level)
    logging.getLogger("uvicorn.access").setLevel(settings.log_level)
