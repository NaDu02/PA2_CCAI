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
from audio.device_manager import DeviceManager
# Geänderte Imports für Audio-Processing
from audio.processor import AudioProcessor

try:
    from audio.ffmpeg_processor import FFmpegAudioProcessor  # FFmpeg-Processor für bessere Audioqualität
except ImportError:
    FFmpegAudioProcessor = None

if settings.USE_WHISPERX:
    from audio.whisperx_processor import WhisperXProcessor
else:
    from audio.diarization_processor import DiarizationProcessor
from gui.dialogs import DeviceSelectionDialog, HelpDialog
from gui.components import SpeakerTimelineWidget, TranscriptionWidget
from tests.test_recording import TestRecording


class ATAAudioApplication:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{settings.APP_NAME} v{settings.APP_VERSION} (macOS)")
        self.root.geometry("900x700")
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

        # Diarization Toggle
        self.diarization_var = tk.BooleanVar(value=settings.ENABLE_SPEAKER_DIARIZATION)
        self.diarization_check = tk.Checkbutton(button_frame, text="Sprechererkennung",
                                                variable=self.diarization_var,
                                                command=self.toggle_diarization)
        self.diarization_check.pack(side=tk.RIGHT, padx=5)

        # WhisperX API Toggle (verbessert)
        if hasattr(settings, 'USE_WHISPERX_API'):
            self.whisperx_api_var = tk.BooleanVar(value=settings.USE_WHISPERX_API)
            self.whisperx_api_check = tk.Checkbutton(button_frame, text="WhisperX API",
                                                     variable=self.whisperx_api_var,
                                                     command=self.toggle_whisperx_api)
            self.whisperx_api_check.pack(side=tk.RIGHT, padx=5)

        # Log-Bereich
        log_frame = tk.LabelFrame(main_frame, text="Protokoll")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=80, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)

        # Speaker Timeline
        self.speaker_frame = tk.LabelFrame(main_frame, text="Sprecher-Timeline")
        self.speaker_frame.pack(fill=tk.X, pady=(10, 0))

        self.speaker_timeline = SpeakerTimelineWidget(self.speaker_frame)
        self.speaker_timeline.pack(fill=tk.X, padx=5, pady=5)

        # Transkription mit Sprechern
        self.transcription_frame = tk.LabelFrame(main_frame, text="Transkription")
        self.transcription_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.transcription_widget = TranscriptionWidget(self.transcription_frame)
        self.transcription_widget.pack(fill=tk.BOTH, expand=True)

        # Logger konfigurieren
        self.logger.set_log_text_widget(self.log_text)

    def toggle_whisperx_api(self):
        """Wechselt zwischen WhisperX API und lokaler Verarbeitung"""
        settings.USE_WHISPERX_API = self.whisperx_api_var.get()
        status = "aktiviert" if settings.USE_WHISPERX_API else "deaktiviert"
        self.logger.log_message(f"WhisperX API {status}", "INFO")

    def initialize_application(self):
        """Initialisiert die Anwendung."""
        self.logger.log_message("=== ATA Audio-Aufnahme für macOS ===", "INFO")
        self.logger.log_message("Überprüfe Audio-Setup...", "INFO")

        blackhole_found, device_name = self.device_manager.check_blackhole()

        if blackhole_found:
            # Check BlackHole configuration
            devices = sd.query_devices()
            blackhole_device = None
            for device in devices:
                if 'BlackHole' in device['name']:
                    blackhole_device = device
                    break

            if blackhole_device and blackhole_device.get('max_input_channels', 0) >= 2:
                self.logger.log_message(f"✅ Gefunden: Loopback-Device '{device_name}' mit Stereo-Unterstützung",
                                        "SUCCESS")
            else:
                self.logger.log_message(
                    f"⚠️ Warnung: BlackHole gefunden, aber möglicherweise nicht für Stereo konfiguriert", "WARNING")

            self.logger.log_message("Audio-Setup-Prüfung OK.", "INFO")
            self.status_label.config(text="Status: Bereit")
        else:
            self.logger.log_message("Kein BlackHole-Gerät gefunden.", "ERROR")
            self.logger.log_message("Audio-Setup unvollständig!", "WARNING")
            self.logger.log_message("Bitte stellen Sie sicher, dass BlackHole installiert und konfiguriert ist.",
                                    "INFO")
            self.status_label.config(text="Status: Fehler beim Audio-Setup")

        # WhisperX-API prüfen, falls aktiviert
        if hasattr(settings, 'USE_WHISPERX_API') and settings.USE_WHISPERX_API:
            try:
                # Teste Erreichbarkeit der WhisperX-API
                import requests
                health_url = settings.WHISPERX_API_URL.replace('/transcribe', '/health')
                try:
                    resp = requests.get(health_url, timeout=5)
                    if resp.ok:
                        self.logger.log_message(f"✅ WhisperX-API erreichbar: {settings.WHISPERX_API_URL}", "SUCCESS")
                    else:
                        self.logger.log_message(f"⚠️ WhisperX-API antwortet mit Fehler: {resp.status_code}", "WARNING")
                except requests.RequestException as e:
                    self.logger.log_message(f"⚠️ WhisperX-API nicht erreichbar: {e}", "WARNING")
            except ImportError:
                self.logger.log_message("⚠️ Requests-Modul nicht verfügbar", "WARNING")

        # Geräteauswahl nach kurzer Verzögerung anzeigen
        self.root.after(500, self.show_device_selection)

    def toggle_diarization(self):
        """Aktiviert/Deaktiviert die Sprechererkennung"""
        settings.ENABLE_SPEAKER_DIARIZATION = self.diarization_var.get()
        status = "aktiviert" if settings.ENABLE_SPEAKER_DIARIZATION else "deaktiviert"
        self.logger.log_message(f"Sprechererkennung {status}", "INFO")

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

            # WhisperX-Status loggen
            self.logger.log_message(f"Verwende WhisperX API: {getattr(settings, 'USE_WHISPERX_API', False)}", "INFO")
            if hasattr(settings, 'WHISPERX_API_URL'):
                self.logger.log_message(f"WhisperX-API URL: {settings.WHISPERX_API_URL}", "INFO")

            # Versuche zuerst FFmpeg zu verwenden für bessere Audioqualität
            if FFmpegAudioProcessor:
                try:
                    self.audio_processor = FFmpegAudioProcessor(
                        system_device=self.selected_loopback,
                        mic_device=self.selected_microphone,
                        system_channels=self.loopback_channels,
                        mic_channels=self.microphone_channels,
                        logger=self.logger
                    )
                    self.logger.log_message("Verwende FFmpeg für hochqualitative Audioaufnahme", "SUCCESS")
                except (ImportError, RuntimeError) as e:
                    self.logger.log_message(f"FFmpeg nicht verfügbar: {e}. Verwende Standard-Processor.", "WARNING")
                    self.audio_processor = None

            # Fallback auf Standard AudioProcessor
            if not self.audio_processor:
                self.audio_processor = AudioProcessor(
                    system_device=self.selected_loopback,
                    mic_device=self.selected_microphone,
                    system_channels=self.loopback_channels,
                    mic_channels=self.microphone_channels,
                    logger=self.logger
                )

            # Lautstärke setzen
            self.audio_processor.set_volumes(self.system_volume, self.mic_volume)

            # Callback für Diarization setzen
            self.audio_processor.on_diarization_complete = self.on_diarization_complete

            # Aufnahme starten
            self.audio_processor.start(settings.FILENAME)
            self.recording = True

            # UI aktualisieren
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

            # Status mit mehr Information
            api_info = ""
            if hasattr(settings, 'USE_WHISPERX_API') and settings.USE_WHISPERX_API:
                api_info = " (WhisperX API)"
            elif hasattr(settings, 'USE_WHISPERX') and settings.USE_WHISPERX:
                api_info = " (WhisperX lokal)"
            else:
                api_info = " (Standard API)"

            self.status_label.config(text=f"Status: Aufnahme läuft{api_info}")

            # Timeline und Transkription leeren
            self.speaker_timeline.canvas.delete("all")
            self.transcription_widget.text.delete(1.0, tk.END)

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

            # Normale Transkription (wenn Diarization deaktiviert)
            if not settings.ENABLE_SPEAKER_DIARIZATION:
                try:
                    # Prüfe, welche Transkriptions-Methode verwendet werden soll
                    if hasattr(settings, 'USE_WHISPERX_API') and settings.USE_WHISPERX_API:
                        # WhisperX-API für Transkription verwenden
                        self.logger.log_message("Transkribiere mit WhisperX-API...", "INFO")

                        with open(settings.FILENAME, "rb") as vf:
                            files = {"file": (settings.FILENAME, vf, "audio/wav")}
                            data = {
                                "language": settings.WHISPERX_LANGUAGE,
                                "compute_type": settings.WHISPERX_COMPUTE_TYPE,
                                "enable_diarization": "false"
                            }
                            resp = requests.post(settings.WHISPERX_API_URL, files=files, data=data,
                                                 timeout=settings.WHISPERX_TIMEOUT)

                        if resp.ok:
                            result = resp.json()
                            transcription = result.get("transcription", result.get("text", "—"))
                            self.logger.log_message("📝 Transkription:\n" + transcription, "INFO")
                            self.transcription_widget.display_transcription({'full_text': transcription})
                        else:
                            self.logger.log_message(f"WhisperX-API Transkriptions-Fehler: {resp.status_code}", "ERROR")

                    elif hasattr(settings, 'USE_WHISPERX') and settings.USE_WHISPERX:
                        # WhisperX lokal für Transkription verwenden
                        import whisperx
                        self.logger.log_message("Transkribiere mit WhisperX lokal...", "INFO")

                        import torch
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                        compute_type = "float16" if device == "cuda" else "int8"

                        model = whisperx.load_model(settings.WHISPERX_MODEL, device, compute_type=compute_type)
                        audio = whisperx.load_audio(settings.FILENAME)
                        result = model.transcribe(audio, batch_size=16)

                        transcription = ' '.join([segment['text'] for segment in result['segments']])
                        self.logger.log_message("📝 Transkription:\n" + transcription, "INFO")
                        self.transcription_widget.display_transcription({'full_text': transcription})

                    else:
                        # Standard-API für Transkription verwenden
                        self.logger.log_message("Transkribiere mit Standard-API...", "INFO")

                        with open(settings.FILENAME, "rb") as vf:
                            resp = requests.post(settings.API_URL, files={"file": (settings.FILENAME, vf, "audio/wav")})

                        if resp.ok:
                            transcription = resp.json().get("transcription", "—")
                            self.logger.log_message("📝 Transkription:\n" + transcription, "INFO")
                            self.transcription_widget.display_transcription({'full_text': transcription})
                        else:
                            self.logger.log_message(f"Standard-API Transkriptions-Fehler: {resp.status_code}", "ERROR")

                except Exception as e:
                    self.logger.log_message(f"Transkription nicht möglich: {e}", "WARNING")
                    traceback.print_exc()

        except Exception as e:
            self.logger.log_message(f"Fehler beim Stoppen der Aufnahme: {e}", "ERROR")
            traceback.print_exc()
            messagebox.showerror("Fehler", f"Fehler beim Stoppen der Aufnahme: {e}")

            # Trotzdem Status zurücksetzen
            self.recording = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Fehler aufgetreten")

    def on_diarization_complete(self, result):
        """Callback wenn die Diarization abgeschlossen ist"""
        try:
            # Timeline aktualisieren
            if 'segments' in result and result['segments']:
                total_duration = max(seg['end'] for seg in result['segments'])
                self.speaker_timeline.display_segments(result['segments'], total_duration)

                # Statistiken anzeigen
                speaker_stats = self.calculate_speaker_statistics(result['segments'])
                for speaker, stats in speaker_stats.items():
                    self.logger.log_message(
                        f"{speaker}: {stats['total_time']:.1f}s ({stats['percentage']:.1f}%)",
                        "INFO"
                    )

            # Transkription anzeigen
            self.transcription_widget.display_transcription(result)

            # Log die Transkription auch
            if 'transcription' in result:
                self.logger.log_message("📝 Transkription:\n" + result['transcription'], "INFO")
            elif 'full_text' in result:
                self.logger.log_message("📝 Transkription:\n" + result['full_text'], "INFO")

        except Exception as e:
            self.logger.log_message(f"Fehler bei Diarization-Anzeige: {e}", "ERROR")
            import traceback
            traceback.print_exc()

    def calculate_speaker_statistics(self, segments):
        """Berechnet Statistiken für jeden Sprecher"""
        stats = {}
        total_time = sum(seg['duration'] for seg in segments)

        for segment in segments:
            speaker = segment['speaker']
            if speaker not in stats:
                stats[speaker] = {'total_time': 0, 'count': 0}

            stats[speaker]['total_time'] += segment['duration']
            stats[speaker]['count'] += 1

        # Prozentsätze berechnen
        for speaker in stats:
            stats[speaker]['percentage'] = (stats[speaker]['total_time'] / total_time) * 100

        return stats

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
    # Python-Version überprüfen
    if sys.version_info < settings.REQUIRED_PYTHON_VERSION:
        print(f"Python {'.'.join(map(str, settings.REQUIRED_PYTHON_VERSION))} oder höher erforderlich!")
        sys.exit(1)

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