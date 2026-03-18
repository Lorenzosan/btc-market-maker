import asyncio
import logging

from src.ingestion.binance import BinanceConnector
from src.ingestion.coinbase import CoinbaseConnector
from src.output.printer import print_books
from src.utils.logging import setup_logging


async def main():
    # Configure console and file logging once at startup.
    setup_logging(level="INFO", logfile="logs/market_data.log")

    # Shared queue used by all connectors to publish normalized events.
    queue = asyncio.Queue()

    # Instantiate the two public BTC market-data connectors.
    binance = BinanceConnector()
    coinbase = CoinbaseConnector()

    # Run both connectors and the consumer loop concurrently.
    await asyncio.gather(
        binance.run(queue),
        coinbase.run(queue),
        print_books(queue),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Clean shutdown message for interactive use.
        logging.getLogger(__name__).info("shutdown requested by user")
