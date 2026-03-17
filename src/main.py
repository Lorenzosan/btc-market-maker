import asyncio

from src.ingestion.binance import BinanceConnector
from src.ingestion.coinbase import CoinbaseConnector
from src.output.printer import print_events
from src.utils.logging import setup_logging


async def main():
    setup_logging(level="INFO", logfile="logs/market_data.log")

    queue = asyncio.Queue()

    binance = BinanceConnector()
    coinbase = CoinbaseConnector()

    await asyncio.gather(
        binance.run(queue),
        coinbase.run(queue),
        print_events(queue),
    )


if __name__ == "__main__":
    asyncio.run(main())
