# audio/summarization_client.py
"""
Verbesserter Client für den Summarization Service mit Pre-Processing
"""
import requests
import logging
import re
from typing import Dict, Optional
from config import settings

logger = logging.getLogger(__name__)


class SummarizationClient:
    """Verbesserter Client für die Kommunikation mit dem Summarization Service"""

    def __init__(self, service_url: str = None, logger=None):
        # Verwende die URL aus settings.py, wenn keine explizite URL übergeben wurde
        self.service_url = service_url if service_url is not None else settings.SUMMARIZATION_SERVICE_URL
        self.logger = logger
        self._health_check_done = False

    def _log(self, message: str, level: str = "INFO"):
        """Logging-Hilfsmethode"""
        if self.logger:
            self.logger.log_message(message, level)
        else:
            print(f"[{level}] {message}")

    def check_service_health(self) -> bool:
        """Überprüft, ob der Summarization Service verfügbar ist"""
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            if response.ok:
                health_data = response.json()
                status = health_data.get('status', 'unknown')

                if status == 'healthy':
                    self._log("✅ Summarization Service ist verfügbar", "SUCCESS")
                    self._health_check_done = True
                    return True
                elif status == 'degraded':
                    self._log("⚠️ Summarization Service läuft, aber mit Problemen", "WARNING")
                    # Versuche trotzdem zu verwenden
                    return True
                else:
                    self._log(f"❌ Summarization Service Status: {status}", "ERROR")
                    return False
            else:
                self._log(f"❌ Summarization Service HTTP {response.status_code}", "ERROR")
                return False
        except requests.exceptions.ConnectionError:
            self._log("❌ Kann nicht mit Summarization Service verbinden", "ERROR")
            return False
        except Exception as e:
            self._log(f"❌ Fehler bei Health Check: {str(e)}", "ERROR")
            return False

    def summarize_conversation(self, transcript_data: Dict) -> Optional[Dict]:
        """
        Erstellt eine verbesserte Zusammenfassung der Konversation

        Args:
            transcript_data: Dictionary mit Transkriptionsdaten

        Returns:
            Dictionary mit detaillierter Zusammenfassung oder None bei Fehler
        """
        try:
            # Führe Health Check durch falls noch nicht gemacht
            if not self._health_check_done:
                if not self.check_service_health():
                    return None

            # Pre-Processing der Daten für bessere Ergebnisse
            processed_data = self._preprocess_transcript_data(transcript_data)

            self._log("Sende optimierte Daten an Summarization Service...", "INFO")

            # Verwende den /summarize Endpunkt für vollständige Zusammenfassung
            response = requests.post(
                f"{self.service_url}/summarize",
                json=processed_data,
                timeout=60,  # Erhöhter Timeout für detailliertere Verarbeitung
                headers={'Content-Type': 'application/json'}
            )

            if response.ok:
                result = response.json()

                # Post-Processing der Ergebnisse
                enhanced_result = self._postprocess_summary(result, transcript_data)

                self._log("✅ Detaillierte Zusammenfassung erfolgreich erhalten", "SUCCESS")
                return enhanced_result
            else:
                error_msg = f"Fehler bei Zusammenfassung: {response.status_code}"
                try:
                    error_detail = response.json().get('detail', 'Unbekannter Fehler')
                    error_msg += f" - {error_detail}"
                except:
                    pass

                self._log(error_msg, "ERROR")
                return None

        except requests.exceptions.Timeout:
            self._log("⏱️ Timeout bei Zusammenfassung (längere Verarbeitung)", "ERROR")
            return None
        except requests.exceptions.ConnectionError:
            self._log("❌ Verbindungsfehler zu Summarization Service", "ERROR")
            return None
        except Exception as e:
            self._log(f"❌ Unerwarteter Fehler bei Zusammenfassung: {str(e)}", "ERROR")
            return None

    def _preprocess_transcript_data(self, transcript_data: Dict) -> Dict:
        """
        Pre-Processing der Transkriptionsdaten für bessere Zusammenfassungen
        """
        processed_data = transcript_data.copy()

        # 1. Verbessere den Text für bessere Analyse
        if 'labeled_text' in processed_data and processed_data['labeled_text']:
            # Bereinige und strukturiere den Text
            cleaned_text = self._clean_transcript_text(processed_data['labeled_text'])
            processed_data['labeled_text'] = cleaned_text
            processed_data['cleaned_for_analysis'] = True

        # 2. Füge Segment-Analyse hinzu
        if 'segments' in processed_data and processed_data['segments']:
            # Berechne Sprecher-Statistiken
            speaker_stats = self._calculate_speaker_statistics(processed_data['segments'])
            processed_data['speaker_statistics'] = speaker_stats

            # Identifiziere längere Monologe
            long_segments = [seg for seg in processed_data['segments'] if seg.get('duration', 0) > 10]
            if long_segments:
                processed_data['has_long_segments'] = True
                processed_data['long_segment_count'] = len(long_segments)

        # 3. Füge Kontext-Informationen hinzu
        processed_data['analysis_context'] = {
            'total_speakers': len(set(seg.get('speaker', 'UNKNOWN') for seg in processed_data.get('segments', []))),
            'estimated_duration': f"{self._estimate_conversation_duration(processed_data.get('segments', [])):.1f}",
            # Als String
            'conversation_type': self._detect_conversation_type(processed_data),
            'language': 'german',  # Für bessere deutsche Analyse
            'detailed_analysis_requested': True
        }

        return processed_data

    def _clean_transcript_text(self, text: str) -> str:
        """Bereinigt und strukturiert den Transkriptions-Text"""
        if not text:
            return text

        # Entferne übermäßige Leerzeichen
        text = re.sub(r'\s+', ' ', text)

        # Verbessere Sprecher-Labels
        text = re.sub(r'\[([^]]+)\]:', r'\n[\1]:', text)

        # Füge Absätze zwischen Sprechern hinzu
        text = re.sub(r'(\[SPEAKER_\d+\]:)', r'\n\1', text)

        # Entferne überflüssige Newlines
        text = re.sub(r'\n+', '\n', text)

        return text.strip()

    def _calculate_speaker_statistics(self, segments: list) -> dict:
        """Berechnet detaillierte Sprecher-Statistiken"""
        speaker_stats = {}
        total_duration = 0

        for segment in segments:
            speaker = segment.get('speaker', 'UNKNOWN')
            duration = segment.get('duration', 0)
            text = segment.get('text', '')
            word_count = len(text.split()) if text else 0

            if speaker not in speaker_stats:
                speaker_stats[speaker] = {
                    'total_time': 0,
                    'word_count': 0,
                    'segment_count': 0,
                    'avg_words_per_segment': 0
                }

            speaker_stats[speaker]['total_time'] += duration
            speaker_stats[speaker]['word_count'] += word_count
            speaker_stats[speaker]['segment_count'] += 1
            total_duration += duration

        # Berechne erweiterte Statistiken - ALLES ALS STRINGS
        for speaker, stats in speaker_stats.items():
            if stats['segment_count'] > 0:
                stats['avg_words_per_segment'] = stats['word_count'] / stats['segment_count']
                stats['time_percentage'] = (stats['total_time'] / total_duration * 100) if total_duration > 0 else 0
                stats['words_per_minute'] = (stats['word_count'] / (stats['total_time'] / 60)) if stats[
                                                                                                      'total_time'] > 0 else 0

                # Klassifiziere Beteiligung
                if stats['time_percentage'] > 40:
                    stats['participation_level'] = 'hoch'
                elif stats['time_percentage'] > 20:
                    stats['participation_level'] = 'mittel'
                else:
                    stats['participation_level'] = 'niedrig'

                # FIX: Konvertiere alle numerischen Werte zu Strings
                stats['total_time_str'] = f"{stats['total_time']:.1f}"
                stats['time_percentage_str'] = f"{stats['time_percentage']:.1f}"
                stats['words_per_minute_str'] = f"{stats['words_per_minute']:.1f}"
                stats['avg_words_per_segment_str'] = f"{stats['avg_words_per_segment']:.1f}"

        return speaker_stats

    def _estimate_conversation_duration(self, segments: list) -> float:
        """Schätzt die Gesamtdauer der Konversation"""
        if not segments:
            return 0

        max_end = max(seg.get('end', 0) for seg in segments)
        return max_end

    def _detect_conversation_type(self, transcript_data: dict) -> str:
        """Erkennt den Typ der Konversation für kontextuelle Analyse"""
        text = transcript_data.get('labeled_text', '') or transcript_data.get('full_text', '')
        text_lower = text.lower()

        # Business-Keywords
        business_keywords = ['meeting', 'projekt', 'task', 'deadline', 'budget', 'team', 'kunde', 'client']
        technical_keywords = ['code', 'bug', 'feature', 'development', 'testing', 'deployment']
        planning_keywords = ['plan', 'strategy', 'goal', 'objective', 'timeline', 'milestone']

        business_count = sum(1 for keyword in business_keywords if keyword in text_lower)
        technical_count = sum(1 for keyword in technical_keywords if keyword in text_lower)
        planning_count = sum(1 for keyword in planning_keywords if keyword in text_lower)

        if business_count > technical_count and business_count > planning_count:
            return 'business_meeting'
        elif technical_count > planning_count:
            return 'technical_discussion'
        elif planning_count > 0:
            return 'planning_session'
        else:
            return 'general_conversation'

    def _postprocess_summary(self, summary: dict, original_data: dict) -> dict:
        """Post-Processing der Zusammenfassung für bessere Präsentation"""
        if not summary:
            return summary

        # Füge Original-Statistiken hinzu
        if 'segments' in original_data:
            segments = original_data['segments']
            total_duration = self._estimate_conversation_duration(segments)

            summary['conversation_metrics'] = {
                'total_segments': len(segments),
                'unique_speakers': len(set(seg.get('speaker', 'UNKNOWN') for seg in segments)),
                'total_words': sum(len(seg.get('text', '').split()) for seg in segments),
                # FIX: Alle numerischen Werte als Strings
                'estimated_duration_minutes': f"{total_duration / 60:.1f}",
                'duration_estimate': f"{total_duration:.1f}s"
            }

        # Validiere und verbessere To-Dos
        if 'todos' in summary:
            summary['todos'] = self._enhance_todos(summary['todos'])

        # Füge Zusammenfassungsstatistiken hinzu - ALLES ALS STRINGS
        summary_stats = {
            'main_points_count': str(len(summary.get('summary', {}).get('main_points', []))),
            'todos_count': str(len(summary.get('todos', []))),
            'participants_count': str(len(summary.get('participants', []))),
            'quality_score': str(self._calculate_quality_score(summary))
        }
        summary['summary_statistics'] = summary_stats

        # FIX: Konvertiere alle participant statistics zu Strings
        if 'participants' in summary:
            for participant in summary['participants']:
                if 'statistics' in participant:
                    stats = participant['statistics']
                    # Konvertiere alle numerischen Werte zu Strings
                    for key, value in stats.items():
                        if isinstance(value, (int, float)):
                            stats[key] = f"{value:.1f}"

        return summary

    def _enhance_todos(self, todos: list) -> list:
        """Verbessert die To-Do-Einträge mit zusätzlichen Informationen"""
        enhanced_todos = []

        for idx, todo in enumerate(todos):
            enhanced_todo = todo.copy()

            # Füge ID hinzu falls nicht vorhanden
            if 'id' not in enhanced_todo:
                enhanced_todo['id'] = f"TODO_{idx + 1}"

            # Verbessere Prioritäts-Bewertung
            task_text = enhanced_todo.get('task', '').lower()
            if any(urgent_word in task_text for urgent_word in ['sofort', 'urgent', 'asap', 'heute']):
                enhanced_todo['priority'] = 'hoch'
            elif 'deadline' in enhanced_todo and enhanced_todo['deadline'] != 'nicht spezifiziert':
                # Hat ein Deadline = mittlere Priorität
                if enhanced_todo['priority'] == 'niedrig':
                    enhanced_todo['priority'] = 'mittel'

            # Schätze Aufwand falls nicht vorhanden
            if 'estimated_effort' not in enhanced_todo:
                # Grobe Schätzung basierend auf Task-Beschreibung
                task_length = len(enhanced_todo.get('task', ''))
                if task_length > 100:
                    enhanced_todo['estimated_effort'] = 'hoch'
                elif task_length > 50:
                    enhanced_todo['estimated_effort'] = 'mittel'
                else:
                    enhanced_todo['estimated_effort'] = 'niedrig'

            enhanced_todos.append(enhanced_todo)

        return enhanced_todos

    def _calculate_quality_score(self, summary: dict) -> int:
        """Berechnet einen Qualitätsscore für die Zusammenfassung (0-100)"""
        score = 0

        # Basis-Score für Vollständigkeit
        if summary.get('summary', {}).get('main_points'):
            score += 20
            # Bonus für detaillierte Punkte
            main_points = summary['summary']['main_points']
            avg_length = sum(len(point.split()) for point in main_points) / len(main_points)
            if avg_length > 10:
                score += 10

        if summary.get('todos'):
            score += 20
            # Bonus für detaillierte To-Dos
            for todo in summary['todos']:
                if len(todo.get('task', '').split()) > 5:
                    score += 2
                if todo.get('deadline') != 'nicht spezifiziert':
                    score += 2
                if todo.get('assigned_to') != 'nicht zugewiesen':
                    score += 2

        if summary.get('participants'):
            score += 15

        if summary.get('sentiment'):
            score += 5

        if summary.get('next_steps'):
            score += 10

        # Bonus für zusätzliche Felder
        bonus_fields = ['open_questions', 'agreements_and_commitments', 'key_takeaways']
        for field in bonus_fields:
            if summary.get(field):
                score += 5

        return min(score, 100)


# Globaler Client für die Anwendung
summarization_client = SummarizationClient(logger=None)