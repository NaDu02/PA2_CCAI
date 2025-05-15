# audio/diarization_processor.py
"""
Lokaler Diarization-Processor als Fallback für API-Ausfälle
Kombiniert lokale Sprechererkennung mit einfacher Transkription
"""
import os
import time
import traceback
from .simple_speaker_diarization import SimpleSpeakerDiarizer


class DiarizationProcessor:
    """
    Lokaler Fallback-Processor für Sprechererkennung
    Verwendet only lokale Komponenten - keine API-Abhängigkeiten
    """

    def __init__(self, logger=None):
        self.diarizer = SimpleSpeakerDiarizer()
        self.logger = logger

    def _log(self, message, level="INFO"):
        """Zentrale Logging-Methode"""
        if self.logger:
            self.logger.log_message(message, level)
        else:
            print(f"[{level}] {message}")

    def process_complete_audio(self, audio_file_path):
        """
        Lokale Verarbeitung als Fallback für API-Ausfälle
        Führt nur Sprechererkennung durch - keine Transkription

        Args:
            audio_file_path: Pfad zur Audio-Datei

        Returns:
            Dict mit Diarization-Ergebnissen (ohne Transkription)
        """
        start_time = time.time()

        try:
            # Datei-Validierung
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio-Datei nicht gefunden: {audio_file_path}")

            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                raise ValueError("Audio-Datei ist leer")

            self._log(f"Lokale Diarization: {audio_file_path} ({file_size / 1024 / 1024:.2f} MB)", "INFO")
            self._log("⚠️ Hinweis: Nur Sprechererkennung - keine Transkription im Fallback-Modus", "WARNING")

            # Lokale Sprechererkennung durchführen
            speaker_segments = self.diarizer.process_audio(audio_file_path)

            if not speaker_segments:
                self._log("Keine Sprecher erkannt", "WARNING")
                return self._create_fallback_result("Keine Sprecher erkannt")

            # Verarbeitung erfolgreich
            processing_time = time.time() - start_time
            self._log(f"Lokale Diarization abgeschlossen in {processing_time:.2f}s", "SUCCESS")

            # Erstelle Ergebnis-Struktur
            speakers = set(seg['speaker'] for seg in speaker_segments)
            self._log(f"Erkannte Sprecher: {len(speakers)}", "INFO")

            # Erstelle formatierte Ausgabe
            labeled_transcription = self._create_speaker_timeline(speaker_segments)

            # Statistiken berechnen
            total_duration = max(seg['end'] for seg in speaker_segments) if speaker_segments else 0
            speaker_stats = self._calculate_speaker_statistics(speaker_segments, total_duration)

            # Log Statistiken
            for speaker, percentage in speaker_stats.items():
                self._log(f"{speaker}: {percentage:.1f}% der Sprechzeit", "INFO")

            return {
                'full_text': "Keine Transkription im Fallback-Modus - nur Sprechererkennung",
                'labeled_text': labeled_transcription,
                'segments': speaker_segments,
                'transcription': f"Lokale Diarization abgeschlossen. {len(speakers)} Sprecher erkannt.",
                'speaker_count': len(speakers),
                'total_duration': total_duration,
                'processing_mode': 'local_fallback'
            }

        except Exception as e:
            self._log(f"Fehler bei lokaler Diarization: {str(e)}", "ERROR")
            traceback.print_exc()
            return self._create_fallback_result(f"Fehler: {str(e)}")

    def _create_speaker_timeline(self, segments):
        """
        Erstellt eine Timeline der Sprecher ohne Transkription

        Args:
            segments: Liste der Sprecher-Segmente

        Returns:
            Formatierte Timeline als String
        """
        if not segments:
            return "Keine Sprecher-Segmente gefunden"

        timeline = ["=== Sprecher-Timeline (ohne Transkription) ===\n"]

        current_speaker = None
        for segment in segments:
            speaker = segment['speaker']
            start_time = segment['start']
            end_time = segment['end']
            duration = segment['duration']

            # Sprecherwechsel markieren
            if speaker != current_speaker:
                current_speaker = speaker
                timeline.append(f"\n[{speaker}]:")

            # Zeit-Segment hinzufügen
            timeline.append(f"  {start_time:.1f}s - {end_time:.1f}s ({duration:.1f}s)")

        timeline.append(f"\n\n📊 Zusammenfassung: {len(set(s['speaker'] for s in segments))} Sprecher erkannt")
        return "\n".join(timeline)

    def _calculate_speaker_statistics(self, segments, total_duration):
        """
        Berechnet Sprecher-Statistiken

        Args:
            segments: Liste der Sprecher-Segmente
            total_duration: Gesamtdauer

        Returns:
            Dict mit Sprecher -> Prozent-Anteil
        """
        speaker_times = {}

        for segment in segments:
            speaker = segment['speaker']
            duration = segment['duration']

            if speaker in speaker_times:
                speaker_times[speaker] += duration
            else:
                speaker_times[speaker] = duration

        # Berechne Prozentsätze
        speaker_percentages = {}
        for speaker, time_spent in speaker_times.items():
            percentage = (time_spent / total_duration * 100) if total_duration > 0 else 0
            speaker_percentages[speaker] = percentage

        return speaker_percentages

    def _create_fallback_result(self, error_message):
        """
        Erstellt ein Fallback-Ergebnis bei Fehlern

        Args:
            error_message: Fehlermeldung

        Returns:
            Standard-Ergebnis-Dictionary
        """
        return {
            'full_text': f"Lokaler Fallback fehlgeschlagen: {error_message}",
            'labeled_text': f"❌ {error_message}",
            'segments': [],
            'transcription': f"Fehler bei lokaler Verarbeitung: {error_message}",
            'speaker_count': 0,
            'total_duration': 0,
            'processing_mode': 'local_fallback_failed'
        }

    def add_transcription_to_segments(self, segments, full_transcription):
        """
        Hilfsmethode um externe Transkription zu Segmenten hinzuzufügen
        Kann verwendet werden wenn Transkription von anderer Quelle kommt

        Args:
            segments: Sprecher-Segmente
            full_transcription: Volltext-Transkription

        Returns:
            Segments mit angehängter Transkription (heuristisch)
        """
        if not segments or not full_transcription:
            return segments

        # Einfache Heuristik: Teile Text auf Segmente auf
        # (In produktivem Code würde man hier sophisticated matching verwenden)
        sentences = self._split_transcription(full_transcription)

        enhanced_segments = []
        for i, segment in enumerate(segments):
            # Versuche Satz zuzuordnen (sehr einfache Heuristik)
            if i < len(sentences):
                segment = segment.copy()
                segment['text'] = sentences[i]
            enhanced_segments.append(segment)

        return enhanced_segments

    def _split_transcription(self, text):
        """
        Teilt Transkription in Sätze auf

        Args:
            text: Volltext

        Returns:
            Liste von Sätzen
        """
        import re
        # Einfache Satz-Trennung an Satzzeichen
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]