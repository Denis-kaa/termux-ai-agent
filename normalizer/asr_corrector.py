"""
Корректор ошибок распознавания речи (ASR).
"""
from __future__ import annotations

import re
from typing import Mapping

from contracts.constants import ASR_CORRECTIONS_DICT
from infra.logger import get_logger


def correct_asr_errors(text: str, correlation_id: str | None = None) -> tuple[str, dict[str, str]]:
    logger = get_logger('normalizer.asr_corrector', correlation_id)
    corrections = {}
    sorted_keys = sorted(ASR_CORRECTIONS_DICT.keys(), key=len, reverse=True)
    result_text = text
    
    for wrong_word in sorted_keys:
        correct_word = ASR_CORRECTIONS_DICT[wrong_word]
        pattern = re.compile(rf'\b{re.escape(wrong_word)}\b', re.IGNORECASE)
        
        if pattern.search(result_text):
            def replace_match(match: re.Match) -> str:
                original = match.group(0)
                return correct_word.capitalize() if original[0].isupper() else correct_word
            
            new_text, count = pattern.subn(replace_match, result_text)
            if count > 0:
                corrections[wrong_word] = correct_word
                result_text = new_text
    
    if corrections:
        logger.info(f'ASR corrections applied: {corrections}')
    return result_text, corrections
