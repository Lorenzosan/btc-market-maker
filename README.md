# BTC Market Maker

This service ingests live BTC spot market data from Binance and Coinbase, maintains a local order book per venue, computes a consolidated fair value, and emits quote recommendations for a simple market making strategy.

The implementation prioritizes correctness, clarity, and robustness over complexity.

---

## Requirements

- Python 3.11+
- Internet access

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
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

Every 250 ms the service prints a consolidated snapshot including:

- timestamp
- Binance best bid and ask
- Coinbase best bid and ask
- consolidated fair value
- recommended bid and ask with sizes
- quote status

Example:

```text
2026-03-18T14:00:00.000000+00:00 | BIN 84250.10/84250.20 | CB 84249.80/84250.30 | FV 84250.08 | BID 84248.08 x 0.0100 | ASK 84252.08 x 0.0100 | QSTATUS active
```

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

Run tests with:

```bash
pytest
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

- Binance sequence gaps trigger a resync through snapshot reload
- Updates received before snapshot are ignored
- Crossed or invalid books are excluded from fair value
- If no valid venues are available, quoting is disabled

---

## Repository Structure

```text
src/
  data_ingestion/     exchange connectors
  order_book/         local order book and manager
  fair_value/         fair value computation
  quoting/            quote logic
  output/             printer loop
  utils/              logging
  config.py

docs/
  DESIGN.md
  sample_output.txt

tests/
  pytest test suite
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
