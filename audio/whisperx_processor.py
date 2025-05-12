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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import settings


class WhisperXProcessor:
    def __init__(self, logger=None):
        self.logger = logger
        self.session = self._create_session()

    def _create_session(self):
        """Erstellt eine Session mit Retry-Strategie"""
        session = requests.Session()

        # Retry-Strategie definieren - kompatibel mit verschiedenen urllib3-Versionen
        try:
            # Versuche neuere urllib3-Version (>= 1.26)
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["POST"]
            )
        except TypeError:
            # Fallback für ältere urllib3-Version (< 1.26)
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

    def process_complete_audio(self, audio_file_path):
        """
        Verarbeitet Audio-Datei mit WhisperX API
        """
        try:
            # Prüfe zunächst, ob die Datei existiert und nicht leer ist
            if not os.path.exists(audio_file_path):
                self._log(f"Audio-Datei nicht gefunden: {audio_file_path}", "ERROR")
                raise FileNotFoundError(f"Audio-Datei nicht gefunden: {audio_file_path}")

            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                self._log("Audio-Datei ist leer", "ERROR")
                raise ValueError("Audio-Datei ist leer")

            # Prüfe Dateigröße (WhisperX hat möglicherweise Limits)
            max_size_mb = 50  # 50MB Limit
            if file_size > max_size_mb * 1024 * 1024:
                self._log(f"Audio-Datei zu groß ({file_size / 1024 / 1024:.1f}MB). Maximum: {max_size_mb}MB", "WARNING")
                # Komprimiere oder teile die Datei auf
                audio_file_path = self._compress_audio(audio_file_path)
                file_size = os.path.getsize(audio_file_path)

            self._log(f"Verarbeite Audio-Datei: {audio_file_path} ({file_size / 1024 / 1024:.2f} MB)", "INFO")

            # Health Check der API
            if not self._check_api_health():
                self._log("WhisperX-API Health Check fehlgeschlagen", "WARNING")

            # Transkription mit WhisperX anfordern
            self._log(f"Sende Anfrage an WhisperX-Server: {settings.WHISPERX_API_URL}", "INFO")

            # Verwende streaming upload für große Dateien
            if file_size > 10 * 1024 * 1024:  # Größer als 10MB
                return self._process_large_file(audio_file_path)
            else:
                return self._process_standard_file(audio_file_path)

        except Exception as e:
            self._log(f"Fehler in process_complete_audio: {str(e)}", "ERROR")
            traceback.print_exc()
            # Fallback: Rückgabe nur mit Fehlermeldung
            return {
                'full_text': "",
                'labeled_text': "",
                'segments': [],
                'transcription': f"Fehler bei der Verarbeitung: {str(e)}"
            }

    def _check_api_health(self):
        """Überprüft, ob die WhisperX-API verfügbar ist"""
        try:
            health_url = settings.WHISPERX_API_URL.replace('/transcribe', '/health')
            resp = self.session.get(health_url, timeout=5)
            return resp.ok
        except:
            return False

    def _compress_audio(self, audio_file_path):
        """Komprimiert Audio-Datei falls zu groß"""
        try:
            self._log("Komprimiere Audio-Datei...", "INFO")

            # Lade Audio und konvertiere zu niedriger Qualität
            audio, sr = sf.read(audio_file_path)

            # Reduziere Sample Rate falls nötig
            if sr > 16000:
                import librosa
                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
                sr = 16000

            # Konvertiere zu Mono falls Stereo
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)

            # Speichere komprimierte Version
            compressed_path = audio_file_path.replace('.wav', '_compressed.wav')
            sf.write(compressed_path, audio, sr)

            self._log(f"Audio komprimiert: {os.path.getsize(compressed_path) / 1024 / 1024:.2f} MB", "INFO")
            return compressed_path

        except Exception as e:
            self._log(f"Fehler bei Audio-Komprimierung: {e}", "WARNING")
            return audio_file_path

    def _process_standard_file(self, audio_file_path):
        """Verarbeitet Standard-Dateien"""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                with open(audio_file_path, "rb") as vf:
                    # WhisperX-API Parameter
                    files = {"file": (os.path.basename(audio_file_path), vf, "audio/wav")}
                    data = {
                        "language": settings.WHISPERX_LANGUAGE,
                        "compute_type": settings.WHISPERX_COMPUTE_TYPE,
                        "enable_diarization": str(settings.WHISPERX_ENABLE_DIARIZATION).lower(),
                        "return_segments": "true",
                        "return_word_timestamps": "true"
                    }

                    self._log(f"Sende Datei an WhisperX (Versuch {attempt + 1}/{max_retries})...", "INFO")

                    # Request mit erweiterten Timeouts
                    resp = self.session.post(
                        settings.WHISPERX_API_URL,
                        files=files,
                        data=data,
                        timeout=(30, 300),  # (Connect Timeout, Read Timeout)
                        stream=False
                    )

                if not resp.ok:
                    if attempt < max_retries - 1:
                        self._log(
                            f"Fehler vom Server (Status: {resp.status_code}), wiederhole in {retry_delay} Sekunden...",
                            "WARNING")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        self._log(f"Fehler vom Server: {resp.status_code} - {resp.text[:200]}", "ERROR")
                        raise Exception(f"WhisperX-Fehler: {resp.status_code}")
                else:
                    # Erfolgreicher Request
                    return self._parse_response(resp)

            except requests.exceptions.ConnectionError as e:
                if "RemoteDisconnected" in str(e):
                    self._log(f"Server hat Verbindung abgebrochen bei Versuch {attempt + 1}", "WARNING")
                    # Erhöhe Retry-Delay für Connection-Abbrüche
                    time.sleep(retry_delay * 2)
                    retry_delay *= 2
                    if attempt < max_retries - 1:
                        continue
                raise Exception(f"Verbindung zum Server abgebrochen: {e}")

            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    self._log(f"Timeout bei Versuch {attempt + 1}, wiederhole...", "WARNING")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise Exception(f"Timeout nach {max_retries} Versuchen: {e}")

            except Exception as e:
                if attempt < max_retries - 1:
                    self._log(f"Unbekannter Fehler bei Versuch {attempt + 1}: {str(e)}, wiederhole...", "WARNING")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise

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