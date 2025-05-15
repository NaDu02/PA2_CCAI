# ATA Audio-Aufnahme

Eine fortschrittliche macOS-Anwendung für hochqualitative Audio-Aufnahme mit intelligenter Sprechererkennung, KI-basierter Transkription und automatischer Gesprächszusammenfassung.

## 🚀 Features

- **🎙️ Hochqualitative Audio-Aufnahme** mit BlackHole Loopback (System + Mikrofon)
- **🗣️ Speaker Diarization** (Sprechererkennung und -zuordnung)
- **📝 WhisperX-basierte Transkription** über API oder lokal
- **🤖 Intelligente Zusammenfassung** mit Large Language Models
- **📊 Visuelle Timeline** der Sprecher-Segmente
- **⚙️ FFmpeg-Integration** für beste Audioqualität

## 📋 Voraussetzungen

### System
- **macOS** (Intel oder Apple Silicon)
- **Python 3.8+** (empfohlen: 3.9-3.12)
- **BlackHole Audio Driver**
- **FFmpeg** (optional, für beste Qualität)
- **Docker & Docker Desktop**

## 🔧 Installation

### 1. Repository klonen
```bash
git clone <repository-url>
cd ata-audio-aufnahme
```

### 2. BlackHole installieren und konfigurieren

#### BlackHole Installation:
```bash
brew install blackhole-2ch
```

#### Audio-MIDI-Setup konfigurieren:
1. Öffnen Sie **Audio-MIDI-Setup** (`/Applications/Utilities/Audio MIDI Setup.app`)
2. Erstellen Sie ein **Aggregat-Gerät**:
   - Wählen Sie Ihre Lautsprecher/Kopfhörer
   - Fügen Sie **BlackHole 2ch** hinzu
3. Erstellen Sie ein **Multi-Output-Gerät**:
   - Wählen Sie Ihre Lautsprecher/Kopfhörer 
   - Fügen Sie **BlackHole 2ch** hinzu
4. Setzen Sie das Multi-Output-Gerät als **Standard-Audioausgang** in den Systemeinstellungen

### 3. Python-Dependencies installieren

#### Virtual Environment erstellen (empfohlen):
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Dependencies installieren:
```bash
pip install -r requirements.txt
```

### 4. FFmpeg installieren (optional, aber empfohlen):
```bash
brew install ffmpeg
```

### 5. Docker Container starten

Die Anwendung benötigt drei Docker Container:

#### WhisperX API (für Transkription):
```bash
docker run -d \
  --name whisperx-api \
  -p 8500:8500 \
  whisperx-api:cuda129
```

#### Summarization Service:
```bash
docker run -d \
  --name summarization-api \
  -p 8501:8501 \
  zf-summarization-api:latest
```

#### Ollama LLM (für Zusammenfassungen):
```bash
docker run -d \
  --name ollama \
  -p 11434:11434 \
  ollama/ollama:latest
```

## ⚙️ Konfiguration

### API-URLs anpassen

Bearbeiten Sie `config/settings.py` um die Docker-Container-IPs zu konfigurieren:

```python
# WhisperX API
WHISPERX_API_URL = "http://IHRE_DOCKER_HOST_IP:8500/transcribe"

# Für lokale Docker-Installation meist:
WHISPERX_API_URL = "http://localhost:8500/transcribe"

# Oder für Remote-Server:
WHISPERX_API_URL = "http://141.72.16.242:8500/transcribe"
```

### Weitere Konfigurationsoptionen:

```python
# Sprache für Transkription
WHISPERX_LANGUAGE = "de"  # Deutsch

# Aktivierung der Sprechererkennung
ENABLE_SPEAKER_DIARIZATION = True

# Timeout für API-Calls
WHISPERX_TIMEOUT = 120  # Sekunden

# Audio-Qualität
SAMPLE_RATE = 44100
BUFFER_SIZE = 4096
```

## 🚀 Anwendung starten

### Mit Startup-Check:
```bash
python startup.py
```

### Direkt:
```bash
python main.py
```

### Mit Shell-Script:
```bash
./start.sh
```

