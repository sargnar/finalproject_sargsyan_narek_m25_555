import argparse
import sys
from prettytable import PrettyTable
from ..core.usecases import UserManager, PortfolioManager, RateManager
from ..core.exceptions import (
    InsufficientFundsError, CurrencyNotFoundError,
    ApiRequestError, UserNotFoundError
)
from ..core.currencies import get_all_currencies


class CLIInterface:

    def __init__(self):
        self.user_manager = UserManager()
        self.portfolio_manager = PortfolioManager()
        self.rate_manager = RateManager()

        self._rates_updater = None
        self._parser_scheduler = None

    @property
    def rates_updater(self):
        if self._rates_updater is None:
            try:
                from ..parser_service.updater import RatesUpdater
                self._rates_updater = RatesUpdater()
            except ImportError as e:
                print(f"Warning: Parser service not available: {e}")
                self._rates_updater = type("StubUpdater", (), {
                    "run_update": lambda *args, **kwargs: {
                        "successful_sources": [],
                        "failed_sources": [],
                        "total_rates": 0
                    },
                    "storage": type("StubStorage", (), {
                        "get_current_rates": lambda: {"pairs": {}, "last_refresh": None}
                    })()
                })()
        return self._rates_updater

    @property
    def parser_scheduler(self):
        if self._parser_scheduler is None:
            try:
                from ..parser_service.scheduler import ParserScheduler
                self._parser_scheduler = ParserScheduler()
            except ImportError as e:
                print(f"Warning: Parser scheduler not available: {e}")
                self._parser_scheduler = type("StubScheduler", (), {
                    "start": lambda: print("Parser service not available"),
                    "stop": lambda: print("Parser service not available"),
                    "get_status":
                        lambda: {"status": "not_available", "is_running": False}
                })()
        return self._parser_scheduler

    def run(self):
        parser = argparse.ArgumentParser(
            description="ValutaTrade Hub - Платформа для торговли валютами",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_help_epilog()
        )
        subparsers = parser.add_subparsers(dest="command", help="Доступные команды")

        register_parser = subparsers.add_parser("register",
                                                help="Регистрация нового пользователя")
        register_parser.add_argument("--username", required=True,
                                     help="Имя пользователя")
        register_parser.add_argument("--password", required=True, help="Пароль")

        login_parser = subparsers.add_parser("login", help="Вход в систему")
        login_parser.add_argument("--username", required=True,
                                  help="Имя пользователя")
        login_parser.add_argument("--password", required=True, help="Пароль")

        portfolio_parser = subparsers.add_parser("show-portfolio",
                                                 help="Показать портфель")
        portfolio_parser.add_argument("--base",
                                      default="USD",
                                      help="Базовая валюта для конвертации")

        buy_parser = subparsers.add_parser("buy",
                                           help="Купить валюту")
        buy_parser.add_argument("--currency",
                                required=True,
                                help="Код покупаемой валюты")
        buy_parser.add_argument("--amount",
                                type=float,
                                required=True,
                                help="Количество покупаемой валюты")

        sell_parser = subparsers.add_parser("sell",
                                            help="Продать валюту")
        sell_parser.add_argument("--currency",
                                 required=True,
                                 help="Код продаваемой валюты")
        sell_parser.add_argument("--amount",
                                 type=float,
                                 required=True,
                                 help="Количество продаваемой валюты")

        rate_parser = subparsers.add_parser("get-rate", help="Получить курс валюты")
        rate_parser.add_argument("--from", required=True, dest="from_currency",
                                 help="Исходная валюта")
        rate_parser.add_argument("--to", required=True, dest="to_currency",
                                 help="Целевая валюта")

        update_parser = subparsers.add_parser("update-rates",
                                              help="Обновить курсы валют")
        update_parser.add_argument("--source",
                                   choices=["coingecko", "exchangerate", "all"],
                                   default="all", help="Источник для обновления")

        show_rates_parser = subparsers.add_parser("show-rates",
                                                  help="Показать актуальные курсы")
        show_rates_parser.add_argument("--currency",
                                       help="Показать курс только для указанной валюты")
        show_rates_parser.add_argument("--top", type=int,
                                       help="Показать N самых дорогих криптовалют")
        show_rates_parser.add_argument("--base", default="USD",
                                       help="Базовая валюта для отображения")

        subparsers.add_parser("list-currencies",
                              help="Показать все поддерживаемые валюты")

        subparsers.add_parser("start-parser", help="Запустить фоновый парсер")
        subparsers.add_parser("stop-parser", help="Остановить фоновый парсер")
        subparsers.add_parser("parser-status", help="Показать статус парсера")

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return

        try:
            if args.command == "register":
                self.handle_register(args.username, args.password)
            elif args.command == "login":
                self.handle_login(args.username, args.password)
            elif args.command == "show-portfolio":
                self.handle_show_portfolio(args.base)
            elif args.command == "buy":
                self.handle_buy(args.currency, args.amount)
            elif args.command == "sell":
                self.handle_sell(args.currency, args.amount)
            elif args.command == "get-rate":
                self.handle_get_rate(args.from_currency, args.to_currency)
            elif args.command == "update-rates":
                self.handle_update_rates(args.source)
            elif args.command == "show-rates":
                self.handle_show_rates(args.currency, args.top, args.base)
            elif args.command == "list-currencies":
                self.handle_list_currencies()
            elif args.command == "start-parser":
                self.handle_start_parser()
            elif args.command == "stop-parser":
                self.handle_stop_parser()
            elif args.command == "parser-status":
                self.handle_parser_status()
        except Exception as e:
            self._handle_error(e)
            sys.exit(1)

    def _get_help_epilog(self) -> str:
        return """
Примеры использования:
  Основные команды:
    register --username alice --password 1234
    login --username alice --password 1234
    buy --currency BTC --amount 0.05
    show-portfolio --base USD

  Команды курсов:
    get-rate --from USD --to BTC
    update-rates --source all
    show-rates --top 5 --base USD

  Служебные команды:
    list-currencies
    start-parser
    parser-status

Подробная информация по команде: project <command> --help
"""

    def _check_logged_in(self) -> None:
        if not self.user_manager.current_user:
            raise ValueError("Сначала выполните login")

    def _handle_error(self, error: Exception):
        if isinstance(error, InsufficientFundsError):
            print(f"Ошибка: {error}")
        elif isinstance(error, CurrencyNotFoundError):
            print(f"Ошибка: {error}")
            print("\nИспользуйте 'list-currencies' для просмотра поддерживаемых валют")
        elif isinstance(error, ApiRequestError):
            print(f"Ошибка: {error}")
            print("Повторите попытку позже или проверьте подключение к сети")
        elif isinstance(error, UserNotFoundError):
            print(f"Ошибка: {error}")
        else:
            print(f"Ошибка: {error}")

    def handle_register(self, username: str, password: str):
        result = self.user_manager.register_user(username, password)
        print(f"Пользователь '{username}' зарегистрирован (id={result['user_id']}).")
        print("Войдите: login --username {} --password ****".format(username))

    def handle_login(self, username: str, password: str):
        self.user_manager.login_user(username, password)
        print(f"Вы вошли как '{username}'")

    def handle_show_portfolio(self, base_currency: str):
        self._check_logged_in()

        user = self.user_manager.current_user
        portfolio = self.portfolio_manager.get_user_portfolio(user.user_id)

        print(f"Портфель пользователя '{user.username}' (база: {base_currency}):")

        if not portfolio.wallets:
            print("  У вас пока нет кошельков")
            return

        total_value = 0.0

        for currency_code, wallet in portfolio.wallets.items():
            balance = wallet.balance

            if currency_code == base_currency:
                value = balance
            else:
                try:
                    rate_info = self.rate_manager.get_rate(currency_code, base_currency)
                    value = balance * rate_info["rate"]
                except (CurrencyNotFoundError, ApiRequestError) as e:
                    value = 0.0
                    print(f"  - {currency_code}: {balance:.4f} → "
                          f"Не удалось получить курс ({e})")
                    continue

            total_value += value
            print(f"  - {currency_code}: {balance:.4f} → {value:.2f} {base_currency}")

        print("-" * 40)
        print(f"ИТОГО: {total_value:,.2f} {base_currency}")

    def handle_buy(self, currency: str, amount: float):
        self._check_logged_in()

        user = self.user_manager.current_user
        result = (self.portfolio_manager
                  .buy_currency(user.user_id, currency.upper(), amount))

        print(f"Покупка выполнена: {amount:.4f} {currency}")

        if result["exchange_rate"]:
            print(f"Курс: {result['exchange_rate']:.2f} USD/{currency}")

        print("Изменения в портфеле:")
        print(f"  - {currency}: "
              f"было {result['old_balance']:.4f} → "
              f"стало {result['new_balance']:.4f}")

        if result["estimated_cost"]:
            print(f"Оценочная стоимость покупки: {result['estimated_cost']:,.2f} USD")

    def handle_sell(self, currency: str, amount: float):
        self._check_logged_in()

        user = self.user_manager.current_user
        result = (self.portfolio_manager
                  .sell_currency(user.user_id, currency.upper(), amount))

        print(f"Продажа выполнена: {amount:.4f} {currency}")

        if result["exchange_rate"]:
            print(f"Курс: {result['exchange_rate']:.2f} USD/{currency}")

        print("Изменения в портфеле:")
        print(f"  - {currency}: было "
              f"{result['old_balance']:.4f} → "
              f"стало {result['new_balance']:.4f}")

        if result["estimated_revenue"]:
            print(f"Оценочная выручка: {result['estimated_revenue']:,.2f} USD")

    def handle_get_rate(self, from_currency: str, to_currency: str):
        rate_info = (self.rate_manager
                     .get_rate(from_currency.upper(), to_currency.upper()))

        print(f"Курс {from_currency}→{to_currency}: {rate_info['rate']:.6f}")
        print(f"Обновлено: {rate_info['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Источник: {rate_info['source']}")

        if from_currency != to_currency:
            reverse_rate = 1 / rate_info["rate"] if rate_info["rate"] != 0 else 0
            print(f"Обратный курс {to_currency}→{from_currency}: {reverse_rate:.6f}")

    def handle_list_currencies(self):

        currencies = get_all_currencies()
        print("Поддерживаемые валюты:")
        print("-" * 60)

        for code, currency in currencies.items():
            print(f"  {currency.get_display_info()}")

        print(f"\nВсего: {len(currencies)} валют")

    def handle_update_rates(self, source: str):
        print("Starting rates update...")

        sources_map = {
            "all": ["coingecko", "exchangerate"],
            "coingecko": ["coingecko"],
            "exchangerate": ["exchangerate"]
        }

        selected_sources = sources_map.get(source, ["coingecko", "exchangerate"])

        try:
            results = self.rates_updater.run_update(selected_sources)

            if results["successful_sources"]:
                print(f"Successfully updated "
                      f"from: {', '.join(results['successful_sources'])}")
                print(f"Total rates updated: {results['total_rates']}")
                print(f"Duration: {results['duration_seconds']:.2f}s")

                if results["failed_sources"]:
                    print(f"Failed sources: {', '.join(results['failed_sources'])}")
                    print("Check logs for details.")
            else:
                print("Update failed for all sources")
                print("Check logs for details.")

        except Exception as e:
            print(f"Update failed: {e}")

    def handle_show_rates(self,
                          currency: str = None,
                          top: int = None,
                          base: str = "USD"):
        current_rates = self.rates_updater.storage.get_current_rates()

        if not current_rates.get("pairs"):
            print("Локальный кеш курсов пуст. "
                  "Выполните 'update-rates', чтобы загрузить данные.")
            return

        pairs = current_rates["pairs"]
        last_refresh = current_rates.get("last_refresh", "Unknown")

        print(f"Rates from cache (updated at {last_refresh}):")
        print("-" * 60)

        if currency:
            currency = currency.upper()
            filtered_pairs = {
                k: v for k, v in pairs.items()
                if k.startswith(f"{currency}_") or k.endswith(f"_{currency}")
            }

            if not filtered_pairs:
                print(f"Курс для '{currency}' не найден в кеше.")
                return

            pairs = filtered_pairs

        sorted_pairs = sorted(
            pairs.items(),
            key=lambda x: x[1]["rate"],
            reverse=True
        )

        if top:
            sorted_pairs = sorted_pairs[:top]

        table = PrettyTable()
        table.field_names = ["Pair", "Rate", "Updated", "Source"]
        table.align["Pair"] = "l"
        table.align["Rate"] = "r"
        table.align["Source"] = "l"

        for pair, data in sorted_pairs:
            rate = data["rate"]
            updated = data["updated_at"][:19]
            source = data["source"]

            if rate < 0.001:
                rate_str = f"{rate:.8f}"
            elif rate < 1:
                rate_str = f"{rate:.6f}"
            elif rate < 1000:
                rate_str = f"{rate:.4f}"
            else:
                rate_str = f"{rate:.2f}"

            table.add_row([pair, rate_str, updated, source])

        print(table)
        print(f"\nTotal pairs: {len(sorted_pairs)}")

    def handle_start_parser(self):
        try:
            self.parser_scheduler.start()
            print("Parser scheduler started successfully")
            print(f"Update interval: "
                  f"{self.parser_scheduler.updater.config.UPDATE_INTERVAL_MINUTES}"
                  f" minutes")
        except Exception as e:
            print(f"Failed to start parser scheduler: {e}")

    def handle_stop_parser(self):
        try:
            self.parser_scheduler.stop()
            print("Parser scheduler stopped successfully")
        except Exception as e:
            print(f"Failed to stop parser scheduler: {e}")

    def handle_parser_status(self):
        status = self.parser_scheduler.get_status()
        update_status = self.rates_updater.get_update_status()

        print("Parser Service Status:")
        print("-" * 40)
        print(f"Status: {'RUNNING' if status['is_running'] else 'STOPPED'}")

        if status["is_running"]:
            print(f"Update interval: {status['update_interval_minutes']} minutes")
            print(f"Active jobs: {status['jobs_count']}")

        print(f"\nLast update: {update_status.get('last_refresh', 'Never')}")
        freshness = "FRESH" if update_status.get('is_fresh') else "STALE"
        print(f"Data freshness: {freshness}")

        if update_status.get("age_seconds"):
            age_minutes = update_status["age_seconds"] / 60
            print(f"Data age: {age_minutes:.1f} minutes")

        print(f"Available pairs: {update_status.get('total_pairs', 0)}")
