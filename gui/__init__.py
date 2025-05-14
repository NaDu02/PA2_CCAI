# gui/__init__.py - AKTUALISIERT
from .dialogs import DeviceSelectionDialog, HelpDialog
from .components import SpeakerTimelineWidget, TranscriptionWidget
from .summary_widget import SummaryWidget  # NEU

__all__ = [
    'DeviceSelectionDialog',
    'HelpDialog',
    'SpeakerTimelineWidget',
    'TranscriptionWidget',
    'SummaryWidget'  # NEU
]