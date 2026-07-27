"""
Watchdog: проверка свободной памяти перед запуском LLM.
"""
from __future__ import annotations

from contracts.constants import OOM_THRESHOLD_MB


def check_available_memory() -> tuple[bool, int]:
    """
    Проверяет доступную память в MB.
    Returns: (is_safe, available_mb). is_safe=True если достаточно памяти.
    """
    try:
        with open('/proc/meminfo', 'r', encoding='utf-8') as f:
            meminfo = f.read()
        
        for line in meminfo.split('\n'):
            if line.startswith('MemAvailable:'):
                available_kb = int(line.split()[1])
                available_mb = available_kb // 1024
                return (available_mb >= OOM_THRESHOLD_MB, available_mb)
            elif line.startswith('MemFree:'):
                free_kb = int(line.split()[1])
                free_mb = free_kb // 1024
                return (free_mb >= OOM_THRESHOLD_MB, free_mb)
        
        return (True, -1)
    except (OSError, ValueError, IndexError):
        return (True, -1)
