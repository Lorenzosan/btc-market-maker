import logging
import sys


def setup_logging(level: str = "INFO", logfile: str | None = None) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handlers = [logging.StreamHandler(sys.stdout)]

    if logfile is not None:
        handlers.append(logging.FileHandler(logfile))

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )
