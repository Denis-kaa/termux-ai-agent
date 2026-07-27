"""
Structured logging с correlation_id.
RotatingFileHandler для ротации логов.
"""
from __future__ import annotations

import logging
import os
import uuid
from logging.handlers import RotatingFileHandler
from typing import Any

from infra.config import Config


def generate_correlation_id() -> str:
    """Генерирует UUID v4 для tracing."""
    return str(uuid.uuid4())


def get_logger(module_name: str, correlation_id: str | None = None) -> logging.Logger:
    """
    Возвращает logger с correlation_id в контексте.
    
    Args:
        module_name: имя модуля
        correlation_id: сквозной ID для tracing (опционально, fallback на 'N/A')
    """
    logger = logging.getLogger(module_name)
    
    if not logger.handlers:
        _setup_handlers(logger, Config.get('LOGS_DIR'))
    
    ctx = {'correlation_id': correlation_id or 'N/A'}
    return _CorrelationAdapter(logger, ctx)


def _setup_handlers(logger: logging.Logger, logs_dir: str) -> None:
    os.makedirs(logs_dir, exist_ok=True)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    log_file = os.path.join(logs_dir, 'agent.log')
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=Config.get('LOG_MAX_BYTES'),
        backupCount=Config.get('LOG_BACKUP_COUNT'),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)


class _CorrelationAdapter(logging.LoggerAdapter):
    def process(self, msg: Any, kwargs: dict) -> tuple[Any, dict]:
        kwargs['extra'] = kwargs.get('extra', {})
        kwargs['extra']['correlation_id'] = self.extra.get('correlation_id', 'N/A')
        return msg, kwargs
