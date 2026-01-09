import json
import os
from datetime import datetime
from typing import Dict, Any, List

from .currencies import get_currency
from .exceptions import ValutaTradeError, CurrencyNotFoundError
from ..infra.database import db


def read_json_file(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def write_json_file(file_path: str, data: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def datetime_to_str(dt: datetime) -> str:
    return dt.isoformat()


def str_to_datetime(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str)


def get_next_user_id() -> int:
    users_data = db.read("users")
    if not users_data:
        return 1
    return max(user.get("user_id", 0) for user in users_data) + 1


def validate_currency_code(currency_code: str) -> bool:
    try:
        get_currency(currency_code.upper())
        return True
    except CurrencyNotFoundError:
        return False


def convert_amount(amount: float,
                   from_currency: str,
                   to_currency: str,
                   rates: Dict[str, Any]) -> float:
    if from_currency == to_currency:
        return amount

    direct_pair = f"{from_currency}_{to_currency}"
    if direct_pair in rates:
        return amount * rates[direct_pair]["rate"]
    from_to_usd = f"{from_currency}_USD"
    usd_to_to = f"USD_{to_currency}"

    if from_to_usd in rates and usd_to_to in rates:
        usd_amount = amount * rates[from_to_usd]["rate"]
        return usd_amount * rates[usd_to_to]["rate"]

    raise ValutaTradeError(f"Не удалось конвертировать {from_currency} в {to_currency}")


def format_currency_amount(amount: float, currency_code: str) -> str:
    if currency_code in ["BTC", "ETH", "LTC"]:
        return f"{amount:.6f}"
    else:
        return f"{amount:.2f}"
