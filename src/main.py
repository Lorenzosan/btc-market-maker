import asyncio
import logging

from src.ingestion.binance import BinanceConnector
from src.ingestion.coinbase import CoinbaseConnector
from src.output.printer import print_books
from src.utils.logging import setup_logging


async def main():
    setup_logging(level="INFO", logfile="logs/market_data.log")

    queue = asyncio.Queue()

    binance = BinanceConnector()
    coinbase = CoinbaseConnector()

    await asyncio.gather(
        binance.run(queue),
        coinbase.run(queue),
        print_books(queue),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("shutdown requested by user")
