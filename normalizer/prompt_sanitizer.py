"""
Санитизация промптов для защиты от инъекций.
"""
from __future__ import annotations

import re

from contracts.constants import SANITIZATION_TRIGGERS
from infra.logger import get_logger


def sanitize_prompt(text: str, correlation_id: str | None = None) -> tuple[str, bool]:
    logger = get_logger('normalizer.prompt_sanitizer', correlation_id)
    was_sanitized = False
    result_text = text
    
    for trigger in SANITIZATION_TRIGGERS:
        pattern = re.compile(re.escape(trigger), re.IGNORECASE)
        if pattern.search(result_text):
            result_text = pattern.sub('[SANITIZED]', result_text)
            was_sanitized = True
    
    if was_sanitized:
        logger.warning('Prompt sanitization applied. Potential injection attempt detected.')
    
    return result_text, was_sanitized
