"""
Главный оркестратор нормализации запроса.
"""
from __future__ import annotations

from contracts.schemas import NormalizedRequest, UnifiedRequest
from infra.logger import get_logger
from normalizer.asr_corrector import correct_asr_errors
from normalizer.date_resolver import resolve_dates
from normalizer.prompt_sanitizer import sanitize_prompt


def normalize_request(request: UnifiedRequest) -> NormalizedRequest:
    """
    Превращает "грязный" ввод в детерминированный, безопасный формат.
    ВАЖНО: Не модифицирует исходный UnifiedRequest (immutability).
    """
    logger = get_logger('normalizer.core', request.correlation_id)
    current_text = request.raw_text
    asr_corrections = {}
    is_sanitized = True
    
    try:
        current_text, asr_corrections = correct_asr_errors(current_text, request.correlation_id)
        current_text = resolve_dates(current_text, request.timestamp, request.correlation_id)
        current_text, was_sanitized = sanitize_prompt(current_text, request.correlation_id)
        is_sanitized = True  # Санитизация прошла успешно (текст очищен или был чист)
    except Exception as e:
        logger.error(f'Normalization pipeline failed: {e}. Returning partial result.')
        is_sanitized = False
    
    return NormalizedRequest(
        correlation_id=request.correlation_id,
        normalized_text=current_text,
        reference_date=request.timestamp,
        sanitized_prompt=current_text,
        asr_corrections=asr_corrections,
        is_sanitized=is_sanitized,
    )
