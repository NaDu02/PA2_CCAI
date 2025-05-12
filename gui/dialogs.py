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

        # Wähle das erste Loopback-Gerät standardmäßig
        if loopback_devices:
            self.loopback_combo.current(0)

        # Mikrofon
        ttk.Label(frame, text="Mikrofon:").grid(column=0, row=2, sticky=tk.W, pady=5)
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(frame, textvariable=self.mic_var, width=50)
        self.mic_combo['values'] = [f"{device[1]} ({device[2]} Kanäle)" for device in microphones]
        self.mic_combo.grid(column=0, row=3, sticky=(tk.W, tk.E), pady=5)

        # Wähle das erste Mikrofon standardmäßig
        if microphones:
            self.mic_combo.current(0)

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
        help_window.geometry("600x500")

        help_text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, width=70, height=25)
        help_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        instructions = """
    # ATA Audio-Aufnahme für macOS

    ## Voraussetzungen

    1. BlackHole Audio-Loopback installiert:
       - Installation über Homebrew: brew install blackhole-2ch

    2. Audio-MIDI-Setup konfiguriert:
       - Multi-Output-Gerät erstellt mit BlackHole und Lautsprechern
       - Als Standardausgabegerät festgelegt

    ## Verwendung

    1. Geräteauswahl:
       - Klicken Sie auf "Geräteauswahl", um Loopback und Mikrofon festzulegen
       - BlackHole sollte als Loopback-Gerät ausgewählt werden
       - Wählen Sie Ihr gewünschtes Mikrofon
       - Passen Sie die Lautstärke von System und Mikrofon an
       - Passen Sie bei Audiostörungen die Puffergröße an

    2. Test:
       - Klicken Sie auf "Test", um Testaufnahmen zu machen
       - Folgen Sie den Anweisungen im Dialog
       - Die Testdateien werden im gleichen Verzeichnis gespeichert

    3. Aufnahme:
       - Klicken Sie auf "Start", um die Aufnahme zu beginnen
       - Klicken Sie auf "Stop", um die Aufnahme zu beenden
       - Die Aufnahme wird in "conversation.wav" gespeichert

    4. Sprechererkennung:
       - Aktivieren Sie "Sprechererkennung" für automatische Speaker Diarization
       - Nach der Aufnahme werden verschiedene Sprecher erkannt
       - Die Transkription wird mit Sprecher-Labels versehen

    ## Fehlerbehebung

    - Zu langsame oder flackernde Aufnahme:
      * Erhöhen Sie die Puffergröße in den Geräteeinstellungen
      * Versuchen Sie, andere Programme zu schließen
      * Überprüfen Sie, ob Ihr System ausreichend Ressourcen hat

    - Kein BlackHole-Gerät gefunden:
      * Prüfen Sie, ob BlackHole korrekt installiert ist
      * Überprüfen Sie die Audio-MIDI-Setup-Konfiguration

    - Keine Audioeingabe:
      * Stellen Sie sicher, dass Ihr System Audio über das Multi-Output-Gerät abspielt
      * Überprüfen Sie die Mikrofon-Berechtigungen in den Systemeinstellungen

    - Keine Mikrofon-Aufnahme:
      * Erhöhen Sie den Mikrofon-Lautstärkeregler in der Geräteauswahl
      * Prüfen Sie die Mikrofon-Berechtigungen in den macOS-Einstellungen
    """

        help_text.insert(tk.END, instructions)
        help_text.config(state=tk.DISABLED)

        close_button = tk.Button(help_window, text="Schließen", command=help_window.destroy)
        close_button.pack(pady=10)