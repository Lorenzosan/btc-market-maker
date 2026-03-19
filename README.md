# BTC Market Maker

This service ingests live BTC spot market data from Binance and Coinbase, maintains a local order book per venue, computes a consolidated fair value, and emits quote recommendations for a simple market making strategy.

---

## Requirements

- Python 3.11+
- Internet access

---

## Setup

```bash
python -m venv btc-venv
source btc-venv/bin/activate
pip install -r requirements.txt
```

---

## Run

```bash
python -m src.main
```

The service connects to:

- Binance BTCUSDT depth stream
- Coinbase BTC-USD level2 feed

---

## Output

At a fixed interval, configured via `OUTPUT_INTERVAL_SECONDS`, the service prints a consolidated snapshot including:

- local reporting timestamp in UTC
- Binance top of book (best bid and ask with top-level sizes)
- Coinbase top of book (best bid and ask with top-level sizes)
- consolidated fair value
- recommended bid and ask with sizes
- quote status

Example:

```text
ts=2026-03-19T12:34:56.123456Z | bin=71330.70(0.4200)/71330.71(0.2500) | cb=71326.84(0.3800)/71326.85(0.1900) | fv=71328.78 | bid=71326.78 x 0.0100 | ask=71330.78 x 0.0100 | status=active

---

## Architecture Overview

The system is composed of four main components.

### Market Data Ingestion

- Binance uses a REST snapshot plus websocket diff stream
- Binance updates are sequence-checked before being applied
- Coinbase uses a snapshot plus incremental level2 updates

### Order Book Layer

- Maintains one local order book per venue
- Applies snapshots and incremental updates
- Tracks best bid and best ask
- Rejects crossed books as invalid

### Fair Value Engine

- Computes a consolidated fair value from venue mids
- Uses inverse-spread weighting
- Excludes invalid or degraded books

### Quote Engine

- Computes a reservation price from fair value and inventory
- Applies a fixed spread around the reservation price
- Disables one side at inventory limits

---

## Configuration

Key parameters are defined in `src/config.py`:

- `OUTPUT_INTERVAL_SECONDS`
- `HALF_SPREAD`
- `BASE_SIZE`
- `INVENTORY_SKEW`
- `MAX_INVENTORY`
- `MAX_FAIR_VALUE_SPREAD`



---

## Tests
The test suite requires pytest and pytest-asyncio (included in requirements.txt).

Run tests with:

```bash
python -m pytest
```

The test suite covers:

- order book snapshot and update logic
- order book manager behavior
- fair value computation
- quote engine behavior

---

## Known Limitations

- Coinbase updates do not have the same strict sequence validation as Binance
- No explicit stale-data timeout per venue
- Fair value uses a simple inverse-spread weighting with a fixed spread filter
- No outlier rejection when venues diverge significantly
- Inventory is static and is not updated from simulated fills
- No persistence or recovery on restart

---

## Failure Handling

- - Binance sequence gaps trigger a resync via snapshot reload without reconnecting the websocket
- Updates received before snapshot are ignored
- Crossed or invalid books are excluded from fair value
- If no valid venues are available, quoting is disabled

---

## Repository Structure

```text
src/
  ingestion/          exchange connectors (Binance, Coinbase)
  orderbook/          local order book and manager
  fair_value/         fair value computation
  quoting/            quote logic
  output/             printer loop
  utils/              time and logging helpers
  config.py
  types.py
  main.py

tests/
  test_binance_connector.py
  test_fair_value.py
  test_manager.py
  test_orderbook.py
  test_quote_engine.py

docs/
  DESIGN.md
  sample_output.txt
```

---

## Design Notes

A detailed design explanation is available in:

`docs/DESIGN.md`

It covers:

- order book construction
- fair value methodology
- quote logic
- failure modes
- assumptions
- unhandled edge cases
- production improvements

---

## Sample Output

A longer sample live run is provided in:

`docs/sample_output.txt`

---
