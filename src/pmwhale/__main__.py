"""A small package-level help entry point."""

from pmwhale import __version__


def main() -> None:
    print(f"pmwhale {__version__}")
    print("Commands: pmwhale-collect, pmwhale-rank, pmwhale-backtest")


if __name__ == "__main__":
    main()
