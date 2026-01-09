from valutatrade_hub.cli.interface import CLIInterface


def main():
    """Создает объект CLI и запускает обработку командной строки."""
    cli = CLIInterface()
    cli.run()


if __name__ == "__main__":
    main()
