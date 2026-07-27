from __future__ import annotations
from collections.abc import Mapping
from typing import Any, Protocol
from contracts.schemas import LLMResponse, ToolResult

class BaseTool(Protocol):
    @property
    def tool_name(self) -> str: ...
    def execute(self, params: Mapping[str, Any], correlation_id: str) -> ToolResult: ...

class LLMGateway(Protocol):
    def generate(self, prompt: str, timeout: int = 25, task_type: str = "general") -> LLMResponse: ...
