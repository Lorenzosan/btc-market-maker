import asyncio
import contextlib
import argparse

from src.config import INITIAL_INVENTORY, QUOTE_BASE_SIZE, OUTPUT_VERBOSITY
from src.ingestion.binance import BinanceConnector
from src.ingestion.coinbase import CoinbaseConnector
from src.output.printer import run_output_loop
from src.utils.logging import setup_logging


async def main() -> None:
    parser = argparse.ArgumentParser(description="BTC market-making quote engine")
    parser.add_argument(
        "--inventory",
        type=float,
        default=INITIAL_INVENTORY,
        help="Initial inventory used for quote skew",
    )
    parser.add_argument(
        "--base_size",
        type=float,
        default=QUOTE_BASE_SIZE,
        help="Base quote size before scaling",
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO"],
        help="Logging level",
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        default=OUTPUT_VERBOSITY,
        choices=[0,1,2],
        help="Verbosity level (0 = compact summary, 1 = per-event concise JSON, 2 = per-event detailed JSON)",
    )
    
    args = parser.parse_args()

    # Initialize logging to stdout and file
    setup_logging(level=args.log_level, logfile="logs/market_data.log")

    # Shared queue used to pass normalized market data events
    queue = asyncio.Queue()

    # Instantiate connectors for each venue
    binance = BinanceConnector()
    coinbase = CoinbaseConnector()

    # Create one task per data source plus one consumer/printer
    tasks = [
        asyncio.create_task(binance.run(queue)),
        asyncio.create_task(coinbase.run(queue)),
        asyncio.create_task(
            run_output_loop(
                queue,
                inventory=args.inventory,
                base_size=args.base_size,
                verbosity=args.verbosity,
            )
        ),
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
