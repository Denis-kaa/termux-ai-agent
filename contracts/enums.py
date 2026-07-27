from enum import Enum

class ToolName(str, Enum):
    SEARCH_WEB = "search_web"
    REMINDER = "reminder"
    FILE_READER = "file_reader"
    CODE_GEN = "code_gen"
    UNKNOWN = "unknown"

class ResponseStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"

class RoutingMethod(str, Enum):
    KEYWORD = "keyword"
    LLM_FALLBACK = "llm_fallback"

class ParseMethod(str, Enum):
    JSON = "json"
    MARKER = "marker"
    HEURISTIC = "heuristic"
    FAILED = "failed"

class ErrorCode(str, Enum):
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_PARSE_FAILURE = "LLM_PARSE_FAILURE"
    LLM_CRASH = "LLM_CRASH"
    LLM_OOM = "LLM_OOM"
    LLM_DISABLED = "LLM_DISABLED"
    PATH_TRAVERSAL_ATTEMPT = "PATH_TRAVERSAL_ATTEMPT"
    PATH_OUTSIDE_WHITELIST = "PATH_OUTSIDE_WHITELIST"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    BINARY_FILE = "BINARY_FILE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    HTTP_ERROR = "HTTP_ERROR"
    PARSE_FAILED = "PARSE_FAILED"
    MISSING_ENTITY = "MISSING_ENTITY"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    CODE_GEN_NO_OUTPUT = "CODE_GEN_NO_OUTPUT"
    NOTIFICATION_FAILED = "NOTIFICATION_FAILED"
    WAKE_LOCK_FAILED = "WAKE_LOCK_FAILED"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"

class LLMStatus(str, Enum):
    OK = "ok"
    TIMEOUT = "timeout"
    CRASH = "crash"
    PARSE_ERROR = "parse_error"
    OOM = "oom"
    DISABLED = "disabled"

class NotificationErrorCode(str, Enum):
    """Коды ошибок termux-api (для NotificationResult)."""
    COMMAND_NOT_FOUND = "command_not_found"
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"
