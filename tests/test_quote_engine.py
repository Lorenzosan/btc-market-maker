from src.fair_value.fair_value import FairValueResult, VenueQuote
from src.quoting.quote_engine import QuoteEngine


def test_inactive_when_no_fair_value():
    engine = QuoteEngine(
        half_spread=2.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.0,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=None,
        inputs=[],
        status="no_usable_venues",
    )

    quote = engine.compute(fair_value)

    assert quote.reservation_price is None
    assert quote.bid_price is None
    assert quote.ask_price is None
    assert quote.bid_size is None
    assert quote.ask_size is None
    assert quote.status == "inactive_no_fair_value"


def test_quotes_center_around_reservation_price():
    engine = QuoteEngine(
        half_spread=2.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.0,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            VenueQuote(
                source="binance",
                bid=99.0,
                ask=101.0,
                mid=100.0,
                spread=2.0,
                weight=1.0,
            ),
            VenueQuote(
                source="coinbase",
                bid=99.5,
                ask=100.5,
                mid=100.0,
                spread=1.0,
                weight=1.0,
            ),
        ],
        status="ok",
    )

    quote = engine.compute(fair_value)

    assert quote.reservation_price == 100.0
    assert quote.bid_price == 98.0
    assert quote.ask_price == 102.0
    assert quote.bid_size == 0.01
    assert quote.ask_size == 0.01
    assert quote.status == "active_two_sided"


def test_inventory_skews_reservation_price_lower_when_long():
    engine = QuoteEngine(
        half_spread=1.0,
        base_size=0.01,
        inventory_skew=10.0,
        inventory=0.02,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            VenueQuote(
                source="binance",
                bid=99.0,
                ask=101.0,
                mid=100.0,
                spread=2.0,
                weight=1.0,
            ),
            VenueQuote(
                source="coinbase",
                bid=99.5,
                ask=100.5,
                mid=100.0,
                spread=1.0,
                weight=1.0,
            ),
        ],
        status="ok",
    )

    quote = engine.compute(fair_value)

    assert quote.reservation_price == 99.8
    assert quote.bid_price == 98.8
    assert quote.ask_price == 100.8
    assert quote.status == "active_two_sided"


def test_single_venue_quotes_are_degraded():
    engine = QuoteEngine(
        half_spread=2.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.0,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            VenueQuote(
                source="binance",
                bid=99.0,
                ask=101.0,
                mid=100.0,
                spread=2.0,
                weight=1.0,
            ),
        ],
        status="single_venue_only",
    )

    quote = engine.compute(fair_value)

    assert quote.reservation_price == 100.0
    assert quote.bid_price == 96.0
    assert quote.ask_price == 104.0
    assert quote.bid_size == 0.005
    assert quote.ask_size == 0.005
    assert quote.status == "active_degraded_single_venue"


def test_quote_size_reduces_when_inventory_nears_limit():
    engine = QuoteEngine(
        half_spread=2.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.04,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            VenueQuote(
                source="binance",
                bid=99.0,
                ask=101.0,
                mid=100.0,
                spread=2.0,
                weight=1.0,
            ),
            VenueQuote(
                source="coinbase",
                bid=99.5,
                ask=100.5,
                mid=100.0,
                spread=1.0,
                weight=1.0,
            ),
        ],
        status="ok",
    )

    quote = engine.compute(fair_value)

    assert quote.bid_size == 0.002
    assert quote.ask_size == 0.002
    assert quote.status == "active_two_sided"


def test_long_inventory_limit_disables_bid_side():
    engine = QuoteEngine(
        half_spread=1.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=0.05,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            VenueQuote(
                source="binance",
                bid=99.0,
                ask=101.0,
                mid=100.0,
                spread=2.0,
                weight=1.0,
            ),
            VenueQuote(
                source="coinbase",
                bid=99.5,
                ask=100.5,
                mid=100.0,
                spread=1.0,
                weight=1.0,
            ),
        ],
        status="ok",
    )

    quote = engine.compute(fair_value)

    assert quote.bid_price is None
    assert quote.bid_size is None
    assert quote.ask_price is not None
    assert quote.ask_size is not None
    assert quote.status == "ask_only_inventory_limit"


def test_short_inventory_limit_disables_ask_side():
    engine = QuoteEngine(
        half_spread=1.0,
        base_size=0.01,
        inventory_skew=0.5,
        inventory=-0.05,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[
            VenueQuote(
                source="binance",
                bid=99.0,
                ask=101.0,
                mid=100.0,
                spread=2.0,
                weight=1.0,
            ),
            VenueQuote(
                source="coinbase",
                bid=99.5,
                ask=100.5,
                mid=100.0,
                spread=1.0,
                weight=1.0,
            ),
        ],
        status="ok",
    )

    quote = engine.compute(fair_value)

    assert quote.ask_price is None
    assert quote.ask_size is None
    assert quote.bid_price is not None
    assert quote.bid_size is not None
    assert quote.status == "bid_only_inventory_limit"
