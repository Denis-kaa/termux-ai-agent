"""
Создание напоминаний через NER (LLM) + 3-level fallback.
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from contracts.constants import LLM_DEFAULT_TIMEOUT_S, NOTIFICATION_TIMEOUT_S, ICS_WRITE_TIMEOUT_S, JSONL_WRITE_TIMEOUT_S, HOME_DIR
from contracts.enums import ErrorCode, LLMStatus
from contracts.schemas import LLMResponse
from infra.logger import get_logger
from llm_gateway import LLMGatewayImpl
from infra.termux_api import send_notification, check_api_available
from tools.factories import create_success_result, create_error_result


class ReminderTool:
    """Реализует BaseTool Protocol."""
    
    def __init__(self, llm_gateway: LLMGatewayImpl):
        self._llm_gateway = llm_gateway
    
    @property
    def tool_name(self) -> str:
        return "reminder"
    
    def execute(self, params: Mapping[str, Any], correlation_id: str) -> 'ToolResult':
        logger = get_logger('tools.reminder', correlation_id)
        start_time = time.time()
        
        raw_text = params.get('raw_text', '')
        reference_date = params.get('reference_date', datetime.now().isoformat())
        
        llm_response = self._extract_entities(raw_text, reference_date, correlation_id)
        if llm_response.status != LLMStatus.OK.value:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                f"LLM_{llm_response.status.upper()}", llm_response.raw[:500],
                llm_calls=1, llm_total_ms=llm_response.latency_ms
            )
        
        try:
            entities = json.loads(llm_response.text)
        except json.JSONDecodeError as e:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                ErrorCode.LLM_PARSE_FAILURE.value, f"Failed to parse NER JSON: {e}",
                llm_calls=1, llm_total_ms=llm_response.latency_ms
            )
        
        action = entities.get('action')
        if not action:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                ErrorCode.MISSING_ENTITY.value, "action",
                llm_calls=1, llm_total_ms=llm_response.latency_ms
            )
        
        person = entities.get('person')
        deadline = entities.get('deadline')
        
        channel_used, error = self._deliver_notification(person, action, deadline, correlation_id, logger)
        
        if error:
            return create_error_result(
                self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
                ErrorCode.NOTIFICATION_FAILED.value, error,
                llm_calls=1, llm_total_ms=llm_response.latency_ms
            )
        
        return create_success_result(
            self.tool_name, correlation_id, int((time.time() - start_time) * 1000),
            data={'person': person, 'action': action, 'deadline': deadline, 'channel_used': channel_used},
            llm_calls=1, llm_total_ms=llm_response.latency_ms
        )
    
    def _extract_entities(self, raw_text: str, reference_date: str, correlation_id: str) -> LLMResponse:
        prompt = _build_ner_prompt(raw_text, reference_date)
        return self._llm_gateway.generate(
            prompt=prompt, timeout=LLM_DEFAULT_TIMEOUT_S, task_type="ner",
            expected_keys=["person", "action", "deadline"], correlation_id=correlation_id
        )
    
    def _deliver_notification(self, person: str | None, action: str, deadline: str | None, correlation_id: str, logger: Any) -> tuple[str | None, str | None]:
        title = f"Напоминание: {action[:50]}"
        content = f"Кому: {person or 'не указан'}\nКогда: {deadline or 'не указано'}"
        
        if check_api_available():
            result = send_notification(title=title, content=content, notification_id=f"reminder_{int(time.time())}", correlation_id=correlation_id)
            if result.success:
                return "termux-notification", None
            logger.warning(f"termux-notification failed: {result.error_code}")
        
        try:
            self._write_ics_file(action, person, deadline, correlation_id)
            return "ics-file", None
        except Exception as e:
            logger.warning(f".ics write failed: {e}")
        
        try:
            self._write_jsonl_log(person, action, deadline, correlation_id)
            return "jsonl-log", None
        except Exception as e:
            logger.error(f"jsonl write failed: {e}")
            return None, f"All fallbacks failed. Last: {e}"
    
    def _write_ics_file(self, action: str, person: str | None, deadline: str | None, correlation_id: str) -> str:
        reminders_dir = os.path.join(HOME_DIR, 'storage', 'downloads', 'reminders')
        os.makedirs(reminders_dir, exist_ok=True)
        
        timestamp = int(time.time())
        filepath = os.path.join(reminders_dir, f"reminder_{timestamp}.ics")
        dtstart = deadline or datetime.now().isoformat()
        description = f"Кому: {person or 'не указан'}\nДействие: {action}"
        
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Local AI Agent//Reminder//RU
BEGIN:VEVENT
UID:reminder-{timestamp}@local-ai-agent
DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%S')}
DTSTART:{dtstart.replace('-', '').replace(':', '').replace('T', 'T').replace(':', '').replace(':', '')[:15]}
SUMMARY:{action}
DESCRIPTION:{description}
END:VEVENT
END:VCALENDAR
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(ics_content)
        return filepath
    
    def _write_jsonl_log(self, person: str | None, action: str, deadline: str | None, correlation_id: str) -> None:
        log_path = os.path.join(HOME_DIR, 'reminders_failed.jsonl')
        entry = {'timestamp': datetime.now().isoformat(), 'correlation_id': correlation_id, 'person': person, 'action': action, 'deadline': deadline}
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def _build_ner_prompt(raw_text: str, reference_date: str) -> str:
    return f"""Ты — система извлечения сущностей. Извлеки person, action, deadline из текста.
Правила: person (имя или null), action (обязательно), deadline (ISO 8601, обязательно).
Примеры:
Текст: "Напомни маме позвонить завтра в 18:00" -> {{"person": "мама", "action": "позвонить", "deadline": "2026-07-28T18:00:00"}}
Текст: "Купить молоко через 2 часа" -> {{"person": null, "action": "Купить молоко", "deadline": "2026-07-27T12:30:00"}}
Текст: "{raw_text}"
Reference date: {reference_date}
Ответ:"""
