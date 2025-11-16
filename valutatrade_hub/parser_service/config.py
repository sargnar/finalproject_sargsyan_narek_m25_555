import os
from dataclasses import dataclass
from typing import Dict, Tuple

from ..infra.settings import settings


@dataclass
class ParserConfig:
    EXCHANGERATE_API_KEY: str = None

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: Tuple[str, ...] = ("EUR", "GBP", "RUB", "JPY",
                                        "CNY", "CHF", "CAD", "AUD")
    CRYPTO_CURRENCIES: Tuple[str, ...] = ("BTC", "ETH", "SOL", "BNB",
                                          "XRP", "ADA", "DOGE", "DOT")

    CRYPTO_ID_MAP: Dict[str, str] = None

    REQUEST_TIMEOUT: int = 10
    UPDATE_INTERVAL_MINUTES: int = 5

    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    def __post_init__(self):
        parser_config = settings.get("parser", {})

        self.EXCHANGERATE_API_KEY = (
                os.getenv("EXCHANGERATE_API_KEY") or
                parser_config.get("exchangerate_api_key") or
                "demo_key"
        )

        self.COINGECKO_URL = parser_config.get("coingecko_url", self.COINGECKO_URL)
        self.EXCHANGERATE_API_URL = parser_config.get("exchangerate_api_url",
                                                    self.EXCHANGERATE_API_URL)

        self.BASE_CURRENCY = parser_config.get("base_currency", self.BASE_CURRENCY)
        self.FIAT_CURRENCIES = tuple(parser_config
                                     .get("fiat_currencies",
                                          list(self.FIAT_CURRENCIES)))
        self.CRYPTO_CURRENCIES = tuple(parser_config
                                       .get("crypto_currencies",
                                        list(self.CRYPTO_CURRENCIES)))

        self.REQUEST_TIMEOUT = (parser_config
                                .get("request_timeout", self.REQUEST_TIMEOUT))
        self.UPDATE_INTERVAL_MINUTES = (parser_config
                                        .get("update_interval_minutes",
                                             self.UPDATE_INTERVAL_MINUTES))

        data_dir = settings.get("data_dir", "data")
        self.RATES_FILE_PATH = os.path.join(data_dir, "rates.json")
        self.HISTORY_FILE_PATH = os.path.join(data_dir, "exchange_rates.json")

        self.CRYPTO_ID_MAP = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "BNB": "binancecoin",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "DOT": "polkadot",
        }

    def validate(self):
        if not self.EXCHANGERATE_API_KEY or self.EXCHANGERATE_API_KEY == "demo_key":
            raise ValueError(
                "EXCHANGERATE_API_KEY не настроен. "
                "Установите через переменную окружения EXCHANGERATE_API_KEY")

        if not self.FIAT_CURRENCIES:
            raise ValueError("Список фиатных валют не может быть пустым")

        if not self.CRYPTO_CURRENCIES:
            raise ValueError("Список криптовалют не может быть пустым")

        for crypto in self.CRYPTO_CURRENCIES:
            if crypto not in self.CRYPTO_ID_MAP:
                raise ValueError(f"Неизвестная криптовалюта: {crypto}")


config = ParserConfig()
