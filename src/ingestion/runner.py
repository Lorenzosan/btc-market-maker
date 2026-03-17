import asyncio
import json
from dataclasses import asdict

from src.types import MarketDataEvent


async def print_events(queue: asyncio.Queue) -> None:
    while True:
        event: MarketDataEvent = await queue.get()
        print(json.dumps(asdict(event), separators=(",", ":")))
        queue.task_done()
