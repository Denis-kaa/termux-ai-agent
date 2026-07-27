"""
Загрузка keywords registry из tools_registry.json для router.
"""
from __future__ import annotations

import json
from collections.abc import Mapping

from infra.config import Config


def load_keywords_registry() -> Mapping[str, tuple[str, ...]]:
    """
    Загружает keywords для каждого инструмента из tools_registry.json.
    
    Returns:
        Mapping: {tool_name: (keywords,)}
    
    Raises:
        RuntimeError: если tools_registry.json отсутствует или malformed
    """
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
    
    registry: dict[str, tuple[str, ...]] = {}
    for tool_config in config['tools']:
        name = tool_config.get('name')
        keywords = tool_config.get('keywords', [])
        
        if name and isinstance(keywords, list):
            # Convert to tuple for immutability
            registry[name] = tuple(str(k).lower() for k in keywords)
    
    return registry
