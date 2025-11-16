import json
import os
import threading
from typing import Any, Dict, List, Optional

from ..core.exceptions import DatabaseError
from .settings import settings


class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if not getattr(self, "_initialized", False):
            self.data_dir = settings.get("data_dir", "data")
            self._initialized = True

    def _get_file_path(self, entity: str) -> str:
        return os.path.join(self.data_dir, f"{entity}.json")

    def read(self, entity: str) -> List[Dict[str, Any]]:
        file_path = self._get_file_path(entity)

        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise DatabaseError(f"Ошибка чтения файла {file_path}: {e}")
        except Exception as e:
            raise DatabaseError(f"Неожиданная ошибка при чтении {file_path}: {e}")

    def write(self, entity: str, data: List[Dict[str, Any]]):
        file_path = self._get_file_path(entity)

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            raise DatabaseError(f"Ошибка записи в файл {file_path}: {e}")

    def find_one(self, entity: str, **filters) -> Optional[Dict[str, Any]]:
        data = self.read(entity)
        for item in data:
            if all(item.get(k) == v for k, v in filters.items()):
                return item
        return None

    def find_all(self, entity: str, **filters) -> List[Dict[str, Any]]:
        data = self.read(entity)
        if not filters:
            return data

        return [item for item in data
                if all(item.get(k) == v for k, v in filters.items())]

    def insert(self, entity: str, record: Dict[str, Any]):
        data = self.read(entity)
        data.append(record)
        self.write(entity, data)

    def update(self, entity: str, filters: Dict[str, Any], updates: Dict[str, Any]):
        data = self.read(entity)
        updated = False

        for item in data:
            if all(item.get(k) == v for k, v in filters.items()):
                item.update(updates)
                updated = True

        if updated:
            self.write(entity, data)

    def delete(self, entity: str, **filters):
        data = self.read(entity)
        initial_count = len(data)

        data = [item for item in data
                if not all(item.get(k) == v for k, v in filters.items())]

        if len(data) < initial_count:
            self.write(entity, data)


db = DatabaseManager()
