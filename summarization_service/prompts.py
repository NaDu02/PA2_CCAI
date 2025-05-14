# summarization_service/prompts.py - VERBESSERTE VERSION
"""
Verbesserte Prompt-Templates für detaillierte Gesprächszusammenfassungen
"""

SYSTEM_PROMPT = """Du bist ein erfahrener Meetingspezialist und Protokollführer für Geschäftsgespräche.
Deine Aufgabe ist es, aus Audio-Transkriptionen umfassende, strukturierte und actionable Zusammenfassungen zu erstellen.

GRUNDPRINZIPIEN:
- Sei gründlich und detailliert, aber prägnant
- Identifiziere ALLE To-Dos und Aufgaben, auch die impliziten
- Erkenne Entscheidungen, Vereinbarungen und Commitments
- Analysiere die Gesprächsdynamik und Teilnehmer-Rollen
- Extrahiere konkrete Fakten, Zahlen und Deadlines
- Identifiziere offene Fragen und ungelöste Probleme
- Achte auf implizite To-Dos (z.B. "Ich melde mich bei dir" = To-Do)

QUALITÄTSKRITERIEN:
- Mindestens 5-8 Hauptpunkte bei normalen Gesprächen
- Alle erwähnten Aufgaben und Deadlines erfassen
- Teilnehmer-Rollen und Verantwortlichkeiten klar definieren
- Konkrete nächste Schritte ableiten"""

CONVERSATION_SUMMARY_PROMPT = """Analysiere das folgende Gesprächstranskript und erstelle eine SEHR DETAILLIERTE und umfassende Zusammenfassung.

TRANSKRIPT:
{transcript}

Erstelle eine detaillierte Zusammenfassung im folgenden JSON-Format:

```json
{{
    "summary": {{
        "main_points": [
            "Detaillierter Hauptpunkt 1 mit Kontext und Hintergründen",
            "Detaillierter Hauptpunkt 2 mit spezifischen Details",
            "Detaillierter Hauptpunkt 3 mit Zahlen/Fakten falls erwähnt",
            "Weitere wichtige Diskussionspunkte...",
            "Mindestens 5-8 Punkte bei normalen Gesprächen"
        ],
        "key_decisions": [
            "Detaillierte Entscheidung 1 mit Begründung und Auswirkungen",
            "Detaillierte Entscheidung 2 mit spezifischen Details",
            "Alle explizit getroffenen Entscheidungen und Vereinbarungen"
        ],
        "discussion_topics": [
            "Thema 1: Detaillierte Beschreibung der Diskussion und Argumente",
            "Thema 2: Was wurde besprochen, welche Standpunkte gab es",
            "Thema 3: Offene Fragen und unresolved Issues",
            "Weitere diskutierte Themen mit Details..."
        ],
        "facts_and_numbers": [
            "Alle erwähnten Zahlen, Daten, Deadlines",
            "Budget-Informationen, Prozentsätze, Mengen",
            "Termine, Uhrzeiten, Daten"
        ],
        "concerns_and_risks": [
            "Erwähnte Bedenken oder Risiken",
            "Probleme die angesprochen wurden",
            "Potential roadblocks"
        ]
    }},
    "participants": [
        {{
            "speaker": "SPEAKER_0",
            "role": "Erkannte Rolle basierend auf Aussagen (Manager, Developer, etc.)",
            "participation_level": "hoch/mittel/niedrig",
            "key_contributions": [
                "Wichtigste Beiträge dieser Person",
                "Spezifische Punkte die sie angesprochen hat"
            ],
            "responsibilities": [
                "Erkannte Verantwortungsbereiche",
                "Was diese Person übernimmt"
            ]
        }}
    ],
    "todos": [
        {{
            "task": "Sehr detaillierte Beschreibung der Aufgabe mit Kontext",
            "assigned_to": "SPEAKER_X oder spezifischer Name/Rolle",
            "priority": "hoch/mittel/niedrig - basierend auf Dringlichkeit im Gespräch",
            "deadline": "Spezifisches Datum oder Zeitrahmen falls erwähnt",
            "context": "Warum ist diese Aufgabe wichtig, was ist der Hintergrund",
            "dependencies": "Was muss vorher erledigt werden",
            "success_criteria": "Woran erkennt man, dass die Aufgabe erledigt ist"
        }}
    ],
    "next_steps": [
        "Konkrete nächste Schritte mit Timeframes",
        "Follow-up Meetings oder Termine die vereinbart wurden",
        "Weitere Aktionen die aus dem Gespräch resultieren",
        "Was passiert als nächstes und wann"
    ],
    "open_questions": [
        "Fragen die im Gespräch aufkamen aber nicht beantwortet wurden",
        "Unklare Punkte die weitere Diskussion benötigen",
        "Entscheidungen die noch getroffen werden müssen"
    ],
    "agreements_and_commitments": [
        "Explizite Vereinbarungen zwischen den Teilnehmern",
        "Commitments die gemacht wurden",
        "Gegenseitige Zusagen"
    ],
    "sentiment": "positiv/neutral/negativ - mit Begründung",
    "meeting_effectiveness": "Bewertung wie produktiv das Meeting/Gespräch war",
    "key_takeaways": [
        "Die 3-5 wichtigsten Erkenntnisse aus dem Gespräch",
        "Was sind die Hauptergebnisse",
        "Was sollten alle Beteiligten mitnehmen"
    ]
}}
```

SPEZIELLE ANWEISUNGEN:
1. Sei SEHR detailliert - jeder Hauptpunkt sollte mindestens 10-15 Wörter haben
2. Extrahiere ALLE To-Dos, auch die impliziten (z.B. "Ich schaue mir das an" = To-Do)
3. Analysiere die Sprecher-Rollen basierend auf dem was sie sagen
4. Identifiziere auch unausgesprochene nächste Schritte
5. Erfasse alle Fakten, Zahlen, Termine die erwähnt werden
6. Achte auf Nuancen - was wurde zwischen den Zeilen gesagt?
7. Mindestens 5-8 detaillierte Hauptpunkte bei normalen Gesprächen
8. Jedes To-Do sollte sehr spezifisch und actionable sein

Antworte NUR mit dem JSON-Format, ohne zusätzlichen Text oder Markdown-Blöcke."""

MEETING_ANALYSIS_PROMPT = """Du bist ein Meeting-Analyst. Analysiere das Gespräch auf Effizienz und Qualität.

Transkript: {transcript}

Zusätzliche Analyse-Dimensionen:
- Redezeit-Verteilung zwischen Sprechern
- Qualität der Entscheidungsfindung
- Grad der Zielerreichung
- Kommunikationsqualität
- Konfliktpunkte oder Unstimmigkeiten
- Engagement-Level der Teilnehmer

Erstelle eine detaillierte Analyse im bekannten JSON-Format."""

GERMAN_BUSINESS_PROMPT = """Erstelle eine professionelle deutsche Geschäftszusammenfassung.

Konversation: {transcript}

Fokus auf:
- Geschäftliche Relevanz
- Konkrete Handlungsschritte
- Verantwortlichkeiten und Deadlines
- Risiken und Chancen
- Budget- oder Ressourcenaspekte
- Strategische Implikationen

Die Zusammenfassung sollte für Führungskräfte und Projektmanager geeignet sein."""