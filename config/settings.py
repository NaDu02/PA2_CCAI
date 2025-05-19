# config/settings.py
"""
Konfigurationseinstellungen für die ATA Audio-Aufnahme
Fokus auf Anwendungslogik-Konfiguration, Dependencies siehe requirements.txt
"""
import os
from typing import Tuple
from enum import Enum

# Environment Detection
class Environment(Enum):
    DEVELOPMENT = "dev"
    PRODUCTION = "prod"
    TESTING = "test"

CURRENT_ENV = Environment(os.getenv('ATA_ENV', 'prod'))

# Helper Function for Environment Variables
def get_env_setting(key: str, default, cast_type: type = str):
    """Lädt Einstellung aus Environment Variables mit Fallback"""
    value = os.getenv(f"ATA_{key}", default)
    if cast_type != str and value != default:
        try:
            if cast_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            return cast_type(value)
        except (ValueError, TypeError):
            return default
    return value

# =============================================================================
# APPLICATION METADATA
# =============================================================================
APP_VERSION = "1.2.0"
APP_NAME = "ATA Audio-Aufnahme"

# =============================================================================
# AUDIO CONFIGURATION
# =============================================================================
# Standard-Dateiname
FILENAME = get_env_setting("FILENAME", "conversation.wav")

# Audio-Qualitäts-Einstellungen
SAMPLE_RATE = get_env_setting("SAMPLE_RATE", 44100, int)  # Hz - Standard CD-Qualität
CHANNELS = get_env_setting("CHANNELS", 2, int)            # Stereo

# Performance-Einstellungen
BUFFER_SIZE = get_env_setting("BUFFER_SIZE", 4096, int)   # Audio-Puffergröße (Samples)
LATENCY = get_env_setting("LATENCY", "high")              # "low", "high" - Latenz vs. Stabilität
QUEUE_SIZE = get_env_setting("QUEUE_SIZE", 100, int)      # Interne Queue-Größe
DEVICE_TIMEOUT = get_env_setting("DEVICE_TIMEOUT", 0.2, float)  # Geräte-Timeout in Sekunden

# Standard-Kanalanzahl (Fallback)
DEFAULT_CHANNELS = CHANNELS

# Audio-Mischung
SYSTEM_VOLUME = get_env_setting("SYSTEM_VOLUME", 0.7, float)  # System-Audio Pegel (0.0-2.0)
MIC_VOLUME = get_env_setting("MIC_VOLUME", 1.0, float)        # Mikrofon Pegel (0.0-2.0)

# =============================================================================
# SPEAKER DIARIZATION CONFIGURATION
# =============================================================================
# Aktivierung der Sprechererkennung
ENABLE_SPEAKER_DIARIZATION = get_env_setting("ENABLE_SPEAKER_DIARIZATION", True, bool)

# Diarization-Parameter
MIN_SPEECH_DURATION = get_env_setting("MIN_SPEECH_DURATION", 0.5, float)      # Min. Segmentlänge (s)
MIN_TRANSCRIBE_DURATION = get_env_setting("MIN_TRANSCRIBE_DURATION", 1.0, float)  # Min. für Transkription (s)
GROUP_GAP_THRESHOLD = get_env_setting("GROUP_GAP_THRESHOLD", 1.0, float)      # Max. Pause für Gruppierung (s)
MAX_GROUP_DURATION = get_env_setting("MAX_GROUP_DURATION", 30.0, float)       # Max. Gruppenlänge (s)
MAX_SPEAKERS = get_env_setting("MAX_SPEAKERS", 3, int)                        # Max. erwartete Sprecher
VAD_AGGRESSIVENESS = get_env_setting("VAD_AGGRESSIVENESS", 2, int)            # Voice Activity Detection (0-3)

# =============================================================================
# SERVER CONFIGURATION (zentrale IP-Definition)
# =============================================================================
# Zentrale Definition der Server-IP-Adresse - NUR HIER ÄNDERN
SERVER_IP = get_env_setting("SERVER_IP", "141.72.16.203")

# Port-Definitionen
WHISPERX_PORT = get_env_setting("WHISPERX_PORT", "8500")
SUMMARIZATION_PORT = get_env_setting("SUMMARIZATION_PORT", "8501")
OLLAMA_PORT = get_env_setting("OLLAMA_PORT", "11434")

# =============================================================================
# WHISPERX API CONFIGURATION
# =============================================================================
# API-Einstellungen
USE_WHISPERX_API = True  # Immer API-basiert in dieser Version
WHISPERX_API_URL = f"http://{SERVER_IP}:{WHISPERX_PORT}/transcribe"
WHISPERX_TIMEOUT = get_env_setting("WHISPERX_TIMEOUT", 120, int)               # Timeout in Sekunden
WHISPERX_LANGUAGE = get_env_setting("WHISPERX_LANGUAGE", "de")                 # Sprache für Transkription
WHISPERX_COMPUTE_TYPE = get_env_setting("WHISPERX_COMPUTE_TYPE", "float16")    # GPU-Compute-Type
WHISPERX_ENABLE_DIARIZATION = get_env_setting("WHISPERX_ENABLE_DIARIZATION", True, bool)  # API-Diarization

