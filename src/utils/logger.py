"""Logger común con formato consistente."""
from __future__ import annotations

import logging


def get_logger(name: str = "proyecto-final", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                                     datefmt="%H:%M:%S"))
    logger.addHandler(h)
    logger.propagate = False
    return logger
