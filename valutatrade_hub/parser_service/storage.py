import json
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List
import hashlib

from ..core.utils import datetime_to_str, str_to_datetime
from .config import config


class RatesStorage:
    def save_current_rates(self, rates: Dict[str, float], source_meta: Dict[str, Any]):
        if not rates:
            return

        clean_rates = {k: v for k, v in rates.items() if not k.startswith("_")}

        pairs_data = {}
        timestamp = datetime.now()

        for pair, rate in clean_rates.items():
            pairs_data[pair] = {
                "rate": rate,
                "updated_at": datetime_to_str(timestamp),
                "source": source_meta.get("source", "Unknown")
            }

        data = {
            "pairs": pairs_data,
            "last_refresh": datetime_to_str(timestamp),
            "source": source_meta.get("source", "Unknown")
        }

        try:
            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(config.RATES_FILE_PATH),
                prefix=".rates_temp_",
                suffix=".json"
            )

            try:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)

                os.replace(temp_path, config.RATES_FILE_PATH)

            except Exception:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise

        except Exception as e:
            raise RuntimeError(f"Ошибка сохранения rates.json: {str(e)}")

    def save_historical_record(self, rates: Dict[str, float],
                               source_meta: Dict[str, Any]):
        if not rates:
            return

        clean_rates = {k: v for k, v in rates.items() if not k.startswith("_")}
        timestamp = datetime.now()

        historical_data = self._load_historical_data()

        for pair, rate in clean_rates.items():
            record_id = self._generate_record_id(pair, timestamp)

            record = {
                "id": record_id,
                "from_currency": pair.split("_")[0],
                "to_currency": pair.split("_")[1],
                "rate": rate,
                "timestamp": datetime_to_str(timestamp),
                "source": source_meta.get("source", "Unknown"),
                "meta": {
                    "raw_id": source_meta.get("raw_id", ""),
                    "request_ms": source_meta
                        .get("request_meta", {})
                        .get("request_ms", 0),
                    "status_code": source_meta
                        .get("request_meta", {})
                        .get("status_code", 0),
                    "etag": source_meta
                        .get("request_meta", {})
                        .get("etag", ""),
                    "base_currency": source_meta.get("base_currency", "")
                }
            }

            historical_data.append(record)

        self._save_historical_data(historical_data)

    def _load_historical_data(self) -> List[Dict[str, Any]]:
        try:
            if os.path.exists(config.HISTORY_FILE_PATH):
                with open(config.HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass

        return []

    def _save_historical_data(self, data: List[Dict[str, Any]]):
        try:
            os.makedirs(os.path.dirname(config.HISTORY_FILE_PATH), exist_ok=True)

            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(config.HISTORY_FILE_PATH),
                prefix=".history_temp_",
                suffix=".json"
            )

            try:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)

                os.replace(temp_path, config.HISTORY_FILE_PATH)

            except Exception:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise

        except Exception as e:
            raise RuntimeError(f"Ошибка сохранения исторических данных: {str(e)}")

    def _generate_record_id(self, pair: str, timestamp: datetime) -> str:
        timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        base_string = f"{pair}_{timestamp_str}"
        return hashlib.md5(base_string.encode()).hexdigest()[:16]

    def get_current_rates(self) -> Dict[str, Any]:
        try:
            if os.path.exists(config.RATES_FILE_PATH):
                with open(config.RATES_FILE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass

        return {"pairs": {}, "last_refresh": None}

    def cleanup_old_records(self, max_age_days: int = 30) -> int:
        try:
            data = self._load_historical_data()
            if not data:
                return 0

            cutoff_date = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)

            filtered_data = [
                record for record in data
                if str_to_datetime(record["timestamp"]).timestamp() > cutoff_date
            ]

            if len(filtered_data) < len(data):
                self._save_historical_data(filtered_data)
                return len(data) - len(filtered_data)

        except Exception as e:
            raise RuntimeError(f"Ошибка очистки исторических данных: {str(e)}")

        return 0