# =============================================================================
# SYSTEM REQUIREMENTS (nur Python-Version)
# =============================================================================
# Python-Version (Dependencies siehe requirements.txt)
REQUIRED_PYTHON_VERSION = (3, 8)

# =============================================================================
# FALLBACK & ERROR HANDLING
# =============================================================================
# Fallback bei API-Fehlern
ENABLE_FALLBACK_ON_API_FAILURE = get_env_setting("ENABLE_FALLBACK_ON_API_FAILURE", True, bool)
SAVE_FAILED_JOBS = get_env_setting("SAVE_FAILED_JOBS", True, bool)
FAILED_JOBS_DIR = get_env_setting("FAILED_JOBS_DIR", "failed_transcriptions")

# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================

# Summarization Service URLs
SUMMARIZATION_SERVICE_URL = f"http://{SERVER_IP}:{SUMMARIZATION_PORT}"

# Ollama LLM Service
OLLAMA_SERVICE_URL = f"http://{SERVER_IP}:{OLLAMA_PORT}"

# Service Health Check Settings
HEALTH_CHECK_TIMEOUT = get_env_setting("HEALTH_CHECK_TIMEOUT", 10, int)
SERVICE_TEST_ENABLED = get_env_setting("SERVICE_TEST_ENABLED", True, bool)

# Automatisches Service-Monitoring (optional)
SERVICE_AUTO_MONITORING = get_env_setting("SERVICE_AUTO_MONITORING", False, bool)
SERVICE_MONITORING_INTERVAL = get_env_setting("SERVICE_MONITORING_INTERVAL", 60, int)

# Docker Container Management
DOCKER_CONTAINER_NAMES = {
    "whisperx": get_env_setting("DOCKER_WHISPERX_NAME", "whisperx-api"),
    "summarization": get_env_setting("DOCKER_SUMMARIZATION_NAME", "summarization-api"),
    "ollama": get_env_setting("DOCKER_OLLAMA_NAME", "ollama")
}

# =============================================================================
# ENVIRONMENT-SPECIFIC OVERRIDES
# =============================================================================
# Development Environment Anpassungen
if CURRENT_ENV == Environment.DEVELOPMENT:
    # Kürzere Timeouts für schnellere Entwicklung
    WHISPERX_TIMEOUT = get_env_setting("WHISPERX_TIMEOUT", 30, int)
    # Dev-Server IP kann überschrieben werden
    DEV_SERVER_IP = get_env_setting("DEV_SERVER_IP", SERVER_IP)
    # URLs für Entwicklungsumgebung
    WHISPERX_API_URL = f"http://{DEV_SERVER_IP}:{WHISPERX_PORT}/transcribe"
    SUMMARIZATION_SERVICE_URL = f"http://{DEV_SERVER_IP}:{SUMMARIZATION_PORT}"
    OLLAMA_SERVICE_URL = f"http://{DEV_SERVER_IP}:{OLLAMA_PORT}"

# Testing Environment Anpassungen
elif CURRENT_ENV == Environment.TESTING:
    # Schnelle Tests ohne echte Diarization
    ENABLE_SPEAKER_DIARIZATION = False
    WHISPERX_TIMEOUT = 10
    SAVE_FAILED_JOBS = False

# =============================================================================
# SERVICE-SPECIFIC CONFIGURATIONS (ERWEITERTE EINSTELLUNGEN)
# =============================================================================

# Ollama Specific
OLLAMA_MODEL_NAME = get_env_setting("OLLAMA_MODEL_NAME", "llama3.1:8b")
OLLAMA_GENERATE_TIMEOUT = get_env_setting("OLLAMA_GENERATE_TIMEOUT", 30, int)

# Summarization Specific
SUMMARIZATION_TIMEOUT = get_env_setting("SUMMARIZATION_TIMEOUT", 60, int)
SUMMARIZATION_DETAILED_ANALYSIS = get_env_setting("SUMMARIZATION_DETAILED_ANALYSIS", True, bool)

# Service Health Check Retry Settings
HEALTH_CHECK_RETRIES = get_env_setting("HEALTH_CHECK_RETRIES", 3, int)
HEALTH_CHECK_RETRY_DELAY = get_env_setting("HEALTH_CHECK_RETRY_DELAY", 1, int)  # Sekunden zwischen Retries

# Service Discovery Konfiguration entfernt, da redundant mit zentraler SERVER_IP

# =============================================================================
# OPTIONAL: SERVICE PRIORITY CONFIGURATION
# =============================================================================

# Definiert welche Services kritisch sind für die Anwendung
CRITICAL_SERVICES = get_env_setting("CRITICAL_SERVICES", ["whisperx"], list)
OPTIONAL_SERVICES = get_env_setting("OPTIONAL_SERVICES", ["summarization", "ollama"], list)

# Service-spezifische Feature Flags
ENABLE_WHISPERX_HEALTH_CHECK = get_env_setting("ENABLE_WHISPERX_HEALTH_CHECK", True, bool)
ENABLE_SUMMARIZATION_HEALTH_CHECK = get_env_setting("ENABLE_SUMMARIZATION_HEALTH_CHECK", True, bool)
ENABLE_OLLAMA_HEALTH_CHECK = get_env_setting("ENABLE_OLLAMA_HEALTH_CHECK", True, bool)