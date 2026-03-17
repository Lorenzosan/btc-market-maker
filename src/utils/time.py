from datetime import datetime, timezone


# Current UTC time in ISO 8601 format
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Convert epoch milliseconds to ISO 8601 UTC timestamp
def ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
