# 🧠 ATA Audio-Aufnahme

Eine hochentwickelte macOS-Anwendung für parallele System- und Mikrofon-Audioaufnahme mit KI-basierter Sprechererkennung, automatischer Transkription und intelligenter Gesprächsanalyse.

## 🚀 Features

- 🎙️ **Hochqualitative Audioaufnahme** (System + Mikrofon via BlackHole)
- 🗣️ **Automatische Sprechererkennung** (Speaker Diarization)
- 📝 **WhisperX-basierte Transkription** mit Zeitstempeln
- 🤖 **KI-Zusammenfassung** durch Large Language Models (Ollama)
- 🌐 **Remote Docker-Services** über DHBW-Server
- 📊 **Visuelle Timeline** der Gesprächssegmente
- ⚙️ **FFmpeg-Integration** für beste Audioqualität

## 📋 Voraussetzungen

- **macOS** (Intel oder Apple Silicon)
- **Python 3.8+** (empfohlen: 3.9–3.12)
- **VPN-Verbindung zur DHBW Mannheim** (für Docker-Services)
- **Homebrew** (wird automatisch installiert, falls nicht vorhanden)
- **FFmpeg** (wird automatisch installiert für beste Audioqualität)

## 🔄 Installation

### 1. Repository klonen
```bash
git clone https://github.com/DEIN_REPO/ata-audio-aufnahme.git
cd ata-audio-aufnahme
```

### 2. DHBW VPN-Verbindung herstellen

**⚠️ WICHTIG: Ohne VPN-Verbindung zur DHBW können die Docker-Services nicht erreicht werden!**

1. Verbinden Sie sich mit dem DHBW VPN
2. Die Services laufen auf dem Server: `141.72.16.242`

### 3. Automatische Installation und Start

```bash
# Einfacher Start mit automatischer Installation
./start.sh
```

Das `start.sh` Skript führt automatisch folgende Schritte durch:
- **Überprüft System-Dependencies**
- **Fragt vor Installation** ob fehlende Komponenten installiert werden sollen:
  - Homebrew (falls nicht vorhanden)
  - Python 3.11+ (falls nicht vorhanden)
  - BlackHole Audio Driver
- **Installiert automatisch:**
  - **FFmpeg (für beste Audioqualität)**
- **Erstellt/aktiviert Virtual Environment**
- **Installiert Python-Dependencies**
- **Startet die Anwendung**

### 4. BlackHole konfigurieren (bei Erstinstallation)

Wenn BlackHole neu installiert wurde, muss es konfiguriert werden:

#### Audio-MIDI-Setup konfigurieren:

1. **Öffnen Sie Audio-MIDI-Setup:**
   - Pfad: `/Programme/Dienstprogramme/Audio-MIDI-Setup.app`
   - Oder: `cmd + space` → "Audio MIDI" suchen

2. **Erstellen Sie ein Aggregat-Gerät:**
   - Klicken Sie auf das `+` Symbol unten links
   - Wählen Sie "Aggregat-Gerät erstellen"
   - **Aktivieren Sie:**
     - Ihr Mikrofon (z.B. "MacBook Pro Mikrofon")
     - BlackHole 2ch
   - Benennen Sie es z.B. "BlackHole + Mikrofon"

3. **Erstellen Sie ein Multi-Output-Gerät:**
   - Klicken Sie erneut auf `+`
   - Wählen Sie "Multi-Output-Gerät erstellen"
   - **Aktivieren Sie:**
     - Ihre Lautsprecher/Kopfhörer
     - BlackHole 2ch
   - Benennen Sie es z.B. "Lautsprecher + BlackHole"

4. **Setzen Sie das Multi-Output-Gerät als Standard:**
   - Gehen Sie zu: Systemeinstellungen → Ton → Ausgabe
   - Wählen Sie Ihr Multi-Output-Gerät als Standardausgabe

## 🐳 Service-Übersicht

| Service               | URL/Port              | Zweck                           | Status               |
|----------------------|----------------------|--------------------------------|---------------------|
| WhisperX API         | Port 8500            | Transkription & Diarization    | ✅ Läuft auf Server  |
| Summarization API    | Port 8501            | KI-Zusammenfassungen           | ✅ Läuft auf Server  |
| Ollama LLM           | Port 11434           | LLM-Modelle für Zusammenfassung | ✅ Läuft auf Server  |

**Hinweis**: Alle Docker-Services laufen bereits auf dem DHBW-Server (`141.72.16.242`) und müssen nicht lokal installiert werden.

### Service Health Checks

Die Anwendung überprüft automatisch alle Services beim Start:
- ✅ **Grün**: Service verfügbar und funktionsfähig
- ⚠️ **Gelb**: Service teilweise verfügbar oder Probleme
- ❌ **Rot**: Service nicht erreichbar

## 🎯 Verwendung

### 1. Grundsetup
1. **DHBW VPN verbinden** (zwingend erforderlich!)
2. Anwendung mit `./start.sh` starten
3. Bei erster Verwendung: **Geräteauswahl** durchführen
   - Loopback-Gerät: BlackHole 2ch wählen
   - Mikrofon: Ihr gewünschtes Mikrofon wählen

### 2. Aufnahme starten
1. **"Start"** klicken
2. **Audio abspielen** (YouTube, Musik, etc.) → wird automatisch aufgenommen
3. **Ins Mikrofon sprechen** → wird parallel aufgenommen
4. **"Stop"** klicken

