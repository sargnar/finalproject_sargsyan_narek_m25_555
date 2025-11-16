# ValutaTrade Hub

Платформа для симуляции торговли крипто и фиатными валютами.

## Основные возможности

- **Реальные курсы** из CoinGecko API
- **Регистрация и авторизация** пользователей  
- **Виртуальные кошельки** для разных валют
- **Покупка/продажа** валют по актуальным курсам
- **Портфель** с общей стоимостью в USD
- **Фоновый парсер** для автоматического обновления курсов

## Запуск

```bash
# Установка
poetry install

# Просмотр курсов
poetry run project show-rates

# Регистрация и торговля
poetry run project register --username user --password 1234
poetry run project login --username user --password 1234
poetry run project buy --currency BTC --amount 0.001
poetry run project show-portfolio