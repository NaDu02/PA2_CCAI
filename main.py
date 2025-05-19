# main.py
"""
Hauptprogramm für die ATA Audio-Aufnahme mit verbessertem WhisperX API Support
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
import sounddevice as sd
import numpy as np
import requests
import traceback
import json

# Unterdrücken von IMK-Meldungen in macOS
os.environ['TK_SILENCE_DEPRECATION'] = '1'

# Lokale Module importieren
from config import settings
from utils.logger import Logger
from audio.device_manager import DeviceManager
from audio.processor import AudioProcessor
from audio.summarization_client import summarization_client
from gui.summary_widget import SummaryWidget
from utils.service_health_monitor import ServiceHealthMonitor


try:
    from audio.ffmpeg_processor import FFmpegAudioProcessor
except ImportError:
    FFmpegAudioProcessor = None
from gui.dialogs import DeviceSelectionDialog, HelpDialog
from gui.components import SpeakerTimelineWidget, TranscriptionWidget


class ATAAudioApplication:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{settings.APP_NAME} v{settings.APP_VERSION} (macOS)")
        self.root.geometry("1300x800")  # Größe des Hauptfensters
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Instanzvariablen
        self.logger = Logger()
        self.device_manager = DeviceManager(self.logger)
        self.summarization_client = summarization_client
        self.summarization_client.logger = self.logger
        self.audio_processor = None
        self.recording = False
        self.service_monitor = ServiceHealthMonitor(logger=self.logger)

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

        # Statusanzeige - verbessertes Layout
        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.status_label = tk.Label(status_frame, text="Status: Initialisierung...", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # API Status Anzeige
        self.api_status_label = tk.Label(status_frame, text="", anchor=tk.E, fg="blue")
        self.api_status_label.pack(side=tk.RIGHT, padx=(10, 0))

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

        # Visuelle Statusmeldung für die Aufnahme
        self.recording_status_label = tk.Label(button_frame, text="", font=('Segoe UI', 10, 'bold'))
        self.recording_status_label.pack(side=tk.LEFT, padx=10)

        self.recording_status_label = tk.Label(button_frame, text="", font=('Segoe UI', 10, 'bold'))
        self.recording_status_label.pack(side=tk.LEFT, padx=10)

        self.devices_button = tk.Button(button_frame, text="Geräteauswahl", command=self.show_device_selection,
                                        width=15)
        self.devices_button.pack(side=tk.LEFT, padx=5)

        self.help_button = tk.Button(button_frame, text="Hilfe", command=self.show_help, width=10)
        self.help_button.pack(side=tk.RIGHT, padx=5)

        # WhisperX API Test Button
        self.api_test_button = tk.Button(button_frame, text="Verbindung prüfen", command=self.test_whisperx_api, width=10)
        self.api_test_button.pack(side=tk.RIGHT, padx=5)

        # Diarization Toggle
        self.diarization_var = tk.BooleanVar(value=settings.ENABLE_SPEAKER_DIARIZATION)
        self.diarization_check = tk.Checkbutton(button_frame, text="Sprechererkennung",
                                                variable=self.diarization_var,
                                                command=self.toggle_diarization)
        self.diarization_check.pack(side=tk.RIGHT, padx=5)

        # SUMMARIZATION TOGGLE BUTTON
        self.summarization_var = tk.BooleanVar(value=True)  # Standardmäßig aktiviert
        self.summarization_check = tk.Checkbutton(button_frame, text="Zusammenfassung",
                                                  variable=self.summarization_var,
                                                  command=self.toggle_summarization)
        self.summarization_check.pack(side=tk.RIGHT, padx=5)

        # Log-Bereich
        log_frame = tk.LabelFrame(main_frame, text="Protokoll")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=30,  # Breiter
            height=3,  # Höher
            font=('Consolas', 11),  # Monospace-Schrift
            bg='#1e1e1e',  # Dunkler Hintergrund
            fg='#d4d4d4',  # Heller Text
            insertbackground='white',
            selectbackground='#0078d4'  # Auswahl-Farbe
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)

        # Speaker Timeline
        self.speaker_frame = tk.LabelFrame(main_frame, text="Sprecher-Timeline")
        self.speaker_frame.pack(fill=tk.X, pady=(10, 0))

        # Kleinere Timeline mit fester Höhe
        self.speaker_timeline = SpeakerTimelineWidget(self.speaker_frame, height=40)  # Verkleinert von 100 auf 60
        self.speaker_timeline.pack(fill=tk.X, padx=5, pady=2)  # Weniger Padding

        # Transkription mit Sprechern
        self.transcription_frame = tk.LabelFrame(main_frame, text="Transkription")
        self.transcription_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))  # Weniger Abstand oben

        self.transcription_widget = TranscriptionWidget(self.transcription_frame)
        self.transcription_widget.pack(fill=tk.BOTH, expand=True)

        # Summary Widget hinzufügen
        self.summary_frame = tk.LabelFrame(main_frame, text="📋 Zusammenfassung")
        self.summary_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))

        self.summary_widget = SummaryWidget(self.summary_frame)
        self.summary_widget.pack(fill=tk.BOTH, expand=True)

        # Logger konfigurieren
        self.logger.set_log_text_widget(self.log_text)

    def test_whisperx_api(self):
        """Testet alle drei API-Services: WhisperX, Summarization und Ollama"""
        if self.recording:
            messagebox.showwarning("Warnung", "Bitte stoppen Sie die Aufnahme vor dem API-Test.")
            return

        try:
            # Verwende den Service Monitor für umfassende Tests
            results = self.service_monitor.check_all_services(detailed=True)

            # Analysiere Ergebnisse
            summary = self.service_monitor.get_service_summary()
            healthy_count = summary["healthy_count"]
            total_count = summary["total_count"]

            # Aktualisiere UI basierend auf Ergebnissen
            self._update_service_status_ui(results, summary)

            # Zeige Docker-Commands wenn Services down sind
            if healthy_count < total_count:
                self._show_docker_help(results)

        except Exception as e:
            self.logger.log_message(f"Unerwarteter Fehler beim Service-Test: {e}", "ERROR")
            traceback.print_exc()

    def _check_api_status(self):
        """Prüft den Status aller APIs beim Startup"""
        try:
            # Verwende Service Monitor für automatische Checks
            results = self.service_monitor.check_all_services(detailed=False)
            summary = self.service_monitor.get_service_summary()

            # Aktualisiere UI
            self._update_service_status_ui(results, summary)

        except Exception as e:
            self.logger.log_message(f"Fehler bei automatischem API-Check: {e}", "ERROR")
            self.api_status_label.config(text="API: Check fehlgeschlagen", fg="red")

    def _update_service_status_ui(self, results: dict, summary: dict):
        """Aktualisiert die UI mit detaillierten Service-Status"""
        healthy_count = summary["healthy_count"]
        total_count = summary["total_count"]

        # Bestimme Gesamtstatus
        if healthy_count == total_count:
            status_text = f"APIs: Alle {total_count} Services OK"
            status_color = "green"
        elif healthy_count > 0:
            status_text = f"APIs: {healthy_count}/{total_count} Services OK"
            status_color = "orange"
        else:
            status_text = "APIs: Alle Services down"
            status_color = "red"

        # Aktualisiere API Status Label
        self.api_status_label.config(text=status_text, fg=status_color)

        # Detaillierte Logs für jeden Service
        self.logger.log_message("\n=== Detaillierter Service-Status ===", "INFO")
        for service_id, status in results.items():
            if status.healthy:
                self.logger.log_message(f"✅ {status.name}: Aktiv", "SUCCESS")

                # Service-spezifische Details loggen
                if status.details:
                    if service_id == "whisperx":
                        device = status.details.get("device", "unknown")
                        model_loaded = status.details.get("model_loaded", False)
                        gpu_memory = status.details.get("gpu_memory")
                        self.logger.log_message(
                            f"   Device: {device}, Model: {'OK' if model_loaded else 'Nicht geladen'}", "INFO")
                        if gpu_memory:
                            self.logger.log_message(f"   GPU Memory: {gpu_memory}MB", "INFO")


                    elif service_id == "summarization":
                        service_status = status.details.get("status", "unknown")
                        ollama_status = status.details.get("ollama_status", "unknown")
                        ollama_model = status.details.get("ollama_model", "unknown")
                        service_initialized = status.details.get("service_initialized", False)
                        self.logger.log_message(f"   Status: {service_status}", "INFO")
                        self.logger.log_message(f"   Ollama: {ollama_status} (Model: {ollama_model})", "INFO")
                        self.logger.log_message(f"   Initialisiert: {'Ja' if service_initialized else 'Nein'}", "INFO")
                        # Zeige positive Meldung wenn alles funktioniert
                        if ollama_status == "available" and service_initialized:
                            self.logger.log_message(f"   ✅ Service vollständig funktionsfähig", "SUCCESS")

                    elif service_id == "ollama":
                        model_count = status.details.get("model_count", 0)
                        available_models = status.details.get("available_models", [])
                        total_size_gb = round(status.details.get("total_size", 0) / (1024 ** 3), 1)
                        self.logger.log_message(f"   Verfügbare Modelle: {model_count}", "INFO")
                        self.logger.log_message(f"   Gesamtgröße: {total_size_gb}GB", "INFO")
                        if available_models:
                            models_str = ", ".join(available_models[:3])
                            if len(available_models) > 3:
                                models_str += f" (+{len(available_models) - 3} weitere)"
                            self.logger.log_message(f"   Modelle: {models_str}", "INFO")
            else:
                self.logger.log_message(f"❌ {status.name}: {status.error_message}", "ERROR")

    def _show_docker_help(self, results: dict):
        """Zeigt Docker-Befehle für fehlerhafte Services an"""
        self.logger.log_message("\n=== Docker-Hilfe für fehlerhafte Services ===", "INFO")

        failed_services = [s for s in results.values() if not s.healthy]

        if failed_services:
            self.logger.log_message("Mögliche Lösungsschritte:", "INFO")
            self.logger.log_message("", "INFO")

            # Service-spezifische Docker-Befehle
            docker_commands = self.service_monitor.get_docker_commands()

            self.logger.log_message("1. Status überprüfen:", "INFO")
            for cmd in docker_commands["status"]:
                self.logger.log_message(f"   {cmd}", "INFO")

            self.logger.log_message("", "INFO")
            self.logger.log_message("2. Services starten:", "INFO")
            for cmd in docker_commands["start"]:
                self.logger.log_message(f"   {cmd}", "INFO")

            self.logger.log_message("", "INFO")
            self.logger.log_message("3. Bei Problemen neu starten:", "INFO")
            for cmd in docker_commands["restart"]:
                self.logger.log_message(f"   {cmd}", "INFO")

            self.logger.log_message("", "INFO")
            self.logger.log_message("4. Logs prüfen:", "INFO")
            for cmd in docker_commands["logs"]:
                self.logger.log_message(f"   {cmd}", "INFO")

            # Spezifische Tipps für einzelne Services
            for service_id, status in results.items():
                if not status.healthy:
                    self._show_service_specific_help(service_id, status)

    def _show_service_specific_help(self, service_id: str, status):
        """Zeigt service-spezifische Hilfe an"""
        self.logger.log_message(f"\n--- Spezifische Hilfe für {status.name} ---", "INFO")

        if service_id == "whisperx":
            self.logger.log_message("WhisperX-spezifische Checks:", "INFO")
            self.logger.log_message("• Prüfen Sie ob CUDA/GPU verfügbar ist", "INFO")
            self.logger.log_message("• WhisperX Model könnte laden: docker logs whisperx-api", "INFO")
            self.logger.log_message("• Port 8500 verfügbar: lsof -i :8500", "INFO")

        elif service_id == "summarization":
            self.logger.log_message("Summarization-spezifische Checks:", "INFO")
            self.logger.log_message("• Service braucht Verbindung zu Ollama", "INFO")
            self.logger.log_message("• Port 8501 verfügbar: lsof -i :8501", "INFO")
            self.logger.log_message("• Überprüfen Sie Ollama-Verbindung im Service", "INFO")

        elif service_id == "ollama":
            self.logger.log_message("Ollama-spezifische Checks:", "INFO")
            self.logger.log_message("• Model downloaden: docker exec ollama ollama pull llama3.1:8b", "INFO")
            self.logger.log_message("• Verfügbarer Speicher für Models prüfen", "INFO")
            self.logger.log_message("• Port 11434 verfügbar: lsof -i :11434", "INFO")

    def initialize_application(self):
        """Initialisiert die Anwendung."""
        self.logger.log_message("=== ATA Audio-Aufnahme für macOS ===", "INFO")
        self.logger.log_message("Überprüfe Audio-Setup...", "INFO")

        blackhole_found, device_name = self.device_manager.check_blackhole()

        if blackhole_found:
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
            self.status_label.config(text="Status: Fehler beim Audio-Setup")

        # WhisperX-API prüfen, falls aktiviert
        if hasattr(settings, 'USE_WHISPERX_API') and settings.USE_WHISPERX_API:
            self.logger.log_message("Prüfe WhisperX-API...", "INFO")
            self.root.after(100, self._check_api_status)

        # Geräteauswahl nach kurzer Verzögerung anzeigen
        self.root.after(500, self.show_device_selection)

    def toggle_diarization(self):
        """Aktiviert/Deaktiviert die Sprechererkennung"""
        settings.ENABLE_SPEAKER_DIARIZATION = self.diarization_var.get()
        status = "aktiviert" if settings.ENABLE_SPEAKER_DIARIZATION else "deaktiviert"
        self.logger.log_message(f"Sprechererkennung {status}", "INFO")

    def toggle_summarization(self):
        """Aktiviert/Deaktiviert die Zusammenfassung"""
        # Prüfe Service-Status beim Aktivieren
        if self.summarization_var.get():
            if not self.summarization_client.check_service_health():
                self.summarization_var.set(False)
                messagebox.showwarning("Warnung", "Summarization Service ist nicht verfügbar!")
                return
            self.logger.log_message("Zusammenfassung aktiviert", "INFO")
        else:
            self.logger.log_message("Zusammenfassung deaktiviert", "INFO")

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

            # Status-Labels aktualisieren
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
            # Geräte prüfen
            if self.selected_loopback is None or self.selected_microphone is None:
                if messagebox.askyesno("Geräteauswahl",
                                       "Keine Audiogeräte ausgewählt. Möchten Sie jetzt Geräte auswählen?"):
                    self.show_device_selection()
                else:
                    return

            if self.selected_loopback is None or self.selected_microphone is None:
                self.logger.log_message("Keine Audiogeräte ausgewählt - Aufnahme abgebrochen", "ERROR")
                return

            # Status loggen
            self.logger.log_message(f"Starte Aufnahme mit WhisperX API: {getattr(settings, 'USE_WHISPERX_API', False)}",
                                    "INFO")
            if hasattr(settings, 'WHISPERX_API_URL'):
                self.logger.log_message(f"WhisperX-API URL: {settings.WHISPERX_API_URL}", "INFO")

            # Audio-Processor wählen
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

            self.recording_status_label.config(text="Aufnahme läuft...", fg="red")

            # Status mit API-Info
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
            self.summary_widget.clear()

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

            # UI aktualisieren
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.recording_status_label.config(text="Aufnahme erfolgreich!", fg="green")
            self.status_label.config(text="Status: Bereit")

            # Normale Transkription (wenn Diarization deaktiviert)
            if not settings.ENABLE_SPEAKER_DIARIZATION:
                try:
                    self.logger.log_message("Führe Transkription ohne Sprechererkennung durch...", "INFO")

                    # WhisperX API verwenden
                    if hasattr(settings, 'USE_WHISPERX_API') and settings.USE_WHISPERX_API:
                        # Verwende den WhisperXProcessor für Transkription
                        from audio.whisperx_processor import WhisperXProcessor
                        processor = WhisperXProcessor(logger=self.logger)

                        # Temporär Diarization deaktivieren
                        old_diarization = settings.WHISPERX_ENABLE_DIARIZATION
                        settings.WHISPERX_ENABLE_DIARIZATION = False

                        result = processor.process_complete_audio(settings.FILENAME)

                        # Diarization-Setting wiederherstellen
                        settings.WHISPERX_ENABLE_DIARIZATION = old_diarization

                        if result and result.get('full_text'):
                            transcription = result['full_text']
                            self.logger.log_message("📝 Transkription:\n" + transcription, "INFO")
                            self.transcription_widget.display_transcription({'full_text': transcription})
                        else:
                            self.logger.log_message("Keine Transkription erhalten", "WARNING")

                    else:
                        # Fallback für andere APIs
                        self.logger.log_message("Keine WhisperX API konfiguriert", "WARNING")

                except Exception as e:
                    self.logger.log_message(f"Transkription nicht möglich: {e}", "WARNING")
                    traceback.print_exc()

        except Exception as e:
            self.logger.log_message(f"Fehler beim Stoppen der Aufnahme: {e}", "ERROR")
            traceback.print_exc()
            messagebox.showerror("Fehler", f"Fehler beim Stoppen der Aufnahme: {e}")
            self.recording_status_label.config(text="Fehler beim Stoppen!", fg="red")

            # Trotzdem Status zurücksetzen
            self.recording = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.recording_status_label.config(text="Fehler bei Aufnahme!", fg="red")
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

            # Summarization durchführen
            if result and (result.get('segments') or result.get('full_text')):
                self.logger.log_message("Starte Zusammenfassung...", "INFO")
                threading.Thread(target=self._perform_summarization, args=(result,), daemon=True).start()

            # Log die Transkription auch
            if 'transcription' in result:
                self.logger.log_message("📝 Transkription:\n" + result['transcription'], "INFO")
            elif 'full_text' in result:
                self.logger.log_message("📝 Transkription:\n" + result['full_text'], "INFO")

        except Exception as e:
            self.logger.log_message(f"Fehler bei Diarization-Anzeige: {e}", "ERROR")
            traceback.print_exc()

    def _perform_summarization(self, transcript_result):
        """Führt die Zusammenfassung in einem separaten Thread durch"""
        try:
            # Prüfe erst, ob Service verfügbar ist
            if not self.summarization_client.check_service_health():
                self.logger.log_message("Summarization Service nicht verfügbar", "WARNING")
                return

            # Führe Zusammenfassung durch
            summary_result = self.summarization_client.summarize_conversation(transcript_result)

            if summary_result:
                # GUI im Hauptthread aktualisieren
                self.root.after(0, self._display_summary, summary_result)
            else:
                self.logger.log_message("Keine Zusammenfassung erhalten", "WARNING")

        except Exception as e:
            self.logger.log_message(f"Fehler bei Zusammenfassung: {e}", "ERROR")
            import traceback
            traceback.print_exc()

    def _display_summary(self, summary_result):
        """Zeigt die Zusammenfassung in der GUI an (läuft im Hauptthread)"""
        try:
            self.summary_widget.display_summary(summary_result)

            # Statistiken loggen
            if summary_result.get('todos'):
                todo_count = len(summary_result['todos'])
                self.logger.log_message(f"Zusammenfassung erstellt: {todo_count} Aufgaben gefunden", "SUCCESS")

            sentiment = summary_result.get('sentiment', 'neutral')
            self.logger.log_message(f"Gesprächsstimmung: {sentiment}", "INFO")

        except Exception as e:
            self.logger.log_message(f"Fehler bei Anzeige der Zusammenfassung: {e}", "ERROR")
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

    def reset_buttons(self):
        """Setzt die Button-Status zurück."""
        if self.recording:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.recording_status_label.config(text="Aufnahme läuft...", fg="red")
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.recording_status_label.config(text="")
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

    # sounddevice optimieren
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