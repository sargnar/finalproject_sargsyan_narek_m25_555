import time
from datetime import datetime
from typing import Dict, Any, List

from ..logging_config import get_logger
from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .storage import RatesStorage


class RatesUpdater:
    """Координатор обновления курсов валют"""

    def __init__(self):
        self.logger = get_logger("parser.updater")
        self.storage = RatesStorage()

        # Инициализируем клиенты
        self.clients = {
            "coingecko": CoinGeckoClient(),
            "exchangerate": ExchangeRateApiClient()
        }

    def run_update(self, sources: List[str] = None) -> Dict[str, Any]:
        """Запускает обновление курсов"""
        if sources is None:
            sources = ["coingecko", "exchangerate"]

        print("Starting rates update...")

        all_rates = {}
        results = {
            "successful_sources": [],
            "failed_sources": [],
            "total_rates": 0,
            "start_time": datetime.now()
        }

        for source_name in sources:
            if source_name not in self.clients:
                print(f"Warning: Unknown source: {source_name}")
                continue

            client = self.clients[source_name]

            try:
                print(f"Fetching rates from {source_name}...")

                start_time = time.time()
                rates = client.fetch_rates()
                fetch_time = time.time() - start_time

                if rates and len(rates) > 1:
                    # Извлекаем метаданные
                    meta = rates.pop("_meta", {})

                    # Сохраняем текущие курсы
                    self.storage.save_current_rates(rates, meta)

                    # Сохраняем историческую запись
                    self.storage.save_historical_record(rates, meta)

                    # Объединяем курсы
                    all_rates.update(rates)

                    results["successful_sources"].append(source_name)
                    results["total_rates"] += len(rates)

                    print(f"Successfully fetched {len(rates)} "
                    f"rates from {source_name} in {fetch_time:.2f}s")

                else:
                    print(f"No rates received from {source_name}")
                    results["failed_sources"].append(source_name)

            except Exception as e:
                print(f"Failed to fetch from {source_name}: {str(e)}")
                results["failed_sources"].append(source_name)

        results["end_time"] = datetime.now()
        results["duration_seconds"] = (
                results["end_time"] - results["start_time"]
        ).total_seconds()

        if results["failed_sources"] and results["successful_sources"]:
            print("Update completed with partial success")
        elif results["successful_sources"]:
            print("Update completed successfully")
        else:
            print("Update failed for all sources")

        return results
