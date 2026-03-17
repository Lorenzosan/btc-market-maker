# Design Note

## 1. Market Data Ingestion

This component connects to multiple public BTC market-data feeds and produces a unified stream of normalized events.

### Overview

The system establishes WebSocket connections to:

* Binance (spot diff-depth stream)
* Coinbase (level2_batch channel)

Each exchange provides market data in its own format and with different update characteristics. The ingestion layer converts these heterogeneous messages into a single internal representation (`MarketDataEvent`), which is then consumed by downstream components.

### Architecture

The ingestion pipeline follows a producer-consumer design:

* **Connectors (producers)**:
  Exchange-specific modules (`binance.py`, `coinbase.py`) handle:

  * WebSocket connection
  * Subscription to BTC order book updates
  * Parsing raw messages
  * Normalization into `MarketDataEvent`

* **Shared queue**:
  An `asyncio.Queue` acts as a buffer between ingestion and downstream processing. This decouples message production from consumption and allows different components to operate at different speeds.

* **Consumer (printer)**:
  A simple consumer reads normalized events from the queue and logs them. This provides a real-time view of the ingestion layer and serves as a validation tool.

### Concurrency Model

The system uses Python `asyncio` to run all components concurrently within a single thread:

* Each connector runs as an independent coroutine
* The printer runs as a separate coroutine
* `asyncio.gather` schedules all tasks concurrently
* Execution switches only at `await` points (non-blocking I/O)

This model is well-suited for network-bound workloads such as WebSocket streaming.

### Normalization

All incoming messages are converted into a common schema:

* `source`: exchange identifier (binance, coinbase)
* `symbol`: instrument symbol
* `event_type`: snapshot or update
* `exchange_ts`: timestamp from the exchange
* `received_ts`: local receipt timestamp
* `bid_updates` / `ask_updates`: changed price levels

This abstraction ensures that downstream components do not depend on exchange-specific message formats.

### Notes on Data Characteristics

* Binance provides diff-depth updates (incremental changes)
* Coinbase `level2_batch` provides batched updates at fixed intervals (~50 ms)
* Update frequency and batch sizes differ significantly between venues

Because of this, the ingestion layer should be interpreted as an **event stream**, not a representation of the current order book state. Maintaining a correct local order book is handled in the next stage.

### Output

At runtime, the system logs compact event summaries such as:

```json
{"source":"coinbase","symbol":"BTC-USD","event_type":"update","num_bid_updates":5,"num_ask_updates":7}
```

This output verifies that:

* multiple feeds are active
* messages are being parsed correctly
* normalization is consistent across venues

```
```

## 2. Order Book Construction

(to be implemented)

## 3. Fair Value Estimation

(to be implemented)

## 4. Quoting Logic

(to be implemented)

## 5. Risk Management

(to be implemented)
