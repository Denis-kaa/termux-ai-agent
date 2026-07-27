"""Single Source of Truth для всех межмодульных констант."""

HOME_DIR: str = "/data/data/com.termux/files/home"
MODEL_PATH: str = f"{HOME_DIR}/models/qwen2.5-0.5b-instruct-q4_k_m.gguf"

ALLOWED_DIRS: list[str] = [
    f"{HOME_DIR}/storage/shared",
    f"{HOME_DIR}/storage/downloads",
    f"{HOME_DIR}/storage/dcim",
    "/sdcard",
    "/storage/emulated/0",
]

WRITE_ALLOWED_DIRS: list[str] = [
    f"{HOME_DIR}/storage/downloads",
    f"{HOME_DIR}/data",
]

MAX_FILE_SIZE_BYTES: int = 16384
MAX_LLM_CALLS_PER_REQUEST: int = 5
ROUTER_LLM_BUDGET: int = 2
TOTAL_LLM_BUDGET: int = 7
MAX_TOTAL_TIMEOUT_MS: int = 90_000
LLM_DEFAULT_TIMEOUT_S: int = 60
HTTP_TIMEOUT_S: int = 15
ROUTER_CONFIDENCE_THRESHOLD: float = 0.25
OOM_THRESHOLD_MB: int = 100
CIRCUIT_BREAKER_THRESHOLD: int = 3
LANGUAGE_WHITELIST: list[str] = [
    "python", "bash", "js", "typescript", "go", "rust", "java", "cpp"
]

# === Circuit Breaker ===
CIRCUIT_BREAKER_RESET_INTERVAL_SEC: int = 60

# === Normalizer: ASR Corrections (SSoT) ===
ASR_CORRECTIONS_DICT: dict[str, str] = {
    "установитт": "установить",
    "питон": "python",
    "термукс": "termux",
    "вайлберис": "wildberries",
    "озон": "ozon",
    "андроид": "android",
    "линукс": "linux",
    "пайтон": "python",
}

# === Normalizer: Sanitization Triggers (SSoT) ===
SANITIZATION_TRIGGERS: list[str] = [
    "ignore previous instructions",
    "забудь предыдущие инструкции",
    "system:",
    "ты теперь не помощник",
    "disregard all prior",
]

# === Phase 4: Notification timeouts (v3.6.0) ===
NOTIFICATION_TIMEOUT_S: int = 5
ICS_WRITE_TIMEOUT_S: int = 2
JSONL_WRITE_TIMEOUT_S: int = 1

# === Phase 4: HTTP retry (v3.6.0) ===
HTTP_RETRY_ATTEMPTS: int = 2
HTTP_RETRY_BACKOFF_S: tuple[int, ...] = (1, 3)

# === Phase 4: USER_AGENTS SSoT (v3.6.0 fix C2) ===
USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
)

# === Phase 4: Language → Extension mapping (v3.6.0 fix M10) ===
LANGUAGE_EXTENSIONS: dict[str, str] = {
    "python": "py",
    "bash": "sh",
    "js": "js",
    "typescript": "ts",
    "go": "go",
    "rust": "rs",
    "java": "java",
    "cpp": "cpp",
}
