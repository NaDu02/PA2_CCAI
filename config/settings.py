# config/settings.py
"""
Konfigurationseinstellungen für die ATA Audio-Aufnahme
"""

# Audio-Einstellungen
FILENAME = "conversation.wav"
API_URL = "http://168.231.106.208:10300/transcribe"
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