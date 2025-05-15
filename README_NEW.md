# 🧠 ATA Audio-Aufnahme

Eine fortschrittliche macOS-Anwendung zur parallelen Aufnahme von System- und Mikrofon-Audio mit Sprechererkennung, WhisperX-Transkription und KI-basierter Gesprächsanalyse.

## 🚀 Features

- 🎙️ Hochqualitative Audioaufnahme (System + Mikrofon via BlackHole)
- 🗣️ Automatische Sprechererkennung (Speaker Diarization)
- 📝 WhisperX-Transkription mit Zeitstempeln
- 🤖 Automatische Gesprächszusammenfassung durch LLMs
- 🧩 Lokale und Server-basierte Docker-API-Unterstützung
- 📊 Visuelle Darstellung der Gesprächssegmente

## 📋 Voraussetzungen

- **macOS** (Intel oder Apple Silicon)
- **Python 3.8+** (empfohlen: 3.9–3.12)
- **BlackHole Audio-Treiber**
- **Docker Desktop**
- **Homebrew** (für einfache Installation von Tools)

## 🧱 Installation

### 1. Repository klonen
```bash
git clone https://github.com/DEIN_REPO/ata-audio-aufnahme.git
cd ata-audio-aufnahme
```

### 2. Starte die Anwendung
```bash
./start.sh
```

Das Skript erledigt automatisch:
- Aktivierung der venv oder Nutzung von System-Python
- Installation fehlender Abhängigkeiten
- Start der Anwendung
- Start vorhandener Docker-Container (z. B. `whisperx-api`, falls installiert)

## 🐳 Docker-Unterstützung

Die Anwendung nutzt Docker-basierte Backends:

| Komponente              | Standard-Port | Zweck                        |
|------------------------|---------------|------------------------------|
| WhisperX API           | 8500          | Transkription & Diarisierung |
| Summarization API      | 8501          | Zusammenfassungen            |
| Ollama (optional)      | 11434         | LLM-Modelle (lokal)          |

### 🔐 Zugriff auf externe Server
Wenn du keinen lokalen Docker einsetzen möchtest, frage nach Zugang zu folgender Remote-Instanz:
```bash
http://141.72.16.242:8500/transcribe
```

## 🎧 Einrichtung von BlackHole (macOS)

### Schritt-für-Schritt (Audio-MIDI-Setup)

1. **Installiere BlackHole**:
   ```bash
   brew install blackhole-2ch
   ```

2. **Öffne**: `/Programme/Dienstprogramme/Audio-MIDI-Setup.app`

3. **Erstelle ein Aggregat-Gerät**:
   - Mikrofon + BlackHole 2ch

4. **Erstelle ein Multi-Output-Gerät**:
   - Lautsprecher + BlackHole 2ch

5. **Setze Multi-Output als Standardausgabe** (Systemeinstellungen > Ton)

## 🧪 Test und Aufnahme

1. Starte `./start.sh`
2. Wähle dein Mikrofon und Loopback-Gerät
3. Drücke „Start“ – Sprich + spiele z. B. ein YouTube-Video ab
4. Nach „Stop“ bekommst du:
   - Transkript mit Sprecherzuordnung
   - Visuelle Timeline
   - Automatische Zusammenfassung

## 🆘 Hilfe & Support

- Hilfe-Funktion in der App: **Hilfe > Dokumentation**
- Direkt im Projekt: `docs/help.html`
- Oder GitHub-Issues eröffnen

## 📄 Lizenz

[Lizenzinformationen einfügen]

## 🤝 Mitwirken

Pull Requests willkommen! Bitte bei größeren Änderungen vorher ein Issue eröffnen.
