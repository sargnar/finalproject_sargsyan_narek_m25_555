import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from .models import User, Wallet, Portfolio
from .currencies import get_currency
from .exceptions import (
    CurrencyNotFoundError,
    ApiRequestError, UserNotFoundError, PortfolioNotFoundError
)
from .utils import get_next_user_id, datetime_to_str, str_to_datetime
from ..infra.database import db
from ..infra.settings import settings
from ..decorators import log_action


class UserManager:
    def __init__(self):
        self.current_user: Optional[User] = None

    @log_action("REGISTER", verbose=True)
    def register_user(self, username: str, password: str) -> Dict[str, Any]:
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        users_data = db.read("users")

        for user_data in users_data:
            if user_data.get("username") == username:
                raise ValueError(f"Имя пользователя '{username}' уже занято")

        user_id = get_next_user_id()
        salt = os.urandom(16).hex()
        hashed_password = self._hash_password(password, salt)
        registration_date = datetime.now()

        user = User(user_id, username, hashed_password, salt, registration_date)

        user_data = {
            "user_id": user.user_id,
            "username": user.username,
            "hashed_password": user.hashed_password,
            "salt": user.salt,
            "registration_date": datetime_to_str(user.registration_date)
        }

        db.insert("users", user_data)

        self._create_empty_portfolio(user_id)

        return {
            "user_id": user_id,
            "username": username,
            "registration_date": registration_date
        }

    @log_action("LOGIN")
    def login_user(self, username: str, password: str) -> User:
        users_data = db.read("users")

        user_data = None
        for data in users_data:
            if data.get("username") == username:
                user_data = data
                break

        if not user_data:
            raise UserNotFoundError(f"Пользователь '{username}' не найден")

        user = User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            hashed_password=user_data["hashed_password"],
            salt=user_data["salt"],
            registration_date=str_to_datetime(user_data["registration_date"])
        )

        if not user.verify_password(password):
            raise ValueError("Неверный пароль")

        self.current_user = user
        return user

    def logout_user(self):
        self.current_user = None

    def _hash_password(self, password: str, salt: str) -> str:
        import hashlib
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

    def _create_empty_portfolio(self, user_id: int):
        portfolios_data = db.read("portfolios")

        for portfolio in portfolios_data:
            if portfolio.get("user_id") == user_id:
                return

        new_portfolio = {
            "user_id": user_id,
            "wallets": {}
        }

        db.insert("portfolios", new_portfolio)


class PortfolioManager:
    def get_user_portfolio(self, user_id: int) -> Portfolio:
        portfolio_data = db.find_one("portfolios", user_id=user_id)

        if not portfolio_data:
            raise PortfolioNotFoundError(f"Портфель для пользователя "
                                         f"{user_id} не найден")

        wallets = {}
        for currency_code, wallet_data in portfolio_data.get("wallets", {}).items():
            wallets[currency_code] = Wallet(
                currency_code=currency_code,
                balance=wallet_data.get("balance", 0.0)
            )

        return Portfolio(user_id, wallets)

    def save_user_portfolio(self, portfolio: Portfolio):
        wallets_data = {}
        for currency_code, wallet in portfolio.wallets.items():
            wallets_data[currency_code] = {
                "currency_code": wallet.currency_code,
                "balance": wallet.balance
            }

        db.update(
            "portfolios",
            {"user_id": portfolio.user_id},
            {"wallets": wallets_data}
        )

    @log_action("BUY", verbose=True)
    def buy_currency(self, user_id: int,
                     currency_code: str,
                     amount: float) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

        get_currency(currency_code)

        portfolio = self.get_user_portfolio(user_id)

        if currency_code not in portfolio.wallets:
            portfolio.add_currency(currency_code)

        wallet = portfolio.get_wallet(currency_code)
        if wallet:
            old_balance = wallet.balance
            wallet.deposit(amount)

        self.save_user_portfolio(portfolio)

        rate_manager = RateManager()
        try:
            rate_info = rate_manager.get_rate(currency_code, "USD")
            exchange_rate = rate_info["rate"]
            estimated_cost = amount * exchange_rate
        except (CurrencyNotFoundError, ApiRequestError):
            exchange_rate = None
            estimated_cost = None

        return {
            "currency": currency_code,
            "amount": amount,
            "old_balance": old_balance,
            "new_balance": wallet.balance if wallet else amount,
            "exchange_rate": exchange_rate,
            "estimated_cost": estimated_cost,
            "user_id": user_id
        }

    @log_action("SELL", verbose=True)
    def sell_currency(self, user_id: int,
                      currency_code: str,
                      amount: float) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

        get_currency(currency_code)

        portfolio = self.get_user_portfolio(user_id)
        wallet = portfolio.get_wallet(currency_code)

        if not wallet:
            raise CurrencyNotFoundError(f"У вас нет кошелька '{currency_code}'")

        old_balance = wallet.balance
        wallet.withdraw(amount)

        self.save_user_portfolio(portfolio)

        rate_manager = RateManager()
        try:
            rate_info = rate_manager.get_rate(currency_code, "USD")
            exchange_rate = rate_info["rate"]
            estimated_revenue = amount * exchange_rate
        except (CurrencyNotFoundError, ApiRequestError):
            exchange_rate = None
            estimated_revenue = None

        return {
            "currency": currency_code,
            "amount": amount,
            "old_balance": old_balance,
            "new_balance": wallet.balance,
            "exchange_rate": exchange_rate,
            "estimated_revenue": estimated_revenue,
            "user_id": user_id
        }


class RateManager:
    def get_rate(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        get_currency(from_currency)
        get_currency(to_currency)

        if from_currency == to_currency:
            return {
                "rate": 1.0,
                "timestamp": datetime.now(),
                "source": "System"
            }

        currency_pair = f"{from_currency}_{to_currency}"

        from ..parser_service.updater import RatesUpdater
        updater = RatesUpdater()
        current_rates = updater.storage.get_current_rates()

        if current_rates.get("pairs") and currency_pair in current_rates["pairs"]:
            rate_info = current_rates["pairs"][currency_pair]
            return {
                "rate": rate_info.get("rate"),
                "timestamp": str_to_datetime(rate_info.get("updated_at")),
                "source": rate_info.get("source", "Cache")
            }

        ttl_seconds = settings.get("rates_ttl_seconds", 300)

        rates_data = db.read("rates")
        if rates_data and isinstance(rates_data, dict):
            rate_info = rates_data.get(currency_pair)
            if rate_info:
                last_updated = str_to_datetime(rate_info.get("updated_at"))

                if datetime.now() - last_updated < timedelta(seconds=ttl_seconds):
                    return {
                        "rate": rate_info.get("rate"),
                        "timestamp": last_updated,
                        "source": rates_data.get("source", "Cache")
                    }

        try:
            print("Курс не найден в кеше. Запускаем обновление...")
            updater.run_update()

            current_rates = updater.storage.get_current_rates()
            if current_rates.get("pairs") and currency_pair in current_rates["pairs"]:
                rate_info = current_rates["pairs"][currency_pair]
                return {
                    "rate": rate_info.get("rate"),
                    "timestamp": str_to_datetime(rate_info.get("updated_at")),
                    "source": rate_info.get("source", "API")
                }
        except Exception as e:
            raise ApiRequestError(str(e))

        raise ApiRequestError(f"Курс для {currency_pair} недоступен")