## 📚 Verwendung

### 1. Erste Schritte
1. **Geräteauswahl**: Klicken Sie auf "Geräteauswahl" und wählen Sie:
   - **Loopback-Gerät**: BlackHole 2ch
   - **Mikrofon**: Ihr gewünschtes Mikrofon
   - Passen Sie die Lautstärke an

2. **API-Test**: Klicken Sie auf "API Test" um die WhisperX-Verbindung zu prüfen

### 2. Aufnahme durchführen
1. **Start**: Beginnen Sie die Aufnahme mit dem "Start"-Button
2. **Audio abspielen**: System-Audio (YouTube, Musik, etc.) wird automatisch aufgenommen
3. **Ins Mikrofon sprechen**: Ihre Stimme wird parallel aufgenommen
4. **Stop**: Beenden Sie mit "Stop"

### 3. Ergebnisse
Nach der Aufnahme erhalten Sie:
- **Visuelle Timeline** der Sprecher-Segmente
- **Transkription** mit Sprecher-Labels
- **Automatische Zusammenfassung** mit To-Dos und Insights

## 🛠️ Fehlerbehebung

### BlackHole-Probleme
- **Kein BlackHole gefunden**: Neuinstallation mit `brew reinstall blackhole-2ch`
- **Kein System-Audio**: Prüfen Sie das Multi-Output-Gerät Setup
- **Audio-Probleme**: Starten Sie Core Audio neu: `sudo killall coreaudiod`

### Docker-Container-Probleme
- **Container prüfen**: `docker ps`
- **Logs einsehen**: `docker logs whisperx-api`
- **Container neu starten**: `docker restart whisperx-api`

### API-Verbindungsprobleme
- **Health Check**: Verwenden Sie den integrierten "API Test"
- **Timeout erhöhen**: Erhöhen Sie `WHISPERX_TIMEOUT` in `settings.py`
- **Netzwerk prüfen**: Testen Sie mit `curl http://localhost:8500/health`

### Audio-Qualitätsprobleme
- **FFmpeg installieren**: `brew install ffmpeg` für beste Qualität
- **Puffergröße anpassen**: Erhöhen Sie die Puffergröße in Geräteeinstellungen
- **Andere Programme schließen**: Reduzieren Sie die Systemlast

## 📁 Projektstruktur

```
ata-audio-aufnahme/
├── main.py                 # Hauptanwendung
├── startup.py             # Startup-Check-Script
├── requirements.txt       # Python-Dependencies
├── config/
│   └── settings.py       # Konfiguration
├── audio/                # Audio-Verarbeitung
│   ├── processor.py      # Standard Audio-Processor  
│   ├── ffmpeg_processor.py # FFmpeg-basierte Aufnahme
│   ├── whisperx_processor.py # WhisperX Integration
│   └── device_manager.py # Audio-Geräte-Management
├── gui/                  # Benutzeroberfläche
│   ├── dialogs.py       # Dialog-Fenster
│   ├── components.py    # UI-Komponenten
│   └── summary_widget.py # Zusammenfassungs-Widget
└── utils/               # Hilfsfunktionen
    └── logger.py        # Logging-System
```

## 🔗 Docker Container URLs

- **WhisperX API**: http://localhost:8500
  - Health Check: http://localhost:8500/health
  - Transcribe: http://localhost:8500/transcribe

- **Summarization API**: http://localhost:8501
  - Health Check: http://localhost:8501/health
  - Summarize: http://localhost:8501/summarize

- **Ollama LLM**: http://localhost:11434
  - API: http://localhost:11434/api/generate

## 📄 Lizenz

[Lizenzinformationen hier einfügen]

## 🤝 Beitragen

Beiträge sind willkommen! Bitte erstellen Sie einen Pull Request oder öffnen Sie ein Issue.

## 📞 Support

Bei Problemen erstellen Sie bitte ein Issue im Repository oder kontaktieren Sie [Support-Kontakt].

---

**Hinweis**: Diese Anwendung ist für macOS optimiert und nutzt systemspezifische Audio-Features. BlackHole ist essentiell für die System-Audio-Aufnahme.
