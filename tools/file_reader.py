"""
Чтение файла + суммаризация через LLM.
"""
from __future__ import annotations

import os
import time
from collections.abc import Mapping
from typing import Any

from contracts.constants import MAX_FILE_SIZE_BYTES
from contracts.enums import ErrorCode, LLMStatus
from infra.logger import get_logger
from infra.path_validator import validate_path
from llm_gateway import LLMGatewayImpl
from tools.factories import create_success_result, create_error_result


class FileReaderTool:
    """Реализует BaseTool Protocol."""
    
    def __init__(self, llm_gateway: LLMGatewayImpl):
        self._llm_gateway = llm_gateway
    
    @property
    def tool_name(self) -> str:
        return "file_reader"
    
    def execute(self, params: Mapping[str, Any], correlation_id: str) -> 'ToolResult':
        logger = get_logger('tools.file_reader', correlation_id)
        start_time = time.time()
        
        path = params.get('path', '')
        validation = validate_path(path, operation='read')
        if not validation.valid:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                validation.error or ErrorCode.PATH_OUTSIDE_WHITELIST.value, f"Path validation failed: {path}"
            )
        
        try:
            file_size = os.path.getsize(validation.resolved_path)
        except OSError as e:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                ErrorCode.FILE_NOT_FOUND.value, str(e)
            )
        
        if file_size > MAX_FILE_SIZE_BYTES:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                ErrorCode.FILE_TOO_LARGE.value, f"Size: {file_size} bytes, max: {MAX_FILE_SIZE_BYTES}"
            )
        
        try:
            with open(validation.resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                ErrorCode.BINARY_FILE.value, "File is not UTF-8 encoded"
            )
        
        word_count = len(content.split())
        if word_count == 0:
            return create_success_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                data={'path': validation.resolved_path, 'summary': "", 'word_count': 0}
            )
        
        llm_response = self._llm_gateway.generate(
            prompt=f"Суммируй текст в 2-3 предложения:\n\n{content[:8000]}",
            task_type="summarization",
            correlation_id=correlation_id,
        )
        
        if llm_response.status != LLMStatus.OK.value:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                f"LLM_{llm_response.status.upper()}", llm_response.raw[:500],
                llm_calls=1, llm_total_ms=llm_response.latency_ms
            )
        
        return create_success_result(
            self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
            data={'path': validation.resolved_path, 'summary': llm_response.text, 'word_count': word_count},
            llm_calls=1, llm_total_ms=llm_response.latency_ms
        )
