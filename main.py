# main.py
"""
Hauptprogramm für die ATA Audio-Aufnahme
"""
import os
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext
import sounddevice as sd
import numpy as np
import requests
import traceback

# Unterdrücken von IMK-Meldungen in macOS
os.environ['TK_SILENCE_DEPRECATION'] = '1'

# Lokale Module importieren
from config import settings
from utils.logger import Logger
from audio.processor import AudioProcessor
from audio.device_manager import DeviceManager
from gui.dialogs import DeviceSelectionDialog, HelpDialog
from tests.test_recording import TestRecording


class ATAAudioApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("ATA Audio-Aufnahme (macOS)")
        self.root.geometry("700x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Instanzvariablen
        self.logger = Logger()
        self.device_manager = DeviceManager(self.logger)
        self.test_recorder = TestRecording(self.device_manager, self.logger)
        self.audio_processor = None
        self.recording = False

        # Ausgewählte Geräte
        self.selected_loopback = None
        self.selected_microphone = None
        self.loopback_channels = settings.DEFAULT_CHANNELS
        self.microphone_channels = settings.DEFAULT_CHANNELS
        self.system_volume = settings.SYSTEM_VOLUME
        self.mic_volume = settings.MIC_VOLUME
        self.buffer_size = settings.BUFFER_SIZE

        self.setup_gui()
        self.initialize_application()

    def setup_gui(self):
        """Richtet die GUI-Komponenten ein."""
        # Hauptframe
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Statusanzeige
        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.status_label = tk.Label(status_frame, text="Status: Initialisierung...", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_mic_label = tk.Label(status_frame, text="", anchor=tk.E)
        self.status_mic_label.pack(side=tk.RIGHT)

        # Button-Frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_button = tk.Button(button_frame, text="Start", command=self.start_recording, width=10)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(button_frame, text="Stop", command=self.stop_recording, width=10,
                                     state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.test_button = tk.Button(button_frame, text="Test", command=self.test_recording, width=10)
        self.test_button.pack(side=tk.LEFT, padx=5)

        self.devices_button = tk.Button(button_frame, text="Geräteauswahl", command=self.show_device_selection,
                                        width=15)
        self.devices_button.pack(side=tk.LEFT, padx=5)

        self.help_button = tk.Button(button_frame, text="Hilfe", command=self.show_help, width=10)
        self.help_button.pack(side=tk.RIGHT, padx=5)

        # Log-Bereich
        log_frame = tk.LabelFrame(main_frame, text="Protokoll")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=80, height=30)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)

        # Logger konfigurieren
        self.logger.set_log_text_widget(self.log_text)

    def initialize_application(self):
        """Initialisiert die Anwendung."""
        self.logger.log_message("=== ATA Audio-Aufnahme für macOS ===", "INFO")
        self.logger.log_message("Überprüfe Audio-Setup...", "INFO")

        blackhole_found, device_name = self.device_manager.check_blackhole()

        if blackhole_found:
            self.logger.log_message(f"Gefunden: Loopback-Device '{device_name}'", "SUCCESS")
            self.logger.log_message("Audio-Setup-Prüfung OK.", "INFO")
            self.status_label.config(text="Status: Bereit")
        else:
            self.logger.log_message("Kein BlackHole-Gerät gefunden.", "ERROR")
            self.logger.log_message("Audio-Setup unvollständig!", "WARNING")
            self.logger.log_message("Bitte stellen Sie sicher, dass BlackHole installiert und konfiguriert ist.",
                                    "INFO")
            self.status_label.config(text="Status: Fehler beim Audio-Setup")

        # Geräteauswahl nach kurzer Verzögerung anzeigen
        self.root.after(500, self.show_device_selection)

    def show_device_selection(self):
        """Zeigt den Geräteauswahl-Dialog."""
        dialog = DeviceSelectionDialog(self.root, self.device_manager, self.logger)
        result = dialog.show()

        if result:
            # Geräte speichern
            self.selected_loopback = result['selected_loopback']
            self.selected_microphone = result['selected_microphone']
            self.loopback_channels = result['loopback_channels']
            self.microphone_channels = result['microphone_channels']
            self.system_volume = result['system_volume']
            self.mic_volume = result['mic_volume']
            self.buffer_size = result['buffer_size']

            # Einstellungen aktualisieren
            settings.BUFFER_SIZE = self.buffer_size

            # Update Status-Labels mit den ausgewählten Geräten
            self.status_label.config(text=f"Loopback: {result['loopback_name']} ({result['loopback_channels']} Kanäle)")
            self.status_mic_label.config(
                text=f"Mikrofon: {result['mic_name']} ({result['microphone_channels']} Kanäle)")

    def show_help(self):
        """Zeigt den Hilfe-Dialog."""
        help_dialog = HelpDialog(self.root)
        help_dialog.show()

    def start_recording(self):
        """Startet die Aufnahme."""
        if self.recording:
            self.logger.log_message("Aufnahme läuft bereits.", "INFO")
            return

        try:
            # Stellen Sie sicher, dass Geräte ausgewählt sind
            if self.selected_loopback is None or self.selected_microphone is None:
                if messagebox.askyesno("Geräteauswahl",
                                       "Keine Audiogeräte ausgewählt. Möchten Sie jetzt Geräte auswählen?"):
                    self.show_device_selection()
                else:
                    return

            # Nochmal prüfen, falls Dialog abgebrochen wurde
            if self.selected_loopback is None or self.selected_microphone is None:
                self.logger.log_message("Keine Audiogeräte ausgewählt - Aufnahme abgebrochen", "ERROR")
                return

            # AudioProcessor erstellen
            self.audio_processor = AudioProcessor(
                system_device=self.selected_loopback,
                mic_device=self.selected_microphone,
                system_channels=self.loopback_channels,
                mic_channels=self.microphone_channels,
                logger=self.logger
            )

            # Lautstärke setzen
            self.audio_processor.set_volumes(self.system_volume, self.mic_volume)

            # Aufnahme starten
            self.audio_processor.start(settings.FILENAME)
            self.recording = True

            # UI aktualisieren
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text=f"Status: Aufnahme läuft")

        except Exception as e:
            self.logger.log_message(f"Fehler beim Starten der Aufnahme: {e}", "ERROR")
            traceback.print_exc()
            messagebox.showerror("Fehler", f"Fehler beim Starten der Aufnahme: {e}")
            self.recording = False

    def stop_recording(self):
        """Stoppt die Aufnahme."""
        if not self.recording:
            self.logger.log_message("Keine Aufnahme aktiv.", "INFO")
            return

        try:
            # Aufnahme stoppen
            if self.audio_processor:
                self.audio_processor.stop()

            self.recording = False

            # Garbage Collection erzwingen
            import gc
            gc.collect()

            # UI aktualisieren
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Bereit")

            # Optional: Transkription
            try:
                with open(settings.FILENAME, "rb") as vf:
                    resp = requests.post(settings.API_URL, files={"file": (settings.FILENAME, vf, "audio/wav")})

                if resp.ok:
                    self.logger.log_message("📝 Transkription:\n" + resp.json().get("transcription", "—"), "INFO")
                else:
                    self.logger.log_message(f"Transkriptions-Fehler: {resp.status_code}", "ERROR")
            except Exception as e:
                self.logger.log_message(f"Transkription nicht möglich: {e}", "WARNING")

        except Exception as e:
            self.logger.log_message(f"Fehler beim Stoppen der Aufnahme: {e}", "ERROR")
            traceback.print_exc()
            messagebox.showerror("Fehler", f"Fehler beim Stoppen der Aufnahme: {e}")

            # Trotzdem Status zurücksetzen
            self.recording = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Fehler aufgetreten")

    def test_recording(self):
        """Führt einen Test durch."""
        if self.recording:
            self.logger.log_message("Test nicht möglich - Aufnahme läuft bereits.", "WARNING")
            messagebox.showwarning("Warnung", "Test nicht möglich - Aufnahme läuft bereits.")
            return

        # Deaktiviere Buttons während Test
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.test_button.config(state=tk.DISABLED)
        self.devices_button.config(state=tk.DISABLED)

        self.logger.log_message("Testaufnahme (5 Sekunden)...", "INFO")

        # Geräteauswahl prüfen
        if self.selected_loopback is None or self.selected_microphone is None:
            if messagebox.askyesno("Geräteauswahl",
                                   "Keine Audiogeräte ausgewählt. Möchten Sie jetzt Geräte auswählen?"):
                self.show_device_selection()
            else:
                self.reset_buttons()
                return

        if self.selected_loopback is None or self.selected_microphone is None:
            self.logger.log_message("Test abgebrochen - keine Geräte ausgewählt.", "WARNING")
            self.reset_buttons()
            return

        # Test durchführen
        self.test_recorder.run_test(
            self.selected_loopback,
            self.selected_microphone,
            self.loopback_channels,
            self.microphone_channels
        )

        # Buttons wieder aktivieren
        self.reset_buttons()

    def reset_buttons(self):
        """Setzt die Button-Status zurück."""
        if self.recording:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
        self.test_button.config(state=tk.NORMAL)
        self.devices_button.config(state=tk.NORMAL)

    def on_closing(self):
        """Handler für das Schließen des Fensters."""
        if self.recording:
            if messagebox.askyesno("Beenden", "Die Aufnahme läuft noch. Wirklich beenden?"):
                self.stop_recording()
                self.root.destroy()
        else:
            self.root.destroy()


if __name__ == "__main__":
    # Versuche, sounddevice zu optimieren
    try:
        sd.default.latency = (settings.DEVICE_TIMEOUT, settings.DEVICE_TIMEOUT)
        sd.default.dtype = 'float32'
        sd.default.channels = 2
        sd.default.samplerate = settings.SAMPLE_RATE
        print("✅ sounddevice-Konfiguration optimiert")
    except Exception as e:
        print(f"⚠️ Warnung: Konnte sounddevice nicht optimieren: {e}")

    # Hauptanwendung starten
    root = tk.Tk()
    app = ATAAudioApplication(root)
    root.mainloop()