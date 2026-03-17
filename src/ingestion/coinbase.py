import asyncio
import json
import logging

import websockets

from src.config import COINBASE_WS_URL, COINBASE_SYMBOL
from src.ingestion.base import BaseConnector
from src.types import MarketDataEvent
from src.utils.time import utc_now_iso

logger = logging.getLogger(__name__)


class CoinbaseConnector(BaseConnector):
    async def run(self, queue: asyncio.Queue) -> None:
        # Coinbase Exchange requires authentication for level2,
        # so we use level2_batch which provides unauthenticated
        # batched L2 updates.
        subscribe_message = {
            "type": "subscribe",
            "product_ids": [COINBASE_SYMBOL],
            "channels": ["level2_batch"],
        }

        while True:
            try:
                logger.info("coinbase connecting")

                # level2_batch messages can exceed the default websocket
                # size limit, so max_size is disabled here.
                async with websockets.connect(
                    COINBASE_WS_URL,
                    max_size=None,
                    ping_interval=20,
                    ping_timeout=20,
                ) as ws:
                    logger.info("coinbase connected")

                    await ws.send(json.dumps(subscribe_message))
                    logger.info("coinbase subscribed")

                    async for raw_msg in ws:
                        msg = json.loads(raw_msg)
                        event = self.parse_message(msg)

                        # Ignore non-market-data messages such as
                        # subscription acknowledgements.
                        if event is not None:
                            await queue.put(event)

            except Exception as exc:
                logger.warning("coinbase reconnecting after error: %s", exc)
                await asyncio.sleep(2)

    def parse_message(self, msg: dict) -> MarketDataEvent | None:
        msg_type = msg.get("type")

        # Snapshot initializes the local book state at subscription start.
        if msg_type == "snapshot":
            bids = [(float(price), float(size)) for price, size in msg.get("bids", [])]
            asks = [(float(price), float(size)) for price, size in msg.get("asks", [])]

            return MarketDataEvent(
                source="coinbase",
                symbol=COINBASE_SYMBOL,
                channel="level2_batch",
                event_type="snapshot",
                exchange_ts=None,  # snapshot does not include timestamp
                received_ts=utc_now_iso(),
                sequence=msg.get("sequence"),
                bid_updates=bids,
                ask_updates=asks,
                raw=msg,
            )

        # Incremental updates: changed bid/ask price levels.
        if msg_type == "l2update":
            bids = []
            asks = []

            for side, price, size in msg.get("changes", []):
                level = (float(price), float(size))
                if side == "buy":
                    bids.append(level)
                elif side == "sell":
                    asks.append(level)

            return MarketDataEvent(
                source="coinbase",
                symbol=COINBASE_SYMBOL,
                channel="level2_batch",
                event_type="update",
                exchange_ts=msg.get("time"),
                received_ts=utc_now_iso(),
                sequence=msg.get("sequence"),
                bid_updates=bids,
                ask_updates=asks,
                raw=msg,
            )

        # Ignore non-market-data messages (subscriptions, errors, etc.).
        return None
