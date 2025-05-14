# summarization_service/summarization_models.py - VERBESSERTE VERSION
"""
Verbesserte Ollama Model Management für detaillierte Summarization
"""
import requests
import json
import asyncio
import aiohttp
import logging
from typing import Dict, Optional
from prompts import SYSTEM_PROMPT, CONVERSATION_SUMMARY_PROMPT, MEETING_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class OllamaClient:
    """Verbesserter Client für Ollama API mit optimierten Parametern"""

    def __init__(self, ollama_url: str = "http://ollama:11434"):
        self.base_url = ollama_url
        self.model_name = "llama3.1:8b"  # Default Modell

    async def check_model_availability(self) -> bool:
        """Prüft, ob das Modell verfügbar ist"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model['name'] for model in data.get('models', [])]
                        return self.model_name in models
            return False
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return False

    async def pull_model(self) -> bool:
        """Lädt das Modell herunter, falls es nicht vorhanden ist"""
        try:
            logger.info(f"Pulling model {self.model_name}...")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        f"{self.base_url}/api/pull",
                        json={"name": self.model_name}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Model {self.model_name} pulled successfully")
                        return True
            return False
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False

    async def generate_summary(self, transcript: str) -> Dict:
        """Generiert eine detaillierte Zusammenfassung des Transkripts"""
        try:
            # Verwende den verbesserten Prompt
            prompt = CONVERSATION_SUMMARY_PROMPT.format(transcript=transcript)

            # Optimierte Parameter für detailliertere Ausgaben
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "system": SYSTEM_PROMPT,
                    "stream": False,
                    "options": {
                        # Erhöhte Temperatur für kreativere, detailliertere Antworten
                        "temperature": 0.4,  # Erhöht von 0.2 auf 0.4
                        "top_p": 0.95,  # Erhöht von 0.9 auf 0.95
                        "top_k": 50,  # Hinzugefügt für mehr Diversität

                        # Längere Ausgaben ermöglichen
                        "num_predict": 4096,  # Verdoppelt von 2048 auf 4096
                        "num_keep": 32,  # Erhöht von 24 auf 32

                        # Wiederholung reduzieren
                        "repeat_penalty": 1.1,
                        "repeat_last_n": 256,

                        # Bessere Struktur
                        "tfs_z": 1.0,
                        "typical_p": 1.0,

                        # Längere Context-Behandlung
                        "num_ctx": 8192,  # Erhöht für längere Eingaben

                        # Spezifische Anweisungen
                        "stop": ["```", "---"]  # Stoppe bei Markdown-Blöcken
                    }
                }

                # Längeres Timeout für detailliertere Verarbeitung
                async with session.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=180)  # 3 Minuten statt 2
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        result_text = data.get('response', '')

                        # Verbesserte JSON-Extraktion
                        try:
                            # Entferne Markdown-Blöcke und bereinige
                            cleaned_text = self._clean_json_response(result_text)
                            parsed_json = json.loads(cleaned_text)

                            # Validiere die Antwort
                            if self._validate_summary_structure(parsed_json):
                                return parsed_json
                            else:
                                logger.warning("Unvollständige Zusammenfassung erhalten, versuche Nachbearbeitung...")
                                return self._enhance_partial_summary(parsed_json, transcript)

                        except json.JSONDecodeError as e:
                            logger.warning(f"Could not parse JSON: {e}")
                            # Fallback: Versuche eine strukturierte Antwort zu erzeugen
                            return self._create_fallback_summary(result_text, transcript)
                    else:
                        logger.error(f"Ollama API error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None

    def _clean_json_response(self, text: str) -> str:
        """Bereinigt die Ollama-Antwort für JSON-Parsing"""
        # Entferne Markdown-Code-Blöcke
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            if end != -1:
                text = text[start:end]
        elif '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            if end != -1:
                text = text[start:end]

        # Entferne führende/nachfolgende Whitespace
        text = text.strip()

        # Repariere häufige JSON-Probleme
        text = text.replace('",\n}', '"\n}')  # Trailing comma
        text = text.replace(',\n]', '\n]')  # Trailing comma in arrays

        return text

    def _validate_summary_structure(self, summary: dict) -> bool:
        """Validiert, ob die Zusammenfassung alle wichtigen Felder hat"""
        required_fields = ['summary', 'todos', 'participants', 'sentiment']

        # Prüfe Hauptfelder
        for field in required_fields:
            if field not in summary:
                return False

        # Prüfe ob summary detailliert genug ist
        summary_section = summary.get('summary', {})
        main_points = summary_section.get('main_points', [])

        # Mindestens 3 Hauptpunkte sollten vorhanden sein
        if len(main_points) < 3:
            return False

        # Prüfe ob die Punkte detailliert genug sind (mindestens 8 Wörter pro Punkt)
        for point in main_points:
            if len(point.split()) < 8:
                return False

        return True

    def _enhance_partial_summary(self, partial_summary: dict, transcript: str) -> dict:
        """Verbessert eine unvollständige Zusammenfassung"""
        # Füge fehlende Felder hinzu
        enhanced = {
            "summary": {
                "main_points": [],
                "key_decisions": [],
                "discussion_topics": [],
                "facts_and_numbers": [],
                "concerns_and_risks": []
            },
            "participants": [],
            "todos": [],
            "next_steps": [],
            "open_questions": [],
            "agreements_and_commitments": [],
            "sentiment": "neutral",
            "meeting_effectiveness": "nicht bewertet",
            "key_takeaways": []
        }

        # Merge mit vorhandenen Daten
        for key, value in partial_summary.items():
            if key in enhanced:
                if isinstance(value, dict) and isinstance(enhanced[key], dict):
                    enhanced[key].update(value)
                else:
                    enhanced[key] = value

        return enhanced

    def _create_fallback_summary(self, raw_text: str, transcript: str) -> dict:
        """Erstellt eine Fallback-Zusammenfassung wenn JSON-Parsing fehlschlägt"""
        logger.info("Creating fallback summary from raw text")

        # Einfache Textanalyse für Fallback
        sentences = [s.strip() for s in raw_text.split('.') if s.strip()]

        # Versuche To-Dos zu extrahieren (einfache Heuristik)
        potential_todos = []
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in
                   ['muss', 'soll', 'wird', 'erstellen', 'machen', 'überprüfen']):
                potential_todos.append({
                    "task": sentence,
                    "assigned_to": "nicht spezifiziert",
                    "priority": "mittel",
                    "deadline": "nicht spezifiziert",
                    "context": "Aus Fallback-Analyse extrahiert",
                    "dependencies": "nicht spezifiziert",
                    "success_criteria": "nicht spezifiziert"
                })

        return {
            "summary": {
                "main_points": sentences[:5] if sentences else ["Keine detaillierte Analyse möglich"],
                "key_decisions": [],
                "discussion_topics": [],
                "facts_and_numbers": [],
                "concerns_and_risks": []
            },
            "participants": [],
            "todos": potential_todos,
            "next_steps": ["Weitere Analyse des Gesprächs erforderlich"],
            "open_questions": [],
            "agreements_and_commitments": [],
            "sentiment": "neutral",
            "meeting_effectiveness": "nicht bewertbar",
            "key_takeaways": [raw_text[:200] + "..." if len(raw_text) > 200 else raw_text]
        }


class SummarizationService:
    """Verbesserter Hauptservice für detaillierte Zusammenfassungen"""

    def __init__(self, ollama_url: str = "http://ollama:11434"):
        self.ollama_client = OllamaClient(ollama_url)
        self.initialized = False

    async def initialize(self):
        """Initialisiert den Service und stellt sicher, dass das Modell verfügbar ist"""
        logger.info("Initializing enhanced summarization service...")

        # Prüfe, ob Modell verfügbar ist
        if not await self.ollama_client.check_model_availability():
            logger.info("Model not found, pulling...")
            if not await self.ollama_client.pull_model():
                raise Exception("Failed to pull model")

        self.initialized = True
        logger.info("Enhanced summarization service initialized successfully")

    async def summarize_conversation(self, transcript_data: Dict) -> Dict:
        """
        Erstellt eine detaillierte Zusammenfassung basierend auf den Transkriptionsdaten

        Args:
            transcript_data: Dictionary mit 'labeled_text', 'segments', etc.

        Returns:
            Dictionary mit detaillierter strukturierter Zusammenfassung
        """
        if not self.initialized:
            await self.initialize()

        # Extrahiere und prepare Text für bessere Summarization
        text_for_summary = self._prepare_text_for_summarization(transcript_data)

        # Generiere Zusammenfassung
        summary = await self.ollama_client.generate_summary(text_for_summary)

        if summary:
            # Ergänze Metadaten
            summary['timestamp'] = asyncio.get_event_loop().time()

            # Berechne tatsächliche Sprecher-Anzahl falls Segmente vorhanden
            if 'segments' in transcript_data:
                speakers = set(seg.get('speaker', 'UNKNOWN') for seg in transcript_data['segments'])
                summary['detected_speakers'] = list(speakers)
                summary['speaker_count'] = len(speakers)

                # Analysiere Sprechzeit-Verteilung
                speaker_stats = self._analyze_speaker_participation(transcript_data['segments'])
                summary['speaker_statistics'] = speaker_stats

            # Verbessere Participant-Informationen mit segment-basierten Insights
            summary = self._enhance_participant_info(summary, transcript_data)

            return summary
        else:
            raise Exception("Failed to generate summary")

    def _prepare_text_for_summarization(self, transcript_data: Dict) -> str:
        """Bereitet den Text optimal für die Zusammenfassung vor"""
        # Priorisiere labeled_text für bessere Speaker-Erkennung
        if 'labeled_text' in transcript_data and transcript_data['labeled_text']:
            text = transcript_data['labeled_text']
        elif 'full_text' in transcript_data:
            text = transcript_data['full_text']
        elif 'transcription' in transcript_data:
            text = transcript_data['transcription']
        else:
            raise ValueError("No suitable text found in transcript data")

        # Füge Kontext hinzu wenn Segmente verfügbar sind
        if 'segments' in transcript_data and transcript_data['segments']:
            segments = transcript_data['segments']
            total_duration = max(seg.get('end', 0) for seg in segments) if segments else 0
            speaker_count = len(set(seg.get('speaker', 'UNKNOWN') for seg in segments))

            context = f"\n\nKONTEXT: {speaker_count} Sprecher, Gesamtdauer ca. {total_duration:.1f} Sekunden\n\n"
            text = context + text

        return text

    def _analyze_speaker_participation(self, segments: list) -> dict:
        """Analysiert die Beteiligung der einzelnen Sprecher"""
        speaker_stats = {}
        total_duration = 0

        for segment in segments:
            speaker = segment.get('speaker', 'UNKNOWN')
            duration = segment.get('duration', 0)
            text = segment.get('text', '')

            if speaker not in speaker_stats:
                speaker_stats[speaker] = {
                    'total_time': 0,
                    'word_count': 0,
                    'segment_count': 0,
                    'avg_segment_length': 0
                }

            speaker_stats[speaker]['total_time'] += duration
            speaker_stats[speaker]['word_count'] += len(text.split())
            speaker_stats[speaker]['segment_count'] += 1
            total_duration += duration

        # Berechne Prozentsätze und Durchschnitte
        for speaker, stats in speaker_stats.items():
            stats['time_percentage'] = (stats['total_time'] / total_duration * 100) if total_duration > 0 else 0
            stats['avg_segment_length'] = stats['total_time'] / stats['segment_count'] if stats[
                                                                                              'segment_count'] > 0 else 0
            stats['words_per_minute'] = (stats['word_count'] / (stats['total_time'] / 60)) if stats[
                                                                                                  'total_time'] > 0 else 0

        return speaker_stats

    def _enhance_participant_info(self, summary: dict, transcript_data: dict) -> dict:
        """Verbessert die Teilnehmer-Informationen mit segment-basierten Insights"""
        if 'segments' not in transcript_data or not summary.get('participants'):
            return summary

        segments = transcript_data['segments']
        speaker_stats = summary.get('speaker_statistics', {})

        # Verbessere jeden Teilnehmer mit detaillierten Informationen
        for participant in summary['participants']:
            speaker = participant['speaker']

            if speaker in speaker_stats:
                stats = speaker_stats[speaker]

                # Bestimme Participation Level basierend auf tatsächlichen Daten
                time_percentage = stats.get('time_percentage', 0)
                if time_percentage > 40:
                    participant['participation_level'] = 'hoch'
                elif time_percentage > 20:
                    participant['participation_level'] = 'mittel'
                else:
                    participant['participation_level'] = 'niedrig'

                # Füge quantitative Daten hinzu
                participant['statistics'] = {
                    'speaking_time': f"{stats['total_time']:.1f}s ({time_percentage:.1f}%)",
                    'word_count': stats['word_count'],
                    'average_segment_length': f"{stats['avg_segment_length']:.1f}s",
                    'speaking_pace': f"{stats['words_per_minute']:.1f} Wörter/Min"
                }

        return summary


# Globaler Service-Instance
summarization_service = SummarizationService()