"""
Основной класс LLMGateway. Единственный модуль, работающий с subprocess llama.cpp.
"""
from __future__ import annotations

import os
import signal
import subprocess
import time
from typing import Sequence

from contracts.constants import LLM_DEFAULT_TIMEOUT_S, MODEL_PATH
from contracts.enums import LLMStatus, ParseMethod
from contracts.interfaces import LLMGateway
from contracts.schemas import LLMResponse
from infra.config import Config
from infra.logger import get_logger
from llm_gateway.circuit_breaker import CircuitBreaker
from llm_gateway.parser import parse_llm_output
from llm_gateway.watchdog import check_available_memory


class LLMGatewayImpl(LLMGateway):
    def generate(
        self,
        prompt: str,
        timeout: int = LLM_DEFAULT_TIMEOUT_S,
        task_type: str = "general",
        expected_keys: Sequence[str] | None = None,
        correlation_id: str | None = None,
    ) -> LLMResponse:
        logger = get_logger('llm_gateway.gateway', correlation_id)
        
        if CircuitBreaker.is_open():
            logger.warning('LLM disabled by circuit breaker')
            return LLMResponse(LLMStatus.DISABLED.value, "", "", ParseMethod.FAILED.value, 0, None)
        
        is_safe, available_mb = check_available_memory()
        if not is_safe:
            logger.warning(f'Insufficient memory: {available_mb}MB available')
            CircuitBreaker.record_failure()
            return LLMResponse(LLMStatus.OOM.value, "", "", ParseMethod.FAILED.value, 0, None)
        
        model_path = Config.get('MODEL_PATH')
        if not os.path.isfile(model_path):
            raise RuntimeError(f"Model file not found: {model_path}")
        
        start_time = time.time()
        try:
            cmd = ['llama-cli', '-m', model_path, '-p', prompt, '--n_predict', '256', '--temp', '0.7', '--threads', '2']
            
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                latency_ms = int((time.time() - start_time) * 1000)
                
                if process.returncode != 0:
                    logger.error(f'LLM crashed with code {process.returncode}: {stderr[:200]}')
                    CircuitBreaker.record_failure()
                    return LLMResponse(LLMStatus.CRASH.value, "", stderr, ParseMethod.FAILED.value, latency_ms, None)
                
                parsed_text, parse_method = parse_llm_output(stdout, expected_keys)
                
                if parse_method == ParseMethod.FAILED.value:
                    logger.warning(f'Failed to parse LLM output. Raw: {stdout[:200]}')
                    return LLMResponse(LLMStatus.PARSE_ERROR.value, "", stdout, parse_method, latency_ms, None)
                
                CircuitBreaker.record_success()
                logger.info(f'LLM call successful ({parse_method}, {latency_ms}ms)')
                return LLMResponse(LLMStatus.OK.value, parsed_text, stdout, parse_method, latency_ms, None)
            
            except subprocess.TimeoutExpired:
                latency_ms = int((time.time() - start_time) * 1000)
                logger.warning(f'LLM timeout after {timeout}s. Killing process group.')
                self._kill_process_group(process)
                CircuitBreaker.record_failure()
                return LLMResponse(LLMStatus.TIMEOUT.value, "", "", ParseMethod.FAILED.value, latency_ms, None)
        
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f'Unexpected LLM error: {e}')
            CircuitBreaker.record_failure()
            return LLMResponse(LLMStatus.CRASH.value, "", str(e), ParseMethod.FAILED.value, latency_ms, None)

    def _kill_process_group(self, process: subprocess.Popen) -> None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            time.sleep(2)
            if process.poll() is None:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            process.wait()
        except ProcessLookupError:
            pass  # Процесс уже завершился, это нормальная ситуация при race condition
        except Exception as e:
            get_logger('llm_gateway.gateway', 'N/A').error(f'Failed to kill process group: {e}')
