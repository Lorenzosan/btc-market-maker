import asyncio
import json
import logging

from src.config import OUTPUT_INTERVAL_SECONDS, OUTPUT_VERBOSITY
from src.orderbook.manager import OrderBookManager
from src.fair_value.fair_value import FairValueEngine
from src.quoting.quote_engine import QuoteEngine
from src.utils.time import utc_now_iso

logger = logging.getLogger(__name__)

def format_top(top: dict) -> str:
    # Compact one-venue rendering for terminal output.
    best_bid = top["best_bid"]
    best_ask = top["best_ask"]

    if best_bid is None or best_ask is None:
        return "NA"

    bid_px, bid_sz = best_bid
    ask_px, ask_sz = best_ask
    return f"{bid_px:.2f}({bid_sz:.4f})/{ask_px:.2f}({ask_sz:.4f})"

def format_quote_side(price: float | None, size: float | None) -> str:
    # Compact rendering for one quote side.
    if price is None or size is None:
        return "NA"
    return f"{price:.2f} x {size:.4f}"


def build_event_payload(event, top: dict, fv, quote, verbosity: int) -> dict:
    # Common payload shared by verbose output modes.
    payload = {
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
        "fair_value": fv.fair_value,
        "fair_value_status": fv.status,
        "reservation_price": quote.reservation_price,
        "quote_bid_price": quote.bid_price,
        "quote_bid_size": quote.bid_size,
        "quote_ask_price": quote.ask_price,
        "quote_ask_size": quote.ask_size,
        "quote_inventory": quote.inventory,
        "quote_status": quote.status,
    }

    if verbosity >= 2:
        payload["fair_value_inputs"] = [
            {
                "source": q.source,
                "mid": round(q.mid, 2),
                "spread": round(q.spread, 2),
                "weight": round(q.weight, 4),
            }
            for q in fv.inputs
        ]

    return payload


async def print_books(queue: asyncio.Queue):
    # Single manager instance that tracks one local book per source.
    manager = OrderBookManager()


    # Fair-value engine built on top of maintained venue books.
    # The spread filter threshold is configured centrally to avoid hard-coded parameters here.
    fair_value_engine = FairValueEngine(max_spread=FAIR_VALUE_MAX_SPREAD)

    # Quote engine built on top of fair value.
    quote_engine = QuoteEngine()

    async def consumer() -> None:
        # Consume and apply events as fast as they arrive.
        while True:
            event = await queue.get()
            manager.apply_event(event)

            if OUTPUT_VERBOSITY >= 1:
                top = manager.top_of_book(event.source)
                fv = fair_value_engine.compute(manager)
                quote = quote_engine.compute(fv)
                payload = build_event_payload(event, top, fv, quote, OUTPUT_VERBOSITY)
                logger.info(json.dumps(payload, separators=(",", ":")))

            queue.task_done()

    async def reporter() -> None:
        # Emit one compact consolidated snapshot periodically in level-0 mode.
        # The timestamp is the local reporting time in UTC.
        if OUTPUT_VERBOSITY != 0:
            return

        while True:
            await asyncio.sleep(OUTPUT_INTERVAL_SECONDS)

            binance_top = manager.top_of_book("binance")
            coinbase_top = manager.top_of_book("coinbase")
            fv = fair_value_engine.compute(manager)
            quote = quote_engine.compute(fv)

            binance_str = format_top(binance_top)
            coinbase_str = format_top(coinbase_top)
            fv_str = "NA" if fv.fair_value is None else f"{fv.fair_value:.2f}"
            bid_str = format_quote_side(quote.bid_price, quote.bid_size)
            ask_str = format_quote_side(quote.ask_price, quote.ask_size)

            logger.info(
                "ts=%s | bin=%s | cb=%s | fv=%s | bid=%s | ask=%s | status=%s",
                utc_now_iso(),
                binance_str,
                coinbase_str,
                fv_str,
                bid_str,
                ask_str,
                quote.status,
            )

    await asyncio.gather(
        consumer(),
        reporter(),
    )
