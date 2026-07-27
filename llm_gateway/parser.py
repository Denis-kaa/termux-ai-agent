"""
4-уровневый парсер вывода llama.cpp.
"""
from __future__ import annotations

import json
import re
from typing import Sequence

from contracts.enums import ParseMethod


def parse_llm_output(raw_output: str, expected_keys: Sequence[str] | None = None) -> tuple[str, str]:
    if not raw_output or not raw_output.strip():
        return ("", ParseMethod.FAILED.value)
    
    # Level 1: JSON
    parsed, method = _try_parse_json(raw_output)
    if method == ParseMethod.JSON.value:
        return (parsed, method)
    
    # Level 2: Marker
    parsed, method = _try_parse_marker(raw_output)
    if method == ParseMethod.MARKER.value:
        return (parsed, method)
    
    # Level 3: Heuristic
    if expected_keys:
        valid_keys = [k for k in expected_keys if k.strip()]
        if valid_keys:
            parsed, method = _try_parse_heuristic(raw_output, valid_keys)
            if method == ParseMethod.HEURISTIC.value:
                return (parsed, method)
    
    # Level 4: Failed
    return ("", ParseMethod.FAILED.value)


def _try_parse_json(raw: str) -> tuple[str, str]:
    patterns = [r'```json\s*([\s\S]*?)\s*```', r'\{[^{}]*\}']
    for pattern in patterns:
        matches = re.findall(pattern, raw, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, (dict, list)):
                    return (json.dumps(parsed, ensure_ascii=False), ParseMethod.JSON.value)
            except json.JSONDecodeError:
                continue
    return ("", "")


def _try_parse_marker(raw: str) -> tuple[str, str]:
    last_gt = raw.rfind('>')
    if last_gt == -1:
        return ("", "")
    
    prompt_marker = raw.find('[ Prompt:', last_gt)
    assistant_marker = raw.find('Assistant:', last_gt)
    
    end_idx = len(raw)
    if prompt_marker != -1:
        end_idx = min(end_idx, prompt_marker)
    if assistant_marker != -1:
        end_idx = min(end_idx, assistant_marker)
    
    extracted = raw[last_gt + 1:end_idx].strip()
    if extracted:
        return (extracted, ParseMethod.MARKER.value)
    return ("", "")


def _try_parse_heuristic(raw: str, expected_keys: Sequence[str]) -> tuple[str, str]:
    extracted_parts = []
    for key in expected_keys:
        pattern = rf'["\']?{re.escape(key)}["\']?\s*[:=]\s*["\']([^"\']*)["\']'
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            extracted_parts.append(f'"{key}": "{match.group(1)}"')
    
    if extracted_parts:
        return ("{" + ", ".join(extracted_parts) + "}", ParseMethod.HEURISTIC.value)
    return ("", "")
