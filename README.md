# BTC Market Maker

## Overview
This project implements a lightweight market-making service for BTC-USD. It ingests live order book data from multiple exchanges (Binance and Coinbase), maintains local books, computes a consolidated fair value, and outputs quote recommendations in real time.

---

## Features

- Live market data ingestion from Binance and Coinbase
- Local order book reconstruction
- Real-time fair value computation
- Quote generation (bid/ask + size)
- Configurable inventory input
- CLI-based output updated at sub-second frequency

---

## Requirements

- Python 3.13 (tested)
- Internet connection for live WebSocket feeds

---

## Installation

```bash
git clone https://github.com/Lorenzosan/btc-market-maker.git
cd btc-market-maker
pip install -e .
pip install -r requirements-dev.txt
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

## Tests

After the installation of the package and development dependencies, run:

```bash
pytest
```
---

## Output

The system emits updates with a target period of 250ms. An example of output is the following:

```
2026-03-20T16:02:56.006781+00:00 | bin=69938.50(2.264810)/69938.51(0.610710) | cb=69926.84(0.083681)/69926.85(0.000016) | fv=69938.45 | disc=1.667bps | bid=69936.95 x 0.007900 | ask=69939.95 x 0.007900 | status=active_two_sided
```

Field description:
- bin, cb: best bid/ask and sizes per venue
- fv: fair value
- disc: cross-venue disagreement (basis points)
- bid, ask: recommended quotes and sizes
- status: quoting state


---

## Architecture

The system is composed of the following components:

- **Data Ingestion Layer**
  Connects to exchange WebSocket feeds (Binance, Coinbase) and processes incremental order book updates.

- **Order Book Engine**
  Maintains local order books per venue using sequence-aware updates and resynchronization logic.

- **Fair Value Engine**
  Computes a consolidated BTC price from valid venues, excluding stale or unreliable data.

- **Quoting Engine**
  Generates bid/ask quotes based on fair value, inventory, and market conditions.

- **Output Layer**
  Streams formatted quote updates to the terminal at sub-second frequency.

---

## Fair Value Methodology

The fair value is computed as a weighted mid-price across exchanges.

### Per-exchange mid price

For each venue:

\[
\text{mid} = \frac{\text{best bid} + \text{best ask}}{2}
\]

### Aggregation

The consolidated fair value is computed as a weighted average of valid venues.

Weights are determined by:
- top-of-book liquidity (size)
- spread tightness

Venues are excluded if:
- data is stale
- the order book is resynchronizing
- updates are inconsistent

### Rationale

- Transparent and interpretable  
- Stable under normal market conditions  
- Avoids overfitting and reliance on noisy signals

---

## Quote Logic

Quotes are generated symmetrically around the fair value.

### Base quotes

\[
\text{bid} = \text{fair value} - \frac{\text{spread}}{2}
\]
\[
\text{ask} = \text{fair value} + \frac{\text{spread}}{2}
\]

### Spread adjustment

The spread is dynamically adjusted based on:
- observed market spread across venues
- cross-venue disagreement
- system or data quality state

### Inventory adjustment

Quotes are skewed based on inventory:

- Long inventory → shift both bid and ask downward  
- Short inventory → shift both bid and ask upward  

This reduces directional exposure by encouraging trades that rebalance inventory.

### Degraded conditions

Under degraded market conditions:
- spreads are widened
- quote sizes are reduced
- quoting may be suppressed entirely if data is unreliable

---

## Failure Handling

The system explicitly handles the following failure modes:

- WebSocket disconnections  
- Stale market data  
- Order book desynchronization  
- Significant cross-exchange divergence  

### Mitigations

- automatic reconnect logic for dropped connections  
- timestamp-based staleness checks  
- order book resynchronization after invalid or missing updates  
- venue exclusion when data is stale or unreliable  
- quote widening or suppression under excessive disagreement  

---

## Assumptions

- inventory is externally provided and static during a run  
- the system produces advisory quotes only and does not place orders  
- only public market data is used  
- latency is not explicitly optimized  

---

## Scope Limitations

The current implementation does not handle:

- order execution or exchange interaction  
- advanced risk management, such as position limits or PnL tracking  
- prolonged exchange outages beyond reconnect and resync behavior  
- latency-aware pricing adjustments  
- strategy logic for arbitrage or predictive alpha generation  

---

## Production Improvements

Potential production extensions include:

- structured metrics for staleness, reconnects, and resync events  
- health monitoring and alerting per venue  
- external configuration for thresholds and risk parameters  
- more robust recovery during prolonged venue degradation  
- integrated position and risk management  
- latency tracking and latency-aware fair value adjustments  

---
