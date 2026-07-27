"""
Circuit breaker для защиты от каскадных сбоев при OOM/crash.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from contracts.constants import CIRCUIT_BREAKER_RESET_INTERVAL_SEC, CIRCUIT_BREAKER_THRESHOLD


class CircuitBreaker:
    """
    Thread-safe circuit breaker с авто-сбросом.
    Состояния: CLOSED (нормальная работа), OPEN (LLM отключена).
    """
    _state: str = "CLOSED"
    _failure_count: int = 0
    _last_failure_time: float = 0.0
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def is_open(cls) -> bool:
        with cls._lock:
            if cls._state == "OPEN":
                if time.time() - cls._last_failure_time > CIRCUIT_BREAKER_RESET_INTERVAL_SEC:
                    cls._state = "CLOSED"
                    cls._failure_count = 0
                    return False
                return True
            return False

    @classmethod
    def record_failure(cls) -> None:
        with cls._lock:
            cls._failure_count += 1
            cls._last_failure_time = time.time()
            if cls._failure_count >= CIRCUIT_BREAKER_THRESHOLD:
                cls._state = "OPEN"

    @classmethod
    def record_success(cls) -> None:
        with cls._lock:
            cls._failure_count = 0
            cls._state = "CLOSED"

    @classmethod
    def inject_state(cls, state: str, failure_count: int, last_failure_time: float) -> None:
        """Инъекция состояния. ТОЛЬКО для тестирования."""
        with cls._lock:
            cls._state = state
            cls._failure_count = failure_count
            cls._last_failure_time = last_failure_time

    @classmethod
    def get_state(cls) -> dict[str, Any]:
        with cls._lock:
            return {
                "state": cls._state,
                "failure_count": cls._failure_count,
                "last_failure_time": cls._last_failure_time,
            }