### 3. Ergebnisse betrachten
Nach der Aufnahme erhalten Sie automatisch:
- 📊 **Visuelle Timeline** der Sprecher-Segmente
- 📝 **Vollständige Transkription** mit Sprecher-Zuordnung
- 🧠 **KI-Zusammenfassung** mit:
  - Hauptpunkte des Gesprächs
  - Identifizierte To-Dos
  - Teilnehmer-Analyse
  - Gesprächsstimmung

## 📖 Hilfe & Dokumentation

- **In der App**: Klicken Sie auf **"Hilfe"** für detaillierte Anweisungen
- **Problembehandlung**: Siehe Hilfe-Bereich in der Anwendung
- **Vollständiges Manual**: Integrierte Dokumentation mit Schritt-für-Schritt Anweisungen

## 🔧 Erweiterte Konfiguration

### Umgebungsvariablen

Erstellen Sie eine `.env` Datei für individuelle Anpassungen:

```bash
# API-Endpunkte (Standard: DHBW Server)
ATA_WHISPERX_API_URL=http://141.72.16.242:8500/transcribe
ATA_SUMMARIZATION_SERVICE_URL=http://141.72.16.242:8501

# Audio-Qualität
ATA_SAMPLE_RATE=44100
ATA_BUFFER_SIZE=4096

# Sprechererkennung
ATA_MAX_SPEAKERS=3
ATA_ENABLE_SPEAKER_DIARIZATION=true
```

### Service-URLs konfigurieren

Die Standard-Konfiguration in `config/settings.py` ist bereits für den DHBW-Server eingestellt:

```python
# DHBW Server (Standard - keine Änderung nötig)
WHISPERX_API_URL = "http://141.72.16.242:8500/transcribe"
SUMMARIZATION_SERVICE_URL = "http://141.72.16.242:8501"
OLLAMA_SERVICE_URL = "http://141.72.16.242:11434"
```

## 🚨 Fehlerbehebung

### Häufige Probleme

1. **"Kein BlackHole gefunden"**
   ```bash
   # BlackHole neu installieren
   brew reinstall blackhole-2ch
   
   # Audio-Services neu starten
   sudo killall coreaudiod
   ```

2. **"API Services nicht erreichbar"**
   - ✅ VPN-Verbindung zur DHBW prüfen
   - ✅ Server erreichbar: Testen Sie in der App mit "API Test"
   - ✅ Service-URLs in settings.py überprüfen

3. **"start.sh findet Komponenten nicht"**
   ```bash
   # Homebrew-Pfad manuell hinzufügen (Apple Silicon Macs)
   echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
   source ~/.zprofile
   ```

4. **Audioqualitätsprobleme**
   - FFmpeg wird automatisch installiert, aber falls manuell nötig: `brew install ffmpeg`
   - Puffergröße in Geräteeinstellungen erhöhen
   - Andere Audio-intensive Programme schließen

### Service-spezifische Probleme

- **WhisperX**: Bei Timeout-Fehlern → Timeout in settings.py erhöhen
- **Summarization**: Bei langsamer Verarbeitung → Normale Wartezeit bei großen Gesprächen
- **Allgemein**: VPN-Verbindung zur DHBW ist essenziell für alle Services

### Manuelle Installation (falls start.sh fehlschlägt)

```bash
# Virtual Environment erstellen
python3 -m venv .venv
source .venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Falls FFmpeg fehlt (wird normalerweise automatisch installiert)
brew install ffmpeg

# Direkt starten
python startup.py
```

## 📁 Projektstruktur

```
ata-audio-aufnahme/
├── start.sh               # Automatisches Setup & Start
├── main.py                # Hauptanwendung
├── startup.py             # Detaillierte System-Checks
├── requirements.txt       # Python-Dependencies
├── config/
│   └── settings.py       # Zentrale Konfiguration
├── audio/                # Audio-Verarbeitung
│   ├── processor.py      # Audio-Aufnahme
│   ├── whisperx_processor.py # WhisperX Integration
│   └── device_manager.py # Audio-Geräte-Management
├── gui/                  # Benutzeroberfläche
│   ├── dialogs.py       # Dialog-Fenster  
│   ├── components.py    # Timeline & Transkription
│   └── summary_widget.py # KI-Zusammenfassung
└── utils/               # Hilfsfunktionen
    ├── logger.py        # Logging-System
    └── service_health_monitor.py # Service-Überwachung
```

## 🌐 Netzwerk-Topologie

```
[macOS App] ←→ [DHBW VPN] ←→ [Server 141.72.16.242]
                                ├── WhisperX API (:8500)
                                ├── Summarization (:8501)
                                └── Ollama LLM (:11434)
```

## 🤝 Mitwirken

Pull Requests sind willkommen! Bei größeren Änderungen bitte vorher ein Issue erstellen.

## 📞 Support

- **In-App Hilfe**: Klicken Sie auf "Hilfe" in der Anwendung
- **GitHub Issues**: Für Bugs und Feature-Requests
- **DHBW-Context**: Bei VPN/Server-Problemen an DHBW IT wenden

---

**⚠️ Wichtiger Hinweis**: Diese Anwendung ist für die Verwendung mit DHBW-Infrastruktur optimiert und erfordert VPN-Zugang. Alle Docker-Services laufen bereits auf dem Server und müssen nicht lokal installiert werden.