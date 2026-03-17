import asyncio
import json
import logging

logger = logging.getLogger(__name__)


def format_event(event):
    return {
        "source": event.source,
        "symbol": event.symbol,
        "channel": event.channel,
        "event_type": event.event_type,
        "num_bid_updates": len(event.bid_updates),
        "num_ask_updates": len(event.ask_updates),
    }


async def print_events(queue: asyncio.Queue):
    while True:
        event = await queue.get()

        logger.info(json.dumps(format_event(event)))

        logger.debug(json.dumps({
            "bids": event.bid_updates,
            "asks": event.ask_updates
        }))

        queue.task_done()
