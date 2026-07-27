"""
Application-логика: оркестрация scoring и LLM-fallback.
"""
from __future__ import annotations

from contracts.constants import LLM_DEFAULT_TIMEOUT_S, ROUTER_CONFIDENCE_THRESHOLD
from contracts.enums import LLMStatus, RoutingMethod
from contracts.interfaces import LLMGateway
from contracts.schemas import NormalizedRequest, RoutingDecision
from infra.logger import get_logger
from router.registry_loader import load_keywords_registry
from router.scorer import calculate_keyword_score


class Router:
    """
    Маршрутизатор запросов.
    
    Использует keyword scoring как primary метод.
    Если confidence < ROUTER_CONFIDENCE_THRESHOLD, использует LLM-fallback.
    """
    
    def __init__(self, llm_gateway: LLMGateway) -> None:
        """
        DI для llm_gateway.
        Загружает keywords registry при инициализации.
        
        Raises:
            RuntimeError: если tools_registry.json отсутствует или невалиден.
        """
        self._llm_gateway = llm_gateway
        self._logger = get_logger('router.core', 'SYSTEM')
        self._keywords_registry = load_keywords_registry()
        self._available_tools = tuple(self._keywords_registry.keys())
        self._logger.info(f"Router initialized with tools: {self._available_tools}")
    
    def route(self, request: NormalizedRequest) -> RoutingDecision:
        """
        Классифицирует запрос и возвращает решение о маршруте.
        
        Никогда не бросает exceptions для business errors.
        При LLM-fallback failure → tool_name="unknown", confidence=0.0.
        """
        # 1. Keyword Scoring
        best_tool, confidence, matched_keywords = calculate_keyword_score(
            request.normalized_text,
            self._keywords_registry
        )
        
        # 2. Decision Tree
        if confidence >= ROUTER_CONFIDENCE_THRESHOLD:
            self._logger.info(
                f"Routed via keyword: {best_tool} (conf={confidence:.2f})",
                extra={'correlation_id': request.correlation_id, 'tool': best_tool}
            )
            return RoutingDecision(
                correlation_id=request.correlation_id,
                tool_name=best_tool,
                confidence=confidence,
                method=RoutingMethod.KEYWORD.value,
                matched_keywords=matched_keywords,
                llm_calls_used=0,
            )
        
        # 3. LLM Fallback
        self._logger.warning(
            f"Keyword confidence too low ({confidence:.2f}). Triggering LLM fallback.",
            extra={'correlation_id': request.correlation_id}
        )
        
        prompt = self._build_fallback_prompt(request.normalized_text)
        
        try:
            llm_response = self._llm_gateway.generate(
                prompt=prompt,
                timeout=LLM_DEFAULT_TIMEOUT_S,
                task_type="intent_classification",
                correlation_id=request.correlation_id,  # H1 fix: observability
            )
        except Exception as e:
            # Catch unexpected errors from gateway (should not happen per contract, but defensive)
            self._logger.error(f"LLM gateway raised exception: {e}", extra={'correlation_id': request.correlation_id})
            llm_response = None
        
        if llm_response and llm_response.status == LLMStatus.OK.value:
            # Простой парсинг: ищем первое совпадение имени инструмента в ответе
            response_lower = llm_response.text.lower()
            for tool_name in self._available_tools:
                if tool_name in response_lower:
                    self._logger.info(
                        f"Routed via LLM fallback: {tool_name}",
                        extra={'correlation_id': request.correlation_id, 'tool': tool_name}
                    )
                    return RoutingDecision(
                        correlation_id=request.correlation_id,
                        tool_name=tool_name,
                        confidence=0.7,  # Уверенность выше порога, так как LLM совпал
                        method=RoutingMethod.LLM_FALLBACK.value,
                        matched_keywords=(),
                        llm_calls_used=1,
                    )
        
        # Fallback failed or returned unknown
        self._logger.warning(
            "LLM fallback failed to identify a valid tool.",
            extra={'correlation_id': request.correlation_id}
        )
        return RoutingDecision(
            correlation_id=request.correlation_id,
            tool_name="unknown",
            confidence=0.0,
            method=RoutingMethod.LLM_FALLBACK.value,
            matched_keywords=(),
            llm_calls_used=1,
        )
    
    def _build_fallback_prompt(self, text: str) -> str:
        tools_list = ", ".join(self._available_tools)
        return (
            f"Определи намерение пользователя и выбери ОДИН инструмент из списка: [{tools_list}].\n"
            f"Запрос пользователя: '{text}'\n"
            f"Ответь ТОЛЬКО названием инструмента (например: search_web). Никаких пояснений."
        )
