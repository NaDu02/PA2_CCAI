# utils/logger.py
"""
Logging-Funktionalität für die ATA Audio-Aufnahme
"""
from datetime import datetime
import tkinter as tk


class Logger:
    def __init__(self, log_text_widget=None):
        self.log_text = log_text_widget

    def log_message(self, message, level="INFO"):
        """Fügt eine Nachricht mit Zeitstempel zum Logfenster hinzu."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "",
            "SUCCESS": "✅ ",
            "ERROR": "❌ ",
            "WARNING": "⚠️ "
        }.get(level, "")

        formatted_msg = f"[{timestamp}] {prefix}{message}"

        if self.log_text:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, formatted_msg + "\n")
            self.log_text.see(tk.END)  # Auto-scroll zum Ende
            self.log_text.config(state=tk.DISABLED)

        # Auch auf der Konsole ausgeben für Debug-Zwecke
        print(formatted_msg)

    def set_log_text_widget(self, widget):
        """Setzt das Log-Text-Widget."""
        self.log_text = widget