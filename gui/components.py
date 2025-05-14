# gui/components.py - VOLLSTÄNDIGE DATEI mit BEIDEN Widgets
import tkinter as tk
from tkinter import ttk
import math


class SpeakerTimelineWidget(tk.Frame):
    def __init__(self, parent, width=600, height=60):  # Reduzierte Höhe
        super().__init__(parent)
        self.canvas = tk.Canvas(self, width=width, height=height,
                                bg='white', highlightthickness=0,  # Entfernt den Rahmen
                                bd=0, relief='flat')  # Entfernt den 3D-Effekt
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=1)  # Weniger Padding

        self.width = width
        self.height = height
        self.speaker_colors = {}
        self.color_palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE']

    def display_segments(self, segments, total_duration):
        """Zeigt die Sprecher-Segmente auf der Timeline an mit verbessertem Design"""
        self.canvas.delete("all")

        if not segments:
            return

        # Farben für Sprecher zuweisen
        speakers = list(set(seg['speaker'] for seg in segments))
        for i, speaker in enumerate(speakers):
            self.speaker_colors[speaker] = self.color_palette[i % len(self.color_palette)]

        # Verbesserte Timeline mit weniger Rand
        timeline_top = 12  # Reduziert von 20
        timeline_bottom = self.height - 20  # Mehr Platz für Zeitmarkierungen
        timeline_height = timeline_bottom - timeline_top

        # Timeline zeichnen
        for segment in segments:
            start_x = (segment['start'] / total_duration) * (self.width - 20) + 10  # 10px Rand links/rechts
            end_x = (segment['end'] / total_duration) * (self.width - 20) + 10
            color = self.speaker_colors[segment['speaker']]

            # Segment zeichnen
            segment_width = max(end_x - start_x, 2)  # Mindestens 2 Pixel breit

            self.canvas.create_rectangle(
                start_x, timeline_top, end_x, timeline_bottom,
                fill=color, outline=color, width=0  # Keine Umrandung
            )

            # Sprecher-Label nur bei größeren Segmenten
            if segment_width > 30:  # Nur wenn mindestens 30 Pixel breit
                # Kompakte Label
                label_text = segment['speaker'].replace('SPEAKER_', 'S')
                self.canvas.create_text(
                    (start_x + end_x) / 2, (timeline_top + timeline_bottom) / 2,
                    text=label_text, fill='white', font=('Arial', 8, 'bold')
                )

        # Verbesserte Zeitmarkierungen
        self._draw_time_markers(total_duration, timeline_bottom)

    def _draw_time_markers(self, total_duration, y_pos):
        """Zeichnet verbesserte Zeitmarkierungen"""
        # Intelligente Intervalle basierend auf Gesamtdauer
        if total_duration <= 60:
            interval = 10  # Alle 10 Sekunden
        elif total_duration <= 300:
            interval = 30  # Alle 30 Sekunden
        else:
            interval = 60  # Alle 60 Sekunden

        for i in range(0, int(total_duration) + 1, interval):
            x = (i / total_duration) * (self.width - 20) + 10

            # Dezentere Markierungen
            self.canvas.create_line(x, y_pos, x, y_pos + 5, fill='#CCCCCC', width=1)

            # Zeitlabels formatieren
            if i >= 60:
                minutes = i // 60
                seconds = i % 60
                time_text = f"{minutes}:{seconds:02d}"
            else:
                time_text = f"{i}s"

            # Kleinere Schrift für Zeitlabels
            self.canvas.create_text(x, y_pos + 8, text=time_text,
                                    anchor='n', fill='#666666', font=('Arial', 7))


class TranscriptionWidget(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Text-Widget für Transkription
        self.text = tk.Text(self, wrap=tk.WORD, height=10)
        self.text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbar hinzufügen
        scrollbar = tk.Scrollbar(self.text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text.yview)

        # Tags für Sprecher-Farben definieren
        self.speaker_tags = {}
        self.color_palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']

    def display_transcription(self, result):
        """Zeigt die Transkription mit Sprecher-Labels an"""
        self.text.delete(1.0, tk.END)

        # Zuerst die vollständige Transkription anzeigen
        if 'transcription' in result or 'full_text' in result:
            full_text = result.get('transcription', result.get('full_text', ''))
            self.text.insert(tk.END, "Vollständige Transkription:\n", "heading")
            self.text.insert(tk.END, full_text + "\n\n")
            self.text.insert(tk.END, "-" * 40 + "\n\n")

        # Dann die nach Sprechern geordnete Transkription
        self.text.insert(tk.END, "Transkription nach Sprechern:\n\n", "heading")

        # Tag für Überschriften konfigurieren
        self.text.tag_configure("heading", font=('Arial', 10, 'bold'), spacing1=5, spacing3=5)

        if 'segments' in result and result['segments']:
            current_speaker = None

            for segment in result['segments']:
                speaker = segment['speaker']
                text = segment.get('text', '')

                # Leere Segmente überspringen
                if not text.strip():
                    continue

                # Tag für Sprecher erstellen, falls noch nicht vorhanden
                if speaker not in self.speaker_tags:
                    color = self.color_palette[len(self.speaker_tags) % len(self.color_palette)]
                    tag_name = f"speaker_{speaker}"
                    self.text.tag_configure(tag_name, foreground=color, font=('Arial', 10, 'bold'))
                    self.speaker_tags[speaker] = tag_name

                # Sprecherwechsel anzeigen
                if speaker != current_speaker:
                    current_speaker = speaker
                    self.text.insert(tk.END, f"\n{speaker}: ", self.speaker_tags[speaker])

                # Text einfügen
                self.text.insert(tk.END, text + " ")

            # Zur Anfang scrollen
            self.text.see("1.0")