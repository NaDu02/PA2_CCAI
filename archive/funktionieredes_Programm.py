"""
ATA Audio-Aufnahme für macOS - Optimierte Version mit verbesserter Performance
Diese Version löst Probleme mit Audiogeschwindigkeit und Unterbrechungen.
"""

import os
import sys
import time
import queue
import threading
import warnings
import traceback
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from datetime import datetime

# Konfiguration
FILENAME = "../conversation.wav"
API_URL = "http://168.231.106.208:10300/transcribe"  # Falls relevant
SAMPLE_RATE = 44100
CHANNELS = 2

# Verbesserte Performance-Einstellungen
BUFFER_SIZE = 4096       # Größerer Buffer für stabilere Aufnahme
LATENCY = "high"         # Höhere Latenz für bessere Stabilität
QUEUE_SIZE = 100         # Größere Queue für bessere Pufferung
DEVICE_TIMEOUT = 0.2     # Längerer Timeout für Geräteabfragen

# Standard-Kanalanzahl (wird für jedes Gerät einzeln angepasst)
DEFAULT_CHANNELS = 2

# Mischverhältnis
SYSTEM_VOLUME = 0.7  # 70% Systemton
MIC_VOLUME = 1.0     # 100% Mikrofon

# Global Flag für Audio-Bibliotheken
AUDIO_AVAILABLE = True

# Wichtige Bibliotheken mit Fehlerbehandlung importieren
try:
    import requests
    print("✅ requests erfolgreich importiert")
except ImportError:
    print("❌ requests nicht verfügbar - pip install requests ausführen")

try:
    import numpy as np
    print("✅ numpy erfolgreich importiert")
except ImportError:
    print("❌ numpy nicht verfügbar - pip install numpy ausführen")
    AUDIO_AVAILABLE = False

try:
    import sounddevice as sd
    print("✅ sounddevice erfolgreich importiert")
except ImportError:
    print("❌ sounddevice nicht verfügbar - pip install sounddevice ausführen")
    AUDIO_AVAILABLE = False

try:
    import soundfile as sf
    print("✅ soundfile erfolgreich importiert")
except ImportError:
    print("❌ soundfile nicht verfügbar - pip install soundfile ausführen")
    AUDIO_AVAILABLE = False

# Verbesserte Fehlerbehandlung für sounddevice
if AUDIO_AVAILABLE:
    try:
        # Gerätestabilität erhöhen
        sd.default.latency = (DEVICE_TIMEOUT, DEVICE_TIMEOUT)
        sd.default.dtype = 'float32'
        sd.default.channels = 2
        sd.default.samplerate = SAMPLE_RATE
        print("✅ sounddevice-Konfiguration optimiert")
    except Exception as e:
        print(f"⚠️ Warnung: Konnte sounddevice nicht optimieren: {e}")

# Globale Steuer-Variablen
recording_event = threading.Event() if AUDIO_AVAILABLE else None
combined_buffer = []  # Gemeinsamer Puffer für gemischtes Audio
buffer_lock = threading.Lock()  # Lock für Thread-sichere Buffer-Zugriffe
recording_threads = []
recording = False

# Ausgewählte Audiogeräte und deren Eigenschaften
selected_loopback = None
selected_microphone = None
loopback_channels = DEFAULT_CHANNELS
microphone_channels = DEFAULT_CHANNELS

