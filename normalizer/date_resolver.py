"""
Детерминированный резолвер относительных дат в ISO 8601.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from infra.logger import get_logger

# Паттерны от наиболее специфичных к общим
DATE_PATTERNS = [
    (r'через\s+(\d+)\s+(часов?|часа?)', lambda m, ref: ref + timedelta(hours=int(m.group(1)))),
    (r'через\s+(\d+)\s+(минут?|мин?)', lambda m, ref: ref + timedelta(minutes=int(m.group(1)))),
    (r'\bзавтра\b', lambda m, ref: ref.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)),
    (r'\bсегодня\b', lambda m, ref: ref.replace(hour=9, minute=0, second=0, microsecond=0)),
]


def resolve_dates(text: str, reference_date: str, correlation_id: str | None = None) -> str:
    logger = get_logger('normalizer.date_resolver', correlation_id)
    
    try:
        ref_dt = datetime.fromisoformat(reference_date.replace('Z', '+00:00'))
    except ValueError:
        logger.warning(f'Invalid reference_date: {reference_date}. Using current time.')
        ref_dt = datetime.now(timezone.utc)
    
    result_text = text
    for pattern, calculator in DATE_PATTERNS:
        matches = list(re.finditer(pattern, result_text, re.IGNORECASE))
        # Заменяем с конца, чтобы не сбить индексы
        for match in reversed(matches):
            try:
                target_dt = calculator(match, ref_dt)
                result_text = result_text[:match.start()] + target_dt.isoformat() + result_text[match.end():]
            except Exception as e:
                logger.warning(f'Failed to resolve date pattern "{match.group(0)}": {e}')
    
    return result_text
