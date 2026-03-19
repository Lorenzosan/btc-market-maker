import asyncio
import json
import logging
from collections import deque
from urllib.parse import urlencode
from urllib.request import urlopen

import websockets

from src.config import BINANCE_REST_SNAPSHOT_URL, BINANCE_SYMBOL, BINANCE_WS_URL
from src.ingestion.base import BaseConnector
from src.types import MarketDataEvent
from src.utils.time import ms_to_iso, utc_now_iso

logger = logging.getLogger(__name__)


class BinanceConnector(BaseConnector):
    async def run(self, queue: asyncio.Queue) -> None:
        # Binance local-book handling is done here, inside the connector.
        # The manager should only see already-validated snapshot/update events.
        while True:
            try:
                logger.info("binance connecting")

                async with websockets.connect(
                    BINANCE_WS_URL,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=None,
                ) as ws:
                    logger.info("binance connected")

                    # Buffer websocket diff events while the REST snapshot is fetched.
                    buffered_events: deque[dict] = deque()
                    stop_reader = asyncio.Event()

                    async def reader() -> None:
                        while not stop_reader.is_set():
                            raw_msg = await ws.recv()
                            msg = json.loads(raw_msg)

                            # Only depthUpdate messages belong on this stream.
                            if msg.get("e") != "depthUpdate":
                                continue

                            buffered_events.append(msg)

                    reader_task = asyncio.create_task(reader())

                    try:
                        # Wait until at least one diff arrives before requesting the snapshot.
                        while not buffered_events:
                            await asyncio.sleep(0.01)

                        # Retry snapshot initialization a few times before giving up on the socket.
                        snapshot, last_update_id = await self.initialize_from_snapshot(
                            buffered_events
                        )

                        await queue.put(snapshot)

                        # Replay all buffered events that are newer than the snapshot.
                        while buffered_events:
                            msg = buffered_events.popleft()
                            event_u = int(msg["u"])
                            event_U = int(msg["U"])

                            # Ignore duplicate or stale messages.
                            if event_u <= last_update_id:
                                continue

                            # Detect sequence gaps before applying the update.
                            if event_U > last_update_id + 1:
                                raise RuntimeError(
                                    f"binance buffered sequence gap: expected at most "
                                    f"{last_update_id + 1}, got {event_U}"
                                )

                            await queue.put(self.parse_update_message(msg))
                            last_update_id = event_u

                        # Continue with live events from the same buffer.
                        while True:
                            while not buffered_events:
                                await asyncio.sleep(0.001)

                            msg = buffered_events.popleft()
                            event_u = int(msg["u"])
                            event_U = int(msg["U"])

                            # Ignore duplicate or stale messages.
                            if event_u <= last_update_id:
                                continue

                            # Detect sequence gaps before applying the update.
                            if event_U > last_update_id + 1:
                                raise RuntimeError(
                                    f"binance live sequence gap: expected at most "
                                    f"{last_update_id + 1}, got {event_U}"
                                )

                            await queue.put(self.parse_update_message(msg))
                            last_update_id = event_u

                    finally:
                        stop_reader.set()
                        reader_task.cancel()
                        try:
                            await reader_task
                        except asyncio.CancelledError:
                            pass

            except Exception as exc:
                logger.warning("binance reconnecting after error: %s", exc)
                await asyncio.sleep(2)

    async def initialize_from_snapshot(
        self,
        buffered_events: deque[dict],
        max_attempts: int = 5,
    ) -> tuple[MarketDataEvent, int]:
        # Retry the REST snapshot a few times while the websocket keeps buffering.
        # This avoids unnecessary full reconnects when one snapshot cannot be bridged.
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            snapshot = await asyncio.to_thread(self.fetch_snapshot_event)
            last_update_id = snapshot.sequence

            if last_update_id is None:
                raise RuntimeError("binance snapshot missing last_update_id")

            try:
                self.drop_stale_buffered_events(buffered_events, last_update_id)
                self.validate_snapshot_bridge(buffered_events, last_update_id)
                return snapshot, last_update_id
            except RuntimeError as exc:
                last_error = exc
                logger.warning(
                    "binance snapshot bridge attempt %s/%s failed: %s",
                    attempt,
                    max_attempts,
                    exc,
                )

                # Give the reader a moment to accumulate fresher diff events.
                await asyncio.sleep(0.1)

        raise RuntimeError(
            f"binance failed to initialize local book after {max_attempts} "
            f"snapshot attempts: {last_error}"
        )

    def drop_stale_buffered_events(
        self,
        buffered_events: deque[dict],
        last_update_id: int,
    ) -> None:
        # Remove buffered events that are already fully covered by the snapshot.
        while buffered_events and int(buffered_events[0]["u"]) <= last_update_id:
            buffered_events.popleft()

    def validate_snapshot_bridge(
        self,
        buffered_events: deque[dict],
        last_update_id: int,
    ) -> None:
        # Binance requires the first retained diff event to cover the next update id
        # after the snapshot, not the snapshot id itself.
        if not buffered_events:
            raise RuntimeError("no buffered events remain")

        first_event = buffered_events[0]
        first_u = int(first_event["u"])
        first_U = int(first_event["U"])
        next_update_id = last_update_id + 1

        if not (first_U <= next_update_id <= first_u):
            raise RuntimeError(
                f"first buffered event does not bridge next snapshot id: "
                f"U={first_U} u={first_u} next={next_update_id}"
            )

    def fetch_snapshot_event(self) -> MarketDataEvent:
        # Fetch the initial REST snapshot required by Binance's local-book procedure.
        query = urlencode({"symbol": BINANCE_SYMBOL, "limit": 1000})
        url = f"{BINANCE_REST_SNAPSHOT_URL}?{query}"

        with urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        bids = [(float(price), float(size)) for price, size in payload.get("bids", [])]
        asks = [(float(price), float(size)) for price, size in payload.get("asks", [])]
        last_update_id = int(payload["lastUpdateId"])

        return MarketDataEvent(
            source="binance",
            symbol=BINANCE_SYMBOL,
            channel="depth",
            event_type="snapshot",
            exchange_ts=None,
            received_ts=utc_now_iso(),
            sequence=last_update_id,
            bid_updates=bids,
            ask_updates=asks,
            raw=payload,
        )

    def parse_update_message(self, msg: dict) -> MarketDataEvent:
        # Convert one already-validated Binance diff message into the normalized form.
        bids = [(float(price), float(size)) for price, size in msg.get("b", [])]
        asks = [(float(price), float(size)) for price, size in msg.get("a", [])]

        return MarketDataEvent(
            source="binance",
            symbol=BINANCE_SYMBOL,
            channel="depth",
            event_type="update",
            exchange_ts=ms_to_iso(msg["E"]),
            received_ts=utc_now_iso(),
            sequence=int(msg["u"]),
            bid_updates=bids,
            ask_updates=asks,
            raw=msg,
        )
