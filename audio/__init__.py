# audio/__init__.py - AKTUALISIERT
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

# NEU: Summarization Client
try:
    from .summarization_client import SummarizationClient, summarization_client
except ImportError:
    SummarizationClient = None
    summarization_client = None

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
if SummarizationClient:
    __all__.extend(['SummarizationClient', 'summarization_client'])