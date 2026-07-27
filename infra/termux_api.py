"""
Обёртка для termux-api команд.
Единственный модуль в infra, имеющий право на subprocess для termux-api.
"""
from __future__ import annotations

import shutil
import subprocess

from contracts.constants import NOTIFICATION_TIMEOUT_S
from contracts.enums import NotificationErrorCode
from contracts.schemas import NotificationResult
from infra.config import Config
from infra.logger import get_logger

_api_available_cache: bool | None = None


def send_notification(
    title: str,
    content: str,
    notification_id: str | None = None,
    correlation_id: str | None = None,
) -> NotificationResult:
    """Отправляет push-уведомление через termux-notification."""
    logger = get_logger('infra.termux_api', correlation_id or "N/A")
    
    cmd = ['termux-notification', '--title', title, '--content', content]
    if notification_id:
        cmd.extend(['--id', notification_id])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=NOTIFICATION_TIMEOUT_S,
            check=False,
        )
        
        if result.returncode == 0:
            logger.info(f"Notification sent: {title[:50]}")
            return NotificationResult(success=True)
        
        error_details = result.stderr.strip() or result.stdout.strip()
        logger.warning(f"Notification failed with code {result.returncode}: {error_details[:200]}")
        
        return NotificationResult(
            success=False,
            error_code=_classify_error(result.stderr, result.returncode),
            error_details=error_details[:500],
        )
    except FileNotFoundError:
        logger.error("termux-notification not found in PATH")
        return NotificationResult(
            success=False,
            error_code=NotificationErrorCode.COMMAND_NOT_FOUND.value,
            error_details="termux-notification binary not found. Install termux-api package.",
        )
    except PermissionError as e:
        logger.error(f"Permission denied for termux-notification: {e}")
        return NotificationResult(
            success=False,
            error_code=NotificationErrorCode.PERMISSION_DENIED.value,
            error_details=str(e),
        )
    except subprocess.TimeoutExpired:
        logger.error(f"termux-notification timed out after {NOTIFICATION_TIMEOUT_S}s")
        return NotificationResult(
            success=False,
            error_code=NotificationErrorCode.TIMEOUT.value,
            error_details=f"Timeout after {NOTIFICATION_TIMEOUT_S}s",
        )
    except Exception as e:
        logger.error(f"Unexpected error in send_notification: {e}")
        return NotificationResult(
            success=False,
            error_code=NotificationErrorCode.UNKNOWN.value,
            error_details=str(e)[:500],
        )


def check_api_available() -> bool:
    """Проверяет доступность termux-notification (кэшируется)."""
    global _api_available_cache
    if _api_available_cache is not None:
        return _api_available_cache
    
    _api_available_cache = shutil.which('termux-notification') is not None
    return _api_available_cache


def reset_api_cache() -> None:
    """Сбросить кэш (для тестов)."""
    global _api_available_cache
    _api_available_cache = None


def _classify_error(stderr: str, returncode: int) -> str:
    """Классифицирует ошибку по stderr."""
    stderr_lower = stderr.lower()
    if 'permission' in stderr_lower or returncode == 126:
        return NotificationErrorCode.PERMISSION_DENIED.value
    if 'not found' in stderr_lower or returncode == 127:
        return NotificationErrorCode.COMMAND_NOT_FOUND.value
    return NotificationErrorCode.UNKNOWN.value
