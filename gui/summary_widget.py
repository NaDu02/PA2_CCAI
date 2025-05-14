# gui/summary_widget.py - VOLLSTÄNDIGE DATEI ohne geschätzte Dauer
"""
Widget für die Anzeige von Gesprächszusammenfassungen
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import math


class SummaryWidget(tk.Frame):
    """Widget zur Anzeige von Zusammenfassungen"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Erstelle das UI"""
        # Notebook für Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Überblick
        self.overview_frame = tk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="📋 Überblick")
        self.setup_overview_tab()

        # Tab 2: To-Do Liste
        self.todo_frame = tk.Frame(self.notebook)
        self.notebook.add(self.todo_frame, text="✅ Aufgaben")
        self.setup_todo_tab()

        # Tab 3: Details
        self.details_frame = tk.Frame(self.notebook)
        self.notebook.add(self.details_frame, text="📝 Details")
        self.setup_details_tab()

    def setup_overview_tab(self):
        """Erstelle Überblick-Tab"""
        # Scroll-Frame für Überblick
        scroll_frame = tk.Frame(self.overview_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Canvas und Scrollbar
        canvas = tk.Canvas(scroll_frame)
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        self.overview_content = tk.Frame(canvas)

        self.overview_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.overview_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def setup_todo_tab(self):
        """Erstelle To-Do-Tab"""
        # Frame für To-Do-Liste
        todo_main_frame = tk.Frame(self.todo_frame)
        todo_main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview für To-Dos
        self.todo_tree = ttk.Treeview(todo_main_frame, columns=('Aufgabe', 'Zugewiesen', 'Priorität', 'Deadline'),
                                      show='tree headings')

        # Spaltenüberschriften
        self.todo_tree.heading('#0', text='#')
        self.todo_tree.heading('Aufgabe', text='Aufgabe')
        self.todo_tree.heading('Zugewiesen', text='Zugewiesen')
        self.todo_tree.heading('Priorität', text='Priorität')
        self.todo_tree.heading('Deadline', text='Deadline')

        # Spaltenbreiten
        self.todo_tree.column('#0', width=50, minwidth=50)
        self.todo_tree.column('Aufgabe', width=300, minwidth=200)
        self.todo_tree.column('Zugewiesen', width=100, minwidth=80)
        self.todo_tree.column('Priorität', width=80, minwidth=60)
        self.todo_tree.column('Deadline', width=100, minwidth=80)

        # Scrollbar für Treeview
        todo_scrollbar = ttk.Scrollbar(todo_main_frame, orient=tk.VERTICAL, command=self.todo_tree.yview)
        self.todo_tree.configure(yscrollcommand=todo_scrollbar.set)

        self.todo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        todo_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_details_tab(self):
        """Erstelle Details-Tab"""
        # Text-Widget für Details
        self.details_text = scrolledtext.ScrolledText(
            self.details_frame,
            wrap=tk.WORD,
            height=15,
            font=('Segoe UI', 10)
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tags für Formatierung
        self.details_text.tag_configure("heading", font=('Segoe UI', 12, 'bold'), foreground="#2E86AB")
        self.details_text.tag_configure("subheading", font=('Segoe UI', 11, 'bold'), foreground="#F24236")
        self.details_text.tag_configure("normal", font=('Segoe UI', 10))
        self.details_text.tag_configure("highlight", background="#FFE66D")

    def display_summary(self, summary_data: dict):
        """Zeige Zusammenfassung an"""
        if not summary_data:
            self.show_error("Keine Zusammenfassung verfügbar")
            return

        # Extrahiere Daten
        summary = summary_data.get('summary', {})
        todos = summary_data.get('todos', [])
        participants = summary_data.get('participants', [])
        sentiment = summary_data.get('sentiment', 'neutral')
        processing_time = summary_data.get('processing_time', 0)

        # Zeige Überblick
        self._display_overview(summary, sentiment, processing_time, participants)

        # Zeige To-Dos
        self._display_todos(todos)

        # Zeige Details
        self._display_details(summary_data)

    def _display_overview(self, summary, sentiment, processing_time, participants):
        """Zeige Überblick an"""
        # Lösche vorherigen Inhalt
        for widget in self.overview_content.winfo_children():
            widget.destroy()

        # Status und Info
        status_frame = tk.Frame(self.overview_content)
        status_frame.pack(fill=tk.X, pady=5)

        # Sentiment mit Emoji
        sentiment_emoji = {
            'positiv': '😊',
            'neutral': '😐',
            'negativ': '😞'
        }.get(sentiment, '😐')

        tk.Label(status_frame, text=f"Stimmung: {sentiment_emoji} {sentiment.capitalize()}",
                 font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)

        tk.Label(status_frame, text=f"Verarbeitung: {processing_time:.2f}s",
                 font=('Segoe UI', 10)).pack(anchor=tk.W)

        # Hauptpunkte
        if summary.get('main_points'):
            main_frame = tk.LabelFrame(self.overview_content, text="📌 Hauptpunkte",
                                       font=('Segoe UI', 11, 'bold'))
            main_frame.pack(fill=tk.X, pady=5, padx=5)

            for i, point in enumerate(summary['main_points'], 1):
                point_label = tk.Label(main_frame, text=f"{i}. {point}",
                                       anchor=tk.W, justify=tk.LEFT, wraplength=400,
                                       font=('Segoe UI', 10))
                point_label.pack(fill=tk.X, padx=5, pady=2)

        # Entscheidungen
        if summary.get('key_decisions'):
            decision_frame = tk.LabelFrame(self.overview_content, text="🎯 Entscheidungen",
                                           font=('Segoe UI', 11, 'bold'))
            decision_frame.pack(fill=tk.X, pady=5, padx=5)

            for decision in summary['key_decisions']:
                decision_label = tk.Label(decision_frame, text=f"• {decision}",
                                          anchor=tk.W, justify=tk.LEFT, wraplength=400,
                                          font=('Segoe UI', 10))
                decision_label.pack(fill=tk.X, padx=5, pady=2)

        # Teilnehmer
        if participants:
            participants_frame = tk.LabelFrame(self.overview_content, text="👥 Teilnehmer",
                                               font=('Segoe UI', 11, 'bold'))
            participants_frame.pack(fill=tk.X, pady=5, padx=5)

            for participant in participants:
                speaker = participant.get('speaker', 'Unbekannt')
                role = participant.get('role', 'Unbekannte Rolle')
                level = participant.get('participation_level', 'mittel')

                level_emoji = {
                    'hoch': '🟢',
                    'mittel': '🟡',
                    'niedrig': '🔴'
                }.get(level, '🟡')

                part_label = tk.Label(participants_frame,
                                      text=f"{level_emoji} {speaker}: {role} (Beteiligung: {level})",
                                      anchor=tk.W, justify=tk.LEFT,
                                      font=('Segoe UI', 10))
                part_label.pack(fill=tk.X, padx=5, pady=2)

    def _display_todos(self, todos):
        """Zeige To-Dos in der Treeview an"""
        # Lösche vorherige Einträge
        for item in self.todo_tree.get_children():
            self.todo_tree.delete(item)

        if not todos:
            self.todo_tree.insert('', 'end', values=('Keine Aufgaben gefunden', '', '', ''))
            return

        # Füge To-Dos hinzu
        for i, todo in enumerate(todos, 1):
            task = todo.get('task', 'Unbekannte Aufgabe')
            assigned = todo.get('assigned_to', 'Nicht zugewiesen')
            priority = todo.get('priority', 'mittel')
            deadline = todo.get('deadline', 'Nicht spezifiziert')

            # Priorität mit Emoji
            priority_display = {
                'hoch': '🔴 Hoch',
                'mittel': '🟡 Mittel',
                'niedrig': '🟢 Niedrig'
            }.get(priority, f'🟡 {priority}')

            self.todo_tree.insert('', 'end', text=str(i),
                                  values=(task, assigned, priority_display, deadline))

    def _display_details(self, summary_data):
        """Zeige Details im Text-Widget an"""
        # Lösche vorherigen Inhalt
        self.details_text.delete(1.0, tk.END)

        # Titel
        self.details_text.insert(tk.END, "Detaillierte Zusammenfassung\n", "heading")
        self.details_text.insert(tk.END, "=" * 50 + "\n\n", "normal")

        # Timestamp
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self.details_text.insert(tk.END, f"Erstellt am: {timestamp}\n\n", "normal")

        # Zusammenfassung
        summary = summary_data.get('summary', {})

        if summary.get('main_points'):
            self.details_text.insert(tk.END, "Hauptpunkte:\n", "subheading")
            for point in summary['main_points']:
                self.details_text.insert(tk.END, f"• {point}\n", "normal")
            self.details_text.insert(tk.END, "\n", "normal")

        if summary.get('key_decisions'):
            self.details_text.insert(tk.END, "Entscheidungen:\n", "subheading")
            for decision in summary['key_decisions']:
                self.details_text.insert(tk.END, f"• {decision}\n", "normal")
            self.details_text.insert(tk.END, "\n", "normal")

        if summary.get('discussion_topics'):
            self.details_text.insert(tk.END, "Diskussionsthemen:\n", "subheading")
            for topic in summary['discussion_topics']:
                self.details_text.insert(tk.END, f"• {topic}\n", "normal")
            self.details_text.insert(tk.END, "\n", "normal")

        if summary.get('facts_and_numbers'):
            self.details_text.insert(tk.END, "Fakten und Zahlen:\n", "subheading")
            for fact in summary['facts_and_numbers']:
                self.details_text.insert(tk.END, f"• {fact}\n", "normal")
            self.details_text.insert(tk.END, "\n", "normal")

        if summary.get('concerns_and_risks'):
            self.details_text.insert(tk.END, "Bedenken und Risiken:\n", "subheading")
            for concern in summary['concerns_and_risks']:
                self.details_text.insert(tk.END, f"• {concern}\n", "normal")
            self.details_text.insert(tk.END, "\n", "normal")

        # To-Dos
        todos = summary_data.get('todos', [])
        if todos:
            self.details_text.insert(tk.END, "Aufgaben:\n", "subheading")
            for i, todo in enumerate(todos, 1):
                self.details_text.insert(tk.END, f"{i}. {todo.get('task', 'Unbekannte Aufgabe')}\n", "normal")
                self.details_text.insert(tk.END, f"   Zugewiesen: {todo.get('assigned_to', 'Nicht zugewiesen')}\n",
                                         "normal")
                self.details_text.insert(tk.END, f"   Priorität: {todo.get('priority', 'mittel')}\n", "normal")
                self.details_text.insert(tk.END, f"   Deadline: {todo.get('deadline', 'Nicht spezifiziert')}\n",
                                         "normal")

                # Zusätzliche To-Do-Details falls vorhanden
                if todo.get('context'):
                    self.details_text.insert(tk.END, f"   Kontext: {todo.get('context')}\n", "normal")
                if todo.get('dependencies'):
                    self.details_text.insert(tk.END, f"   Abhängigkeiten: {todo.get('dependencies')}\n", "normal")
                if todo.get('success_criteria'):
                    self.details_text.insert(tk.END, f"   Erfolgskriterien: {todo.get('success_criteria')}\n", "normal")

                self.details_text.insert(tk.END, "\n", "normal")

        # Nächste Schritte
        next_steps = summary_data.get('next_steps', [])
        if next_steps:
            self.details_text.insert(tk.END, "Nächste Schritte:\n", "subheading")
            for step in next_steps:
                self.details_text.insert(tk.END, f"• {step}\n", "normal")
            self.details_text.insert(tk.END, "\n", "normal")

        # Offene Fragen
        open_questions = summary_data.get('open_questions', [])
        if open_questions:
            self.details_text.insert(tk.END, "Offene Fragen:\n", "subheading")
            for question in open_questions:
                self.details_text.insert(tk.END, f"• {question}\n", "normal")
            self.details_text.insert(tk.END, "\n", "normal")

        # Vereinbarungen
        agreements = summary_data.get('agreements_and_commitments', [])
        if agreements:
            self.details_text.insert(tk.END, "Vereinbarungen und Commitments:\n", "subheading")
            for agreement in agreements:
                self.details_text.insert(tk.END, f"• {agreement}\n", "normal")
            self.details_text.insert(tk.END, "\n", "normal")

        # Key Takeaways
        key_takeaways = summary_data.get('key_takeaways', [])
        if key_takeaways:
            self.details_text.insert(tk.END, "Wichtigste Erkenntnisse:\n", "subheading")
            for takeaway in key_takeaways:
                self.details_text.insert(tk.END, f"• {takeaway}\n", "normal")
            self.details_text.insert(tk.END, "\n", "normal")

        # Metadaten (ohne geschätzte Dauer)
        self.details_text.insert(tk.END, "Metadaten:\n", "subheading")
        self.details_text.insert(tk.END, f"Stimmung: {summary_data.get('sentiment', 'Unbekannt')}\n", "normal")
        self.details_text.insert(tk.END, f"Verarbeitungszeit: {summary_data.get('processing_time', 0):.2f}s\n",
                                 "normal")

        # Meeting-Effektivität
        if summary_data.get('meeting_effectiveness'):
            self.details_text.insert(tk.END, f"Meeting-Effektivität: {summary_data.get('meeting_effectiveness')}\n",
                                     "normal")

        participants = summary_data.get('participants', [])
        if participants:
            self.details_text.insert(tk.END, f"Anzahl Sprecher: {len(participants)}\n", "normal")

        # Scroll zum Anfang
        self.details_text.see("1.0")

    def show_error(self, message):
        """Zeige Fehlermeldung an"""
        for widget in self.overview_content.winfo_children():
            widget.destroy()

        error_label = tk.Label(self.overview_content,
                               text=f"❌ {message}",
                               font=('Segoe UI', 12),
                               foreground='red')
        error_label.pack(pady=20)

    def clear(self):
        """Lösche alle Inhalte"""
        # Lösche Überblick
        for widget in self.overview_content.winfo_children():
            widget.destroy()

        # Lösche To-Dos
        for item in self.todo_tree.get_children():
            self.todo_tree.delete(item)

        # Lösche Details
        self.details_text.delete(1.0, tk.END)