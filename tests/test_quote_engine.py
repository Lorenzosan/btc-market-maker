from src.quoting.fair_value import FairValueResult
from src.quoting.quote_engine import QuoteEngine


def test_no_fair_value_disables_quotes():
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
        inputs=[],
        status="ok",
    )

    quote = engine.compute(fair_value)

    assert quote.reservation_price == 100.0
    assert quote.bid_price == 98.0
    assert quote.ask_price == 102.0
    assert quote.bid_size == 0.01
    assert quote.ask_size == 0.01
    assert quote.status == "active"


def test_long_inventory_shifts_quotes_down():
    engine = QuoteEngine(
        half_spread=2.0,
        base_size=0.01,
        inventory_skew=1.0,
        inventory=0.02,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[],
        status="ok",
    )

    quote = engine.compute(fair_value)

    assert quote.reservation_price == 99.98
    assert quote.bid_price == 97.98
    assert quote.ask_price == 101.98


def test_max_long_inventory_disables_bid():
    engine = QuoteEngine(
        half_spread=2.0,
        base_size=0.01,
        inventory_skew=1.0,
        inventory=0.05,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[],
        status="ok",
    )

    quote = engine.compute(fair_value)

    assert quote.bid_price is None
    assert quote.bid_size is None
    assert quote.ask_price is not None
    assert quote.status == "ask_only_inventory_limit"


def test_max_short_inventory_disables_ask():
    engine = QuoteEngine(
        half_spread=2.0,
        base_size=0.01,
        inventory_skew=1.0,
        inventory=-0.05,
        max_long_inventory=0.05,
        max_short_inventory=-0.05,
    )

    fair_value = FairValueResult(
        fair_value=100.0,
        inputs=[],
        status="ok",
    )

    quote = engine.compute(fair_value)

    assert quote.ask_price is None
    assert quote.ask_size is None
    assert quote.bid_price is not None
    assert quote.status == "bid_only_inventory_limit"
