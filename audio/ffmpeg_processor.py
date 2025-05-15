# audio/ffmpeg_processor.py
"""
FFmpeg-based Audio-Verarbeitungsklasse für die ATA Audio-Aufnahme
Verwendet Subprozesse statt direkter Audio-Streams für bessere Audioqualität
"""
import os
import time
import threading
import subprocess
import tempfile
import shutil
import sounddevice as sd
from config import settings

# Import basierend auf Konfiguration
# Prüfe erst, ob USE_WHISPERX existiert, sonst verwende USE_WHISPERX_API
use_whisperx = getattr(settings, 'USE_WHISPERX', False) or getattr(settings, 'USE_WHISPERX_API', False)

if use_whisperx:
    try:
        from .whisperx_processor import WhisperXProcessor as AudioTranscriber
    except ImportError:
        from .diarization_processor import DiarizationProcessor as AudioTranscriber
else:
    from .diarization_processor import DiarizationProcessor as AudioTranscriber


class FFmpegAudioProcessor:
    """Audio-Verarbeitungsklasse basierend auf FFmpeg für höchste Audioqualität."""

    def __init__(self, system_device, mic_device, system_channels, mic_channels, logger=None):
        self.system_device = system_device
        self.mic_device = mic_device
        self.system_channels = system_channels
        self.mic_channels = mic_channels
        self.logger = logger

        self.system_volume = 1.0
        self.mic_volume = 1.0

        self.output_file = None
        self.is_recording = False
        self.processes = []
        self.temp_dir = None
        self.input_format = None

        # Speaker Diarization - verwende die korrekte Einstellung
        enable_diarization = getattr(settings, 'ENABLE_SPEAKER_DIARIZATION', False)
        self.diarizer = AudioTranscriber(logger=logger) if enable_diarization else None
        self.speaker_segments = []
        self.on_diarization_complete = None  # Callback für GUI

        # Überprüfe, ob FFmpeg installiert ist und bestimme das beste Input-Format
        self._check_and_configure_ffmpeg()

    def _check_and_configure_ffmpeg(self):
        """Überprüft FFmpeg und konfiguriert das beste verfügbare Input-Format"""
        try:
            # Basis FFmpeg-Check
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            # Teste verfügbare Input-Formate
            if self._test_avfoundation():
                self.input_format = 'avfoundation'
                if self.logger:
                    self.logger.log_message("✅ FFmpeg mit AVFoundation konfiguriert", "SUCCESS")
            else:
                # Fallback-Formate testen
                self._configure_fallback_format()

        except (subprocess.SubprocessError, FileNotFoundError):
            if self.logger:
                self.logger.log_message(
                    "❌ FFmpeg nicht gefunden! Bitte installieren Sie FFmpeg mit 'brew install ffmpeg'", "ERROR")
            raise RuntimeError("FFmpeg ist erforderlich, aber nicht installiert")

    def _test_avfoundation(self):
        """Testet, ob AVFoundation verfügbar ist"""
        try:
            # Teste AVFoundation mit einem schnellen Check
            cmd = ['ffmpeg', '-f', 'avfoundation', '-list_devices', 'true', '-i', '']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            # Prüfe, ob BlackHole in der Device-Liste erscheint
            if 'BlackHole' in result.stderr:
                return True
            else:
                if self.logger:
                    self.logger.log_message("⚠️ AVFoundation verfügbar, aber BlackHole nicht erkannt", "WARNING")
                return True  # AVFoundation ist verfügbar, auch wenn BlackHole nicht gelistet ist

        except subprocess.TimeoutExpired:
            if self.logger:
                self.logger.log_message("⚠️ AVFoundation-Test timeout", "WARNING")
            return False
        except Exception as e:
            if self.logger:
                self.logger.log_message(f"⚠️ AVFoundation-Test fehlgeschlagen: {e}", "WARNING")
            return False

    def _configure_fallback_format(self):
        """Konfiguriert Fallback-Input-Format falls AVFoundation nicht verfügbar"""
        if self.logger:
            self.logger.log_message("⚠️ AVFoundation nicht optimal verfügbar, teste Alternativen...", "WARNING")

        # Teste alternative Formate
        formats_to_test = ['coreaudio', 'pulse']

        for fmt in formats_to_test:
            try:
                cmd = ['ffmpeg', '-f', fmt, '-list_devices', 'true', '-i', '']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    self.input_format = fmt
                    if self.logger:
                        self.logger.log_message(f"✅ Verwende {fmt} als Audio-Input-Format", "INFO")
                    return
            except:
                continue

        # Wenn alle Formate fehlschlagen, verwende trotzdem AVFoundation
        self.input_format = 'avfoundation'
        if self.logger:
            self.logger.log_message("⚠️ Fallback auf AVFoundation (könnte instabil sein)", "WARNING")

    def _get_device_names_for_format(self):
        """Ermittelt Gerätenamen basierend auf dem Input-Format"""
        devices = sd.query_devices()

        if self.input_format == 'avfoundation':
            # AVFoundation-Syntax: verwende Gerätenamen
            blackhole_name = ":BlackHole 2ch"

            # Finde Mikrofon-Namen
            if self.mic_device is not None and self.mic_device < len(devices):
                mic_device_info = devices[self.mic_device]
                mic_name = f":{mic_device_info['name']}"
            else:
                mic_name = ":default"

        elif self.input_format == 'coreaudio':
            # CoreAudio-Syntax: verwende Geräte-IDs
            blackhole_name = str(self.system_device)
            mic_name = str(self.mic_device) if self.mic_device is not None else "default"

        else:
            # Fallback: Standard-Namen
            blackhole_name = "default"
            mic_name = "default"

        return blackhole_name, mic_name

    def set_volumes(self, system_volume, mic_volume):
        """Setzt die Lautstärke für System und Mikrofon."""
        self.system_volume = system_volume
        self.mic_volume = mic_volume

    def start(self, output_file):
        """Startet die Audio-Aufnahme über FFmpeg-Subprozesse."""
        self.output_file = output_file
        self.is_recording = True
        self.processes = []

        # Temporäres Verzeichnis für Zwischendateien erstellen
        self.temp_dir = tempfile.mkdtemp()

        # Ausgabepfade für temporäre Dateien
        system_audio_file = os.path.join(self.temp_dir, "system_audio.wav")
        mic_audio_file = os.path.join(self.temp_dir, "mic_audio.wav")

        # Gerätenamen für FFmpeg ermitteln
        blackhole_name, mic_name = self._get_device_names_for_format()

        if self.logger:
            self.logger.log_message(
                f"🎵 Starte Aufnahme mit {self.input_format}: System({blackhole_name}), Mic({mic_name})",
                "INFO"
            )

        # System-Audio aufnehmen (BlackHole)
        system_cmd = [
            "ffmpeg", "-y",  # Überschreiben ohne Nachfrage
            "-f", self.input_format,
            "-i", blackhole_name,
            "-c:a", "pcm_f32le",  # Hochqualitatives Audioformat
            "-ar", str(settings.SAMPLE_RATE),
            "-ac", str(self.system_channels),
            system_audio_file
        ]

        # Mikrofon aufnehmen
        mic_cmd = [
            "ffmpeg", "-y",  # Überschreiben ohne Nachfrage
            "-f", self.input_format,
            "-i", mic_name,
            "-c:a", "pcm_f32le",
            "-ar", str(settings.SAMPLE_RATE),
            "-ac", str(self.mic_channels),
            mic_audio_file
        ]

        # Starte Prozesse
        try:
            if self.logger:
                self.logger.log_message("🚀 Starte FFmpeg-Prozesse...", "INFO")

            self.processes = [
                subprocess.Popen(system_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE),
                subprocess.Popen(mic_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ]

            if self.logger:
                self.logger.log_message("✅ Audio-Aufnahme gestartet (hochqualitativ, keine Verluste)", "SUCCESS")

        except Exception as e:
            if self.logger:
                self.logger.log_message(f"❌ Fehler beim Starten der FFmpeg-Aufnahme: {e}", "ERROR")
            self.cleanup()
            raise

    def stop(self):
        """Stoppt die Audio-Aufnahme und führt optional Speaker Diarization durch."""
        if not self.is_recording:
            return

        self.is_recording = False

        if self.logger:
            self.logger.log_message("⏹️ Stoppe Aufnahme und beende FFmpeg-Prozesse...", "INFO")

        # Stoppe alle FFmpeg-Prozesse sanft mit SIGTERM
        for proc in self.processes:
            proc.terminate()

        # Warte auf sauberes Beenden
        for proc in self.processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if self.logger:
                    self.logger.log_message("⚠️ FFmpeg-Prozess reagiert nicht, erzwinge Beendigung...", "WARNING")
                proc.kill()
                proc.wait()

        if self.logger:
            self.logger.log_message("✅ FFmpeg-Prozesse beendet, mische Audio...", "INFO")

        # Warte kurz, um sicherzustellen, dass die Dateien vollständig geschrieben wurden
        time.sleep(0.5)

        # Temporäre Dateipfade
        system_audio_file = os.path.join(self.temp_dir, "system_audio.wav")
        mic_audio_file = os.path.join(self.temp_dir, "mic_audio.wav")

        # Prüfe, ob beide Dateien existieren und nicht leer sind
        files_ok = True
        for file_path, name in [(system_audio_file, "System-Audio"), (mic_audio_file, "Mikrofon-Audio")]:
            if not os.path.exists(file_path):
                if self.logger:
                    self.logger.log_message(f"❌ {name}-Datei nicht gefunden: {file_path}", "ERROR")
                files_ok = False
            elif os.path.getsize(file_path) == 0:
                if self.logger:
                    self.logger.log_message(f"❌ {name}-Datei ist leer: {file_path}", "ERROR")
                files_ok = False
            else:
                file_size = os.path.getsize(file_path) / 1024  # KB
                if self.logger:
                    self.logger.log_message(f"✅ {name}: {file_size:.1f} KB", "INFO")

        if not files_ok:
            if self.logger:
                self.logger.log_message("❌ Audio-Aufnahme unvollständig!", "ERROR")
            self.cleanup()
            return

        # Mische die Audiodateien mit FFmpeg
        mix_cmd = [
            "ffmpeg", "-y",  # Überschreiben ohne Nachfrage
            "-i", system_audio_file,
            "-i", mic_audio_file,
            "-filter_complex",
            f"[0]volume={self.system_volume}[a0];[1]volume={self.mic_volume}[a1];[a0][a1]amix=inputs=2:duration=longest[out]",
            "-map", "[out]",
            "-c:a", "pcm_f32le",  # Hochqualitatives Audioformat beibehalten
            "-ar", str(settings.SAMPLE_RATE),
            "-ac", "2",  # Endgültige Ausgabe ist immer Stereo
            self.output_file
        ]

        try:
            if self.logger:
                self.logger.log_message("🔄 Mische Audio-Kanäle...", "INFO")

            result = subprocess.run(mix_cmd, check=True, capture_output=True, text=True)

            # Prüfe das Ergebnis
            if os.path.exists(self.output_file):
                file_size = os.path.getsize(self.output_file) / (1024 * 1024)  # MB
                if self.logger:
                    self.logger.log_message(f"✅ Datei gespeichert: {self.output_file} ({file_size:.2f} MB)", "SUCCESS")
            else:
                if self.logger:
                    self.logger.log_message("❌ Ausgabedatei wurde nicht erstellt!", "ERROR")

            # Räume temporäre Dateien auf
            self.cleanup()

            # Speaker Diarization durchführen
            if self.diarizer and os.path.exists(self.output_file):
                if self.logger:
                    self.logger.log_message("🎙️ Starte Sprechererkennung...", "INFO")
                threading.Thread(target=self._perform_diarization, daemon=True).start()

        except subprocess.CalledProcessError as e:
            if self.logger:
                self.logger.log_message(f"❌ Fehler beim Mischen der Audiodateien: {e}", "ERROR")
                if e.stderr:
                    self.logger.log_message(f"FFmpeg Fehler: {e.stderr}", "ERROR")
            self.cleanup()

    def cleanup(self):
        """Bereinigt temporäre Dateien und Verzeichnisse."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
                if self.logger:
                    self.logger.log_message("🧹 Temporäre Dateien aufgeräumt", "INFO")
            except Exception as e:
                if self.logger:
                    self.logger.log_message(f"⚠️ Fehler beim Aufräumen temporärer Dateien: {e}", "WARNING")

    def _perform_diarization(self):
        """Führt die Speaker Diarization in einem separaten Thread durch"""
        try:
            if self.logger:
                self.logger.log_message("🎯 Analysiere Sprechersegmente...", "INFO")

            # Diarization mit Transkription durchführen
            result = self.diarizer.process_complete_audio(self.output_file)
            self.speaker_segments = result['segments']

            if self.logger and self.speaker_segments:
                # Sprecher-Statistiken berechnen und anzeigen
                speakers = set(seg['speaker'] for seg in self.speaker_segments)
                num_speakers = len(speakers)
                self.logger.log_message(f"🎤 Erkannte Sprecher: {num_speakers}", "SUCCESS")

                # Statistiken pro Sprecher
                total_duration = sum(seg['duration'] for seg in self.speaker_segments)

                for speaker in speakers:
                    speaker_segs = [seg for seg in self.speaker_segments if seg['speaker'] == speaker]
                    speaker_duration = sum(seg['duration'] for seg in speaker_segs)
                    speaker_percentage = (speaker_duration / total_duration) * 100 if total_duration > 0 else 0
                    self.logger.log_message(f"  {speaker}: {speaker_duration:.1f}s ({speaker_percentage:.1f}%)", "INFO")

                    # Transkription pro Sprecher zeigen (max. 2 Beispiele)
                    examples = [seg['text'] for seg in speaker_segs if seg.get('text')][:2]
                    for i, example in enumerate(examples):
                        if example and len(example.strip()) > 0:
                            # Kürze lange Beispiele
                            display_text = example[:100] + "..." if len(example) > 100 else example
                            self.logger.log_message(f"    └─ \"{display_text}\"", "INFO")

            # GUI benachrichtigen
            if self.on_diarization_complete:
                self.on_diarization_complete(result)

        except Exception as e:
            if self.logger:
                self.logger.log_message(f"❌ Fehler bei Sprechererkennung: {e}", "ERROR")
                import traceback
                traceback.print_exc()