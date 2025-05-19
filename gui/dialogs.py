# gui/dialogs.py
"""
Dialog-Fenster für die ATA Audio-Aufnahme
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from config import settings


class DeviceSelectionDialog:
    def __init__(self, parent, device_manager, logger):
        self.parent = parent
        self.device_manager = device_manager
        self.logger = logger
        self.result = None

    def show(self):
        """Zeigt den Dialog und gibt das Ergebnis zurück."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Audiogeräte auswählen")
        self.dialog.geometry("500x420")
        self.dialog.grab_set()  # Modal machen

        self._create_widgets()

        self.dialog.wait_window()
        return self.result

    def _create_widgets(self):
        """Erstellt die Widgets für den Dialog."""
        # Geräte abrufen
        loopback_devices, microphones = self.device_manager.get_audio_devices()

        if not loopback_devices:
            messagebox.showerror("Fehler", "Kein BlackHole-Gerät gefunden.\n"
                                           "Bitte installieren Sie BlackHole und konfigurieren Sie es in Audio-MIDI-Setup.")
            self.dialog.destroy()
            return

        # Frames für Comboboxen
        frame = ttk.Frame(self.dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Loopback-Gerät
        ttk.Label(frame, text="Loopback-Gerät (Systemton):").grid(column=0, row=0, sticky=tk.W, pady=5)
        self.loopback_var = tk.StringVar()
        self.loopback_combo = ttk.Combobox(frame, textvariable=self.loopback_var, width=50)
        self.loopback_combo['values'] = [f"{device[1]} ({device[2]} Kanäle)" for device in loopback_devices]
        self.loopback_combo.grid(column=0, row=1, sticky=(tk.W, tk.E), pady=5)

        # Kein Gerät standardmäßig ausgewählt
        self.loopback_var.set("-- Bitte wählen --")

        # Mikrofon
        ttk.Label(frame, text="Mikrofon:").grid(column=0, row=2, sticky=tk.W, pady=5)
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(frame, textvariable=self.mic_var, width=50)
        self.mic_combo['values'] = [f"{device[1]} ({device[2]} Kanäle)" for device in microphones]
        self.mic_combo.grid(column=0, row=3, sticky=(tk.W, tk.E), pady=5)

        # Kein Gerät standardmäßig ausgewählt
        self.mic_var.set("-- Bitte wählen --")

        # Lautstärke-Regler
        ttk.Label(frame, text="System-Lautstärke:").grid(column=0, row=4, sticky=tk.W, pady=5)
        self.system_volume_var = tk.DoubleVar(value=settings.SYSTEM_VOLUME)
        self.system_volume_scale = ttk.Scale(frame, variable=self.system_volume_var, from_=0.0, to=1.0)
        self.system_volume_scale.grid(column=0, row=5, sticky=(tk.W, tk.E), pady=2)

        ttk.Label(frame, text="Mikrofon-Lautstärke:").grid(column=0, row=6, sticky=tk.W, pady=5)
        self.mic_volume_var = tk.DoubleVar(value=settings.MIC_VOLUME)
        self.mic_volume_scale = ttk.Scale(frame, variable=self.mic_volume_var, from_=0.0,
                                          to=2.0)  # Bis 200% für Mikrofon
        self.mic_volume_scale.grid(column=0, row=7, sticky=(tk.W, tk.E), pady=2)

        # Performance-Einstellungen
        ttk.Label(frame, text="--- Erweiterte Einstellungen ---").grid(column=0, row=8, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(frame, text="Puffergröße:").grid(column=0, row=9, sticky=tk.W, pady=5)
        self.buffer_size_var = tk.IntVar(value=settings.BUFFER_SIZE)
        self.buffer_size_combo = ttk.Combobox(frame, textvariable=self.buffer_size_var, width=20)
        self.buffer_size_combo['values'] = [1024, 2048, 4096, 8192, 16384]
        self.buffer_size_combo.current(
            self.buffer_size_combo['values'].index(settings.BUFFER_SIZE) if settings.BUFFER_SIZE in
                                                                            self.buffer_size_combo['values'] else 2)
        self.buffer_size_combo.grid(column=0, row=10, sticky=tk.W, pady=2)

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(column=0, row=11, pady=20)

        ttk.Button(button_frame, text="Speichern", command=self._on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Die aktuellen Geräte speichern
        self.loopback_devices = loopback_devices
        self.microphones = microphones

    def _on_save(self):
        """Speichert die ausgewählten Einstellungen."""
        loopback_idx = self.loopback_combo.current()
        mic_idx = self.mic_combo.current()

        # Prüfung hinzufügen
        if loopback_idx < 0:
            messagebox.showwarning("Warnung", "Bitte wählen Sie ein Loopback-Gerät aus!")
            return

        if mic_idx < 0:
            messagebox.showwarning("Warnung", "Bitte wählen Sie ein Mikrofon aus!")
            return

        if loopback_idx >= 0 and loopback_idx < len(self.loopback_devices):
            selected_loopback = self.loopback_devices[loopback_idx][0]
            loopback_name = self.loopback_devices[loopback_idx][1]
            loopback_channels = self.loopback_devices[loopback_idx][2]
        else:
            selected_loopback = None
            loopback_name = ""
            loopback_channels = settings.DEFAULT_CHANNELS

        if mic_idx >= 0 and mic_idx < len(self.microphones):
            selected_microphone = self.microphones[mic_idx][0]
            mic_name = self.microphones[mic_idx][1]
            microphone_channels = self.microphones[mic_idx][2]
        else:
            selected_microphone = None
            mic_name = ""
            microphone_channels = settings.DEFAULT_CHANNELS

        # Ergebnis speichern
        self.result = {
            'selected_loopback': selected_loopback,
            'loopback_name': loopback_name,
            'loopback_channels': loopback_channels,
            'selected_microphone': selected_microphone,
            'mic_name': mic_name,
            'microphone_channels': microphone_channels,
            'system_volume': self.system_volume_var.get(),
            'mic_volume': self.mic_volume_var.get(),
            'buffer_size': self.buffer_size_var.get()
        }

        if self.logger:
            self.logger.log_message(
                f"Lautstärke: System={self.result['system_volume']:.2f}, Mikrofon={self.result['mic_volume']:.2f}",
                "INFO")
            self.logger.log_message(f"Puffergröße: {self.result['buffer_size']}", "INFO")
            self.logger.log_message(f"Geräte ausgewählt: Loopback={loopback_name} ({loopback_channels} Kanäle), "
                                    f"Mikrofon={mic_name} ({microphone_channels} Kanäle)", "SUCCESS")

        self.dialog.destroy()


class HelpDialog:
    def __init__(self, parent):
        self.parent = parent

    def show(self):
        """Zeigt den Hilfe-Dialog."""
        help_window = tk.Toplevel(self.parent)
        help_window.title("Hilfe - ATA Audio-Aufnahme")
        help_window.geometry("700x600")

        help_text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, width=90, height=35)
        help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        instructions = """
# ATA Audio-Aufnahme für macOS

## Voraussetzungen

1. BlackHole Audio-Loopback installiert:
   - Installation über Homebrew: brew install blackhole-2ch

2. Audio-MIDI-Setup konfiguriert:
   - Multi-Output-Gerät erstellt mit BlackHole und Lautsprechern
   - Als Standardausgabegerät festgelegt

3. WhisperX-Server läuft:
   - Entweder lokaler WhisperX-Server oder externer API-Server
   - Standard-URL: http://141.72.16.242:8500
   - Prüfbar über Health Check: GET /health

## Verwendung

1. Geräteauswahl:
   - Klicken Sie auf "Geräteauswahl", um Loopback und Mikrofon festzulegen
   - BlackHole sollte als Loopback-Gerät ausgewählt werden
   - Wählen Sie Ihr gewünschtes Mikrofon
   - Passen Sie die Lautstärke von System und Mikrofon an
   - Passen Sie bei Audiostörungen die Puffergröße an

2. WhisperX-Konfiguration:
   - ✅ WhisperX API: Nutzt externen Server für Transkription
   - ⬜ WhisperX API: Nutzt lokale Verarbeitung (wenn installiert)
   - Bei API-Nutzung wird der konfigurierte Server verwendet
   - Server-Status wird beim Start automatisch geprüft

3. Test:
   - Klicken Sie auf "Test", um Testaufnahmen zu machen
   - Folgen Sie den Anweisungen im Dialog
   - Die Testdateien werden im gleichen Verzeichnis gespeichert
   - Teste verschiedene Szenarien: nur Audio, nur Mikrofon, beides

4. Aufnahme:
   - Klicken Sie auf "Start", um die Aufnahme zu beginnen
   - Status zeigt an, welche Methode verwendet wird (WhisperX API/lokal)
   - Klicken Sie auf "Stop", um die Aufnahme zu beenden
   - Die Aufnahme wird in "conversation.wav" gespeichert

5. Sprechererkennung:
   - ✅ Sprechererkennung: Aktiviert automatische Speaker Diarization
   - ⬜ Sprechererkennung: Deaktiviert (nur einfache Transkription)
   - Server-seitige Diarization (empfohlen) oder lokale Verarbeitung
   - Nach der Aufnahme werden verschiedene Sprecher erkannt
   - Die Transkription wird mit Sprecher-Labels versehen
   - Timeline zeigt visuell die Sprecher-Segmente an

## Transkriptions-Verfahren

### WhisperX API-Server (empfohlen):
- Nutzt externen GPU-Server für schnelle Verarbeitung
- Server-Status wird automatisch geprüft
- Unterstützt sowohl Transkription als auch Diarization
- Automatische Retry-Mechanismen bei Verbindungsproblemen

### Lokale Verarbeitung:
- Nutzt pyannote.audio für Sprechererkennung
- Erfordert Hugging Face Token in settings.py
- Langsamer, aber vollständig offline

### Audio-Engine:
- FFmpeg: Beste Audioqualität (empfohlen)
- Standard-Processor: Fallback bei FFmpeg-Problemen
- Automatische Auswahl basierend auf verfügbaren Tools

## Ausgabeformate

1. Timeline-Ansicht:
   - Visualisiert Sprecher-Segmente über Zeit
   - Farbkodiert für jeden erkannten Sprecher
   - Zeigt relative Sprechdauer an

2. Transkription:
   - Vollständige Transkription ohne Sprecher-Markierung
   - Sprecher-gebundene Transkription mit Labels
   - Statistiken über Sprechzeiten und -anteile

3. Audio-Dateien:
   - conversation.wav: Finale gemischte Aufnahme
   - test_*.wav: Testaufnahmen zur Verifikation

## Fehlerbehebung

### Audio-Probleme:
- Zu langsame oder flackernde Aufnahme:
  * Erhöhen Sie die Puffergröße in den Geräteeinstellungen
  * Versuchen Sie, andere Programme zu schließen
  * Überprüfen Sie, ob Ihr System ausreichend Ressourcen hat

- Kein BlackHole-Gerät gefunden:
  * Prüfen Sie, ob BlackHole korrekt installiert ist
  * Überprüfen Sie die Audio-MIDI-Setup-Konfiguration
  * Neustart kann helfen: sudo brew services restart blackhole-2ch

- Keine Audioeingabe:
  * Stellen Sie sicher, dass Audio über Multi-Output-Gerät abspielt
  * Überprüfen Sie die Mikrofon-Berechtigungen in Systemeinstellungen

### WhisperX API-Probleme:
- Server nicht erreichbar:
  * Prüfen Sie die URL in config/settings.py
  * Firewall-Einstellungen überprüfen
  * Bei Timeouts: Erhöhen Sie WHISPERX_TIMEOUT

- Server-Fehler 500/503:
  * Temporäre Überlastung - warten und wiederholen
  * Server könnte neu starten - automatische Retry aktiv

- Transkription fehlgeschlagen:
  * Audio-Datei möglicherweise zu groß/lang
  * Prüfen Sie Audio-Format (WAV empfohlen)
  * Bei großen Dateien: Automatisches Chunking aktiviert

### Lokale Verarbeitung:
- Pyannote.audio Fehler:
  * Hugging Face Token erforderlich
  * Modell-Download kann beim ersten Mal dauern
  * Internetverbindung für Modell-Download nötig

- Speicher-Probleme:
  * Schließen Sie andere speicherintensive Programme
  * Bei sehr langen Aufnahmen: Nutzen Sie WhisperX API

## Konfiguration

Erweiterte Einstellungen in config/settings.py:

```python
# API-Einstellungen
WHISPERX_API_URL = "http://141.72.16.203:8500/transcribe"
WHISPERX_TIMEOUT = 120  # Timeout in Sekunden
WHISPERX_ENABLE_DIARIZATION = True

# Audio-Qualität
USE_FFMPEG_PROCESSOR = True  # Für beste Qualität
SAMPLE_RATE = 44100
BUFFER_SIZE = 4096

# Sprechererkennung
MAX_SPEAKERS = 3  # Maximale Anzahl erwarteter Sprecher
```

## Performance-Tipps

1. Für beste Qualität: FFmpeg installieren
2. Für schnellste Verarbeitung: WhisperX API nutzen
3. Bei Problemen: Lokalen Fallback aktivieren
4. Große Aufnahmen: Automatisches Chunking nutzen
5. Multiple Sprecher: Diarization aktiviert lassen

## Statistiken und Visualisierung

Nach einer Aufnahme mit Sprechererkennung erhalten Sie:

1. Sprecher-Timeline:
   - Farbkodierte Darstellung aller Sprecher
   - Zeitstempel für jeden Sprecher-Wechsel
   - Visuelle Übersicht über Gesprächsverteilung

2. Sprecher-Statistiken:
   - Sprechzeit pro Person in Sekunden und Prozent
   - Anzahl der Wortbeiträge pro Sprecher
   - Beispiel-Transkriptionen pro Sprecher

3. Exportmöglichkeiten:
   - Volltext-Transkription
   - Sprecher-gelabelte Transkription
   - Audio-Export als WAV-Datei

Das System erkennt automatisch 2-3 verschiedene Sprecher und ordnet
die Transkription entsprechend zu. Bei mehr Sprechern oder schwierigen
Audiobedingungen kann die Erkennungsgenauigkeit variieren.
        """

        help_text.insert(tk.END, instructions)
        help_text.config(state=tk.DISABLED)

        close_button = tk.Button(help_window, text="Schließen", command=help_window.destroy)
        close_button.pack(pady=10)