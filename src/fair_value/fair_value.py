import time
from dataclasses import dataclass
from statistics import median

from src.config import (
    FAIR_VALUE_EXCLUDE_AFTER_RESYNC_SECONDS,
    FAIR_VALUE_LOW_CONFIDENCE_PENALTY,
    FAIR_VALUE_MAX_DEVIATION_BPS,
    FAIR_VALUE_MAX_SPREAD_BPS,
    FAIR_VALUE_MIN_TOP_LEVEL_SIZE,
    QUOTE_SUPPRESS_MAX_DISAGREEMENT_BPS,
)
from src.orderbook.manager import OrderBookManager


@dataclass
class VenueQuote:
    # Compact per-venue pricing view used by the fair-value engine.
    source: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    mid: float
    spread: float
    spread_bps: float
    top_size: float
    deviation_bps: float
    weight: float
    confidence: str
    recently_resynced: bool
    excluded_reason: str | None = None


@dataclass
class FairValueResult:
    # Final fair-value output plus diagnostics.
    fair_value: float | None
    inputs: list[VenueQuote]
    excluded_inputs: list[VenueQuote]
    status: str
    reference_mid: float | None
    best_bid: float | None
    best_ask: float | None
    cross_venue_best_spread: float | None
    disagreement_bps: float | None
    market_health: str
    confidence_profile: str
    active_source_count: int
    low_confidence_source_count: int


