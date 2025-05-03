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
from config.settings import BUFFER_SIZE, SAMPLE_RATE, LATENCY


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

            # Mikrofon zu Stereo konvertieren, falls nötig
            if self.mic_channels == 1 and self.system_channels == 2:
                try:
                    if len(mic_data.shape) == 2 and mic_data.shape[1] == 1:
                        mic_data = np.column_stack((mic_data, mic_data))
                except Exception as e:
                    if self.logger:
                        self.logger.log_message(f"Fehler bei Stereo-Konvertierung: {e}", "WARNING")

            # Audio mischen
            try:
                if len(system_data.shape) == len(mic_data.shape):
                    if system_data.shape[1] != mic_data.shape[1]:
                        if mic_data.shape[1] == 1 and system_data.shape[1] == 2:
                            mic_data = np.column_stack((mic_data[:, 0], mic_data[:, 0]))

                    min_length = min(len(system_data), len(mic_data))
                    system_part = system_data[:min_length] * self.system_volume
                    mic_part = mic_data[:min_length] * self.mic_volume

                    if system_part.shape == mic_part.shape:
                        mixed = system_part + mic_part
                        # Clipping vermeiden
                        max_val = np.max(np.abs(mixed))
                        if max_val > 1.0:
                            mixed = mixed / max_val * 0.9

                        self.output_buffer.append(mixed)
                    else:
                        self.output_buffer.append(system_part)
                else:
                    self.output_buffer.append(system_data * self.system_volume)
            except Exception as e:
                if self.logger:
                    self.logger.log_message(f"Fehler beim Audio-Mixing: {e}", "WARNING")
                try:
                    self.output_buffer.append(system_data * self.system_volume)
                except Exception:
                    pass

    def start(self, output_file):
        """Startet die Audio-Aufnahme."""
        self.output_file = output_file
        self.is_recording = True

        # Puffer leeren
        self.system_buffer = []
        self.mic_buffer = []
        self.output_buffer = []

        # Ausgabedatei vorbereiten
        if os.path.exists(output_file):
            os.remove(output_file)

        # Soundfile öffnen
        self.sf_file = sf.SoundFile(
            output_file,
            mode='w',
            samplerate=SAMPLE_RATE,
            channels=2,  # Immer Stereo-Ausgabe
            format='WAV'
        )

        # Streams starten
        self.system_stream = sd.InputStream(
            device=self.system_device,
            channels=self.system_channels,
            callback=self.system_callback,
            blocksize=BUFFER_SIZE,
            samplerate=SAMPLE_RATE,
            latency=LATENCY
        )

        self.mic_stream = sd.InputStream(
            device=self.mic_device,
            channels=self.mic_channels,
            callback=self.mic_callback,
            blocksize=BUFFER_SIZE,
            samplerate=SAMPLE_RATE,
            latency=LATENCY
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
                    self.sf_file.write(chunk)

                time.sleep(0.01)

            self.sf_file.close()
            if self.logger:
                self.logger.log_message(f"Datei gespeichert: {self.output_file}", "SUCCESS")

        except Exception as e:
            if self.logger:
                self.logger.log_message(f"Fehler im Writer-Thread: {e}", "ERROR")

    def stop(self):
        """Stoppt die Audio-Aufnahme."""
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