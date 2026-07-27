"""
Генерация кода через LLM + сохранение в файл. БЕЗ выполнения (Scope freeze).
"""
from __future__ import annotations

import os
import re
import time
from collections.abc import Mapping
from typing import Any

from contracts.constants import HOME_DIR, LANGUAGE_WHITELIST, LANGUAGE_EXTENSIONS
from contracts.enums import ErrorCode, LLMStatus
from infra.logger import get_logger
from infra.path_validator import validate_path
from llm_gateway import LLMGatewayImpl
from tools.factories import create_success_result, create_error_result


class CodeGenTool:
    """Реализует BaseTool Protocol."""
    
    def __init__(self, llm_gateway: LLMGatewayImpl):
        self._llm_gateway = llm_gateway
    
    @property
    def tool_name(self) -> str:
        return "code_gen"
    
    def execute(self, params: Mapping[str, Any], correlation_id: str) -> 'ToolResult':
        logger = get_logger('tools.code_gen', correlation_id)
        start_time = time.time()
        
        task = params.get('task', '')
        language = params.get('language', 'python')
        
        if language not in LANGUAGE_WHITELIST:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                ErrorCode.UNSUPPORTED_LANGUAGE.value,
                f"Language '{language}' not supported. Available: {', '.join(LANGUAGE_WHITELIST)}"
            )
        
        llm_response = self._llm_gateway.generate(
            prompt=f"Напиши код на {language} для задачи: {task}\n\nВерни ТОЛЬКО код в markdown-блоке ```{language}\n...\n```",
            task_type="code_generation",
            correlation_id=correlation_id,
        )
        
        if llm_response.status != LLMStatus.OK.value:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                f"LLM_{llm_response.status.upper()}", llm_response.raw[:500],
                llm_calls=1, llm_total_ms=llm_response.latency_ms
            )
        
        if not llm_response.text.strip():
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                ErrorCode.CODE_GEN_NO_OUTPUT.value, "LLM returned empty response",
                llm_calls=1, llm_total_ms=llm_response.latency_ms
            )
        
        code, method = _extract_code(llm_response.text, language)
        if not code.strip():
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                ErrorCode.CODE_GEN_NO_OUTPUT.value, f"Failed to extract code (method={method})",
                llm_calls=1, llm_total_ms=llm_response.latency_ms
            )
        
        if method != "markdown":
            logger.warning(f"Code extraction fallback: {method}")
        
        ext = LANGUAGE_EXTENSIONS.get(language, 'txt')
        filename = _generate_unique_filename(language, ext)
        
        # AUDIT FIX M1: Используем HOME_DIR из contracts, а не os.path.expanduser
        generated_dir = os.path.join(HOME_DIR, 'storage', 'downloads', 'generated')
        os.makedirs(generated_dir, exist_ok=True)
        filepath = os.path.join(generated_dir, filename)
        
        validation = validate_path(filepath, operation='write')
        if not validation.valid:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                validation.error or ErrorCode.WRITE_FAILED.value, f"Path validation failed: {filepath}",
                llm_calls=1, llm_total_ms=llm_response.latency_ms
            )
        
        try:
            with open(validation.resolved_path, 'w', encoding='utf-8') as f:
                f.write(code)
        except Exception as e:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                ErrorCode.WRITE_FAILED.value, str(e),
                llm_calls=1, llm_total_ms=llm_response.latency_ms
            )
        
        code_preview = '\n'.join(code.split('\n')[:10])
        return create_success_result(
            self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
            data={
                'file_path': validation.resolved_path, 'language': language,
                'lines': len(code.split('\n')), 'code_preview': code_preview,
                'executed': False, 'extraction_method': method,
            },
            llm_calls=1, llm_total_ms=llm_response.latency_ms
        )


def _extract_code(llm_output: str, language: str) -> tuple[str, str]:
    pattern = rf"```{language}\n(.*?)\n```"
    match = re.search(pattern, llm_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1), "markdown"
    
    pattern = r"```\w*\n(.*?)\n```"
    match = re.search(pattern, llm_output, re.DOTALL)
    if match:
        return match.group(1), "first_block"
    
    stripped = llm_output.strip()
    return (stripped, "full_output") if stripped else ("", "empty")


def _generate_unique_filename(language: str, ext: str) -> str:
    timestamp = int(time.time())
    base_name = f"{timestamp}_{language}"
    generated_dir = os.path.join(HOME_DIR, 'storage', 'downloads', 'generated')
    
    counter = 0
    while True:
        filename = f"{base_name}_{counter}.{ext}" if counter > 0 else f"{base_name}.{ext}"
        filepath = os.path.join(generated_dir, filename)
        if not os.path.exists(filepath):
            return filename
        counter += 1
        if counter > 100:
            ms = int((time.time() % 1) * 1000)
            return f"{timestamp}_{ms}_{language}.{ext}"