class FairValueEngine:
    def __init__(
        self,
        max_spread_bps: float = FAIR_VALUE_MAX_SPREAD_BPS,
        max_deviation_bps: float = FAIR_VALUE_MAX_DEVIATION_BPS,
        min_top_level_size: float = FAIR_VALUE_MIN_TOP_LEVEL_SIZE,
        exclude_after_resync_seconds: float = FAIR_VALUE_EXCLUDE_AFTER_RESYNC_SECONDS,
        low_confidence_penalty: float = FAIR_VALUE_LOW_CONFIDENCE_PENALTY,
    ) -> None:
        # Venues wider than this are excluded from pricing.
        self.max_spread_bps = max_spread_bps

        # Venues too far from the cross-venue median mid are excluded.
        self.max_deviation_bps = max_deviation_bps

        # Tiny visible top-of-book sizes are floored to avoid zero weight.
        self.min_top_level_size = min_top_level_size

        # Recently recovered venues are temporarily excluded.
        self.exclude_after_resync_seconds = exclude_after_resync_seconds

        # Lower-confidence venues receive a multiplicative weight penalty.
        self.low_confidence_penalty = low_confidence_penalty

    def _classify_confidence(self, source: str) -> str:
        # Binance is treated as higher confidence because the local book is
        # sequence-maintained. Coinbase is best-effort with periodic resync.
        if source == "binance":
            return "high"
        if source == "coinbase":
            return "low"
        return "medium"

    def _extract_candidate_quote(
        self,
        manager: OrderBookManager,
        source: str,
        now_monotonic: float,
    ) -> VenueQuote | None:
        # Pull one venue out of the manager and decide whether it is usable.
        state = manager.get_state(source)

        if not state.initialized or not state.valid or state.is_stale or state.needs_resync:
            return None

        best_bid = state.book.best_bid()
        best_ask = state.book.best_ask()

        if best_bid is None or best_ask is None:
            return None

        bid_price, bid_size = best_bid
        ask_price, ask_size = best_ask
        spread = ask_price - bid_price

        if spread <= 0:
            return None

        mid = (bid_price + ask_price) / 2.0
        if mid <= 0:
            return None

        spread_bps = (spread / mid) * 10000.0
        if spread_bps > self.max_spread_bps:
            return None

        recently_resynced = False
        if state.last_resync_monotonic is not None:
            recently_resynced = (
                now_monotonic - state.last_resync_monotonic
            ) < self.exclude_after_resync_seconds

        confidence = self._classify_confidence(source)

        # The minimum visible size across the best bid and best ask is a more
        # conservative measure than using only one side.
        top_size = max(self.min_top_level_size, min(bid_size, ask_size))

        # Weighting combines tight spread with some liquidity awareness.
        # The square root dampens the impact of very large displayed size.
        weight = (top_size ** 0.5) / spread_bps

        # Lower-confidence venues remain usable, but carry less influence.
        if confidence == "low":
            weight *= self.low_confidence_penalty

        return VenueQuote(
            source=source,
            bid=bid_price,
            ask=ask_price,
            bid_size=bid_size,
            ask_size=ask_size,
            mid=mid,
            spread=spread,
            spread_bps=spread_bps,
            top_size=top_size,
            deviation_bps=0.0,
            weight=weight,
            confidence=confidence,
            recently_resynced=recently_resynced,
            excluded_reason=None,
        )

    def _reject_outliers(
        self,
        quotes: list[VenueQuote],
    ) -> tuple[list[VenueQuote], list[VenueQuote], float | None]:
        # Use the median mid as a stable cross-venue reference.
        if not quotes:
            return [], [], None

        reference_mid = median(q.mid for q in quotes)
        filtered_quotes: list[VenueQuote] = []
        excluded_quotes: list[VenueQuote] = []

        for quote in quotes:
            if quote.recently_resynced:
                quote.excluded_reason = "recent_resync_cooldown"
                excluded_quotes.append(quote)
                continue

            deviation_bps = abs(quote.mid - reference_mid) / reference_mid * 10000.0
            quote.deviation_bps = deviation_bps

            if deviation_bps <= self.max_deviation_bps:
                filtered_quotes.append(quote)
            else:
                quote.excluded_reason = "mid_outlier"
                excluded_quotes.append(quote)

        return filtered_quotes, excluded_quotes, reference_mid

    def _confidence_profile(self, active_quotes: list[VenueQuote]) -> str:
        # Confidence profile describes the trust composition of active venues.
        if not active_quotes:
            return "none"

        confidences = {quote.confidence for quote in active_quotes}

        if confidences == {"high"}:
            return "high_only"

        if confidences == {"low"}:
            return "low_only"

        return "mixed"

    def _market_health(
        self,
        active_quotes: list[VenueQuote],
        disagreement_bps: float | None,
    ) -> str:
        # Market health reflects current pricing conditions, not venue identity.
        if not active_quotes:
            return "unhealthy"

        if len(active_quotes) == 1:
            if active_quotes[0].confidence == "low":
                return "unhealthy"
            return "degraded"

        if disagreement_bps is None:
            return "degraded"

        if disagreement_bps >= QUOTE_SUPPRESS_MAX_DISAGREEMENT_BPS:
            return "unhealthy"

        if disagreement_bps >= 4.0:
            return "degraded"

        return "healthy"

    def compute(self, manager: OrderBookManager) -> FairValueResult:
        # Collect candidate venues from the current manager state.
        now_monotonic = time.monotonic()
        candidate_quotes: list[VenueQuote] = []

        for source in sorted(manager.states.keys()):
            quote = self._extract_candidate_quote(manager, source, now_monotonic)
            if quote is not None:
                candidate_quotes.append(quote)

        if not candidate_quotes:
            return FairValueResult(
                fair_value=None,
                inputs=[],
                excluded_inputs=[],
                status="no_usable_venues",
                reference_mid=None,
                best_bid=None,
                best_ask=None,
                cross_venue_best_spread=None,
                disagreement_bps=None,
                market_health="unhealthy",
                confidence_profile="none",
                active_source_count=0,
                low_confidence_source_count=0,
            )

        filtered_quotes, excluded_quotes, reference_mid = self._reject_outliers(candidate_quotes)

        if not filtered_quotes:
            return FairValueResult(
                fair_value=None,
                inputs=[],
                excluded_inputs=excluded_quotes,
                status="all_venues_filtered",
                reference_mid=round(reference_mid, 2) if reference_mid is not None else None,
                best_bid=None,
                best_ask=None,
                cross_venue_best_spread=None,
                disagreement_bps=None,
                market_health="unhealthy",
                confidence_profile="none",
                active_source_count=0,
                low_confidence_source_count=0,
            )

        total_weight = sum(q.weight for q in filtered_quotes)
        if total_weight <= 0:
            return FairValueResult(
                fair_value=None,
                inputs=[],
                excluded_inputs=filtered_quotes + excluded_quotes,
                status="invalid_weights",
                reference_mid=round(reference_mid, 2) if reference_mid is not None else None,
                best_bid=None,
                best_ask=None,
                cross_venue_best_spread=None,
                disagreement_bps=None,
                market_health="unhealthy",
                confidence_profile="none",
                active_source_count=0,
                low_confidence_source_count=0,
            )

        fair_value = sum(q.mid * q.weight for q in filtered_quotes) / total_weight
        best_bid = max(q.bid for q in filtered_quotes)
        best_ask = min(q.ask for q in filtered_quotes)
        cross_venue_best_spread = best_ask - best_bid

        mids = [q.mid for q in filtered_quotes]
        disagreement_bps = ((max(mids) - min(mids)) / fair_value) * 10000.0 if len(mids) > 1 else 0.0

        market_health = self._market_health(filtered_quotes, disagreement_bps)
        confidence_profile = self._confidence_profile(filtered_quotes)
        low_confidence_source_count = sum(1 for q in filtered_quotes if q.confidence == "low")

        if len(filtered_quotes) == 1:
            if filtered_quotes[0].confidence == "low":
                status = "single_low_confidence_venue"
            else:
                status = "single_venue_only"
        elif excluded_quotes:
            status = "ok_filtered"
        else:
            status = "ok"

        return FairValueResult(
            fair_value=round(fair_value, 2),
            inputs=filtered_quotes,
            excluded_inputs=excluded_quotes,
            status=status,
            reference_mid=round(reference_mid, 2) if reference_mid is not None else None,
            best_bid=round(best_bid, 2),
            best_ask=round(best_ask, 2),
            cross_venue_best_spread=round(cross_venue_best_spread, 2),
            disagreement_bps=round(disagreement_bps, 3),
            market_health=market_health,
            confidence_profile=confidence_profile,
            active_source_count=len(filtered_quotes),
            low_confidence_source_count=low_confidence_source_count,
        )
