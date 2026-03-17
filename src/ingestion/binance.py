import asyncio
import json
import websockets

from src.config import BINANCE_WS_URL, BINANCE_SYMBOL
from src.ingestion.base import BaseConnector
from src.types import MarketDataEvent
from src.utils.time import utc_now_iso


class BinanceConnector(BaseConnector):
    async def run(self, queue: asyncio.Queue) -> None:
        while True:
            try:
                async with websockets.connect(BINANCE_WS_URL) as ws:
                    async for raw_msg in ws:
                        msg = json.loads(raw_msg)
                        event = self.parse_message(msg)
                        await queue.put(event)
            except Exception as exc:
                print(f"binance reconnecting after error: {exc}")
                await asyncio.sleep(2)

    def parse_message(self, msg: dict) -> MarketDataEvent:
        bids = [(float(price), float(size)) for price, size in msg.get("b", [])]
        asks = [(float(price), float(size)) for price, size in msg.get("a", [])]

        return MarketDataEvent(
            source="binance",
            symbol=BINANCE_SYMBOL,
            channel="depth",
            event_type="update",
            exchange_ts=None,
            received_ts=utc_now_iso(),
            sequence=msg.get("u"),
            bid_updates=bids,
            ask_updates=asks,
            raw=msg,
        )
