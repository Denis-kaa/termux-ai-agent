from __future__ import annotations
import os
from dataclasses import dataclass
from contracts.constants import HOME_DIR
from infra.config import Config

@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    resolved_path: str | None = None
    error: str | None = None

def validate_path(requested_path: str, operation: str = "read") -> ValidationResult:
    if not requested_path:
        return ValidationResult(valid=False, error="PATH_OUTSIDE_WHITELIST")
    if len(requested_path) > 4096:
        return ValidationResult(valid=False, error="PATH_OUTSIDE_WHITELIST")
    
    try:
        resolved = _resolve_path(requested_path)
    except Exception:
        return ValidationResult(valid=False, error="PATH_OUTSIDE_WHITELIST")
    
    if operation == "write":
        for blacklist_path in Config.get('WRITE_BLACKLIST'):
            if resolved == blacklist_path or resolved.startswith(blacklist_path + os.sep):
                return ValidationResult(valid=False, error="PATH_TRAVERSAL_ATTEMPT")
    
    if operation == "read":
        whitelist = Config.get('ALLOWED_DIRS')
    elif operation == "write":
        whitelist = Config.get('WRITE_ALLOWED_DIRS')
    else:
        raise ValueError(f"Unknown operation: {operation}")
    
    if not _is_in_whitelist(resolved, whitelist):
        return ValidationResult(valid=False, error="PATH_OUTSIDE_WHITELIST")
    
    if operation == "read" and not os.path.exists(resolved):
        return ValidationResult(valid=False, error="FILE_NOT_FOUND")
    if operation == "read" and not os.access(resolved, os.R_OK):
        return ValidationResult(valid=False, error="PERMISSION_DENIED")
    if operation == "write":
        parent_dir = os.path.dirname(resolved)
        if not os.path.exists(parent_dir):
            return ValidationResult(valid=False, error="PATH_OUTSIDE_WHITELIST")
        if not os.access(parent_dir, os.W_OK):
            return ValidationResult(valid=False, error="PERMISSION_DENIED")
    
    return ValidationResult(valid=True, resolved_path=resolved)

def _resolve_path(path: str) -> str:
    if path.startswith('~'):
        path = path.replace('~', HOME_DIR, 1)
    return os.path.realpath(path)

def _is_in_whitelist(resolved_path: str, whitelist: list[str]) -> bool:
    for wl_path in whitelist:
        if resolved_path == wl_path:
            return True
        if resolved_path.startswith(wl_path + os.sep):
            return True
    return False
