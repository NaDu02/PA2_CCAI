# audio/processor.py
"""
Audio-Verarbeitungsklasse für die ATA Audio-Aufnahme
"""
import os
import time
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from config import settings

# Import basierend auf Konfiguration
if settings.USE_WHISPERX_API:
    from .whisperx_processor import WhisperXProcessor as AudioTranscriber
else:
    from .diarization_processor import DiarizationProcessor as AudioTranscriber


class AudioProcessor:
    """Audio-Verarbeitungsklasse für verbesserte Stabilität und Synchronisation."""

    def __init__(self, system_device, mic_device, system_channels, mic_channels, logger=None):
        self.system_device = system_device
        self.mic_device = mic_device
        self.system_channels = system_channels
        self.mic_channels = mic_channels
        self.logger = logger

        self.system_buffer = []
        self.mic_buffer = []
        self.output_buffer = []

        self.system_volume = 1.0
        self.mic_volume = 1.0

        self.buffer_lock = threading.Lock()
        self.system_stream = None
        self.mic_stream = None

        self.output_file = None
        self.is_recording = False
        self.logger = logger

        # Speaker Diarization
        self.diarizer = AudioTranscriber(logger=logger) if settings.ENABLE_SPEAKER_DIARIZATION else None
        self.speaker_segments = []
        self.on_diarization_complete = None  # Callback für GUI

    def set_volumes(self, system_volume, mic_volume):
        """Setzt die Lautstärke für System und Mikrofon."""
        self.system_volume = system_volume
        self.mic_volume = mic_volume

    def system_callback(self, indata, frames, time, status):
        """Callback für System-Audio."""
        if status and self.logger:
            self.logger.log_message(f"System-Status: {status}", "WARNING")

        with self.buffer_lock:
            self.system_buffer.append(indata.copy())
            self._mix_if_possible()

    def mic_callback(self, indata, frames, time, status):
        """Callback für Mikrofon-Audio."""
        if status and self.logger:
            self.logger.log_message(f"Mikrofon-Status: {status}", "WARNING")

        with self.buffer_lock:
            self.mic_buffer.append(indata.copy())
            self._mix_if_possible()

    def _mix_if_possible(self):
        """Mischt Audio, wenn in beiden Puffern Daten vorhanden sind."""
        while self.system_buffer and self.mic_buffer:
            system_data = self.system_buffer.pop(0)
            mic_data = self.mic_buffer.pop(0)

            # Preserve original stereo quality for system audio
            try:
                # Make sure system audio maintains stereo format
                if len(system_data.shape) < 2 or system_data.shape[1] < 2:
                    # If somehow system audio is mono, convert to stereo
                    system_data = np.column_stack((system_data, system_data))

                # Handle microphone conversion to appropriate format
                if self.mic_channels == 1:
                    # Properly expand mono mic to stereo
                    if len(mic_data.shape) == 1:
                        mic_data = np.column_stack((mic_data, mic_data))
                    elif len(mic_data.shape) == 2 and mic_data.shape[1] == 1:
                        mic_data = np.column_stack((mic_data[:, 0], mic_data[:, 0]))

                # Ensure both arrays are the same length before mixing
                min_length = min(len(system_data), len(mic_data))
                system_part = system_data[:min_length] * self.system_volume
                mic_part = mic_data[:min_length] * self.mic_volume

                # Ensure both have the same shape
                if system_part.shape[1] == 2 and (len(mic_part.shape) == 1 or mic_part.shape[1] == 1):
                    # Convert mic to stereo if needed
                    if len(mic_part.shape) == 1:
                        mic_part = np.column_stack((mic_part, mic_part))
                    else:
                        mic_part = np.column_stack((mic_part[:, 0], mic_part[:, 0]))

                # Mix only if shapes match
                if system_part.shape == mic_part.shape:
                    mixed = system_part + mic_part
                    # Avoid clipping while preserving stereo field
                    max_val = np.max(np.abs(mixed))
                    if max_val > 1.0:
                        mixed = mixed / max_val * 0.9

                    self.output_buffer.append(mixed)
                else:
                    # If mixing fails, at least preserve the stereo system audio
                    self.output_buffer.append(system_part)

            except Exception as e:
                if self.logger:
                    self.logger.log_message(f"Fehler beim Audio-Mixing: {e}", "WARNING")
                # Fallback: just use system audio with original stereo preserved
                try:
                    self.output_buffer.append(system_data * self.system_volume)
                except Exception as ex:
                    if self.logger:
                        self.logger.log_message(f"Kritischer Audio-Fehler: {ex}", "ERROR")

    def start(self, output_file):
        """Startet die Audio-Aufnahme mit verbesserter Audioqualität."""
        self.output_file = output_file
        self.is_recording = True

        # Puffer leeren
        self.system_buffer = []
        self.mic_buffer = []
        self.output_buffer = []

        # Ausgabedatei vorbereiten
        if os.path.exists(output_file):
            os.remove(output_file)

        # Soundfile mit höchster Qualität öffnen
        self.sf_file = sf.SoundFile(
            output_file,
            mode='w',
            samplerate=settings.SAMPLE_RATE,
            channels=2,  # Immer Stereo-Ausgabe
            format='WAV',
            subtype='FLOAT'  # Explizit höchste Qualität verwenden
        )

        # Debug-Informationen loggen
        if self.logger:
            self.logger.log_message(f"Starte Aufnahme: System ({self.system_device}: {self.system_channels}ch), "
                                    f"Mic ({self.mic_device}: {self.mic_channels}ch)", "INFO")

        # Streams mit expliziten Qualitätseinstellungen
        self.system_stream = sd.InputStream(
            device=self.system_device,
            channels=self.system_channels,
            callback=self.system_callback,
            blocksize=settings.BUFFER_SIZE,
            samplerate=settings.SAMPLE_RATE,
            latency=settings.LATENCY,
            dtype='float32'  # Explizit Datentyp angeben
        )

        self.mic_stream = sd.InputStream(
            device=self.mic_device,
            channels=self.mic_channels,
            callback=self.mic_callback,
            blocksize=settings.BUFFER_SIZE,
            samplerate=settings.SAMPLE_RATE,
            latency=settings.LATENCY,
            dtype='float32'
        )

        # Streams starten
        self.system_stream.start()
        self.mic_stream.start()

        # Writer-Thread starten
        self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.writer_thread.start()

        if self.logger:
            self.logger.log_message("Audio-Aufnahme gestartet mit optimierten Einstellungen", "SUCCESS")

    def _writer_loop(self):
        """Schreibt gemischte Audiodaten in die Datei."""
        try:
            while self.is_recording or self.output_buffer:
                data_to_write = []

                with self.buffer_lock:
                    chunks_to_process = min(10, len(self.output_buffer))
                    if chunks_to_process > 0:
                        data_to_write = self.output_buffer[:chunks_to_process]
                        self.output_buffer = self.output_buffer[chunks_to_process:]

                for chunk in data_to_write:
                    # Stelle sicher, dass wir Stereo-Audio schreiben
                    if len(chunk.shape) == 1 or chunk.shape[1] == 1:
                        if len(chunk.shape) == 1:
                            stereo_chunk = np.column_stack((chunk, chunk))
                        else:
                            stereo_chunk = np.column_stack((chunk[:, 0], chunk[:, 0]))
                        self.sf_file.write(stereo_chunk)
                    else:
                        self.sf_file.write(chunk)

                time.sleep(0.01)

            self.sf_file.close()
            if self.logger:
                self.logger.log_message(f"Datei gespeichert: {self.output_file}", "SUCCESS")

        except Exception as e:
            if self.logger:
                self.logger.log_message(f"Fehler im Writer-Thread: {e}", "ERROR")

    def stop(self):
        """Stoppt die Audio-Aufnahme und führt optional Speaker Diarization durch."""
        self.is_recording = False

        # Streams stoppen
        if self.system_stream:
            self.system_stream.stop()
            self.system_stream.close()

        if self.mic_stream:
            self.mic_stream.stop()
            self.mic_stream.close()

        # Auf Writer-Thread warten
        if hasattr(self, 'writer_thread') and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=5)

        if self.logger:
            self.logger.log_message("Audio-Aufnahme gestoppt", "INFO")

        # Speaker Diarization durchführen
        if self.diarizer and os.path.exists(self.output_file):
            threading.Thread(target=self._perform_diarization, daemon=True).start()

    def _perform_diarization(self):
        """Führt die Speaker Diarization in einem separaten Thread durch"""
        try:
            if self.logger:
                self.logger.log_message("Starte Sprechererkennung...", "INFO")

            # Kurz warten bis die Datei vollständig geschrieben ist
            time.sleep(1)

            # Prüfe, ob die Datei existiert und nicht leer ist
            if not os.path.exists(self.output_file):
                if self.logger:
                    self.logger.log_message(f"Audio-Datei nicht gefunden: {self.output_file}", "ERROR")
                return

            file_size = os.path.getsize(self.output_file)
            if file_size == 0:
                if self.logger:
                    self.logger.log_message("Audio-Datei ist leer - keine Sprechererkennung möglich", "WARNING")
                return

            if self.logger:
                self.logger.log_message(f"Verarbeite Audio-Datei: {file_size} Bytes", "INFO")

            # Diarization mit Transkription durchführen
            result = self.diarizer.process_complete_audio(self.output_file)

            # Prüfe das Ergebnis
            if not result:
                if self.logger:
                    self.logger.log_message("Keine Ergebnisse von der Sprechererkennung erhalten", "WARNING")
                return

            self.speaker_segments = result.get('segments', [])

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
            elif self.logger:
                # Auch wenn keine Segmente gefunden wurden, zeige die Transkription
                if 'transcription' in result or 'full_text' in result:
                    transcription = result.get('transcription', result.get('full_text', ''))
                    if transcription:
                        self.logger.log_message(f"Transkription (ohne Sprecher): {transcription}", "INFO")
                    else:
                        self.logger.log_message("Keine Transkription erhalten", "WARNING")
                else:
                    self.logger.log_message("Keine Sprecher-Segmente und keine Transkription erhalten", "WARNING")

            # GUI benachrichtigen (auch bei leeren Ergebnissen)
            if self.on_diarization_complete:
                self.on_diarization_complete(result)

        except Exception as e:
            if self.logger:
                self.logger.log_message(f"Fehler bei Sprechererkennung: {e}", "ERROR")
                import traceback
                traceback.print_exc()

            # Auch bei Fehler die GUI benachrichtigen mit einem Fallback-Ergebnis
            if self.on_diarization_complete:
                fallback_result = {
                    'full_text': f"Fehler bei der Sprechererkennung: {str(e)}",
                    'labeled_text': "",
                    'segments': [],
                    'transcription': f"Fehler bei der Sprechererkennung: {str(e)}"
                }
                self.on_diarization_complete(fallback_result)