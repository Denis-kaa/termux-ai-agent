"""
Unit и Integration тесты для Phase 4 Tools.
"""
import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch, mock_open

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts.enums import ErrorCode, LLMStatus, NotificationErrorCode
from contracts.schemas import NotificationResult
from tools.factories import create_success_result, create_error_result
from infra.termux_api import send_notification, check_api_available, reset_api_cache


class TestTermuxAPI:
    def setup_method(self):
        reset_api_cache()

    @patch('platform.termux_api.subprocess.run')
    def test_send_notification_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = send_notification("Title", "Content", correlation_id="test-1")
        assert result.success is True
        assert result.error_code is None

    @patch('platform.termux_api.subprocess.run')
    def test_send_notification_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="termux-notification", timeout=5)
        result = send_notification("Title", "Content", correlation_id="test-2")
        assert result.success is False
        assert result.error_code == NotificationErrorCode.TIMEOUT.value

    @patch('platform.termux_api.shutil.which')
    def test_check_api_available(self, mock_which):
        mock_which.return_value = "/usr/bin/termux-notification"
        assert check_api_available() is True
        mock_which.return_value = None
        reset_api_cache()
        assert check_api_available() is False


class TestSearchWeb:
    @patch('tools.search_web.requests.get')
    def test_search_web_success(self, mock_get):
        from tools.search_web import SearchWebTool
        mock_get.return_value = MagicMock(
            status_code=200,
            text='<div class="result"><a class="result__title">Test</a><a class="result__snippet">Snippet</a></div>'
        )
        tool = SearchWebTool()
        result = tool.execute({'query': 'test'}, 'test-3')
        assert result.status == "ok"
        assert len(result.data['results']) == 1

    @patch('tools.search_web.requests.get')
    def test_search_web_captcha(self, mock_get):
        from tools.search_web import SearchWebTool
        mock_get.return_value = MagicMock(status_code=200, text="unusual traffic from your computer")
        tool = SearchWebTool()
        result = tool.execute({'query': 'test'}, 'test-4')
        assert result.status == "error"
        assert result.error == ErrorCode.HTTP_ERROR.value


class TestCodeGen:
    @patch('tools.code_gen.validate_path')
    @patch('tools.code_gen.os.path.exists')
    @patch('tools.code_gen.open', new_callable=mock_open)
    def test_code_gen_success(self, mock_file, mock_exists, mock_validate):
        from tools.code_gen import CodeGenTool
        mock_validate.return_value = MagicMock(valid=True, resolved_path='/fake/path/test.py')
        mock_exists.return_value = False
        
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(
            status=LLMStatus.OK.value, text="```python\nprint('hello')\n```", raw="", latency_ms=100
        )
        
        tool = CodeGenTool(llm_gateway=mock_llm)
        result = tool.execute({'task': 'hello', 'language': 'python'}, 'test-5')
        
        assert result.status == "ok"
        assert result.data['executed'] is False
        assert result.data['extraction_method'] == "markdown"


class TestReminder:
    @patch('tools.reminder.check_api_available')
    @patch('tools.reminder.send_notification')
    def test_reminder_fallback_to_ics(self, mock_send, mock_check):
        from tools.reminder import ReminderTool
        mock_check.return_value = False # Force fallback
        
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(
            status=LLMStatus.OK.value, 
            text=json.dumps({"person": "Mom", "action": "Call", "deadline": "2026-07-28T10:00:00"}), 
            raw="", latency_ms=100
        )
        
        tool = ReminderTool(llm_gateway=mock_llm)
        # Mock file operations for ICS
        with patch('tools.reminder.os.makedirs'), patch('tools.reminder.open', new_callable=mock_open):
            result = tool.execute({'raw_text': 'call mom tomorrow', 'reference_date': '2026-07-27T10:00:00'}, 'test-6')
            
        assert result.status == "ok"
        assert result.data['channel_used'] == "ics-file"
