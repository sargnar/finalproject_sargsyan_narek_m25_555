import functools
from typing import Any, Callable

from .logging_config import get_logger


def log_action(action_name: str, verbose: bool = False):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(func.__module__)

            try:
                # Выполняем функцию
                result = func(*args, **kwargs)

                # Логируем успех
                logger.info(
                    f"Action {action_name} completed successfully",
                    extra={"action": action_name, "result": "OK"}
                )
                return result

            except Exception as e:
                # Логируем ошибку
                logger.error(
                    f"Action {action_name} failed: {str(e)}",
                    extra={"action": action_name, "result": "ERROR", "error": str(e)}
                )
                raise

        return wrapper

    return decorator
