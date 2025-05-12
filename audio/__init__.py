# audio/__init__.py
# Basis-Importe die immer verfügbar sind
from .device_manager import DeviceManager
from .simple_speaker_diarization import SimpleSpeakerDiarizer

# Bedingte Importe
try:
    from .processor import AudioProcessor
except ImportError:
    AudioProcessor = None

try:
    from .diarization_processor import DiarizationProcessor
except ImportError:
    DiarizationProcessor = None

try:
    from .whisperx_processor import WhisperXProcessor
except ImportError:
    WhisperXProcessor = None

__all__ = [
    'DeviceManager',
    'SimpleSpeakerDiarizer'
]

# Füge nur hinzu, was erfolgreich importiert wurde
if AudioProcessor:
    __all__.append('AudioProcessor')
if DiarizationProcessor:
    __all__.append('DiarizationProcessor')
if WhisperXProcessor:
    __all__.append('WhisperXProcessor')