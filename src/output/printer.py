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


def fmt_size(size: float) -> str:
    if size is None:
        return "NA"
    if size <= 0:
        return "0"
    if size < 0.0001:
        return "<0.0001"
    return f"{size:.4f}"


def format_top(top: dict) -> str:
    best_bid = top["best_bid"]
    best_ask = top["best_ask"]

    if best_bid is None or best_ask is None:
        return "NA"

    bid_px, bid_sz = best_bid
    ask_px, ask_sz = best_ask
    return f"{bid_px:.2f}({fmt_size(bid_sz)})/{ask_px:.2f}({fmt_size(ask_sz)})"


def format_quote_side(price: float | None, size: float | None) -> str:
    if price is None or size is None:
        return "NA"
    return f"{price:.2f} x {fmt_size(size)}"


def build_event_payload(event, top: dict, fv, quote, verbosity: int) -> dict:
    payload = {
        "event_source": event.source,
        "symbol": event.symbol,
        "exchange_ts": event.exchange_ts,
        "observed_ts": utc_now_iso(),
        "book": {
            "best_bid": top["best_bid"],
            "best_ask": top["best_ask"],
            "mid": top["mid"],
            "spread": top["spread"],
            "initialized": top["initialized"],
            "valid": top["valid"],
            "status": top["status"],
            "last_sequence": top["last_sequence"],
            "last_received_ts": top["last_received_ts"],
            "age_ms": top["age_ms"],
            "is_stale": top["is_stale"],
        },
        "fair_value": {
            "value": fv.fair_value,
            "status": fv.status,
            "reference_mid": fv.reference_mid,
            "best_bid": fv.best_bid,
            "best_ask": fv.best_ask,
            "cross_venue_best_spread": fv.cross_venue_best_spread,
            "disagreement_bps": fv.disagreement_bps,
        },
        "quote": {
            "reservation_price": quote.reservation_price,
            "bid_price": quote.bid_price,
            "bid_size": quote.bid_size,
            "ask_price": quote.ask_price,
            "ask_size": quote.ask_size,
            "inventory": quote.inventory,
            "status": quote.status,
        },
    }

    if hasattr(fv, "market_health"):
        payload["fair_value"]["market_health"] = fv.market_health

    if hasattr(fv, "confidence_profile"):
        payload["fair_value"]["confidence_profile"] = fv.confidence_profile

    if verbosity >= 2:
        payload["fair_value"]["inputs"] = [
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
                "confidence": getattr(q, "confidence", None),
            }
            for q in fv.inputs
        ]

        excluded_inputs = getattr(fv, "excluded_inputs", [])
        payload["fair_value"]["excluded_inputs"] = [
            {
                "source": q.source,
                "mid": round(q.mid, 2) if q.mid is not None else None,
                "spread_bps": round(q.spread_bps, 4) if q.spread_bps is not None else None,
                "deviation_bps": round(q.deviation_bps, 4) if q.deviation_bps is not None else None,
                "confidence": getattr(q, "confidence", None),
                "excluded_reason": getattr(q, "excluded_reason", "unknown"),
            }
            for q in excluded_inputs
        ]

        payload["quote"]["debug"] = {
            "raw_size": quote.raw_size,
            "liquidity_cap": quote.liquidity_cap,
            "health_factor": quote.health_factor,
            "spread_factor": quote.spread_factor,
            "disagreement_factor": quote.disagreement_factor,
            "bid_size_factor": quote.bid_size_factor,
            "ask_size_factor": quote.ask_size_factor,
            "half_spread": quote.half_spread,
        }

    return payload


def build_summary_payload(payload: dict) -> dict:
    fair_value = payload["fair_value"]
    quote = payload["quote"]
    book = payload["book"]

    return {
        "event_source": payload["event_source"],
        "symbol": payload["symbol"],
        "exchange_ts": payload["exchange_ts"],
        "observed_ts": payload["observed_ts"],
        "book": {
            "best_bid": book["best_bid"],
            "best_ask": book["best_ask"],
            "status": book["status"],
            "is_stale": book["is_stale"],
        },
        "fair_value": {
            "value": fair_value["value"],
            "status": fair_value["status"],
            "reference_mid": fair_value["reference_mid"],
            "best_bid": fair_value["best_bid"],
            "best_ask": fair_value["best_ask"],
            "cross_venue_best_spread": fair_value["cross_venue_best_spread"],
            "disagreement_bps": fair_value["disagreement_bps"],
            "market_health": fair_value.get("market_health"),
            "confidence_profile": fair_value.get("confidence_profile"),
        },
        "quote": {
            "reservation_price": quote["reservation_price"],
            "bid_price": quote["bid_price"],
            "bid_size": quote["bid_size"],
            "ask_price": quote["ask_price"],
            "ask_size": quote["ask_size"],
            "inventory": quote["inventory"],
            "status": quote["status"],
        },
    }


async def run_output_loop(
    queue: asyncio.Queue,
    inventory=INITIAL_INVENTORY,
    base_size=QUOTE_BASE_SIZE,
    verbosity=OUTPUT_VERBOSITY,
):
    manager = OrderBookManager(backend="cpp")
    fair_value_engine = FairValueEngine()
    quote_engine = QuoteEngine(
        inventory=inventory,
        base_size=base_size,
    )

    async def consumer() -> None:
        while True:
            event = await queue.get()
            try:
                manager.apply_event(event)
                manager.refresh_staleness(VENUE_STALE_AFTER_SECONDS)

                if verbosity >= 1:
                    top = manager.top_of_book(event.source)
                    fv = fair_value_engine.compute(manager)
                    quote = quote_engine.compute(fv)
                    payload = build_event_payload(event, top, fv, quote, verbosity)

                    if verbosity == 1:
                        logger.info(
                            json.dumps(
                                build_summary_payload(payload),
                                separators=(",", ":"),
                            )
                        )
                    else:
                        logger.info(json.dumps(payload, separators=(",", ":")))
            finally:
                queue.task_done()

    async def reporter() -> None:
        if verbosity != 0:
            return

        while True:
            await asyncio.sleep(OUTPUT_INTERVAL_SECONDS)
            manager.refresh_staleness(VENUE_STALE_AFTER_SECONDS)

            bn_top = manager.top_of_book("binance")
            cb_top = manager.top_of_book("coinbase")

            fv = fair_value_engine.compute(manager)
            quote = quote_engine.compute(fv)

            bn_str = format_top(bn_top)
            cb_str = format_top(cb_top)

            fv_str = "NA" if fv.fair_value is None else f"{fv.fair_value:.2f}"
            bid_str = format_quote_side(quote.bid_price, quote.bid_size)
            ask_str = format_quote_side(quote.ask_price, quote.ask_size)

            disc_str = "NA"
            if fv.disagreement_bps is not None and fv.active_source_count >= 2:
                disc_str = f"{fv.disagreement_bps:.3f}bps"

            print(
                f"{utc_now_iso()} | "
                f"bn={bn_str} | "
                f"cb={cb_str} | "
                f"fv={fv_str} | "
                f"disc={disc_str} | "
                f"bid={bid_str} | "
                f"ask={ask_str} | "
                f"sts={quote.status}",
                flush=True,
            )

    await asyncio.gather(
        consumer(),
        reporter(),
    )
