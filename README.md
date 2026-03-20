# BTC Market Maker

## Overview
This project implements a lightweight market-making service that ingests live BTC market data from multiple public venues, maintains local order books, computes a real-time fair value, and outputs quote recommendations.

The system prioritizes correctness, robustness, and transparency over model complexity.

---

## Features

- Live market data ingestion from multiple exchanges
- Local order book reconstruction
- Real-time fair value computation
- Quote generation (bid/ask + size)
- Configurable inventory input
- CLI-based output updated at sub-second frequency

---

## Requirements

- Python 3.10+ (or specify your version)
- Internet connection

---

## Installation

```bash
git clone <your-repo-url>
cd btc-market-maker
pip install -r requirements.txt
```

---

## Running the System

```bash
python main.py
```

Optional parameters:

```bash
python main.py --inventory 0.5
```

---

## Output Format

The system emits updates every ~500ms:

- timestamp
- per-exchange best bid / ask
- consolidated fair value
- recommended bid / ask
- quote sizes
- quote status

Example:

```
timestamp: 2026-03-20T12:00:00Z
binance_bid: 65000.1
binance_ask: 65000.5
coinbase_bid: 64999.8
coinbase_ask: 65000.6
fair_value: 65000.2
bid: 64999.9 size: 0.01
ask: 65000.5 size: 0.01
status: active
```

---

## Architecture

The system is composed of the following components:

- **Data Ingestion Layer**
  Connects to exchange WebSocket feeds and processes order book updates.

- **Order Book Engine**
  Maintains local order books per exchange using incremental updates.

- **Fair Value Engine**
  Computes a consolidated BTC price using cross-exchange data.

- **Quoting Engine**
  Generates bid/ask quotes based on fair value and inventory.

- **Output Layer**
  Streams formatted results to CLI.

---

## Fair Value Methodology

The fair value is computed as a weighted mid-price across exchanges:

- Mid price per exchange:
  (best bid + best ask) / 2

- Aggregation:
  Simple average or weighted average (based on liquidity or spread)

Rationale:
- Transparent
- Stable
- Avoids overfitting or noisy signals

---

## Quote Logic

Quotes are generated around fair value:

- Bid = fair value - spread / 2
- Ask = fair value + spread / 2

Spread may depend on:
- market spread
- inventory skew

Inventory adjustment:
- Long inventory → shift quotes downward
- Short inventory → shift quotes upward

---

## Failure Modes

- WebSocket disconnections
- Stale market data
- Order book desynchronization
- One exchange diverging significantly

Mitigations:
- Reconnect logic
- Timestamp checks
- Periodic book reset (if implemented)

---

## Assumptions

- Market data feeds are reliable
- Latency is not explicitly optimized
- Inventory is static or simulated

---

## Edge Cases Not Handled

- Extreme market volatility spikes
- Exchange outages beyond simple reconnect
- Cross-exchange arbitrage exploitation

---

## Production Improvements

- Persistent order book storage
- Advanced health monitoring
- Dynamic source weighting
- Latency tracking
- Risk limits and position management

---

## Tests

Run tests with:

```bash
pytest
```

---

## Sample Output
```
2026-03-20T16:02:56.006781+00:00 | bin=69938.50(2.264810)/69938.51(0.610710) | cb=69926.84(0.083681)/69926.85(0.000016) | fv=69938.45 | disc=1.667bps | bid=69936.95 x 0.007900 | ask=69939.95 x 0.007900 | status=active_two_sided
```
---

## Notes

This implementation focuses on clarity and robustness rather than trading performance.