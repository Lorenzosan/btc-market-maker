# BTC Market Maker

## Overview

This project is an advisory quote engine built on public BTC-USD market data, ingesting live data from multiple exchanges (Binance and Coinbase).

It is not intended to predict price or optimize execution. The goal is to maintain usable local books, compute a defensible consolidated fair value, and generate conservative quote recommendations that degrade safely when data becomes stale, inconsistent, or incomplete.

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

- Python 3.11+ (tested on 3.13)
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
python main.py [options]
```

Available options are:

- `--inventory`: Initial inventory used for reservation-price skew and inventory-aware sizing
- `--base_size`: Base quote size before applying liquidity and risk scaling.
- `--log_level {INFO,DEBUG}`: Controls logging verbosity for internal diagnostics.
- `--verbosity {0,1,2}`: Controls output detail level:
  - 0: periodic compact summary
  - 1: per-event concise output
  - 2: per-event detailed output

Example:

```bash
python main.py --inventory 0.5 --log_level INFO --verbosity 1
```

---

## Tests

After the installation of the package and development dependencies, run:

```bash
pytest
```
---

## Output

The system emits updates with a target period of 250ms. An example of output (verbosity level 0) is the following:

```
2026-03-22T16:25:00.898584+00:00 | bn=68739.80(0.2010)/68739.81(2.4191) | cb=68736.15(0.0604)/68736.16(0.3767) | fv=68739.22 | disc=0.531bps | bid=68737.72 x 0.0093 | ask=68740.72 x 0.0093 | sts=active_two_sided
```

Fields:
- `bn`, `cb`: top-of-book per venue, formatted as `bid(size)/ask(size)`
- `fv`: consolidated fair value
- `disc`: cross-venue mid-price disagreement in basis points (displayed as `NA` if fewer than two filtered venues; internally defined as 0 in that case)
- `bid`, `ask`: recommended quote price and size
- `sts`: quoting status (e.g. inactive, one-sided, two-sided)

### Verbosity levels

The system supports three output modes:

- **verbosity = 0 (summary mode)**  
  Periodic compact output printed to stdout at a fixed interval.  
  Includes:
  - per-venue top-of-book
  - fair value
  - disagreement
  - final quotes and status  

- **verbosity = 1 (event mode)**  
  Emits a JSON payload for each market event.  
  Includes:
  - top-of-book state
  - `cross_venue_best_spread` is the synthetic spread defined as min(best ask) − max(best bid) across filtered venues.
  - fair value (including cross_venue_best_spread, disagreement, and market health)
  - final quotes

- **verbosity = 2 (debug mode)**  
  Extends verbosity 1 with detailed diagnostics.  
  Includes:
  - per-venue inputs to fair value (weights, spreads, sizes)
  - excluded venues and reasons
  - internal quote construction factors

---

## Architecture

The system is composed of the following components:

- **Data Ingestion Layer**
  Connects to exchange WebSocket feeds (Binance, Coinbase) and processes incremental order book updates.

- **Order Book Engine**
  Maintains local order books per venue using sequence-aware updates and resynchronization logic.

- **Fair Value Engine**
  Computes a consolidated BTC price from filtered venues, excluding stale or unreliable data.

- **Quoting Engine**
  Generates bid/ask quotes based on fair value, inventory, and market conditions.

- **Output Layer**
  Streams formatted quote updates to the terminal at sub-second frequency.

---

## Fair Value Methodology

The fair value is computed as a weighted average of filtered venue mid-prices.

### Per-exchange mid price

For each venue:

\[
\text{mid} = \frac{\text{best bid} + \text{best ask}}{2}
\]

### Venue filtering

A venue is excluded from fair-value computation if:
- its data is stale
- its order book is invalid or resynchronizing
- its spread exceeds a configured threshold
- its midpoint is an outlier relative to the cross-venue median
- it has only recently recovered from a resync

### Weighting

For each remaining venue, the weight is computed as:

\[
\text{weight} = \frac{\sqrt{\min(\text{bid size}, \text{ask size})}}{\text{spread}_{bps}}
\]

Top-of-book size is used as a local measure of support at the current best price, while spread is used as a measure of midpoint quality. The square-root term dampens the influence of unusually large displayed size.

Lower-confidence venues are further penalized multiplicatively.

### Rationale

This weighting favors venues with tighter and better-supported top-of-book quotes, while reducing sensitivity to fragile quotes, wide markets, and recently unstable venue states.

The synthetic cross-venue best spread is computed for diagnostics but is not used directly in fair value or quote construction.

---

## Quote Logic

Quote size is intentionally low-variance and controlled by conservative heuristics. Size is capped using trusted visible top-of-book liquidity and adjusted through bounded factors based on market health, spread, and cross-venue disagreement. This design ensures stable sizing and avoids overreacting to noisy or transient book updates.

Quotes are generated around a reservation price derived from the fair value and adjusted for inventory.

### Reservation price

\[
\text{reservation price} = \text{fair value} - (\text{inventory utilization} \times \text{inventory skew})
\]

This shifts quotes away from inventory that the strategy already holds, encouraging rebalancing.

### Spread construction

Quote width is based on:
- a minimum half-spread floor
- the per-venue observed spread from trusted venues
- an additional widening term proportional to cross-venue disagreement

Single-venue and degraded states widen quotes further.

### Market protection

Quotes are clamped to remain passive relative to the visible market and are suppressed entirely when:
- no fair value is available
- disagreement exceeds a configured suppression threshold
- the market is unhealthy
- only a single low-confidence venue is available

### Size construction

Quote size is determined from:
- a base size budget
- a liquidity cap based on trusted top-of-book size
- market-health scaling
- spread-quality scaling
- disagreement scaling

Inventory pressure is applied asymmetrically by reducing the side that would worsen the current position.

### Inventory limits

If inventory reaches a configured long or short limit, the strategy switches to one-sided quoting to encourage rebalancing.

---

## Failure Handling

The system explicitly handles the following failure modes:

- WebSocket disconnections  
- Stale market data  
- Order book desynchronization  
- Significant cross-venue disagreement  

### Mitigations

- automatic reconnect logic for dropped connections  
- timestamp-based staleness checks  
- order book resynchronization after invalid or missing updates  
- venue exclusion when data is stale or unreliable  
- quote widening or suppression under excessive disagreement  

---

## Assumptions

- Inventory is externally provided at startup and remains fixed during a run.
- Quotes are advisory outputs only; no orders are sent.
- Only public spot market data is used.
- The objective is safe and explainable quote generation, not execution optimization or alpha generation.
- Visible top-of-book size is used only as a heuristic input to weighting and sizing, not as a full liquidity model.

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

Model and pricing improvements may include:

- dynamic venue trust scoring  
- lightweight fair value smoothing  
- incorporation of external reference prices  
- quote quality evaluation (e.g. markouts)

---
