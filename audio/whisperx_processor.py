# audio/whisperx_processor.py
"""
Verbesserte WhisperX-basierte Verarbeitung mit robuster Fehlerbehandlung
"""
import numpy as np
import soundfile as sf
import requests
import io
import json
import traceback
import os
import time
import subprocess
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import settings


class WhisperXProcessor:
    def __init__(self, logger=None):
        self.logger = logger
        self.session = self._create_session()

    def _create_session(self):
        """Erstellt eine Session mit urllib3 2.x kompatiblen Einstellungen"""
        session = requests.Session()

        # Retry-Strategie (angepasst basierend auf Tests)
        try:
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["POST"]
            )
        except TypeError:
            # Fallback für ältere urllib3-Version
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],
                method_whitelist=["POST"]
            )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _log(self, message, level="INFO"):
        """Logging-Hilfsmethode"""
        if self.logger:
            self.logger.log_message(message, level)
        else:
            print(f"[{level}] {message}")

    # audio/whisperx_processor.py - Server Health Monitoring

    def _check_server_health(self):
        """Erweiterte Server-Health-Prüfung"""
        health_url = settings.WHISPERX_API_URL.replace('/transcribe', '/health')

        try:
            self._log("Checking server health...", "INFO")

            # Schneller Health Check (5s Timeout)
            start_time = time.time()
            resp = self.session.get(health_url, timeout=5)
            latency = time.time() - start_time

            if resp.ok:
                try:
                    health_data = resp.json()
                    device = health_data.get('device', 'unknown')
                    self._log(f"Server healthy (device: {device}, latency: {latency:.2f}s)", "SUCCESS")

                    # Warnung bei hoher Latenz
                    if latency > 1.0:
                        self._log(f"High server latency detected: {latency:.2f}s", "WARNING")

                    return True
                except:
                    # Auch OK, wenn JSON nicht parsebar ist
                    self._log("Server responds but health format unexpected", "WARNING")
                    return True
            else:
                self._log(f"Server health check failed: {resp.status_code}", "WARNING")
                return False

        except requests.exceptions.Timeout:
            self._log("Server health check timed out", "WARNING")
            return False
        except requests.exceptions.ConnectionError as e:
            self._log(f"Cannot connect to server: {e}", "ERROR")
            return False
        except Exception as e:
            self._log(f"Health check failed: {e}", "ERROR")
            return False

    def process_complete_audio(self, audio_file_path):
        """Hauptmethode mit Health-Check"""
        try:
            # Prüfe Datei
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                raise ValueError("Audio file is empty")

            self._log(f"Processing audio file: {file_size / 1024 / 1024:.2f} MB", "INFO")

            # Health Check vor Verarbeitung
            if not self._check_server_health():
                # Warte kurz und versuche erneut
                self._log("Server not healthy, waiting 5s and retrying...", "INFO")
                time.sleep(5)

                if not self._check_server_health():
                    # Gehe trotzdem weiter, aber mit veränderten Timeouts
                    self._log("Server still not responding to health checks, proceeding with caution", "WARNING")
                    settings.WHISPERX_TIMEOUT *= 2  # Verdopple Timeout

            # Verarbeitung durchführen
            return self._process_standard_file(audio_file_path)

        except Exception as e:
            self._log(f"Error in process_complete_audio: {str(e)}", "ERROR")
            return {
                'full_text': "",
                'labeled_text': "",
                'segments': [],
                'transcription': f"Error: {str(e)}"
            }

    def _check_api_health(self):
        """Überprüft, ob die WhisperX-API verfügbar ist"""
        try:
            health_url = settings.WHISPERX_API_URL.replace('/transcribe', '/health')
            resp = self.session.get(health_url, timeout=5)
            return resp.ok
        except:
            return False

    def _compress_audio(self, audio_file_path, target_size_mb=5):
        """Komprimiert Audio-Datei auf Zielgröße"""
        try:
            self._log("Komprimiere Audio-Datei für API-Upload...", "INFO")

            # Lade Audio und analysiere
            audio, sr = sf.read(audio_file_path)
            duration = len(audio) / sr

            # Berechne Ziel-Bitrate basierend auf gewünschter Dateigröße
            target_size_bytes = target_size_mb * 1024 * 1024
            target_bitrate = int((target_size_bytes * 8) / duration) // 1000  # kbps
            target_bitrate = max(32, min(target_bitrate, 128))  # Zwischen 32-128 kbps

            self._log(f"Ziel-Bitrate: {target_bitrate} kbps", "INFO")

            # Verwende FFmpeg für effiziente Komprimierung
            compressed_path = audio_file_path.replace('.wav', '_compressed.wav')

            # FFmpeg-Befehl für optimale Komprimierung
            ffmpeg_cmd = [
                'ffmpeg', '-y',  # Überschreiben ohne Nachfrage
                '-i', audio_file_path,
                '-ar', '16000',  # Sample rate auf 16kHz reduzieren
                '-ac', '1',  # Mono (falls Stereo)
                '-b:a', f'{target_bitrate}k',  # Bitrate
                '-f', 'wav',
                compressed_path
            ]

            try:
                subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                final_size = os.path.getsize(compressed_path)
                self._log(f"Komprimierung erfolgreich: {final_size / 1024 / 1024:.2f} MB", "SUCCESS")
                return compressed_path
            except subprocess.CalledProcessError:
                # Fallback ohne FFmpeg
                return self._fallback_compression(audio_file_path, target_size_mb)

        except Exception as e:
            self._log(f"Fehler bei Audio-Komprimierung: {e}", "WARNING")
            return audio_file_path

    def _fallback_compression(self, audio_file_path, target_size_mb):
        """Fallback-Komprimierung ohne FFmpeg"""
        try:
            self._log("Verwende Fallback-Komprimierung...", "INFO")

            # Lade Audio und konvertiere
            audio, sr = sf.read(audio_file_path)

            # Reduziere Sample Rate falls nötig
            if sr > 16000:
                import librosa
                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
                sr = 16000

            # Konvertiere zu Mono falls Stereo
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)

            # Reduziere Bit-Tiefe auf 16-bit integer für kleinere Dateien
            audio = (audio * 32767).astype(np.int16)

            # Speichere komprimierte Version
            compressed_path = audio_file_path.replace('.wav', '_compressed.wav')
            sf.write(compressed_path, audio, sr, subtype='PCM_16')

            final_size = os.path.getsize(compressed_path)
            self._log(f"Fallback-Komprimierung: {final_size / 1024 / 1024:.2f} MB", "INFO")
            return compressed_path

        except Exception as e:
            self._log(f"Fehler bei Fallback-Komprimierung: {e}", "ERROR")
            return audio_file_path

    # audio/whisperx_processor.py - Verbesserte Retry-Logik

    def _process_standard_file(self, audio_file_path):
        """Verarbeitet Standard-Dateien mit robuster Fehlerbehandlung"""
        max_retries = 3
        base_delay = 2
        backoff_factor = 2.0
        max_delay = 30

        # Berechne Timeout basierend auf Dateigröße (30s per MB, mindestens 60s)
        file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
        timeout = max(60, int(30 + file_size_mb * 30))

        self._log(f"Processing file: {file_size_mb:.2f} MB, Timeout: {timeout}s", "INFO")

        for attempt in range(max_retries):
            # Berechne Retry-Delay mit exponential backoff
            if attempt > 0:
                delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                self._log(f"Waiting {delay}s before retry {attempt + 1}...", "INFO")
                time.sleep(delay)

            try:
                with open(audio_file_path, "rb") as vf:
                    files = {"file": (os.path.basename(audio_file_path), vf, "audio/wav")}
                    data = {
                        "language": settings.WHISPERX_LANGUAGE,
                        "compute_type": settings.WHISPERX_COMPUTE_TYPE,
                        "enable_diarization": str(settings.WHISPERX_ENABLE_DIARIZATION).lower(),
                        "return_segments": "true",
                        "return_word_timestamps": "true"
                    }

                    self._log(f"Sending file (attempt {attempt + 1}/{max_retries})...", "INFO")

                    # Session für jeden Versuch neu erstellen, falls vorheriger fehlgeschlagen
                    if attempt > 0:
                        self.session = self._create_session()

                    # Request mit progressiven Timeouts
                    current_timeout = timeout + (attempt * 30)  # Erhöhe Timeout bei Retries

                    resp = self.session.post(
                        settings.WHISPERX_API_URL,
                        files=files,
                        data=data,
                        timeout=(30, current_timeout),  # Connect-Timeout bleibt konstant
                        stream=False,
                        headers={
                            'Connection': 'keep-alive',
                            'User-Agent': 'ATA-AudioApp/1.0'
                        }
                    )

                # Erfolgreiche Antwort verarbeiten
                if resp.ok:
                    self._log(f"Successfully received response from server", "SUCCESS")
                    return self._parse_response(resp)

                # Server-Fehler behandeln
                if resp.status_code >= 500:
                    # Server-Fehler: Retry lohnt sich
                    self._log(f"Server error {resp.status_code}, will retry", "WARNING")
                    continue
                elif resp.status_code >= 400:
                    # Client-Fehler: Wahrscheinlich kein Retry nötig
                    error_msg = resp.text[:200] if resp.text else "Unknown error"
                    self._log(f"Client error {resp.status_code}: {error_msg}", "ERROR")
                    raise Exception(f"Client error {resp.status_code}: {error_msg}")

            except requests.exceptions.ConnectionError as e:
                error_str = str(e)
                if "Connection aborted" in error_str or "Connection reset" in error_str:
                    self._log(f"Connection reset on attempt {attempt + 1} (server may have restarted)", "WARNING")
                    # Bei Connection Reset besonders lange warten
                    if attempt < max_retries - 1:
                        extra_delay = 15  # Extra 15 Sekunden bei Connection Reset
                        self._log(f"Server may be restarting, waiting extra {extra_delay}s...", "INFO")
                        time.sleep(extra_delay)
                    continue
                else:
                    self._log(f"Connection error: {error_str}", "ERROR")
                    if attempt == max_retries - 1:
                        raise Exception(f"Connection failed after {max_retries} attempts: {e}")
                    continue

            except requests.exceptions.Timeout as e:
                self._log(f"Timeout after {current_timeout}s on attempt {attempt + 1}", "WARNING")
                if attempt == max_retries - 1:
                    raise Exception(f"Timeout after {max_retries} attempts (last timeout: {current_timeout}s)")
                continue

            except Exception as e:
                self._log(f"Unexpected error on attempt {attempt + 1}: {str(e)}", "WARNING")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed after {max_retries} attempts: {str(e)}")
                continue

        # Sollte nicht erreicht werden
        raise Exception(f"Failed to process file after {max_retries} attempts")

    def _process_large_file(self, audio_file_path):
        """Verarbeitet große Dateien mit Chunking"""
        self._log("Verarbeite große Datei mit Chunking...", "INFO")

        # Teile Datei in kleinere Segmente
        chunks = self._split_audio_file(audio_file_path)
        all_segments = []

        for i, chunk_path in enumerate(chunks):
            self._log(f"Verarbeite Chunk {i + 1}/{len(chunks)}...", "INFO")
            try:
                result = self._process_standard_file(chunk_path)
                if result and 'segments' in result:
                    # Verschiebe Timestamps entsprechend dem Chunk-Offset
                    chunk_offset = i * 30  # 30 Sekunden pro Chunk
                    for segment in result['segments']:
                        segment['start'] += chunk_offset
                        segment['end'] += chunk_offset
                    all_segments.extend(result['segments'])
            except Exception as e:
                self._log(f"Fehler bei Chunk {i + 1}: {e}", "WARNING")
            finally:
                # Lösche temporäre Chunk-Datei
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)

        # Kombiniere Ergebnisse
        full_transcription = " ".join([seg['text'] for seg in all_segments])
        labeled_transcription = self._create_labeled_transcription(all_segments)

        return {
            'full_text': full_transcription,
            'labeled_text': labeled_transcription,
            'segments': all_segments,
            'transcription': full_transcription
        }

    def _split_audio_file(self, audio_file_path, chunk_duration=30):
        """Teilt Audio-Datei in Chunks auf"""
        chunks = []
        try:
            audio, sr = sf.read(audio_file_path)
            chunk_samples = int(chunk_duration * sr)

            for i in range(0, len(audio), chunk_samples):
                chunk = audio[i:i + chunk_samples]
                chunk_path = audio_file_path.replace('.wav', f'_chunk_{i // chunk_samples}.wav')
                sf.write(chunk_path, chunk, sr)
                chunks.append(chunk_path)

            self._log(f"Audio in {len(chunks)} Chunks aufgeteilt", "INFO")
            return chunks

        except Exception as e:
            self._log(f"Fehler beim Aufteilen der Audio-Datei: {e}", "ERROR")
            return [audio_file_path]

    def _parse_response(self, resp):
        """Parst die Antwort von WhisperX"""
        try:
            response_data = resp.json()
            self._log("Server-Antwort erhalten", "SUCCESS")

            # Debugging: Prüfen, welche Felder in der Antwort enthalten sind
            self._log(f"Antwort-Felder: {', '.join(response_data.keys())}", "INFO")

            # Flexible Extraktion der Daten
            full_transcription = response_data.get("transcription", response_data.get("text", ""))
            segments = response_data.get("segments", [])

            # Verarbeite Segmente
            processed_segments = []
            if segments:
                self._log(f"Verarbeite {len(segments)} Segmente...", "INFO")

                for segment in segments:
                    # Extrahiere Sprecher-Info falls vorhanden
                    speaker = segment.get("speaker", "SPEAKER_0")

                    # Wenn WhisperX keine Sprecher zurückgibt, alterniere zwischen SPEAKER_0 und SPEAKER_1
                    if speaker == "SPEAKER_0" and settings.WHISPERX_ENABLE_DIARIZATION:
                        # Einfache Heuristik: wechsle Sprecher bei größeren Pausen
                        if processed_segments:
                            last_end = processed_segments[-1]['end']
                            current_start = segment.get('start', 0)
                            if current_start - last_end > 2.0:  # Pause > 2 Sekunden
                                speaker = "SPEAKER_1" if processed_segments[-1][
                                                             'speaker'] == "SPEAKER_0" else "SPEAKER_0"

                    processed_segment = {
                        'start': segment.get('start', 0),
                        'end': segment.get('end', 0),
                        'speaker': speaker,
                        'text': segment.get('text', ''),
                        'duration': segment.get('end', 0) - segment.get('start', 0)
                    }
                    processed_segments.append(processed_segment)

            # Erstelle Transkription mit Sprecher-Labels
            labeled_transcription = self._create_labeled_transcription(processed_segments)

            # Rückgabedaten zusammenstellen
            result = {
                'full_text': full_transcription,
                'labeled_text': labeled_transcription,
                'segments': processed_segments,
                'transcription': full_transcription
            }

            self._log(f"Verarbeitung abgeschlossen: {len(processed_segments)} Segmente", "SUCCESS")
            return result

        except json.JSONDecodeError as e:
            self._log(f"Ungültige JSON-Antwort vom Server: {e}", "ERROR")
            self._log(f"Server-Antwort (erste 500 Zeichen): {resp.text[:500]}", "ERROR")
            raise Exception(f"Ungültige JSON-Antwort: {e}")

    def _create_labeled_transcription(self, segments):
        """Erstellt eine formatierte Transkription mit Sprecher-Labels"""
        if not segments:
            return "Keine Segmente verfügbar."

        try:
            labeled_text = []
            current_speaker = None

            # Gruppiere nach Sprechern in chronologischer Reihenfolge
            for segment in segments:
                speaker = segment['speaker']
                text = segment.get('text', '')

                # Skip leere Segmente
                if not text.strip():
                    continue

                # Neuen Sprecher mit eigenem Label beginnen
                if speaker != current_speaker:
                    current_speaker = speaker
                    labeled_text.append(f"\n[{speaker}]: ")

                # Text hinzufügen
                labeled_text.append(text + " ")

            return "".join(labeled_text).strip()

        except Exception as e:
            self._log(f"Fehler in _create_labeled_transcription: {str(e)}", "ERROR")
            traceback.print_exc()
            return "Fehler bei der Erstellung der Transkription."