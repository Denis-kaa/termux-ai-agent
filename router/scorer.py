"""
Domain-логика: вычисление score на основе keyword matching.
Чистая функция, не имеет побочных эффектов.
"""
from __future__ import annotations

import re
from collections.abc import Mapping


def calculate_keyword_score(
    text: str,
    keywords_registry: Mapping[str, tuple[str, ...]]
) -> tuple[str, float, tuple[str, ...]]:
    """
    Вычисляет score для каждого инструмента на основе keywords.
    
    Edge case: если len(keywords) == 0 для инструмента → score = 0.0.
    Tie-breaker: при равенстве score выбирается инструмент с наименьшим 
    лексикографическим именем.
    
    Returns:
        (best_tool_name, confidence, matched_keywords)
    """
    text_lower = text.lower()
    best_tool = "unknown"
    best_score = 0.0
    best_matched: tuple[str, ...] = ()
    
    # Сортируем по имени для детерминированного tie-breaker
    sorted_tools = sorted(keywords_registry.keys())
    
    for tool_name in sorted_tools:
        keywords = keywords_registry[tool_name]
        
        if not keywords:
            continue
        
        matched = []
        for kw in keywords:
            # \b обеспечивает границу слова, предотвращая частичные совпадения
            if re.search(rf'\b{re.escape(kw)}\b', text_lower):
                matched.append(kw)
        
        if matched:
            score = len(matched) / len(keywords)
            
            # Строгое '>' обеспечивает tie-breaker в пользу первого по алфавиту
            if score > best_score:
                best_score = score
                best_tool = tool_name
                best_matched = tuple(matched)
    
    return best_tool, best_score, best_matched
