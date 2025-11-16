from abc import ABC, abstractmethod
from typing import Dict


class Currency(ABC):

    def __init__(self, name: str, code: str):
        if not name or not name.strip():
            raise ValueError("Название валюты не может быть пустым")
        if not code or not 2 <= len(code) <= 5 or not code.isupper() or " " in code:
            raise ValueError("Код валюты должен быть 2-5 "
                             "символов в верхнем регистре без пробелов")

        self._name = name
        self._code = code

    @property
    def name(self) -> str:
        return self._name

    @property
    def code(self) -> str:
        return self._code

    @abstractmethod
    def get_display_info(self) -> str:
        pass

    def __str__(self) -> str:
        return self.get_display_info()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', code='{self.code}')"


class FiatCurrency(Currency):

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        if not issuing_country or not issuing_country.strip():
            raise ValueError("Страна эмитент не может быть пустой")

        self._issuing_country = issuing_country

    @property
    def issuing_country(self) -> str:
        return self._issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        super().__init__(name, code)
        if not algorithm or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")
        if market_cap < 0:
            raise ValueError("Рыночная капитализация не может быть отрицательной")

        self._algorithm = algorithm
        self._market_cap = market_cap

    @property
    def algorithm(self) -> str:
        return self._algorithm

    @property
    def market_cap(self) -> float:
        return self._market_cap

    def get_display_info(self) -> str:
        mcap_str = f"{self.market_cap:.2e}" \
            if self.market_cap > 1e6 \
            else f"{self.market_cap:,.2f}"
        return (f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, "
                f"MCAP: {mcap_str})")


_currency_registry: Dict[str, Currency] = {}


def register_currency(currency: Currency):
    _currency_registry[currency.code] = currency


def get_currency(code: str) -> Currency:
    code = code.upper()
    if code not in _currency_registry:
        from .exceptions import CurrencyNotFoundError
        raise CurrencyNotFoundError(code)
    return _currency_registry[code]


def get_all_currencies() -> Dict[str, Currency]:
    return _currency_registry.copy()


def get_supported_currency_codes() -> list:
    return list(_currency_registry.keys())


def _initialize_default_currencies():
    default_currencies = [
        FiatCurrency("US Dollar", "USD", "United States"),
        FiatCurrency("Euro", "EUR", "Eurozone"),
        FiatCurrency("Russian Ruble", "RUB", "Russia"),
        CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
        CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
        CryptoCurrency("Litecoin", "LTC", "Scrypt", 6.5e9),
    ]

    for currency in default_currencies:
        register_currency(currency)

_initialize_default_currencies()
