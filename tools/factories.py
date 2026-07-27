"""
Helper-функции для создания ToolResult.
НЕ переопределяет BaseTool (SSoT: BaseTool живёт только в contracts.interfaces).
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from contracts.enums import ErrorCode, ResponseStatus
from contracts.schemas import ToolResult


def create_success_result(
    tool: str,
    correlation_id: str,
    duration_ms: int,
    data: Mapping[str, Any],
    llm_calls: int = 0,
    llm_total_ms: int = 0,
) -> ToolResult:
    """
    Создаёт успешный ToolResult.
    
    Raises:
        ValueError: если data is None (нарушение контракта ToolResult).
    """
    if data is None:
        raise ValueError("create_success_result requires non-None data")
    
    return ToolResult(
        status=ResponseStatus.OK.value,
        tool=tool,
        correlation_id=correlation_id,
        duration_ms=duration_ms,
        llm_calls=llm_calls,
        llm_total_ms=llm_total_ms,
        data=data,
        error=None,
        error_details=None,
    )


def create_error_result(
    tool: str,
    correlation_id: str,
    duration_ms: int,
    error_code: str,
    error_details: str | None = None,
    llm_calls: int = 0,
    llm_total_ms: int = 0,
) -> ToolResult:
    """
    Создаёт error ToolResult.
    
    Raises:
        ValueError: если error_code не является валидным значением ErrorCode.
    """
    valid_codes = {e.value for e in ErrorCode}
    if error_code not in valid_codes:
        raise ValueError(f"Invalid error_code: {error_code}. Must be one of {valid_codes}")
    
    return ToolResult(
        status=ResponseStatus.ERROR.value,
        tool=tool,
        correlation_id=correlation_id,
        duration_ms=duration_ms,
        llm_calls=llm_calls,
        llm_total_ms=llm_total_ms,
        data=None,
        error=error_code,
        error_details=error_details,
    )
