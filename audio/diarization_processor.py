# audio/diarization_processor.py
"""
Verbesserte Diarization-Processor mit WhisperX-Integration
"""
import numpy as np
import soundfile as sf
import requests
import io
import json
import traceback
import os
import time
from .simple_speaker_diarization import SimpleSpeakerDiarizer
from config import settings


class DiarizationProcessor:
    def __init__(self, whisper_api_url=None, diarizer=None, logger=None):
        # Verwende die neue WHISPERX_API_URL aus den Einstellungen
        self.whisper_api_url = whisper_api_url or settings.WHISPERX_API_URL
        self.diarizer = diarizer or SimpleSpeakerDiarizer()
        self.logger = logger

    def _log(self, message, level="INFO"):
        """Logging-Hilfsmethode"""
        if self.logger:
            self.logger.log_message(message, level)
        else:
            print(f"[{level}] {message}")

    def process_complete_audio(self, audio_file_path):
        """
        Optimierte Methode mit Zeitstempel-basierter Zuordnung
        """
        full_transcription = ""
        whisper_segments = []
        speaker_segments = []

        try:
            # Prüfe zunächst, ob die Datei existiert und nicht leer ist
            if not os.path.exists(audio_file_path):
                self._log(f"Audio-Datei nicht gefunden: {audio_file_path}", "ERROR")
                raise FileNotFoundError(f"Audio-Datei nicht gefunden: {audio_file_path}")

            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                self._log("Audio-Datei ist leer", "ERROR")
                raise ValueError("Audio-Datei ist leer")

            self._log(f"Verarbeite Audio-Datei: {audio_file_path} ({file_size} Bytes)", "INFO")

            # Transkription mit Zeitstempeln anfordern
            self._log(f"Anfrage an WhisperX-Server: {self.whisper_api_url}", "INFO")

            max_retries = 3
            retry_delay = 2  # Sekunden

            for attempt in range(max_retries):
                try:
                    with open(audio_file_path, "rb") as vf:
                        # WhisperX-API Parameter
                        files = {"file": (audio_file_path, vf, "audio/wav")}
                        data = {
                            "timestamps": "true",
                            "language": settings.WHISPERX_LANGUAGE,
                            "compute_type": settings.WHISPERX_COMPUTE_TYPE,
                            "enable_diarization": str(settings.WHISPERX_ENABLE_DIARIZATION).lower()
                        }

                        self._log(f"Sende Datei an WhisperX (Versuch {attempt + 1}/{max_retries})...", "INFO")

                        # Request mit Timeout
                        resp = requests.post(
                            self.whisper_api_url,
                            files=files,
                            data=data,
                            timeout=settings.WHISPERX_TIMEOUT,
                            headers={'Accept': 'application/json'}
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
                            self._log(f"Fehler vom Server: {resp.status_code} - {resp.text}", "ERROR")
                            raise Exception(f"WhisperX-Fehler: {resp.status_code}")
                    else:
                        break  # Erfolgreicher Request

                except requests.Timeout:
                    if attempt < max_retries - 1:
                        self._log(f"Timeout bei Versuch {attempt + 1}, wiederhole...", "WARNING")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        self._log("Timeout beim Senden an WhisperX-Server nach allen Versuchen", "ERROR")
                        raise Exception("Timeout beim Senden an WhisperX-Server")

                except requests.ConnectionError as e:
                    if attempt < max_retries - 1:
                        self._log(f"Verbindungsfehler bei Versuch {attempt + 1}: {str(e)}, wiederhole...", "WARNING")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        self._log(f"Verbindungsfehler zu WhisperX-Server: {e}", "ERROR")
                        raise Exception(f"Verbindungsfehler: {e}")

            # Daten aus der Antwort extrahieren
            try:
                response_data = resp.json()
            except json.JSONDecodeError as e:
                self._log(f"Ungültige JSON-Antwort vom Server: {e}", "ERROR")
                self._log(f"Server-Antwort (erste 500 Zeichen): {resp.text[:500]}", "ERROR")
                raise Exception(f"Ungültige JSON-Antwort: {e}")

            self._log("Server-Antwort erhalten", "SUCCESS")

            # Debugging: Prüfen, welche Felder in der Antwort enthalten sind
            self._log(f"Antwort-Felder: {', '.join(response_data.keys())}", "INFO")

            # Flexible Extraktion der Daten (verschiedene WhisperX-Versionen)
            full_transcription = response_data.get("transcription", response_data.get("text", ""))
            whisper_segments = response_data.get("segments", response_data.get("words", []))

            # Prüfen und erstellen von Whisper-Segmenten, falls keine in der Antwort enthalten sind
            if not whisper_segments:
                self._log("Keine Whisper-Segmente in der Antwort gefunden - erstelle eigene Segmente", "WARNING")
                # Einfache Segmentierung basierend auf Satzzeichen und Länge
                sentences = self._split_into_sentences(full_transcription)
                avg_duration = 5.0  # Annahme: durchschnittlich 5 Sekunden pro Segment

                whisper_segments = []
                start_time = 0

                for sentence in sentences:
                    # Berechne ungefähre Dauer basierend auf Wortanzahl
                    words = len(sentence.split())
                    duration = max(1.0, words * 0.5)  # ca. 0.5 Sekunden pro Wort, mindestens 1 Sekunde

                    whisper_segments.append({
                        "start": start_time,
                        "end": start_time + duration,
                        "text": sentence
                    })

                    start_time += duration
            else:
                self._log(f"Whisper-Segmente gefunden: {len(whisper_segments)}", "INFO")

            # Prüfen, ob die WhisperX-API bereits Diarization gemacht hat
            if settings.WHISPERX_ENABLE_DIARIZATION and 'speaker' in str(response_data):
                self._log("WhisperX-API hat bereits Sprechererkennung durchgeführt", "INFO")
                # Konvertiere WhisperX-Ausgabe in unser Format
                transcribed_segments = self._convert_whisperx_segments(whisper_segments)
            else:
                # Speaker Diarization durchführen (lokal)
                self._log("Starte lokale Speaker Diarization...", "INFO")
                speaker_segments = self.diarizer.process_audio(audio_file_path)

                if not speaker_segments:
                    self._log("Keine Sprecher-Segmente gefunden!", "WARNING")
                    # Probe-Segment erstellen für Debugging
                    speaker_segments = [{"start": 0, "end": 5, "speaker": "SPEAKER_0", "duration": 5}]
                else:
                    self._log(f"Sprecher-Segmente gefunden: {len(speaker_segments)}", "INFO")

                # Die Timestamps aus Whisper mit den Sprecher-Segments zuordnen
                self._log("Ordne Sprecher den Whisper-Segmenten zu...", "INFO")
                transcribed_segments = self._assign_speakers_to_whisper_segments(whisper_segments, speaker_segments)

            if not transcribed_segments:
                self._log("Keine transkribierten Segmente nach Zuordnung!", "WARNING")
            else:
                self._log(f"Transkribierte Segmente erstellt: {len(transcribed_segments)}", "INFO")

            # Sortierte Zusammenfassung erstellen
            labeled_transcription = self._create_labeled_transcription(transcribed_segments)

            # Rückgabedaten zusammenstellen
            result = {
                'full_text': full_transcription,
                'labeled_text': labeled_transcription,
                'segments': transcribed_segments,
                'transcription': full_transcription
            }

            return result

        except Exception as e:
            self._log(f"Fehler in process_complete_audio: {str(e)}", "ERROR")
            traceback.print_exc()
            # Fallback: Rückgabe nur mit Transkription
            return {
                'full_text': full_transcription if 'full_transcription' in locals() else "",
                'labeled_text': "",
                'segments': [],
                'transcription': full_transcription if 'full_transcription' in locals() else ""
            }

    def _convert_whisperx_segments(self, whisperx_segments):
        """Konvertiert WhisperX-Segmente mit Speaker-Info in unser Format"""
        result_segments = []

        for segment in whisperx_segments:
            result_segments.append({
                'start': segment.get('start', 0),
                'end': segment.get('end', 0),
                'speaker': segment.get('speaker', 'SPEAKER_0'),
                'text': segment.get('text', ''),
                'duration': segment.get('end', 0) - segment.get('start', 0)
            })

        return sorted(result_segments, key=lambda x: x['start'])

    def _split_into_sentences(self, text):
        """Teilt den Text in Sätze auf"""
        import re
        # Verbesserte Segmentierung nach deutschen Satzzeichen
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Entferne leere Sätze und sehr kurze Segmente
        return [s.strip() for s in sentences if len(s.strip()) > 2]

    def _assign_speakers_to_whisper_segments(self, whisper_segments, speaker_segments):
        """Optimierte Methode zur Zuordnung zwischen Whisper-Segments und Sprechern"""
        result_segments = []

        try:
            for whisper_seg in whisper_segments:
                # Extrahiere Zeitstempel aus Whisper-Segmenten (Namen können variieren)
                whisper_start = whisper_seg.get('start', 0)
                whisper_end = whisper_seg.get('end', 0)
                whisper_text = whisper_seg.get('text', '').strip()

                # Skip leere Segmente
                if not whisper_text:
                    continue

                # Finde den besten überlappenden Sprecher
                best_speaker = None
                best_overlap = 0

                for speaker_seg in speaker_segments:
                    # Berechne Überlappung
                    overlap_start = max(whisper_start, speaker_seg['start'])
                    overlap_end = min(whisper_end, speaker_seg['end'])
                    overlap = max(0, overlap_end - overlap_start)

                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_speaker = speaker_seg['speaker']

                # Wenn kein Überlapp gefunden, nimm den nächsten Sprecher
                if not best_speaker and speaker_segments:
                    # Finde nächstliegenden Sprecher
                    nearest_dist = float('inf')

                    for speaker_seg in speaker_segments:
                        # Abstand zum Segment berechnen
                        if whisper_end < speaker_seg['start']:
                            dist = speaker_seg['start'] - whisper_end
                        elif whisper_start > speaker_seg['end']:
                            dist = whisper_start - speaker_seg['end']
                        else:
                            dist = 0  # Überlappung

                        if dist < nearest_dist:
                            nearest_dist = dist
                            best_speaker = speaker_seg['speaker']

                    # Nur zuweisen wenn nah genug
                    if nearest_dist > 2.0:  # mehr als 2 Sekunden Abstand
                        best_speaker = "SPEAKER_0"  # Default-Sprecher

                # Wenn immer noch kein Sprecher gefunden wurde, Standard verwenden
                if not best_speaker:
                    best_speaker = "SPEAKER_0"

                # Segment hinzufügen
                result_segments.append({
                    'start': whisper_start,
                    'end': whisper_end,
                    'speaker': best_speaker,
                    'text': whisper_text,
                    'duration': whisper_end - whisper_start
                })

            # Nach Start-Zeit sortieren
            result_segments.sort(key=lambda x: x['start'])

            return result_segments

        except Exception as e:
            self._log(f"Fehler in _assign_speakers_to_whisper_segments: {str(e)}", "ERROR")
            traceback.print_exc()
            return []

    def _create_labeled_transcription(self, segments):
        """Erstellt eine formatierte Transkription mit Sprecher-Labels"""
        if not segments:
            return "Keine Sprecher-Segmente verfügbar."

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