class ValutaTradeError(Exception):
    pass


class InsufficientFundsError(ValutaTradeError):

    def __init__(self, currency_code: str, available: float, required: float):
        self.currency_code = currency_code
        self.available = available
        self.required = required
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {currency_code}, "
            f"требуется {required:.4f} {currency_code}"
        )


class CurrencyNotFoundError(ValutaTradeError):

    def __init__(self, currency_code: str):
        self.currency_code = currency_code
        super().__init__(f"Неизвестная валюта '{currency_code}'")


class ApiRequestError(ValutaTradeError):

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class DatabaseError(ValutaTradeError):
    pass


class UserNotFoundError(ValutaTradeError):
    pass


class PortfolioNotFoundError(ValutaTradeError):
    pass
