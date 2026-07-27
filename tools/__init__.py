"""
tools — реестр и фабрики для модульных инструментов AI-агента.
"""
from tools.factories import create_success_result, create_error_result
from tools.registry import ToolRegistry

__all__ = [
    "create_success_result",
    "create_error_result",
    "ToolRegistry",
]
