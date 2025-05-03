# tests/test_recording.py
"""
Test-Funktionen für die ATA Audio-Aufnahme
"""
import time
import sounddevice as sd
import soundfile as sf
from tkinter import messagebox
from config.settings import SAMPLE_RATE
from audio.processor import AudioProcessor


class TestRecording:
    def __init__(self, device_manager, logger=None):
        self.device_manager = device_manager
        self.logger = logger

    def run_test(self, selected_loopback, selected_microphone, loopback_channels, microphone_channels):
        """Führt einen 5-Sekunden-Test der Audioaufnahme durch."""
        try:
            # System-Audio aufnehmen
            self._log("Nehme System-Audio auf... BITTE JETZT AUDIO ABSPIELEN", "INFO")
            messagebox.showinfo("Test", "Bitte spielen Sie jetzt Audio ab (z.B. YouTube, Musik).")

            # Mit sounddevice aufnehmen
            try:
                duration = 5  # Sekunden
                self._log(f"Nehme {duration} Sekunden von BlackHole auf...", "INFO")

                frames = int(duration * SAMPLE_RATE)
                # Wichtig: Verwende die erkannte Kanalanzahl
                sys_data = sd.rec(frames, samplerate=SAMPLE_RATE, channels=loopback_channels,
                                  device=selected_loopback, blocking=True)

                sf.write("test_system.wav", sys_data, SAMPLE_RATE)
                self._log("System-Audio aufgenommen und in test_system.wav gespeichert", "SUCCESS")

            except Exception as e:
                self._log(f"Fehler bei System-Audio-Aufnahme: {e}", "ERROR")
                messagebox.showerror("Fehler", f"Fehler bei System-Audio-Aufnahme: {e}")

            # Mikrofon aufnehmen
            self._log("Nehme Mikrofon auf... BITTE JETZT SPRECHEN", "INFO")
            messagebox.showinfo("Test", "Bitte sprechen Sie jetzt ins Mikrofon.")

            # Mit sounddevice aufnehmen
            try:
                duration = 5  # Sekunden
                self._log(f"Nehme {duration} Sekunden vom Mikrofon auf...", "INFO")

                frames = int(duration * SAMPLE_RATE)
                # Wichtig: Verwende die erkannte Kanalanzahl für das Mikrofon
                mic_data = sd.rec(frames, samplerate=SAMPLE_RATE, channels=microphone_channels,
                                  device=selected_microphone, blocking=True)

                sf.write("test_mic.wav", mic_data, SAMPLE_RATE)
                self._log("Mikrofon-Audio aufgenommen und in test_mic.wav gespeichert", "SUCCESS")

            except Exception as e:
                self._log(f"Fehler bei Mikrofon-Aufnahme: {e}", "ERROR")
                messagebox.showerror("Fehler", f"Fehler bei Mikrofon-Aufnahme: {e}")

            # Kombinierter Test mit AudioProcessor
            self._log("Teste kombinierte Aufnahme (5 Sekunden)...", "INFO")
            messagebox.showinfo("Test", "Bitte spielen Sie Audio ab UND sprechen Sie gleichzeitig ins Mikrofon.")

            try:
                # AudioProcessor für Test erstellen
                test_processor = AudioProcessor(
                    system_device=selected_loopback,
                    mic_device=selected_microphone,
                    system_channels=loopback_channels,
                    mic_channels=microphone_channels,
                    logger=self.logger
                )

                # Test starten
                test_processor.start("test_combined.wav")

                # 5 Sekunden warten
                for i in range(5):
                    self._log(f"Test läuft... {i + 1}/5 Sekunden", "INFO")
                    time.sleep(1)

                # Test stoppen
                test_processor.stop()

                self._log("Kombinierte Aufnahme in test_combined.wav gespeichert", "SUCCESS")

            except Exception as e:
                self._log(f"Fehler beim kombinierten Test: {e}", "ERROR")

            self._log("Testaufnahmen gespeichert: test_system.wav, test_mic.wav, test_combined.wav", "SUCCESS")

            # Garbage Collection erzwingen
            import gc
            gc.collect()

        except Exception as e:
            self._log(f"Fehler bei Testaufnahme: {e}", "ERROR")
            messagebox.showerror("Fehler", f"Fehler bei Testaufnahme: {e}")

    def _log(self, message, level):
        """Hilfsfunktion für Logging."""
        if self.logger:
            self.logger.log_message(message, level)
        else:
            print(f"[{level}] {message}")