# Funktion zur Protokollierung mit Zeitstempel
def log_message(message, level="INFO"):
    """Fügt eine Nachricht mit Zeitstempel zum Logfenster hinzu."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {
        "INFO": "",
        "SUCCESS": "✅ ",
        "ERROR": "❌ ",
        "WARNING": "⚠️ "
    }.get(level, "")

    formatted_msg = f"[{timestamp}] {prefix}{message}"

    if log_text:
        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, formatted_msg + "\n")
        log_text.see(tk.END)  # Auto-scroll zum Ende
        log_text.config(state=tk.DISABLED)

    # Auch auf der Konsole ausgeben für Debug-Zwecke
    print(formatted_msg)

# === Geräte-Management ===
def get_audio_devices():
    """Ermittelt alle verfügbaren Audiogeräte und gibt sie als Listen zurück."""
    if not AUDIO_AVAILABLE:
        return [], []

    loopback_devices = []
    microphones = []

    try:
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            name = device['name']
            max_input_channels = device.get('max_input_channels', 0)
            max_output_channels = device.get('max_output_channels', 0)

            # Geräteinformationen loggen
            log_message(f"Gerät {i}: {name} (Input: {max_input_channels}, Output: {max_output_channels})", "INFO")

            # Auf macOS ist BlackHole ein Eingabe- und Ausgabegerät
            if 'BlackHole' in name:
                if max_input_channels > 0:
                    loopback_devices.append((i, name, max_input_channels))
            elif max_input_channels > 0:
                microphones.append((i, name, max_input_channels))

    except Exception as e:
        log_message(f"Fehler beim Abrufen der Audiogeräte: {e}", "ERROR")
        traceback.print_exc()
        if root:
            messagebox.showerror("Fehler", f"Fehler beim Abrufen der Audiogeräte: {e}")

    return loopback_devices, microphones

def show_device_selection():
    """Zeigt ein Fenster zur Geräteauswahl."""
    global selected_loopback, selected_microphone, loopback_channels, microphone_channels

    if not AUDIO_AVAILABLE:
        messagebox.showerror("Fehler", "Audio-Bibliotheken nicht verfügbar")
        return

    # Geräte abrufen
    loopback_devices, microphones = get_audio_devices()

    if not loopback_devices:
        messagebox.showerror("Fehler", "Kein BlackHole-Gerät gefunden.\n"
                             "Bitte installieren Sie BlackHole und konfigurieren Sie es in Audio-MIDI-Setup.")
        return

    # Dialogfenster erstellen
    dialog = tk.Toplevel(root)
    dialog.title("Audiogeräte auswählen")
    dialog.geometry("500x420")
    dialog.grab_set()  # Modal machen

    # Frames für Comboboxen
    frame = ttk.Frame(dialog, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Loopback-Gerät
    ttk.Label(frame, text="Loopback-Gerät (Systemton):").grid(column=0, row=0, sticky=tk.W, pady=5)
    loopback_var = tk.StringVar()
    loopback_combo = ttk.Combobox(frame, textvariable=loopback_var, width=50)
    loopback_combo['values'] = [f"{device[1]} ({device[2]} Kanäle)" for device in loopback_devices]
    loopback_combo.grid(column=0, row=1, sticky=(tk.W, tk.E), pady=5)

    # Wähle das erste Loopback-Gerät standardmäßig
    if loopback_devices:
        loopback_combo.current(0)

    # Mikrofon
    ttk.Label(frame, text="Mikrofon:").grid(column=0, row=2, sticky=tk.W, pady=5)
    mic_var = tk.StringVar()
    mic_combo = ttk.Combobox(frame, textvariable=mic_var, width=50)
    mic_combo['values'] = [f"{device[1]} ({device[2]} Kanäle)" for device in microphones]
    mic_combo.grid(column=0, row=3, sticky=(tk.W, tk.E), pady=5)

    # Wähle das erste Mikrofon standardmäßig
    if microphones:
        mic_combo.current(0)

    # Lautstärke-Regler
    ttk.Label(frame, text="System-Lautstärke:").grid(column=0, row=4, sticky=tk.W, pady=5)
    system_volume_var = tk.DoubleVar(value=SYSTEM_VOLUME)
    system_volume_scale = ttk.Scale(frame, variable=system_volume_var, from_=0.0, to=1.0)
    system_volume_scale.grid(column=0, row=5, sticky=(tk.W, tk.E), pady=2)

    ttk.Label(frame, text="Mikrofon-Lautstärke:").grid(column=0, row=6, sticky=tk.W, pady=5)
    mic_volume_var = tk.DoubleVar(value=MIC_VOLUME)
    mic_volume_scale = ttk.Scale(frame, variable=mic_volume_var, from_=0.0, to=2.0)  # Bis 200% für Mikrofon
    mic_volume_scale.grid(column=0, row=7, sticky=(tk.W, tk.E), pady=2)

    # Performance-Einstellungen
    ttk.Label(frame, text="--- Erweiterte Einstellungen ---").grid(column=0, row=8, sticky=(tk.W, tk.E), pady=5)

    ttk.Label(frame, text="Puffergröße:").grid(column=0, row=9, sticky=tk.W, pady=5)
    buffer_size_var = tk.IntVar(value=BUFFER_SIZE)
    buffer_size_combo = ttk.Combobox(frame, textvariable=buffer_size_var, width=20)
    buffer_size_combo['values'] = [1024, 2048, 4096, 8192, 16384]
    buffer_size_combo.current(buffer_size_combo['values'].index(BUFFER_SIZE) if BUFFER_SIZE in buffer_size_combo['values'] else 2)
    buffer_size_combo.grid(column=0, row=10, sticky=tk.W, pady=2)

    # Buttons
    button_frame = ttk.Frame(frame)
    button_frame.grid(column=0, row=11, pady=20)

    def on_save():
        global selected_loopback, selected_microphone, loopback_channels, microphone_channels
        global SYSTEM_VOLUME, MIC_VOLUME, BUFFER_SIZE

        loopback_idx = loopback_combo.current()
        mic_idx = mic_combo.current()

        if loopback_idx >= 0 and loopback_idx < len(loopback_devices):
            selected_loopback = loopback_devices[loopback_idx][0]
            loopback_name = loopback_devices[loopback_idx][1]
            loopback_channels = loopback_devices[loopback_idx][2]
            status_label.config(text=f"Loopback: {loopback_name} ({loopback_channels} Kanäle)")

        if mic_idx >= 0 and mic_idx < len(microphones):
            selected_microphone = microphones[mic_idx][0]
            mic_name = microphones[mic_idx][1]
            microphone_channels = microphones[mic_idx][2]
            status_mic_label.config(text=f"Mikrofon: {mic_name} ({microphone_channels} Kanäle)")

        # Lautstärke-Einstellungen speichern
        SYSTEM_VOLUME = system_volume_var.get()
        MIC_VOLUME = mic_volume_var.get()

        # Performance-Einstellungen
        BUFFER_SIZE = buffer_size_var.get()

        log_message(f"Lautstärke: System={SYSTEM_VOLUME:.2f}, Mikrofon={MIC_VOLUME:.2f}", "INFO")
        log_message(f"Puffergröße: {BUFFER_SIZE}", "INFO")
        log_message(f"Geräte ausgewählt: Loopback={loopback_devices[loopback_idx][1]} ({loopback_channels} Kanäle), "
                   f"Mikrofon={microphones[mic_idx][1]} ({microphone_channels} Kanäle)", "SUCCESS")
        dialog.destroy()

    ttk.Button(button_frame, text="Speichern", command=on_save).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Abbrechen", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

def check_audio_setup():
    """Überprüft das Audio-Setup und gibt eine Statusmeldung zurück."""
    if not AUDIO_AVAILABLE:
        return False, "Audio-Setup nicht möglich - Bibliotheken fehlen"

    try:
        devices = sd.query_devices()
        blackhole_found = False
        blackhole_name = ""

        for device in devices:
            if 'BlackHole' in device['name']:
                blackhole_found = True
                blackhole_name = device['name']
                break

        if not blackhole_found:
            return False, "Kein BlackHole-Gerät gefunden."

        return True, f"Gefunden: Loopback-Device '{blackhole_name}'"
    except Exception as e:
        return False, f"Fehler bei Audio-Setup: {e}"

# === Verbesserte Audio-Verarbeitung ===
class AudioProcessor:
    """Audio-Verarbeitungsklasse für verbesserte Stabilität und Synchronisation."""
    def __init__(self, system_device, mic_device, system_channels, mic_channels):
        self.system_device = system_device
        self.mic_device = mic_device
        self.system_channels = system_channels
        self.mic_channels = mic_channels

        self.system_buffer = []
        self.mic_buffer = []
        self.output_buffer = []

        self.system_volume = SYSTEM_VOLUME
        self.mic_volume = MIC_VOLUME

        self.buffer_lock = threading.Lock()
        self.system_stream = None
        self.mic_stream = None

        self.output_file = None
        self.is_recording = False

    def system_callback(self, indata, frames, time, status):
        """Callback für System-Audio."""
        if status:
            log_message(f"System-Status: {status}", "WARNING")

        with self.buffer_lock:
            # System-Audio zum Puffer hinzufügen
            self.system_buffer.append(indata.copy())

            # Wenn beide Puffer Daten haben, mischen
            self._mix_if_possible()

    def mic_callback(self, indata, frames, time, status):
        """Callback für Mikrofon-Audio."""
        if status:
            log_message(f"Mikrofon-Status: {status}", "WARNING")

        with self.buffer_lock:
            # Mikrofon-Audio zum Puffer hinzufügen
            self.mic_buffer.append(indata.copy())

            # Wenn beide Puffer Daten haben, mischen
            self._mix_if_possible()

    def _mix_if_possible(self):
        """Mischt Audio, wenn in beiden Puffern Daten vorhanden sind."""
        # Verarbeite, solange beide Puffer Daten haben
        while self.system_buffer and self.mic_buffer:
            system_data = self.system_buffer.pop(0)
            mic_data = self.mic_buffer.pop(0)

            # Mikrofon zu Stereo konvertieren, falls nötig
            if self.mic_channels == 1 and self.system_channels == 2:
                try:
                    if len(mic_data.shape) == 2 and mic_data.shape[1] == 1:
                        # Dupliziere die Monospur für Stereo
                        mic_data = np.column_stack((mic_data, mic_data))
                except Exception as e:
                    log_message(f"Fehler bei Stereo-Konvertierung: {e}", "WARNING")

            # Audio mischen
            try:
                if len(system_data.shape) == len(mic_data.shape):
                    if system_data.shape[1] != mic_data.shape[1]:
                        # Unterschiedliche Kanalanzahl anpassen
                        if mic_data.shape[1] == 1 and system_data.shape[1] == 2:
                            mic_data = np.column_stack((mic_data[:, 0], mic_data[:, 0]))

                    # Längen angleichen
                    min_length = min(len(system_data), len(mic_data))
                    system_part = system_data[:min_length] * self.system_volume
                    mic_part = mic_data[:min_length] * self.mic_volume

                    if system_part.shape == mic_part.shape:
                        mixed = system_part + mic_part
                        # Clipping vermeiden
                        max_val = np.max(np.abs(mixed))
                        if max_val > 1.0:
                            mixed = mixed / max_val * 0.9

                        # Zum Ausgabepuffer hinzufügen
                        self.output_buffer.append(mixed)
                    else:
                        # Fallback
                        self.output_buffer.append(system_part)
                else:
                    # Nur System-Audio verwenden
                    self.output_buffer.append(system_data * self.system_volume)
            except Exception as e:
                log_message(f"Fehler beim Audio-Mixing: {e}", "WARNING")
                # Fallback: nur System-Audio
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

        # Lautstärke-Einstellungen aktualisieren
        self.system_volume = SYSTEM_VOLUME
        self.mic_volume = MIC_VOLUME

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

        log_message("Audio-Aufnahme gestartet mit optimierten Einstellungen", "SUCCESS")

    def _writer_loop(self):
        """Schreibt gemischte Audiodaten in die Datei."""
        try:
            while self.is_recording or self.output_buffer:
                # Daten aus Output-Buffer holen, falls vorhanden
                data_to_write = []

                with self.buffer_lock:
                    # Max. 10 Chunks pro Durchlauf für gleichmäßigeres Schreiben
                    chunks_to_process = min(10, len(self.output_buffer))
                    if chunks_to_process > 0:
                        data_to_write = self.output_buffer[:chunks_to_process]
                        self.output_buffer = self.output_buffer[chunks_to_process:]

                # Daten in Datei schreiben
                for chunk in data_to_write:
                    self.sf_file.write(chunk)

                # Kurze Pause, um CPU zu entlasten
                time.sleep(0.01)

            # Datei schließen
            self.sf_file.close()
            log_message(f"Datei gespeichert: {self.output_file}", "SUCCESS")

        except Exception as e:
            log_message(f"Fehler im Writer-Thread: {e}", "ERROR")
            traceback.print_exc()

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

        log_message("Audio-Aufnahme gestoppt", "INFO")

# === Steuerfunktionen ===
def start_recording():
    """Startet die Aufnahme mit dem AudioProcessor."""
    global recording, recording_threads, audio_processor

    if not AUDIO_AVAILABLE:
        log_message("Aufnahme nicht möglich - Audio-Bibliotheken fehlen", "ERROR")
        messagebox.showerror("Fehler", "Aufnahme nicht möglich - Audio-Bibliotheken fehlen")
        return False

    if recording:
        log_message("Aufnahme läuft bereits.", "INFO")
        return False

    try:
        # Stellen Sie sicher, dass Geräte ausgewählt sind
        if selected_loopback is None or selected_microphone is None:
            if messagebox.askyesno("Geräteauswahl",
                                 "Keine Audiogeräte ausgewählt. Möchten Sie jetzt Geräte auswählen?"):
                show_device_selection()
            else:
                return False

        # Nochmal prüfen, falls Dialog abgebrochen wurde
        if selected_loopback is None or selected_microphone is None:
            log_message("Keine Audiogeräte ausgewählt - Aufnahme abgebrochen", "ERROR")
            return False

        # AudioProcessor erstellen
        audio_processor = AudioProcessor(
            system_device=selected_loopback,
            mic_device=selected_microphone,
            system_channels=loopback_channels,
            mic_channels=microphone_channels
        )

        # Aufnahme starten
        audio_processor.start(FILENAME)
        recording = True

        # UI aktualisieren
        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)
        status_label.config(text=f"Status: Aufnahme läuft")

        return True
    except Exception as e:
        log_message(f"Fehler beim Starten der Aufnahme: {e}", "ERROR")
        traceback.print_exc()
        messagebox.showerror("Fehler", f"Fehler beim Starten der Aufnahme: {e}")
        recording = False
        return False

def stop_recording():
    """Stoppt die Aufnahme."""
    global recording, audio_processor

    if not AUDIO_AVAILABLE:
        log_message("Aufnahme-Stopp nicht möglich - Audio-Bibliotheken fehlen", "ERROR")
        return False

    if not recording:
        log_message("Keine Aufnahme aktiv.", "INFO")
        return False

    try:
        # Aufnahme stoppen
        if audio_processor:
            audio_processor.stop()

        recording = False

        # Garbage Collection erzwingen
        import gc
        gc.collect()

        # UI aktualisieren
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
        status_label.config(text="Status: Bereit")

        # Optional: Transkription
        try:
            # Prüfen ob API_URL verfügbar ist (dieser Teil kann entfernt werden, wenn nicht benötigt)
            with open(FILENAME, "rb") as vf:
                resp = requests.post(API_URL, files={"file": (FILENAME, vf, "audio/wav")})

            if resp.ok:
                log_message("📝 Transkription:\n" + resp.json().get("transcription", "—"), "INFO")
            else:
                log_message(f"Transkriptions-Fehler: {resp.status_code}", "ERROR")
        except Exception as e:
            log_message(f"Transkription nicht möglich: {e}", "WARNING")

        return True
    except Exception as e:
        log_message(f"Fehler beim Stoppen der Aufnahme: {e}", "ERROR")
        traceback.print_exc()
        messagebox.showerror("Fehler", f"Fehler beim Stoppen der Aufnahme: {e}")

        # Trotzdem Status zurücksetzen
        recording = False
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
        status_label.config(text="Status: Fehler aufgetreten")

        return False

def test_recording():
    """5-Sekunden-Testaufnahme von System und Mikrofon."""
    global loopback_channels, microphone_channels

    if not AUDIO_AVAILABLE:
        log_message("Test nicht möglich - Audio-Bibliotheken fehlen", "ERROR")
        messagebox.showerror("Fehler", "Test nicht möglich - Audio-Bibliotheken fehlen")
        return

    try:
        # Stellen Sie sicher, dass keine Aufnahme läuft
        if recording:
            log_message("Test nicht möglich - Aufnahme läuft bereits.", "WARNING")
            messagebox.showwarning("Warnung", "Test nicht möglich - Aufnahme läuft bereits.")
            return

        # Deaktiviere Buttons während Test
        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.DISABLED)
        test_button.config(state=tk.DISABLED)
        devices_button.config(state=tk.DISABLED)

        log_message("Testaufnahme (5 Sekunden)...", "INFO")

        # Geräteauswahl prüfen
        if selected_loopback is None or selected_microphone is None:
            if messagebox.askyesno("Geräteauswahl",
                                "Keine Audiogeräte ausgewählt. Möchten Sie jetzt Geräte auswählen?"):
                show_device_selection()
            else:
                reset_buttons()
                return

        if selected_loopback is None or selected_microphone is None:
            log_message("Test abgebrochen - keine Geräte ausgewählt.", "WARNING")
            reset_buttons()
            return

        # System-Audio aufnehmen
        log_message("Nehme System-Audio auf... BITTE JETZT AUDIO ABSPIELEN", "INFO")
        messagebox.showinfo("Test", "Bitte spielen Sie jetzt Audio ab (z.B. YouTube, Musik).")

        # Mit sounddevice aufnehmen
        try:
            duration = 5  # Sekunden
            log_message(f"Nehme {duration} Sekunden von BlackHole auf...", "INFO")

            frames = int(duration * SAMPLE_RATE)
            # Wichtig: Verwende die erkannte Kanalanzahl
            sys_data = sd.rec(frames, samplerate=SAMPLE_RATE, channels=loopback_channels,
                             device=selected_loopback, blocking=True)

            sf.write("../test_system.wav", sys_data, SAMPLE_RATE)
            log_message("System-Audio aufgenommen und in test_system.wav gespeichert", "SUCCESS")

        except Exception as e:
            log_message(f"Fehler bei System-Audio-Aufnahme: {e}", "ERROR")
            traceback.print_exc()
            messagebox.showerror("Fehler", f"Fehler bei System-Audio-Aufnahme: {e}")

        # Mikrofon aufnehmen
        log_message("Nehme Mikrofon auf... BITTE JETZT SPRECHEN", "INFO")
        messagebox.showinfo("Test", "Bitte sprechen Sie jetzt ins Mikrofon.")

        # Mit sounddevice aufnehmen
        try:
            duration = 5  # Sekunden
            log_message(f"Nehme {duration} Sekunden vom Mikrofon auf...", "INFO")

            frames = int(duration * SAMPLE_RATE)
            # Wichtig: Verwende die erkannte Kanalanzahl für das Mikrofon
            mic_data = sd.rec(frames, samplerate=SAMPLE_RATE, channels=microphone_channels,
                             device=selected_microphone, blocking=True)

            sf.write("../test_mic.wav", mic_data, SAMPLE_RATE)
            log_message("Mikrofon-Audio aufgenommen und in test_mic.wav gespeichert", "SUCCESS")

        except Exception as e:
            log_message(f"Fehler bei Mikrofon-Aufnahme: {e}", "ERROR")
            traceback.print_exc()
            messagebox.showerror("Fehler", f"Fehler bei Mikrofon-Aufnahme: {e}")

        # Kombinierter Test mit AudioProcessor
        log_message("Teste kombinierte Aufnahme (5 Sekunden)...", "INFO")
        messagebox.showinfo("Test", "Bitte spielen Sie Audio ab UND sprechen Sie gleichzeitig ins Mikrofon.")

        try:
            # AudioProcessor für Test erstellen
            test_processor = AudioProcessor(
                system_device=selected_loopback,
                mic_device=selected_microphone,
                system_channels=loopback_channels,
                mic_channels=microphone_channels
            )

            # Test starten
            test_processor.start("test_combined.wav")

            # 5 Sekunden warten
            for i in range(5):
                log_message(f"Test läuft... {i+1}/5 Sekunden", "INFO")
                time.sleep(1)

            # Test stoppen
            test_processor.stop()

            log_message("Kombinierte Aufnahme in test_combined.wav gespeichert", "SUCCESS")

        except Exception as e:
            log_message(f"Fehler beim kombinierten Test: {e}", "ERROR")
            traceback.print_exc()

        log_message("Testaufnahmen gespeichert: test_system.wav, test_mic.wav, test_combined.wav", "SUCCESS")

        # Garbage Collection erzwingen
        import gc
        gc.collect()

        # Buttons wieder aktivieren
        reset_buttons()

    except Exception as e:
        log_message(f"Fehler bei Testaufnahme: {e}", "ERROR")
        traceback.print_exc()
        messagebox.showerror("Fehler", f"Fehler bei Testaufnahme: {e}")
        reset_buttons()

def reset_buttons():
    """Setzt die Button-Status zurück."""
    if recording:
        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)
    else:
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
    test_button.config(state=tk.NORMAL)
    devices_button.config(state=tk.NORMAL)

def on_closing():
    """Handler für das Schließen des Fensters."""
    if recording:
        if messagebox.askyesno("Beenden", "Die Aufnahme läuft noch. Wirklich beenden?"):
            stop_recording()
            root.destroy()
    else:
        root.destroy()

def show_help():
    """Zeigt ein Hilfefenster mit Anweisungen."""
    help_window = tk.Toplevel(root)
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

# === GUI erstellen ===
root = tk.Tk()
root.title("ATA Audio-Aufnahme (macOS)")
root.geometry("700x600")
root.protocol("WM_DELETE_WINDOW", on_closing)

# Hauptframe
main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# Statusanzeige
status_frame = tk.Frame(main_frame)
status_frame.pack(fill=tk.X, pady=(0, 10))

status_label = tk.Label(status_frame, text="Status: Initialisierung...", anchor=tk.W)
status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

status_mic_label = tk.Label(status_frame, text="", anchor=tk.E)
status_mic_label.pack(side=tk.RIGHT)

# Button-Frame
button_frame = tk.Frame(main_frame)
button_frame.pack(fill=tk.X, pady=(0, 10))

start_button = tk.Button(button_frame, text="Start", command=start_recording, width=10)
start_button.pack(side=tk.LEFT, padx=5)

stop_button = tk.Button(button_frame, text="Stop", command=stop_recording, width=10, state=tk.DISABLED)
stop_button.pack(side=tk.LEFT, padx=5)

test_button = tk.Button(button_frame, text="Test", command=test_recording, width=10)
test_button.pack(side=tk.LEFT, padx=5)

devices_button = tk.Button(button_frame, text="Geräteauswahl", command=show_device_selection, width=15)
devices_button.pack(side=tk.LEFT, padx=5)

help_button = tk.Button(button_frame, text="Hilfe", command=show_help, width=10)
help_button.pack(side=tk.RIGHT, padx=5)

# Log-Bereich
log_frame = tk.LabelFrame(main_frame, text="Protokoll")
log_frame.pack(fill=tk.BOTH, expand=True)

log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=80, height=30)
log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
log_text.config(state=tk.DISABLED)

# Initialisieren
log_message("=== ATA Audio-Aufnahme für macOS ===", "INFO")
log_message("Überprüfe Audio-Setup...", "INFO")

audio_ok, msg = check_audio_setup()
if audio_ok:
    log_message(msg, "SUCCESS")
    log_message("Audio-Setup-Prüfung OK.", "INFO")
    status_label.config(text="Status: Bereit")
else:
    log_message(msg, "ERROR")
    log_message("Audio-Setup unvollständig!", "WARNING")
    log_message("Bitte stellen Sie sicher, dass BlackHole installiert und konfiguriert ist.", "INFO")
    status_label.config(text="Status: Fehler beim Audio-Setup")

# Hauptschleife starten
if __name__ == "__main__":
    try:
        # Nach dem Starten automatisch Geräteauswahl anzeigen
        if AUDIO_AVAILABLE:
            # Verzögern, um sicherzustellen, dass das Hauptfenster zuerst erscheint
            root.after(500, show_device_selection)

        root.mainloop()
    except Exception as e:
        print(f"Fataler Fehler: {e}")
        traceback.print_exc()