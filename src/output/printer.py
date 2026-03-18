import asyncio
import json
import logging

from src.orderbook.manager import OrderBookManager

logger = logging.getLogger(__name__)


async def print_books(queue: asyncio.Queue):
    # Single manager instance that tracks one local book per source.
    manager = OrderBookManager()

    while True:
        # Consume one normalized event at a time from the shared queue.
        event = await queue.get()

        # Update the corresponding local book.
        manager.apply_event(event)

        # Extract the current top-of-book state for that source.
        top = manager.top_of_book(event.source)

        # Emit a compact JSON log line to make debugging and later processing easier.
        logger.info(
            json.dumps(
                {
                    "source": event.source,
                    "symbol": event.symbol,
                    "exchange_ts": event.exchange_ts,
                    "best_bid": top["best_bid"],
                    "best_ask": top["best_ask"],
                    "mid": top["mid"],
                    "spread": top["spread"],
                    "initialized": top["initialized"],
                    "valid": top["valid"],
                    "last_sequence": top["last_sequence"],
                    "status": top["status"],
                },
                separators=(",", ":"),
            )
        )

        queue.task_done()
