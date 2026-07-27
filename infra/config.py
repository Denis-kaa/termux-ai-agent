"""
Runtime config loader.
Импортирует константы из contracts (SSoT) и добавляет platform-internal values.
"""
from __future__ import annotations

import os
import threading
from typing import Any

from contracts.constants import (
    HOME_DIR as CONTRACTS_HOME_DIR,
    MODEL_PATH, ALLOWED_DIRS, WRITE_ALLOWED_DIRS,
    MAX_FILE_SIZE_BYTES, MAX_LLM_CALLS_PER_REQUEST,
    LLM_DEFAULT_TIMEOUT_S, HTTP_TIMEOUT_S, MAX_TOTAL_TIMEOUT_MS,
    ROUTER_CONFIDENCE_THRESHOLD, OOM_THRESHOLD_MB,
    CIRCUIT_BREAKER_THRESHOLD, ROUTER_LLM_BUDGET, TOTAL_LLM_BUDGET,
    LANGUAGE_WHITELIST,
)


class Config:
    _loaded: bool = False
    _lock: threading.Lock = threading.Lock()
    _data: dict[str, Any] = {}

    @classmethod
    def get(cls, key: str) -> Any:
        if not cls._loaded:
            with cls._lock:
                if not cls._loaded:
                    cls._load()
        if key not in cls._data:
            raise KeyError(f"Config key not found: {key}")
        return cls._data[key]

    @classmethod
    def reset(cls) -> None:
        if os.environ.get('PYTEST_CURRENT_TEST') is None:
            raise RuntimeError("Config.reset() can only be called in tests")
        with cls._lock:
            cls._loaded = False
            cls._data = {}

    @classmethod
    def _load(cls) -> None:
        effective_home = os.environ.get('HOME', CONTRACTS_HOME_DIR)
        
        if not os.path.isdir(effective_home):
            raise RuntimeError(
                f"HOME_DIR does not exist: {effective_home}. "
                f"Set $HOME correctly or run 'termux-setup-storage'."
            )
        
        def _resolve(p: str) -> str:
            return p.replace(CONTRACTS_HOME_DIR, effective_home)
        
        cls._data = {
            'HOME_DIR': effective_home,
            'MODEL_PATH': _resolve(MODEL_PATH),
            'DATA_DIR': os.path.join(effective_home, 'data'),
            'LOGS_DIR': os.path.join(effective_home, 'logs'),
            'ALLOWED_DIRS': [_resolve(d) for d in ALLOWED_DIRS],
            'WRITE_ALLOWED_DIRS': [_resolve(d) for d in WRITE_ALLOWED_DIRS],
            'MAX_FILE_SIZE_BYTES': MAX_FILE_SIZE_BYTES,
            'MAX_LLM_CALLS_PER_REQUEST': MAX_LLM_CALLS_PER_REQUEST,
            'LLM_DEFAULT_TIMEOUT_S': LLM_DEFAULT_TIMEOUT_S,
            'HTTP_TIMEOUT_S': HTTP_TIMEOUT_S,
            'MAX_TOTAL_TIMEOUT_MS': MAX_TOTAL_TIMEOUT_MS,
            'ROUTER_CONFIDENCE_THRESHOLD': ROUTER_CONFIDENCE_THRESHOLD,
            'OOM_THRESHOLD_MB': OOM_THRESHOLD_MB,
            'CIRCUIT_BREAKER_THRESHOLD': CIRCUIT_BREAKER_THRESHOLD,
            'ROUTER_LLM_BUDGET': ROUTER_LLM_BUDGET,
            'TOTAL_LLM_BUDGET': TOTAL_LLM_BUDGET,
            'LANGUAGE_WHITELIST': list(LANGUAGE_WHITELIST),
            'LOG_MAX_BYTES': 5 * 1024 * 1024,
            'LOG_BACKUP_COUNT': 3,
            'TOOLS_REGISTRY_PATH': os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'tools',
                'tools_registry.json'
            ),
            'WRITE_BLACKLIST': [
                '/system',
                os.path.join(effective_home, '.termux'),
                os.path.normpath(os.path.join(effective_home, '..', 'usr')),
            ],
        }
        cls._loaded = True
