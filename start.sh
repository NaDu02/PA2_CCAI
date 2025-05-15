#!/bin/bash
# start.sh - Starter-Skript für ATA Audio-Aufnahme
# Version: 1.3.0 - Check First, Install on Request

set -e  # Exit bei Fehlern

# Farbcodes für bessere Ausgabe
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== ATA Audio-Aufnahme Startup Check ===${NC}"

# Track was installiert werden muss
needs_homebrew=false
needs_blackhole=false
needs_ffmpeg=false
needs_python=false
needs_venv=false

# Funktion zum Fragen ob installieren
ask_install() {
    local component=$1
    echo -e "${YELLOW}$component fehlt. Installieren? (j/n):${NC}"
    read -r response
    if [[ "$response" =~ ^([jJ][aA]?|[yY][eE]?[sS]?)$ ]]; then
        return 0
    else
        return 1
    fi
}

# === SYSTEM CHECKS ===
echo -e "\n${BLUE}=== System-Check ===${NC}"

# Check Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${RED}✗ Homebrew nicht gefunden${NC}"
    needs_homebrew=true
else
    echo -e "${GREEN}✓ Homebrew gefunden${NC}"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 nicht gefunden${NC}"
    needs_python=true
else
    python_version=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python3 gefunden: $python_version${NC}"
fi

# Check BlackHole
if command -v brew &> /dev/null && ! brew list blackhole-2ch &> /dev/null; then
    echo -e "${RED}✗ BlackHole nicht installiert${NC}"
    needs_blackhole=true
elif command -v brew &> /dev/null; then
    echo -e "${GREEN}✓ BlackHole installiert${NC}"
else
    echo -e "${YELLOW}? BlackHole-Status unbekannt (Homebrew fehlt)${NC}"
fi

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}✗ FFmpeg nicht gefunden${NC}"
    needs_ffmpeg=true
else
    echo -e "${GREEN}✓ FFmpeg gefunden${NC}"
fi

# Check Virtual Environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}! Virtual Environment (.venv) existiert nicht${NC}"
    needs_venv=true
else
    echo -e "${GREEN}✓ Virtual Environment gefunden${NC}"
fi

# === INSTALLATION PROMPTS ===
echo -e "\n${BLUE}=== Fehlende Komponenten ===${NC}"

# Homebrew (kritisch - ohne geht nichts)
if $needs_homebrew; then
    echo -e "${RED}Homebrew ist für macOS-Installation kritisch!${NC}"
    if ask_install "Homebrew"; then
        echo -e "${YELLOW}Installiere Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Homebrew zu PATH hinzufügen
        if [[ $(uname -m) == 'arm64' ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi

        if command -v brew &> /dev/null; then
            echo -e "${GREEN}✓ Homebrew installiert${NC}"
        else
            echo -e "${RED}✗ Homebrew Installation fehlgeschlagen${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Ohne Homebrew können andere Komponenten nicht installiert werden.${NC}"
        exit 1
    fi
fi

# Python (kritisch)
if $needs_python; then
    echo -e "${RED}Python3 ist erforderlich!${NC}"
    if ask_install "Python3"; then
        echo -e "${YELLOW}Installiere Python...${NC}"
        brew install python@3.11
        echo -e "${GREEN}✓ Python installiert${NC}"
    else
        echo -e "${RED}Python ist erforderlich für die Anwendung.${NC}"
        exit 1
    fi
fi

# BlackHole (kritisch für Audio)
if $needs_blackhole; then
    echo -e "${YELLOW}BlackHole ist für System-Audio-Aufnahme erforderlich!${NC}"
    if ask_install "BlackHole Audio Driver"; then
        echo -e "${YELLOW}Installiere BlackHole...${NC}"
        brew install blackhole-2ch
        echo -e "${GREEN}✓ BlackHole installiert${NC}"
        echo -e "${YELLOW}⚠️  WICHTIG: Konfigurieren Sie BlackHole in Audio-MIDI-Setup!${NC}"
        echo -e "${BLUE}   Siehe README für detaillierte Anweisungen.${NC}"
    else
        echo -e "${YELLOW}Ohne BlackHole ist keine System-Audio-Aufnahme möglich.${NC}"
        echo -e "${BLUE}Die App kann trotzdem gestartet werden (nur Mikrofon-Aufnahme).${NC}"
    fi
fi

# FFmpeg (automatisch installieren ohne Nachfrage)
if $needs_ffmpeg; then
    echo -e "${YELLOW}FFmpeg wird für optimale Audio-Qualität installiert...${NC}"
    brew install ffmpeg
    if command -v ffmpeg &> /dev/null; then
        echo -e "${GREEN}✓ FFmpeg installiert${NC}"
    else
        echo -e "${YELLOW}⚠️  FFmpeg Installation fehlgeschlagen (nicht kritisch)${NC}"
        echo -e "${BLUE}   Fallback auf Standard-Audio-Processor möglich${NC}"
    fi
fi

# === PYTHON ENVIRONMENT SETUP ===
echo -e "\n${BLUE}=== Python Environment Setup ===${NC}"

# Virtual Environment
if $needs_venv; then
    echo -e "${YELLOW}Erstelle Virtual Environment...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual Environment erstellt${NC}"
fi

# Aktiviere venv
echo -e "${YELLOW}Aktiviere Virtual Environment...${NC}"
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual Environment aktiv${NC}"

# Install/Update Python dependencies
echo -e "${YELLOW}Installiere Python-Dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    echo -e "${GREEN}✓ Python-Dependencies installiert${NC}"
else
    echo -e "${RED}requirements.txt nicht gefunden!${NC}"
    exit 1
fi

# === STARTUP ===
echo -e "\n${GREEN}=== Starte ATA Audio-Aufnahme ===${NC}"
echo -e "${BLUE}Führe detaillierte System-Checks durch...${NC}"
python startup.py

# Cleanup
echo -e "\n${YELLOW}Bereinigung...${NC}"
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate 2>/dev/null || true
fi

echo -e "${GREEN}Session beendet.${NC}"