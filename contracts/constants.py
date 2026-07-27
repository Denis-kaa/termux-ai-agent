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
LLM_DEFAULT_TIMEOUT_S: int = 25
HTTP_TIMEOUT_S: int = 15
ROUTER_CONFIDENCE_THRESHOLD: float = 0.6
OOM_THRESHOLD_MB: int = 200
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
