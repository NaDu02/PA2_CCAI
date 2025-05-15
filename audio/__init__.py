# audio/__init__.py
"""
Audio-Package für ATA Audio-Aufnahme
Enthält alle Audio-Verarbeitungskomponenten
"""

# Kern-Komponenten (immer verfügbar)
from .device_manager import DeviceManager
from .simple_speaker_diarization import SimpleSpeakerDiarizer

# Audio-Verarbeitung
from .processor import AudioProcessor
from .diarization_processor import DiarizationProcessor
from .whisperx_processor import WhisperXProcessor

# Zusätzliche Features
from .summarization_client import SummarizationClient, summarization_client

# FFmpeg-Processor (optional, da externe Abhängigkeit)
try:
    from .ffmpeg_processor import FFmpegAudioProcessor
except ImportError:
    # FFmpeg nicht installiert - das ist OK
    FFmpegAudioProcessor = None

# Exportierte Komponenten
__all__ = [
    'DeviceManager',
    'SimpleSpeakerDiarizer',
    'AudioProcessor',
    'DiarizationProcessor',
    'WhisperXProcessor',
    'SummarizationClient',
    'summarization_client'
]

# FFmpeg-Processor nur hinzufügen wenn verfügbar
if FFmpegAudioProcessor:
    __all__.append('FFmpegAudioProcessor')