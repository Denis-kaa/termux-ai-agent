"""
Динамическая загрузка инструментов из tools_registry.json.
Реализует graceful degradation при сбоях загрузки.
"""
from __future__ import annotations

import importlib
import json
import re
from typing import Any

from contracts.interfaces import BaseTool
from infra.config import Config
from infra.logger import get_logger


class ToolRegistry:
    """
    Реестр инструментов с динамической загрузкой.
    
    Graceful degradation: если инструмент не загружен (ImportError, 
    AttributeError или любая другая Exception), логируется WARNING, 
    и реестр продолжает загрузку остальных инструментов.
    """
    
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._logger = get_logger('tools.registry', 'SYSTEM')
        self._load_tools()
    
    def _load_tools(self) -> None:
        registry_path = Config.get('TOOLS_REGISTRY_PATH')
        
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"tools_registry.json not found at {registry_path}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Malformed tools_registry.json: {e}")
        
        if 'tools' not in config or not isinstance(config['tools'], list):
            raise RuntimeError("tools_registry.json must contain a 'tools' array")
        
        for tool_config in config['tools']:
            tool_name = tool_config.get('name')
            module_path = tool_config.get('module')
            class_name = tool_config.get('class')
            
            # Security validation: restrict module path to tools.*
            if not module_path or not re.match(r'^tools\.[a-z_]+$', module_path):
                self._logger.warning(
                    f"Invalid module path for tool {tool_name}: {module_path}. Skipping.",
                    extra={'tool': tool_name}
                )
                continue
            
            if not class_name or not re.match(r'^[A-Z][a-zA-Z0-9]*Tool$', class_name):
                self._logger.warning(
                    f"Invalid class name for tool {tool_name}: {class_name}. Skipping.",
                    extra={'tool': tool_name}
                )
                continue
            
            try:
                module = importlib.import_module(module_path)
                tool_class = getattr(module, class_name)
                
                # Structural subtyping check (optional but safe)
                # We trust the Protocol, but instantiate it
                instance = tool_class()
                self._tools[tool_name] = instance
                self._logger.info(f"Tool loaded successfully: {tool_name}", extra={'tool': tool_name})
                
            except Exception as e:
                # Graceful degradation: catch ANY exception (including SyntaxError) 
                # to prevent one broken tool from crashing the entire registry.
                self._logger.warning(
                    f"Failed to load tool {tool_name} from {module_path}: {e}",
                    extra={'tool': tool_name, 'module': module_path, 'error': str(e)}
                )
    
    def get_tool(self, name: str) -> BaseTool | None:
        """Возвращает экземпляр инструмента или None, если не загружен."""
        return self._tools.get(name)
    
    def get_available_tools(self) -> tuple[str, ...]:
        """Возвращает tuple имен успешно загруженных инструментов."""
        return tuple(self._tools.keys())
