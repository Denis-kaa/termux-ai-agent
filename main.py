"""
Orchestrator: главная точка входа.
Оркестрация pipeline, управление lifecycle, агрегация результата.
v3.9.0: generic context, module-level singletons, safe serialization.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from contracts.constants import MAX_TOTAL_TIMEOUT_MS
from contracts.enums import ErrorCode, ToolName
from contracts.schemas import UnifiedRequest, UserResponse
from infra.config import Config
from infra.logger import get_logger, generate_correlation_id
from infra.wake_lock import wake_lock
from llm_gateway import get_gateway
from normalizer import normalize_request
from router import Router
from tools.registry import get_registry


def run(raw_query: str, source: str = "text") -> dict:
    """Главная точка входа. Pipeline: normalize → route → execute → aggregate."""
    correlation_id = generate_correlation_id()
    logger = get_logger('main', correlation_id)
    start_time = time.time()
    
    logger.info("Request started", extra={'raw_query': raw_query, 'source': source})
    
    try:
        with wake_lock(correlation_id) as wake_acquired:
            if not wake_acquired:
                logger.warning("Wake-lock not acquired, continuing without protection")
            
            request = UnifiedRequest(
                correlation_id=correlation_id,
                raw_text=raw_query,
                source=source,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            
            _check_timeout(start_time, correlation_id)
            normalized = normalize_request(request)
            logger.debug("Normalized", extra={'normalized_text': normalized.normalized_text[:100]})
            
            _check_timeout(start_time, correlation_id)
            llm_gateway = get_gateway()
            router = Router(llm_gateway=llm_gateway)
            decision = router.route(normalized)
            logger.debug("Routed", extra={'tool_name': decision.tool_name, 'confidence': decision.confidence})
            
            if decision.tool_name == ToolName.UNKNOWN.value:
                return _build_error_response(
                    correlation_id=correlation_id,
                    start_time=start_time,
                    error_code=ErrorCode.UNKNOWN_TOOL.value,
                    error_details="Router could not determine the tool. Please rephrase your request.",
                    llm_calls_used=decision.llm_calls_used,
                )
            
            _check_timeout(start_time, correlation_id)
            registry = get_registry()
            tool = registry.get_tool(decision.tool_name)
            
            if tool is None:
                return _build_error_response(
                    correlation_id=correlation_id,
                    start_time=start_time,
                    error_code=ErrorCode.TOOL_NOT_FOUND.value,
                    error_details=f"Tool '{decision.tool_name}' is not available",
                    llm_calls_used=decision.llm_calls_used,
                )
            
            _check_timeout(start_time, correlation_id)
            context = {
                "normalized_text": normalized.normalized_text,
                "sanitized_prompt": normalized.sanitized_prompt,
                "reference_date": normalized.reference_date,
                "raw_text": request.raw_text,
            }
            
            tool_result = tool.execute(context=context, correlation_id=correlation_id)
            
            total_ms = int((time.time() - start_time) * 1000)
            logger.info("Request completed", extra={
                'tool': tool_result.tool,
                'status': tool_result.status,
                'duration_ms': total_ms,
            })
            
            response = UserResponse(
                status=tool_result.status,
                correlation_id=correlation_id,
                tool=tool_result.tool,
                result=tool_result.data,
                error=tool_result.error,
                error_details=tool_result.error_details,
                metrics={
                    'total_ms': total_ms,
                    'llm_calls': tool_result.llm_calls + decision.llm_calls_used,
                    'llm_total_ms': tool_result.llm_total_ms,
                },
            )
            
            return _serialize_response(response, logger)
    
    except TimeoutError as e:
        return _build_error_response(
            correlation_id=correlation_id,
            start_time=start_time,
            error_code=ErrorCode.TIMEOUT_EXCEEDED.value,
            error_details=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error in orchestrator: {e}", exc_info=True)
        return _build_error_response(
            correlation_id=correlation_id,
            start_time=start_time,
            error_code=ErrorCode.ORCHESTRATOR_FAILED.value,
            error_details=str(e)[:500],
        )


def _check_timeout(start_time: float, correlation_id: str) -> None:
    """Проверяет, не превышен ли глобальный таймаут."""
    elapsed_ms = int((time.time() - start_time) * 1000)
    if elapsed_ms > MAX_TOTAL_TIMEOUT_MS:
        raise TimeoutError(f"Total timeout exceeded: {elapsed_ms}ms > {MAX_TOTAL_TIMEOUT_MS}ms")


def _build_error_response(
    correlation_id: str,
    start_time: float,
    error_code: str,
    error_details: str,
    llm_calls_used: int = 0,
) -> dict:
    """Строит error UserResponse."""
    total_ms = int((time.time() - start_time) * 1000)
    response = UserResponse(
        status="error",
        correlation_id=correlation_id,
        tool="orchestrator",
        result=None,
        error=error_code,
        error_details=error_details,
        metrics={
            'total_ms': total_ms,
            'llm_calls': llm_calls_used,
            'llm_total_ms': 0,
        },
    )
    logger = get_logger('main', correlation_id)
    return _serialize_response(response, logger)


def _safe_dict(obj: Any) -> Any:
    """
    Рекурсивно преобразует объект в JSON-сериализуемый примитив.
    v3.9.0 fix: приоритет кастомному __str__ над __dict__.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_safe_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _safe_dict(v) for k, v in obj.items()}
    # Приоритет: кастомный __str__ (определён в классе)
    if type(obj).__str__ is not object.__str__:
        return str(obj)
    # Fallback: рекурсивный обход __dict__
    if hasattr(obj, '__dict__'):
        return _safe_dict(obj.__dict__)
    return repr(obj)


def _serialize_response(response: UserResponse, logger: Any) -> dict:
    """
    Безопасная сериализация с custom encoder.
    v3.9.0 fix M3: логирует ERROR при срабатывании fallback.
    """
    try:
        result = asdict(response)
        json.dumps(result, ensure_ascii=False)
        return result
    except (TypeError, ValueError) as e:
        logger.error(
            "Contract violation: Tool returned non-primitive data in ToolResult.data, "
            "using fallback serialization",
            extra={
                'tool': response.tool,
                'error': str(e),
                'data_type': type(response.result).__name__ if response.result else None,
            }
        )
        return {
            'status': response.status,
            'correlation_id': response.correlation_id,
            'tool': response.tool,
            'result': _safe_dict(response.result) if response.result else None,
            'error': response.error,
            'error_details': response.error_details,
            'metrics': dict(response.metrics) if response.metrics else None,
        }
