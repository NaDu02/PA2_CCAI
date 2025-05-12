#!/bin/bash
# start.sh - Starter-Skript für ATA Audio-Aufnahme

# Aktiviere Virtual Environment, falls vorhanden
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Starte das Startup-Skript
python startup.py

# Deaktiviere Virtual Environment
deactivate 2>/dev/null