import os
import logging
from typing import Tuple

import httpx

logger = logging.getLogger(__name__)


def get_positive_float_env(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None:
        return float(default)
    try:
        f = float(val)
        if f > 0:
            return f
        else:
            logger.warning("%s must be > 0, using default %s", name, default)
            return float(default)
    except Exception:
        logger.warning("%s is not a float (%r), using default %s", name, val, default)
        return float(default)


# Defaults per specification
SOPE_CONNECT_TIMEOUT = get_positive_float_env("SOPE_CONNECT_TIMEOUT", 5.0)
SOPE_API_TIMEOUT = get_positive_float_env("SOPE_API_TIMEOUT", 20.0)


def requests_timeout_tuple() -> Tuple[float, float]:
    return (SOPE_CONNECT_TIMEOUT, SOPE_API_TIMEOUT)


def httpx_timeout() -> httpx.Timeout:
    # return httpx.Timeout object with connect/read set explicitly
    return httpx.Timeout(connect=SOPE_CONNECT_TIMEOUT, read=SOPE_API_TIMEOUT)
