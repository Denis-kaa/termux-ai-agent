from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class UnifiedRequest:
    correlation_id: str
    raw_text: str
    source: str
    timestamp: str

@dataclass(frozen=True)
class NormalizedRequest:
    correlation_id: str
    normalized_text: str
    reference_date: str
    sanitized_prompt: str
    asr_corrections: Mapping[str, str] = field(default_factory=dict)
    is_sanitized: bool = True

@dataclass(frozen=True)
class RoutingDecision:
    correlation_id: str
    tool_name: str
    confidence: float
    method: str
    matched_keywords: tuple[str, ...] = ()
    llm_calls_used: int = 0

@dataclass(frozen=True)
class ToolResult:
    status: str
    tool: str
    correlation_id: str
    duration_ms: int
    llm_calls: int
    llm_total_ms: int
    data: Mapping[str, Any] | None = None
    error: str | None = None
    error_details: str | None = None

    def __post_init__(self) -> None:
        if self.status == "ok" and self.data is None:
            raise ValueError("status='ok' requires non-None data")
        if self.status == "error" and self.error is None:
            raise ValueError("status='error' requires non-None error")

@dataclass(frozen=True)
class LLMResponse:
    status: str
    text: str
    raw: str
    parse_method: str
    latency_ms: int
    tokens_used: int | None = None
