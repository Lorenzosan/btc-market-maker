import asyncio
import json
import logging

from src.orderbook.manager import OrderBookManager

logger = logging.getLogger(__name__)


async def print_books(queue: asyncio.Queue):
    manager = OrderBookManager()

    while True:
        event = await queue.get()

        # Apply each normalized market event to the corresponding local book.
        manager.apply_event(event)

        top = manager.top_of_book(event.source)

        logger.info(json.dumps({
            "source": event.source,
            "symbol": event.symbol,
            "exchange_ts": event.exchange_ts,
            "best_bid": top["best_bid"],
            "best_ask": top["best_ask"],
        }, separators=(",", ":")))

        queue.task_done()
