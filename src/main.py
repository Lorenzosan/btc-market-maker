import asyncio
import contextlib

from src.ingestion.binance import BinanceConnector
from src.ingestion.coinbase import CoinbaseConnector
from src.output.printer import print_books
from src.utils.logging import setup_logging


async def main() -> None:
    # Initialize logging to stdout and file
    setup_logging(level="INFO", logfile="logs/market_data.log")

    # Shared queue used to pass normalized market data events
    queue = asyncio.Queue()

    # Instantiate connectors for each venue
    binance = BinanceConnector()
    coinbase = CoinbaseConnector()

    # Create one task per data source plus one consumer/printer
    tasks = [
        asyncio.create_task(binance.run(queue)),
        asyncio.create_task(coinbase.run(queue)),
        asyncio.create_task(print_books(queue)),
    ]

    try:
        # Run all tasks concurrently
        await asyncio.gather(*tasks)

    except asyncio.CancelledError:
        # Expected during shutdown, suppress noisy traceback
        pass

    finally:
        # Ensure all tasks are cancelled on exit
        for task in tasks:
            task.cancel()

        # Await cancellation to avoid "task was destroyed" warnings
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task


if __name__ == "__main__":
    try:
        # Entrypoint for running the async application
        asyncio.run(main())
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C without extra logging noise
        pass
