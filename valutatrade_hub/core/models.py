import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional

from .exceptions import InsufficientFundsError


class User:
    def __init__(self, user_id: int, username: str, hashed_password: str,
                 salt: str, registration_date: datetime):
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def get_user_info(self) -> str:
        return (f"User ID: {self._user_id}, "
                f"Username: {self._username}, "
                f"Registered: {self._registration_date}")

    def change_password(self, new_password: str):
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        new_salt = secrets.token_hex(8)
        new_hashed_password = self._hash_password(new_password, new_salt)

        self._hashed_password = new_hashed_password
        self._salt = new_salt

    def verify_password(self, password: str) -> bool:
        test_hash = self._hash_password(password, self._salt)
        return test_hash == self._hashed_password

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self._balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float):
        if not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float):
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма пополнения должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")
        self.balance += amount

    def withdraw(self, amount: float):
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма снятия должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной")
        if amount > self._balance:
            raise InsufficientFundsError(
                self.currency_code, self._balance, amount
            )
        self.balance -= amount

    def get_balance_info(self) -> str:
        return f"{self.currency_code}: {self._balance:.4f}"


class Portfolio:

    def __init__(self, user_id: int, wallets: Optional[Dict[str, Wallet]] = None):
        self._user_id = user_id
        self._wallets = wallets or {}

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> Dict[str, Wallet]:
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        from .currencies import get_currency

        currency_code = currency_code.upper()
        get_currency(currency_code)  # валидация

        if currency_code not in self._wallets:
            self._wallets[currency_code] = Wallet(currency_code)

        return self._wallets[currency_code]

    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        currency_code = currency_code.upper()
        return self._wallets.get(currency_code)

    def get_total_value(self, base_currency: str = "USD") -> float:
        exchange_rates = {
            "EUR_USD": 1.07,
            "BTC_USD": 59337.21,
            "ETH_USD": 3720.00,
            "RUB_USD": 0.01016,
            "LTC_USD": 85.50,
        }

        total_value = 0.0

        for wallet in self._wallets.values():
            if wallet.currency_code == base_currency:
                total_value += wallet.balance
            else:
                rate_key = f"{wallet.currency_code}_{base_currency}"
                if rate_key in exchange_rates:
                    total_value += wallet.balance * exchange_rates[rate_key]
                else:
                    usd_rate_key = f"{wallet.currency_code}_USD"
                    if usd_rate_key in exchange_rates:
                        usd_value = wallet.balance * exchange_rates[usd_rate_key]
                        if base_currency != "USD":
                            base_rate_key = f"USD_{base_currency}"
                            if base_rate_key in exchange_rates:
                                total_value += usd_value * exchange_rates[base_rate_key]

        return total_value
