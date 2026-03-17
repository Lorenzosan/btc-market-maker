import asyncio
import json
import logging

import websockets

from src.config import BINANCE_WS_URL, BINANCE_SYMBOL
from src.ingestion.base import BaseConnector
from src.types import MarketDataEvent
from src.utils.time import utc_now_iso, ms_to_iso

logger = logging.getLogger(__name__)


class BinanceConnector(BaseConnector):
    async def run(self, queue: asyncio.Queue) -> None:
        # Reconnect loop to handle transient network or exchange-side errors
        while True:
            try:
                # Binance diff-depth stream emits incremental order book updates
                async with websockets.connect(BINANCE_WS_URL) as ws:
                    async for raw_msg in ws:
                        msg = json.loads(raw_msg)

                        try:
                            event = self.parse_message(msg)
                        except ValueError as exc:
                            # Ignore unexpected non-depth messages from the stream
                            continue

                        # Decouple ingestion from downstream consumers
                        await queue.put(event)

            except Exception as exc:
                logger.warning("binance reconnecting after error: %s", exc)
                await asyncio.sleep(2)

    def parse_message(self, msg: dict) -> MarketDataEvent:
        # Only depthUpdate messages are expected on this stream
        if msg.get("e") != "depthUpdate":
            raise ValueError(f"unexpected Binance message type: {msg.get('e')}")

        bids = [(float(price), float(size)) for price, size in msg.get("b", [])]
        asks = [(float(price), float(size)) for price, size in msg.get("a", [])]

        return MarketDataEvent(
            source="binance",
            symbol=BINANCE_SYMBOL,
            channel="depth",
            event_type="update",
            exchange_ts=ms_to_iso(msg["E"]),
            received_ts=utc_now_iso(),
            sequence=msg.get("u"),
            sequence_start=msg.get("U"),
            sequence_end=msg.get("u"),
            bid_updates=bids,
            ask_updates=asks,
            raw=msg,
        )
