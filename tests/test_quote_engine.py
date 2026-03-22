from src.fair_value.fair_value import FairValueResult, VenueQuote
from src.quoting.quote_engine import QuoteEngine


def make_quote(
    source: str,
    bid: float,
    ask: float,
    size: float = 1.0,
    confidence: str = "high",
) -> VenueQuote:
    mid = (bid + ask) / 2.0
    spread = ask - bid
    return VenueQuote(
        source=source,
        bid=bid,
        ask=ask,
        bid_size=size,
        ask_size=size,
        mid=mid,
        spread=spread,
        spread_bps=(spread / mid) * 10000.0,
        top_size=size,
        deviation_bps=0.0,
        weight=1.0,
        confidence=confidence,
        recently_resynced=False,
        excluded_reason=None,
    )


def test_inactive_when_no_fair_value():
    engine = QuoteEngine(
        min_half_spread=2.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.0,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
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

    quote = engine.compute(fair_value)

    assert quote.reservation_price is None
    assert quote.bid_price is None
    assert quote.ask_price is None
    assert quote.bid_size is None
    assert quote.ask_size is None
    assert quote.status == "inactive_no_fair_value"


def test_quotes_are_suppressed_for_single_low_confidence_venue():
    engine = QuoteEngine(
        min_half_spread=1.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.0,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[make_quote("coinbase", 99.0, 101.0, confidence="low")],
        excluded_inputs=[],
        status="single_low_confidence_venue",
        reference_mid=100.0,
        best_bid=99.0,
        best_ask=101.0,
        cross_venue_best_spread=2.0,
        disagreement_bps=0.0,
        market_health="unhealthy",
        confidence_profile="low_only",
        active_source_count=1,
        low_confidence_source_count=1,
    )

    quote = engine.compute(fair_value)

    assert quote.bid_price is None
    assert quote.ask_price is None
    assert quote.status == "inactive_single_low_confidence_venue"


def test_quotes_are_suppressed_for_excessive_disagreement():
    engine = QuoteEngine(
        min_half_spread=1.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.0,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            make_quote("binance", 99.0, 101.0, confidence="high"),
            make_quote("coinbase", 98.0, 102.0, confidence="low"),
        ],
        excluded_inputs=[],
        status="ok",
        reference_mid=100.0,
        best_bid=99.0,
        best_ask=101.0,
        cross_venue_best_spread=2.0,
        disagreement_bps=12.0,
        market_health="unhealthy",
        confidence_profile="mixed",
        active_source_count=2,
        low_confidence_source_count=1,
    )

    quote = engine.compute(fair_value)

    assert quote.bid_price is None
    assert quote.ask_price is None
    assert quote.status == "inactive_excessive_disagreement"


def test_quotes_do_not_cross_visible_market():
    engine = QuoteEngine(
        min_half_spread=1.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.0,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            make_quote("binance", 99.0, 101.0, confidence="high"),
            make_quote("coinbase", 99.2, 100.8, confidence="low"),
        ],
        excluded_inputs=[],
        status="ok",
        reference_mid=100.0,
        best_bid=99.2,
        best_ask=100.8,
        cross_venue_best_spread=1.6,
        disagreement_bps=1.0,
        market_health="healthy",
        confidence_profile="mixed",
        active_source_count=2,
        low_confidence_source_count=1,
    )

    quote = engine.compute(fair_value)

    assert quote.bid_price is not None
    assert quote.ask_price is not None
    assert quote.bid_price <= 99.19
    assert quote.ask_price >= 100.81
    assert quote.status == "active_two_sided"


def test_inventory_skews_reservation_price_lower_when_long():
    engine = QuoteEngine(
        min_half_spread=1.0,
        base_size=0.01,
        inventory_skew=10.0,
        inventory=0.02,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            make_quote("binance", 99.0, 101.0, confidence="high"),
            make_quote("coinbase", 99.5, 100.5, confidence="low"),
        ],
        excluded_inputs=[],
        status="ok",
        reference_mid=100.0,
        best_bid=99.5,
        best_ask=100.5,
        cross_venue_best_spread=1.0,
        disagreement_bps=1.0,
        market_health="healthy",
        confidence_profile="mixed",
        active_source_count=2,
        low_confidence_source_count=1,
    )

    quote = engine.compute(fair_value)

    assert quote.reservation_price == 96.0
    assert quote.bid_size is not None
    assert quote.ask_size is not None
    assert quote.bid_size < quote.ask_size
    assert quote.status == "active_two_sided"


def test_long_inventory_limit_disables_bid_side():
    engine = QuoteEngine(
        min_half_spread=1.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.05,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            make_quote("binance", 99.0, 101.0, confidence="high"),
            make_quote("coinbase", 99.5, 100.5, confidence="low"),
        ],
        excluded_inputs=[],
        status="ok",
        reference_mid=100.0,
        best_bid=99.5,
        best_ask=100.5,
        cross_venue_best_spread=1.0,
        disagreement_bps=1.0,
        market_health="healthy",
        confidence_profile="mixed",
        active_source_count=2,
        low_confidence_source_count=1,
    )

    quote = engine.compute(fair_value)

    assert quote.bid_price is None
    assert quote.bid_size is None
    assert quote.ask_price is not None
    assert quote.ask_size is not None
    assert quote.status == "ask_only_inventory_limit"


def test_tiny_low_confidence_size_does_not_collapse_quote_size_when_high_confidence_exists():
    engine = QuoteEngine(
        min_half_spread=1.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.0,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            make_quote("binance", 99.9, 100.1, size=0.02, confidence="high"),
            make_quote("coinbase", 99.8, 100.2, size=0.0001, confidence="low"),
        ],
        excluded_inputs=[],
        status="ok",
        reference_mid=100.0,
        best_bid=99.9,
        best_ask=100.1,
        cross_venue_best_spread=0.2,
        disagreement_bps=1.0,
        market_health="healthy",
        confidence_profile="mixed",
        active_source_count=2,
        low_confidence_source_count=1,
    )

    quote = engine.compute(fair_value)

    assert quote.bid_size is not None
    assert quote.ask_size is not None
    assert quote.bid_size >= 0.004
    assert quote.ask_size >= 0.004
    assert quote.status == "active_two_sided"


def test_both_sides_are_suppressed_when_size_is_too_small():
    engine = QuoteEngine(
        min_half_spread=1.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.0,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[make_quote("binance", 99.9, 100.1, size=0.0004, confidence="high")],
        excluded_inputs=[],
        status="single_venue_only",
        reference_mid=100.0,
        best_bid=99.9,
        best_ask=100.1,
        cross_venue_best_spread=0.2,
        disagreement_bps=0.0,
        market_health="degraded",
        confidence_profile="high_only",
        active_source_count=1,
        low_confidence_source_count=0,
    )

    quote = engine.compute(fair_value)

    assert quote.bid_price is None
    assert quote.bid_size is None
    assert quote.ask_price is None
    assert quote.ask_size is None
    assert quote.status == "inactive_size_too_small"
