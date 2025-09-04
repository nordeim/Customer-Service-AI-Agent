from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger

# Correlation context
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
conversation_id_ctx: ContextVar[Optional[str]] = ContextVar("conversation_id", default=None)


class ContextualJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger", record.name)
        # Correlation
        log_record.setdefault("request_id", request_id_ctx.get())
        log_record.setdefault("user_id", user_id_ctx.get())
        log_record.setdefault("conversation_id", conversation_id_ctx.get())
        # Static context
        log_record.setdefault("service", "ai-agent")
        log_record.setdefault("environment", os.getenv("ENVIRONMENT", "development"))


def _build_handler(stream: Any, level: int) -> logging.Handler:
    handler = logging.StreamHandler(stream)
    formatter = ContextualJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def get_logger(name: str = "app", level: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_level = getattr(logging, (level or os.getenv("LOG_LEVEL", "INFO")).upper(), logging.INFO)

    logger.setLevel(log_level)
    logger.addHandler(_build_handler(sys.stdout, log_level))

    # Error file handler (optional path)
    error_log_path = os.getenv("ERROR_LOG_PATH")
    if error_log_path:
        file_handler = logging.FileHandler(error_log_path)
        file_handler.setFormatter(ContextualJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s"))
        file_handler.setLevel(logging.ERROR)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def set_correlation_ids(request_id: Optional[str] = None, user_id: Optional[str] = None, conversation_id: Optional[str] = None) -> None:
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_ctx.set(request_id)
    if user_id is not None:
        user_id_ctx.set(user_id)
    if conversation_id is not None:
        conversation_id_ctx.set(conversation_id)


def clear_correlation_ids() -> None:
    request_id_ctx.set(None)
    user_id_ctx.set(None)
    conversation_id_ctx.set(None)
