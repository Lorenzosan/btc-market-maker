This is the README

1. Install websockets


main.py
  -> starts connectors
  -> connectors read websocket messages
  -> connectors normalize exchange-specific payloads
  -> normalized events go into one asyncio queue
  -> printer consumes the queue and logs summaries