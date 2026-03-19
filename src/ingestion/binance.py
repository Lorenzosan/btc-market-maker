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
        # Maintain a Binance local order book from websocket diffs plus REST snapshot.
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

                    # Buffer diff events while snapshot sync is performed.
                    buffered_events: deque[dict] = deque()
                    stop_reader = asyncio.Event()

                    async def reader() -> None:
                        while not stop_reader.is_set():
                            raw_msg = await ws.recv()
                            msg = json.loads(raw_msg)

                            # Only depthUpdate messages belong to the diff-depth stream.
                            if msg.get("e") != "depthUpdate":
                                continue

                            buffered_events.append(msg)

                    reader_task = asyncio.create_task(reader())

                    try:
                        # Wait until at least one diff event arrives before starting sync.
                        while not buffered_events:
                            await asyncio.sleep(0.01)

                        snapshot, last_update_id = await self.initialize_from_snapshot(
                            buffered_events
                        )

                        # Publish the validated snapshot first.
                        await queue.put(snapshot)

                        # Replay buffered events newer than the snapshot.
                        while buffered_events:
                            msg = buffered_events.popleft()
                            event_u = int(msg["u"])
                            event_U = int(msg["U"])

                            # Ignore stale or duplicate events.
                            if event_u <= last_update_id:
                                continue

                            # Detect a forward gap in the update sequence.
                            if event_U > last_update_id + 1:
                                raise RuntimeError(
                                    f"binance buffered sequence gap: expected at most "
                                    f"{last_update_id + 1}, got {event_U}"
                                )

                            await queue.put(self.parse_update_message(msg))
                            last_update_id = event_u

                        # Continue processing live diff events.
                        while True:
                            while not buffered_events:
                                await asyncio.sleep(0.001)

                            msg = buffered_events.popleft()
                            event_u = int(msg["u"])
                            event_U = int(msg["U"])

                            # Ignore stale or duplicate events.
                            if event_u <= last_update_id:
                                continue

                            # Detect a forward gap in the update sequence.
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
        max_attempts: int = 10,
    ) -> tuple[MarketDataEvent, int]:
        # Retry snapshot sync while keeping the websocket alive.
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            # If the buffer is empty, give the websocket a moment to accumulate diffs.
            if not buffered_events:
                await asyncio.sleep(0.05)
                continue

            snapshot = await asyncio.to_thread(self.fetch_snapshot_event)
            last_update_id = snapshot.sequence

            if last_update_id is None:
                raise RuntimeError("binance snapshot missing last_update_id")

            # Discard events fully covered by the snapshot.
            self.drop_stale_buffered_events(buffered_events, last_update_id)

            # If the snapshot overtook the current tiny buffer, wait briefly for fresher diffs.
            waited = 0.0
            sleep_step = 0.01
            wait_timeout = 1.0

            while not buffered_events and waited < wait_timeout:
                await asyncio.sleep(sleep_step)
                waited += sleep_step

            try:
                self.validate_snapshot_bridge(buffered_events, last_update_id)
                return snapshot, last_update_id
            except RuntimeError as exc:
                last_error = exc
                logger.warning(
                    "binance snapshot sync attempt %s/%s failed: %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                await asyncio.sleep(0.05)

        raise RuntimeError(
            f"binance failed to initialize local book after {max_attempts} "
            f"snapshot attempts: {last_error}"
        )

    def drop_stale_buffered_events(
        self,
        buffered_events: deque[dict],
        last_update_id: int,
    ) -> None:
        # Discard events that are fully older than the snapshot.
        while buffered_events and int(buffered_events[0]["u"]) <= last_update_id:
            buffered_events.popleft()

    def validate_snapshot_bridge(
        self,
        buffered_events: deque[dict],
        last_update_id: int,
    ) -> None:
        # The first remaining event must bridge the next update id after the snapshot.
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
        # Fetch the REST snapshot used to initialize the local order book.
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
        # Convert one Binance diff-depth message into the normalized update form.
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
