import asyncio
import json
import logging

from src.config import (
    OUTPUT_INTERVAL_SECONDS,
    VENUE_STALE_AFTER_SECONDS,
    INITIAL_INVENTORY,
    QUOTE_BASE_SIZE,
    OUTPUT_VERBOSITY,
)
from src.fair_value.fair_value import FairValueEngine
from src.orderbook.manager import OrderBookManager
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
    return f"{bid_px:.2f}({bid_sz:.6f})/{ask_px:.2f}({ask_sz:.6f})"


def format_quote_side(price: float | None, size: float | None) -> str:
    # Compact rendering for one quote side.
    if price is None or size is None:
        return "NA"
    return f"{price:.2f} x {size:.6f}"


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
        "fair_value_reference_mid": fv.reference_mid,
        "fair_value_best_bid": fv.best_bid,
        "fair_value_best_ask": fv.best_ask,
        "fair_value_market_spread": fv.market_spread,
        "fair_value_disagreement_bps": fv.disagreement_bps,
        "reservation_price": quote.reservation_price,
        "quote_bid_price": quote.bid_price,
        "quote_bid_size": quote.bid_size,
        "quote_ask_price": quote.ask_price,
        "quote_ask_size": quote.ask_size,
        "quote_inventory": quote.inventory,
        "quote_status": quote.status,
        "last_received_ts": top["last_received_ts"],
        "age_ms": top["age_ms"],
        "is_stale": top["is_stale"],
    }

    if verbosity >= 2:
        payload["fair_value_inputs"] = [
            {
                "source": q.source,
                "mid": round(q.mid, 2),
                "spread": round(q.spread, 2),
                "spread_bps": round(q.spread_bps, 4),
                "bid_size": round(q.bid_size, 6),
                "ask_size": round(q.ask_size, 6),
                "top_size": round(q.top_size, 6),
                "deviation_bps": round(q.deviation_bps, 4),
                "weight": round(q.weight, 6),
            }
            for q in fv.inputs
        ]

    return payload


async def print_books(queue: asyncio.Queue,
                      inventory=INITIAL_INVENTORY,
                      base_size=QUOTE_BASE_SIZE,
                      verbosity=OUTPUT_VERBOSITY):
    # Single manager instance that tracks one local book per source.
    manager = OrderBookManager()

    # Fair-value engine built on top of maintained venue books.
    fair_value_engine = FairValueEngine()

    # Quote engine built on top of fair value.
    quote_engine = QuoteEngine(inventory=inventory,base_size=base_size,)

    async def consumer() -> None:
        # Consume and apply events as fast as they arrive.
        while True:
            event = await queue.get()
            manager.apply_event(event)
            manager.refresh_staleness(VENUE_STALE_AFTER_SECONDS)

            if verbosity >= 1:
                top = manager.top_of_book(event.source)
                fv = fair_value_engine.compute(manager)
                quote = quote_engine.compute(fv)
                payload = build_event_payload(event, top, fv, quote, verbosity)
                logger.info(json.dumps(payload, separators=(",", ":")))

            queue.task_done()

    async def reporter() -> None:
        # Emit one compact consolidated snapshot periodically in level-0 mode.
        if verbosity != 0:
            return

        while True:
            await asyncio.sleep(OUTPUT_INTERVAL_SECONDS)
            manager.refresh_staleness(VENUE_STALE_AFTER_SECONDS)

            binance_top = manager.top_of_book("binance")
            coinbase_top = manager.top_of_book("coinbase")
            fv = fair_value_engine.compute(manager)
            quote = quote_engine.compute(fv)

            binance_str = format_top(binance_top)
            coinbase_str = format_top(coinbase_top)
            fv_str = "NA" if fv.fair_value is None else f"{fv.fair_value:.2f}"
            bid_str = format_quote_side(quote.bid_price, quote.bid_size)
            ask_str = format_quote_side(quote.ask_price, quote.ask_size)
            disagreement_str = (
                "NA"
                if fv.disagreement_bps is None
                else f"{fv.disagreement_bps:.3f}bps"
            )

            print(
                f"{utc_now_iso()} | bin={binance_str} | cb={coinbase_str} | "
                f"fv={fv_str} | disc={disagreement_str} | "
                f"bid={bid_str} | ask={ask_str} | status={quote.status}",
                flush=True,
            )

    await asyncio.gather(
        consumer(),
        reporter(),
    )
