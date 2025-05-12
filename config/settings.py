# config/settings.py
"""
Konfigurationseinstellungen für die ATA Audio-Aufnahme
"""

# Versionsinformation
APP_VERSION = "1.1.0"
APP_NAME = "ATA Audio-Aufnahme"

# Audio-Einstellungen
FILENAME = "conversation.wav"
SAMPLE_RATE = 44100
CHANNELS = 2

# Performance-Einstellungen
BUFFER_SIZE = 4096
LATENCY = "high"
QUEUE_SIZE = 100
DEVICE_TIMEOUT = 0.2

# Standard-Kanalanzahl
DEFAULT_CHANNELS = 2

# Mischverhältnis
SYSTEM_VOLUME = 0.7
MIC_VOLUME = 1.0

# Speaker Diarization Einstellungen
ENABLE_SPEAKER_DIARIZATION = True
MIN_SPEECH_DURATION = 0.5  # Minimale Segmentlänge in Sekunden
MIN_TRANSCRIBE_DURATION = 1.0  # Erhöht auf 1 Sekunde
GROUP_GAP_THRESHOLD = 1.0  # Maximale Pause zwischen Segmenten zum Gruppieren
MAX_GROUP_DURATION = 30.0  # Maximale Länge einer Gruppe
MAX_SPEAKERS = 3  # Maximale erwartete Anzahl von Sprechern
VAD_AGGRESSIVENESS = 2  # 0-3, höher = aggressiver

# WhisperX API Einstellungen
USE_WHISPERX = True
USE_WHISPERX_API = True
WHISPERX_API_URL = "http://141.72.16.242:8500/transcribe"
WHISPERX_TIMEOUT = 120  # Timeout für API-Aufrufe in Sekunden
WHISPERX_LANGUAGE = "de"  # Standard-Sprache
WHISPERX_COMPUTE_TYPE = "float16"  # Compute-Type für GPU
WHISPERX_ENABLE_DIARIZATION = True  # API-seitige Sprechererkennung

# Hugging Face Einstellungen (für lokale Verarbeitung)
HUGGINGFACE_TOKEN = "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"
PYANNOTE_DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"
PYANNOTE_SEGMENTATION_MODEL = "pyannote/segmentation"

# Systemanforderungen
REQUIRED_PYTHON_VERSION = (3, 8)
REQUIRED_PACKAGES = {
    'numpy': '1.24.0',
    'sounddevice': '0.4.6',
    'soundfile': '0.12.1',
    'requests': '2.31.0',
    'webrtcvad': '2.0.10',
    'scikit-learn': '1.3.0',
    'librosa': '0.10.0',
    'scipy': '1.11.0',
    'matplotlib': '3.7.0'
}