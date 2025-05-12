# gui/components.py
import tkinter as tk
from tkinter import ttk
import math


class SpeakerTimelineWidget(tk.Frame):
    def __init__(self, parent, width=600, height=100):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, width=width, height=height, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.width = width
        self.height = height
        self.speaker_colors = {}
        self.color_palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']

    def display_segments(self, segments, total_duration):
        """Zeigt die Sprecher-Segmente auf der Timeline an"""
        self.canvas.delete("all")

        if not segments:
            return

        # Farben für Sprecher zuweisen
        speakers = list(set(seg['speaker'] for seg in segments))
        for i, speaker in enumerate(speakers):
            self.speaker_colors[speaker] = self.color_palette[i % len(self.color_palette)]

        # Timeline zeichnen
        for segment in segments:
            start_x = (segment['start'] / total_duration) * self.width
            end_x = (segment['end'] / total_duration) * self.width
            color = self.speaker_colors[segment['speaker']]

            # Segment zeichnen
            self.canvas.create_rectangle(
                start_x, 20, end_x, self.height - 20,
                fill=color, outline=color
            )

            # Sprecher-Label
            if end_x - start_x > 30:  # Nur wenn genug Platz
                self.canvas.create_text(
                    (start_x + end_x) / 2, self.height / 2,
                    text=segment['speaker'], fill='white'
                )

        # Zeitmarkierungen
        for i in range(0, int(total_duration) + 1, 30):  # Alle 30 Sekunden
            x = (i / total_duration) * self.width
            self.canvas.create_line(x, self.height - 10, x, self.height, fill='gray')
            self.canvas.create_text(x, self.height - 5, text=f"{i}s", anchor='n')


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