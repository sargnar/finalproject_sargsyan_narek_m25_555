# valutatrade_hub/logging_config.py
import logging
import logging.handlers
import os

from .infra.settings import settings


def setup_logging():
    """Настраивает логирование для приложения"""
    log_dir = settings.get("log_dir", "logs")
    log_level = settings.get("log_level", "INFO").upper()

    os.makedirs(log_dir, exist_ok=True)

    # Простой формат без дополнительных полей
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Обработчик для файла
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Настройка корневого логгера
    root_logger = logging.getLogger("valutatrade_hub")
    root_logger.setLevel(log_level)

    # Удаляем старые обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addHandler(file_handler)

    # Консольный обработчик для разработки
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Возвращает настроенный логгер"""
    return logging.getLogger(f"valutatrade_hub.{name}")


# Автоматическая настройка при импорте
setup_logging()
