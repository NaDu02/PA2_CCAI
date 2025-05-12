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
from config import settings

# Import basierend auf Konfiguration
if settings.USE_WHISPERX:
    from .whisperx_processor import WhisperXProcessor as AudioTranscriber
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

        # Speaker Diarization
        self.diarizer = AudioTranscriber(logger=logger) if settings.ENABLE_SPEAKER_DIARIZATION else None
        self.speaker_segments = []
        self.on_diarization_complete = None  # Callback für GUI

        # Überprüfe, ob FFmpeg installiert ist
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Überprüft, ob FFmpeg installiert ist"""
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if self.logger:
                self.logger.log_message("FFmpeg gefunden, bereit für hochqualitative Audioaufnahme", "INFO")
        except (subprocess.SubprocessError, FileNotFoundError):
            if self.logger:
                self.logger.log_message(
                    "FFmpeg nicht gefunden! Bitte installieren Sie FFmpeg mit 'brew install ffmpeg'", "ERROR")
            raise RuntimeError("FFmpeg ist erforderlich, aber nicht installiert")

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

        # Konvertiere sounddevice-Geräteindex zu FFmpeg-Gerätenamen
        import sounddevice as sd
        devices = sd.query_devices()

        # Gerätenamen für FFmpeg finden
        blackhole_name = None
        mic_name = None

        for device in devices:
            if device['index'] == self.system_device:
                blackhole_name = f":BlackHole 2ch"  # AVFoundation name
            if device['index'] == self.mic_device:
                mic_name = f":{device['name']}"  # AVFoundation name

        if not blackhole_name:
            blackhole_name = ":BlackHole 2ch"  # Fallback

        if not mic_name:
            mic_name = ":default"  # Fallback zum Standard-Mikrofon

        if self.logger:
            self.logger.log_message(f"Starte Hochqualitäts-Aufnahme: System ({blackhole_name}), Mic ({mic_name})",
                                    "INFO")

        # System-Audio aufnehmen (BlackHole)
        system_cmd = [
            "ffmpeg",
            "-f", "avfoundation",
            "-i", blackhole_name,
            "-c:a", "pcm_f32le",  # Hochqualitatives Audioformat
            "-ar", str(settings.SAMPLE_RATE),
            "-ac", str(self.system_channels),
            "-y",  # Überschreiben, falls Datei existiert
            system_audio_file
        ]

        # Mikrofon aufnehmen
        mic_cmd = [
            "ffmpeg",
            "-f", "avfoundation",
            "-i", mic_name,
            "-c:a", "pcm_f32le",
            "-ar", str(settings.SAMPLE_RATE),
            "-ac", str(self.mic_channels),
            "-y",
            mic_audio_file
        ]

        # Starte Prozesse
        try:
            self.processes = [
                subprocess.Popen(system_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE),
                subprocess.Popen(mic_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ]

            if self.logger:
                self.logger.log_message("Audio-Aufnahme gestartet mit FFmpeg (keine Qualitätseinbußen)", "SUCCESS")

        except Exception as e:
            if self.logger:
                self.logger.log_message(f"Fehler beim Starten der FFmpeg-Aufnahme: {e}", "ERROR")
            self.cleanup()
            raise

    def stop(self):
        """Stoppt die Audio-Aufnahme und führt optional Speaker Diarization durch."""
        if not self.is_recording:
            return

        self.is_recording = False

        if self.logger:
            self.logger.log_message("Stoppe Aufnahme und beende FFmpeg-Prozesse...", "INFO")

        # Stoppe alle FFmpeg-Prozesse
        for proc in self.processes:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        if self.logger:
            self.logger.log_message("FFmpeg-Prozesse beendet, mische Audio...", "INFO")

        # Warte kurz, um sicherzustellen, dass die Dateien geschrieben wurden
        time.sleep(0.5)

        # Temporäre Dateipfade
        system_audio_file = os.path.join(self.temp_dir, "system_audio.wav")
        mic_audio_file = os.path.join(self.temp_dir, "mic_audio.wav")

        # Stelle sicher, dass beide Dateien existieren und nicht leer sind
        if not (os.path.exists(system_audio_file) and os.path.getsize(system_audio_file) > 0 and
                os.path.exists(mic_audio_file) and os.path.getsize(mic_audio_file) > 0):
            if self.logger:
                self.logger.log_message("Eine oder beide Audiodateien fehlen oder sind leer!", "ERROR")
            self.cleanup()
            return

        # Mische die Audiodateien mit FFmpeg
        mix_cmd = [
            "ffmpeg",
            "-i", system_audio_file,
            "-i", mic_audio_file,
            "-filter_complex", f"amix=inputs=2:duration=longest:weights={self.system_volume} {self.mic_volume}",
            "-c:a", "pcm_f32le",  # Hochqualitatives Audioformat beibehalten
            "-ar", str(settings.SAMPLE_RATE),
            "-ac", "2",  # Endgültige Ausgabe ist immer Stereo
            "-y",
            self.output_file
        ]

        try:
            subprocess.run(mix_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if self.logger:
                self.logger.log_message(f"Datei gespeichert: {self.output_file}", "SUCCESS")

            # Räume temporäre Dateien auf
            self.cleanup()

            # Speaker Diarization durchführen
            if self.diarizer and os.path.exists(self.output_file):
                threading.Thread(target=self._perform_diarization, daemon=True).start()

        except Exception as e:
            if self.logger:
                self.logger.log_message(f"Fehler beim Mischen der Audiodateien: {e}", "ERROR")
            self.cleanup()

    def cleanup(self):
        """Bereinigt temporäre Dateien und Verzeichnisse."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
            except Exception as e:
                if self.logger:
                    self.logger.log_message(f"Fehler beim Aufräumen temporärer Dateien: {e}", "WARNING")

    def _perform_diarization(self):
        """Führt die Speaker Diarization in einem separaten Thread durch"""
        try:
            if self.logger:
                self.logger.log_message("Starte Sprechererkennung...", "INFO")

            # Diarization mit Transkription durchführen
            result = self.diarizer.process_complete_audio(self.output_file)
            self.speaker_segments = result['segments']

            if self.logger and self.speaker_segments:
                # Sprecher-Statistiken berechnen und anzeigen
                speakers = set(seg['speaker'] for seg in self.speaker_segments)
                num_speakers = len(speakers)
                self.logger.log_message(f"Erkannte Sprecher: {num_speakers}", "SUCCESS")

                # Statistiken pro Sprecher
                speaker_stats = {}
                total_duration = sum(seg['duration'] for seg in self.speaker_segments)

                for speaker in speakers:
                    speaker_segs = [seg for seg in self.speaker_segments if seg['speaker'] == speaker]
                    speaker_duration = sum(seg['duration'] for seg in speaker_segs)
                    speaker_percentage = (speaker_duration / total_duration) * 100 if total_duration > 0 else 0
                    self.logger.log_message(f"{speaker}: {speaker_duration:.1f}s ({speaker_percentage:.1f}%)", "INFO")

                    # Transkription pro Sprecher zeigen (max. 3 Beispiele)
                    examples = [seg['text'] for seg in speaker_segs if seg.get('text')][:3]
                    if examples:
                        for i, example in enumerate(examples):
                            if example:  # Leere Beispiele überspringen
                                self.logger.log_message(f"  Beispiel {i + 1}: {example}", "INFO")

            # GUI benachrichtigen
            if self.on_diarization_complete:
                self.on_diarization_complete(result)

        except Exception as e:
            if self.logger:
                self.logger.log_message(f"Fehler bei Sprechererkennung: {e}", "ERROR")
                import traceback
                traceback.print_exc()