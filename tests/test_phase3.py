"""
Unit и Integration тесты для Phase 3 (router + tools infrastructure).
"""
import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts.schemas import NormalizedRequest, ToolResult
from contracts.enums import ErrorCode, ResponseStatus, LLMStatus, RoutingMethod
from tools.factories import create_success_result, create_error_result
from tools.registry import ToolRegistry
from router.scorer import calculate_keyword_score
from router.router import Router


class TestFactories:
    def test_create_success_result_valid(self):
        res = create_success_result(
            tool="search_web",
            correlation_id="test-123",
            duration_ms=10,
            data={"query": "test"}
        )
        assert res.status == ResponseStatus.OK.value
        assert res.data == {"query": "test"}

    def test_create_success_result_invalid_data(self):
        with pytest.raises(ValueError, match="requires non-None data"):
            create_success_result("search_web", "test-123", 10, data=None)

    def test_create_error_result_valid(self):
        res = create_error_result(
            tool="search_web",
            correlation_id="test-123",
            duration_ms=10,
            error_code=ErrorCode.UNKNOWN_TOOL.value
        )
        assert res.status == ResponseStatus.ERROR.value
        assert res.error == ErrorCode.UNKNOWN_TOOL.value

    def test_create_error_result_invalid_code(self):
        with pytest.raises(ValueError, match="Invalid error_code"):
            create_error_result("search_web", "test-123", 10, error_code="INVALID_CODE")


class TestScorer:
    def test_exact_match(self):
        registry = {"search_web": ("поиск", "найди"), "reminder": ("напомни",)}
        tool, score, matched = calculate_keyword_score("найди информацию", registry)
        assert tool == "search_web"
        assert score == 0.5  # 1 из 2 keywords
        assert "найди" in matched

    def test_empty_keywords(self):
        registry = {"search_web": (), "reminder": ("напомни",)}
        tool, score, matched = calculate_keyword_score("найди", registry)
        assert tool == "unknown"
        assert score == 0.0

    def test_tie_breaker_lexicographical(self):
        # Оба инструмента имеют score 1.0. "code_gen" < "search_web" лексикографически.
        registry = {
            "search_web": ("тест",),
            "code_gen": ("тест",)
        }
        tool, score, matched = calculate_keyword_score("тест", registry)
        assert tool == "code_gen"
        assert score == 1.0


class TestRouter:
    @pytest.fixture
    def mock_llm_gateway(self):
        gateway = MagicMock()
        gateway.generate.return_value = MagicMock(
            status=LLMStatus.OK.value,
            text="reminder",
            raw="reminder",
            parse_method="heuristic",
            latency_ms=100,
            tokens_used=None
        )
        return gateway

    @patch('router.registry_loader.load_keywords_registry')
    def test_keyword_routing_high_confidence(self, mock_load, mock_llm_gateway):
        mock_load.return_value = {"search_web": ("поиск", "найди"), "reminder": ("напомни",)}
        
        router = Router(llm_gateway=mock_llm_gateway)
        req = NormalizedRequest(
            correlation_id="test-001",
            normalized_text="найди рецепт",
            reference_date="2026-07-27T10:00:00Z",
            sanitized_prompt="найди рецепт",
            asr_corrections={},
            is_sanitized=True
        )
        
        decision = router.route(req)
        assert decision.tool_name == "search_web"
        assert decision.method == RoutingMethod.KEYWORD.value
        assert decision.llm_calls_used == 0
        mock_llm_gateway.generate.assert_not_called()

    @patch('router.registry_loader.load_keywords_registry')
    def test_llm_fallback_routing(self, mock_load, mock_llm_gateway):
        mock_load.return_value = {"search_web": ("поиск",), "reminder": ("напомни",)}
        
        router = Router(llm_gateway=mock_llm_gateway)
        req = NormalizedRequest(
            correlation_id="test-002",
            normalized_text="помоги мне с задачей",
            reference_date="2026-07-27T10:00:00Z",
            sanitized_prompt="помоги мне с задачей",
            asr_corrections={},
            is_sanitized=True
        )
        
        decision = router.route(req)
        assert decision.method == RoutingMethod.LLM_FALLBACK.value
        assert decision.llm_calls_used == 1
        mock_llm_gateway.generate.assert_called_once()
        # Проверка передачи correlation_id
        call_kwargs = mock_llm_gateway.generate.call_args.kwargs
        assert call_kwargs['correlation_id'] == "test-002"

    @patch('router.registry_loader.load_keywords_registry')
    def test_llm_fallback_failure(self, mock_load, mock_llm_gateway):
        mock_load.return_value = {"search_web": ("поиск",)}
        mock_llm_gateway.generate.return_value = MagicMock(
            status=LLMStatus.TIMEOUT.value,
            text="",
            raw="",
            parse_method="failed",
            latency_ms=25000,
            tokens_used=None
        )
        
        router = Router(llm_gateway=mock_llm_gateway)
        req = NormalizedRequest(
            correlation_id="test-003",
            normalized_text="помоги мне",
            reference_date="2026-07-27T10:00:00Z",
            sanitized_prompt="помоги мне",
            asr_corrections={},
            is_sanitized=True
        )
        
        decision = router.route(req)
        assert decision.tool_name == "unknown"
        assert decision.confidence == 0.0
        assert decision.llm_calls_used == 1


class TestToolRegistry:
    @patch('infra.config.Config.get')
    @patch('builtins.open')
    @patch('importlib.import_module')
    def test_graceful_degradation_on_import_error(self, mock_import, mock_open, mock_config):
        mock_config.return_value = "/fake/path/tools_registry.json"
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
            "tools": [
                {"name": "valid_tool", "module": "tools.valid", "class": "ValidTool", "keywords": [], "description": ""},
                {"name": "broken_tool", "module": "tools.broken", "class": "BrokenTool", "keywords": [], "description": ""}
            ]
        })
        
        # Первый импорт успешен, второй бросает Exception
        mock_import.side_effect = [
            MagicMock(ValidTool=MagicMock(return_value=MagicMock())),
            Exception("Syntax error in module")
        ]
        
        registry = ToolRegistry()
        
        assert registry.get_tool("valid_tool") is not None
        assert registry.get_tool("broken_tool") is None
        assert "valid_tool" in registry.get_available_tools()
        assert "broken_tool" not in registry.get_available_tools()
