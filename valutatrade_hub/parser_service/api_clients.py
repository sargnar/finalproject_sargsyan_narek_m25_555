import time
from abc import ABC, abstractmethod
from typing import Dict, Any
import requests

from ..core.exceptions import ApiRequestError
from .config import config


class BaseApiClient(ABC):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ValutaTradeHub/0.3.0",
            "Accept": "application/json"
        })

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        pass

    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        start_time = time.time()

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            request_time = int((time.time() - start_time) * 1000)
            return {
                "data": response.json(),
                "meta": {
                    "status_code": response.status_code,
                    "request_ms": request_time,
                    "etag": response.headers.get("ETag", ""),
                    "url": response.url
                }
            }

        except requests.exceptions.Timeout:
            raise ApiRequestError(f"Timeout после {config.REQUEST_TIMEOUT} секунд")
        except requests.exceptions.ConnectionError:
            raise ApiRequestError("Ошибка подключения к API")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise ApiRequestError("Превышен лимит запросов к API")
            elif e.response.status_code == 401:
                raise ApiRequestError("Неверный API ключ")
            else:
                raise ApiRequestError(f"HTTP ошибка: {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"Ошибка запроса: {str(e)}")
        except ValueError as e:
            raise ApiRequestError(f"Ошибка парсинга JSON: {str(e)}")


class CoinGeckoClient(BaseApiClient):

    def fetch_rates(self) -> Dict[str, float]:
        crypto_ids = [
            config.CRYPTO_ID_MAP[crypto]
            for crypto in config.CRYPTO_CURRENCIES
        ]
        crypto_ids_param = ",".join(crypto_ids)

        url = config.COINGECKO_URL
        params = {
            "ids": crypto_ids_param,
            "vs_currencies": "usd"
        }

        result = self._make_request(url, params)
        data = result["data"]
        meta = result["meta"]

        rates = {}

        for crypto_code, crypto_id in config.CRYPTO_ID_MAP.items():
            if crypto_id in data and "usd" in data[crypto_id]:
                pair_key = f"{crypto_code}_{config.BASE_CURRENCY}"
                rates[pair_key] = data[crypto_id]["usd"]

                reverse_pair = f"{config.BASE_CURRENCY}_{crypto_code}"
                if data[crypto_id]["usd"] > 0:
                    rates[reverse_pair] = 1 / data[crypto_id]["usd"]

        rates["_meta"] = {
            "source": "CoinGecko",
            "timestamp": time.time(),
            "request_meta": meta
        }

        return rates


class ExchangeRateApiClient(BaseApiClient):

    def fetch_rates(self) -> Dict[str, float]:
        url = (f"{config.EXCHANGERATE_API_URL}/"
               f"{config.EXCHANGERATE_API_KEY}/latest/{config.BASE_CURRENCY}")

        result = self._make_request(url)
        data = result["data"]
        meta = result["meta"]

        if data.get("result") != "success":
            raise ApiRequestError(f"API вернуло ошибку: "
                                  f"{data.get('error-type', 'unknown')}")

        rates = {}
        base_currency = data.get("base_code", config.BASE_CURRENCY)

        for currency in config.FIAT_CURRENCIES:
            if currency in data.get("conversion_rates", {}):
                rate = data["conversion_rates"][currency]
                pair_key = f"{currency}_{base_currency}"
                rates[pair_key] = rate

                reverse_pair = f"{base_currency}_{currency}"
                if rate > 0:
                    rates[reverse_pair] = 1 / rate

        rates[f"{base_currency}_{base_currency}"] = 1.0

        rates["_meta"] = {
            "source": "ExchangeRate-API",
            "timestamp": time.time(),
            "request_meta": meta,
            "base_currency": base_currency,
            "time_last_update": data.get("time_last_update_utc")
        }

        return rates
