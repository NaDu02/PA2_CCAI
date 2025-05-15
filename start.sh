#!/bin/bash
# start.sh - Starter-Skript für ATA Audio-Aufnahme
# Version: 1.2.0

set -e  # Exit bei Fehlern

# Farbcodes für bessere Ausgabe
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== ATA Audio-Aufnahme Start ===${NC}"

# Prüfe, ob Docker-Services laufen
echo -e "${YELLOW}Überprüfe Docker-Services...${NC}"
if command -v docker &> /dev/null; then
    # Prüfe WhisperX API
    if docker ps --format "table {{.Names}}" | grep -q "whisperx-api"; then
        echo -e "${GREEN}✓ WhisperX API läuft${NC}"
    else
        echo -e "${RED}⚠ WhisperX API läuft nicht${NC}"
        echo -e "${YELLOW}Starte WhisperX API...${NC}"
        # Optional: Container starten falls vorhanden
        docker start whisperx-api-new 2>/dev/null || echo -e "${RED}WhisperX Container nicht gefunden${NC}"
    fi
else
    echo -e "${YELLOW}Docker nicht installiert/verfügbar${NC}"
fi

# Python-Version prüfen
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 nicht gefunden!${NC}"
    exit 1
fi

# Virtual Environment aktivieren
echo -e "${YELLOW}Aktiviere Virtual Environment...${NC}"
if [ -d ".venv" ]; then
    echo -e "${GREEN}Verwende .venv${NC}"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo -e "${GREEN}Verwende venv${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}Kein Virtual Environment gefunden - verwende System Python${NC}"
fi

# Prüfe, ob requirements installiert sind
echo -e "${YELLOW}Prüfe Dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    python -m pip check &> /dev/null || {
        echo -e "${YELLOW}Installiere fehlende Dependencies...${NC}"
        python -m pip install -r requirements.txt
    }
fi

# Starte das Startup-Skript
echo -e "${GREEN}Starte ATA Audio-Aufnahme...${NC}"
python startup.py

# Cleanup
echo -e "${YELLOW}Bereinigung...${NC}"
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate 2>/dev/null
fi

echo -e "${GREEN}Programm beendet.${NC}"