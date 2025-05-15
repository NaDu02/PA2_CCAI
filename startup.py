# startup.py
"""
Startup-Skript für ATA Audio-Aufnahme
Überprüft alle Voraussetzungen vor dem Start des Hauptprogramms
"""
import os
import sys
import subprocess
import importlib
from importlib import metadata
from packaging import version


# Farbcodes für bessere Lesbarkeit
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_colored(text, color):
    print(f"{color}{text}{Colors.ENDC}")


def print_header(text):
    print_colored(f"\n{Colors.BOLD}=== {text} ==={Colors.ENDC}", Colors.BLUE)


def check_file_structure():
    """Überprüft, ob alle erforderlichen Dateien vorhanden sind"""
    print_header("Überprüfe Dateistruktur")

    required_files = [
        'main.py',
        'config/__init__.py',
        'config/settings.py',
        'audio/__init__.py',
        'audio/processor.py',
        'audio/device_manager.py',
        'audio/diarization_processor.py',
        'audio/simple_speaker_diarization.py',
        'audio/whisperx_processor.py',
        'gui/__init__.py',
        'gui/dialogs.py',
        'gui/components.py',
        'utils/__init__.py',
        'utils/logger.py',
        'requirements.txt'
    ]

    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print_colored(f"✓ {file_path}", Colors.GREEN)
        else:
            print_colored(f"✗ {file_path}", Colors.RED)
            missing_files.append(file_path)

    if missing_files:
        print_colored(f"\n⚠️ Es fehlen {len(missing_files)} Dateien!", Colors.RED)
        return False
    else:
        print_colored("\n✓ Alle erforderlichen Dateien sind vorhanden!", Colors.GREEN)
        return True


def check_requirements():
    """Überprüft, ob alle Python-Pakete installiert sind"""
    print_header("Überprüfe Python-Pakete")

    # Hole Paket-Anforderungen aus settings.py
    try:
        from config.settings import REQUIRED_PACKAGES
        required_packages = REQUIRED_PACKAGES
    except ImportError:
        # Fallback
        required_packages = {
            'numpy': '1.24.0',
            'sounddevice': '0.4.6',
            'soundfile': '0.12.1',
            'requests': '2.31.0',
            'webrtcvad': '2.0.10',
            'scikit-learn': '1.3.0',
            'librosa': '0.10.0',
            'scipy': '1.11.0',
            'matplotlib': '3.7.0'
        }

    missing_packages = []
    wrong_version_packages = []

    for package, min_version in required_packages.items():
        try:
            # Überprüfe, ob das Paket installiert ist
            if package == 'scikit-learn':
                import_name = 'sklearn'
            elif package == 'whisperx':
                # Spezielle Behandlung für whisperx
                try:
                    # Versuche zu importieren
                    importlib.import_module('whisperx')
                    print_colored(f"✓ whisperx (Version kann bei GitHub-Installation nicht ermittelt werden)",
                                  Colors.GREEN)
                    continue
                except ImportError:
                    print_colored(f"✓ whisperx (nicht installiert - wird nur für lokale Verarbeitung benötigt)",
                                  Colors.YELLOW)
                    continue
            else:
                import_name = package.replace('-', '_')

            importlib.import_module(import_name)

            # Überprüfe die Version
            try:
                installed_version = metadata.version(package)
                # Verwende packaging.version für korrekten Versionsvergleich
                if version.parse(installed_version) < version.parse(min_version):
                    print_colored(f"⚠ {package} {installed_version} (mindestens {min_version} erforderlich)",
                                  Colors.YELLOW)
                    wrong_version_packages.append(package)
                else:
                    print_colored(f"✓ {package} {installed_version}", Colors.GREEN)
            except:
                print_colored(f"✓ {package} (Version konnte nicht ermittelt werden)", Colors.GREEN)

        except ImportError:
            print_colored(f"✗ {package} nicht installiert", Colors.RED)
            missing_packages.append(package)

    if missing_packages or wrong_version_packages:
        if missing_packages:
            print_colored(f"\n⚠️ Es fehlen {len(missing_packages)} Pakete!", Colors.RED)
        if wrong_version_packages:
            print_colored(f"⚠️ {len(wrong_version_packages)} Pakete haben die falsche Version!", Colors.YELLOW)
        return False
    else:
        print_colored("\n✓ Alle erforderlichen Pakete sind korrekt installiert!", Colors.GREEN)
        return True


def check_system_requirements():
    """Überprüft systemspezifische Voraussetzungen"""
    print_header("Überprüfe Systemvoraussetzungen")

    issues = []
    critical_issues = False  # Flag für kritische Probleme

    # Python-Version überprüfen
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        issues.append("Python 3.8 oder höher erforderlich")
        print_colored(f"✗ Python-Version: {sys.version.split()[0]} (3.8+ erforderlich)", Colors.RED)
        critical_issues = True  # Dies ist ein kritisches Problem
    else:
        print_colored(f"✓ Python-Version: {sys.version.split()[0]}", Colors.GREEN)

    # WhisperX API oder lokale Installation prüfen
    try:
        from config.settings import USE_WHISPERX_API, WHISPERX_API_URL

        if USE_WHISPERX_API:
            if WHISPERX_API_URL:
                print_colored(f"✓ WhisperX API URL konfiguriert: {WHISPERX_API_URL}", Colors.GREEN)
            else:
                print_colored("✗ WhisperX API URL nicht konfiguriert", Colors.RED)
                issues.append("WhisperX API URL fehlt in settings.py")
                critical_issues = True
        else:
            print_colored("⚠️ WhisperX API deaktiviert", Colors.YELLOW)
            if python_version.major == 3 and python_version.minor > 12:
                    print_colored(
                        "  Hinweis: Python 3.13+ ist nicht mit WhisperX kompatibel. Verwenden Sie Python 3.9-3.12 oder die API.", Colors.YELLOW)
                    issues.append("WhisperX nicht installiert (nur für lokale Verarbeitung nötig)")
    except (ImportError, AttributeError):
        print_colored("✗ WhisperX-Konfiguration unvollständig in settings.py", Colors.RED)
        issues.append("WhisperX-Konfiguration fehlt oder ist unvollständig")
        critical_issues = True

    # FFmpeg als optional markieren, wenn API verwendet wird
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            ffmpeg_version = result.stdout.split('\n')[0]
            print_colored(f"✓ FFmpeg gefunden: {ffmpeg_version}", Colors.GREEN)
        else:
            print_colored("✗ FFmpeg gefunden, aber Version konnte nicht ermittelt werden", Colors.YELLOW)
            issues.append("FFmpeg Version konnte nicht ermittelt werden")
    except FileNotFoundError:
        try:
            from config.settings import USE_WHISPERX_API
            if USE_WHISPERX_API:
                # Wenn API verwendet wird, ist FFmpeg nur für bessere Audioqualität empfohlen
                print_colored("✗ FFmpeg nicht gefunden - für bessere Audioqualität empfohlen", Colors.YELLOW)
                # Nicht als kritisches Problem markieren
                issues.append("FFmpeg nicht gefunden (brew install ffmpeg)")
            else:
                print_colored("✗ FFmpeg nicht gefunden - empfohlen für Audio-Verarbeitung", Colors.RED)
                issues.append("FFmpeg nicht gefunden (brew install ffmpeg)")
                critical_issues = True
        except (ImportError, AttributeError):
            print_colored("✗ FFmpeg nicht gefunden - für beste Audioqualität empfohlen", Colors.YELLOW)
            issues.append("FFmpeg nicht gefunden (brew install ffmpeg)")

    # macOS-spezifische Überprüfungen
    if sys.platform == 'darwin':
        # Überprüfe, ob BlackHole installiert ist
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            blackhole_found = any('BlackHole' in device.get('name', '') for device in devices)

            if blackhole_found:
                print_colored("✓ BlackHole Audio-Loopback gefunden", Colors.GREEN)
            else:
                print_colored("✗ BlackHole Audio-Loopback nicht gefunden", Colors.RED)
                issues.append("BlackHole muss installiert werden: brew install blackhole-2ch")
                critical_issues = True
        except:
            print_colored("⚠ Konnte Audio-Geräte nicht überprüfen", Colors.YELLOW)
            issues.append("Konnte Audio-Geräte nicht überprüfen")

    if issues:
        print_colored(f"\n⚠️ Es gibt {len(issues)} Systemprobleme:",
                      Colors.YELLOW if not critical_issues else Colors.RED)
        for issue in issues:
            print_colored(f"  - {issue}", Colors.YELLOW if not critical_issues else Colors.RED)
        return False, critical_issues
    else:
        print_colored("\n✓ Alle Systemvoraussetzungen erfüllt!", Colors.GREEN)
        return True, False


def install_missing_requirements():
    """Installiert fehlende Requirements"""
    print_header("Installiere fehlende Pakete")

    try:
        print_colored("Führe 'pip install -r requirements.txt' aus...", Colors.BLUE)
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                                capture_output=True, text=True)

        if result.returncode == 0:
            print_colored("✓ Pakete erfolgreich installiert!", Colors.GREEN)
            return True
        else:
            print_colored(f"✗ Fehler bei der Installation: {result.stderr}", Colors.RED)
            return False
    except Exception as e:
        print_colored(f"✗ Installationsfehler: {e}", Colors.RED)
        return False


def check_service_health():
    """Überprüft den Status aller API-Services"""
    print_header("Überprüfe API-Services")

    # Import hier um zirkuläre Imports zu vermeiden
    try:
        from utils.service_health_monitor import ServiceHealthMonitor
        from config import settings

        monitor = ServiceHealthMonitor()
        results = monitor.check_all_services(detailed=False)
        summary = monitor.get_service_summary()

        healthy_count = summary["healthy_count"]
        total_count = summary["total_count"]

        # Zeige Ergebnisse
        for service_id, status in results.items():
            if status.healthy:
                print_colored(f"✓ {status.name}: OK ({status.response_time:.2f}s)", Colors.GREEN)
            else:
                print_colored(f"✗ {status.name}: {status.error_message}", Colors.RED)

        # Zusammenfassung
        if healthy_count == total_count:
            print_colored(f"\n✓ Alle {total_count} Services sind verfügbar!", Colors.GREEN)
            return True, False
        elif healthy_count > 0:
            print_colored(f"\n⚠️ {healthy_count} von {total_count} Services verfügbar", Colors.YELLOW)
            print_colored("Das Programm kann trotzdem gestartet werden mit eingeschränkter Funktionalität",
                          Colors.YELLOW)
            return True, False  # Nicht kritisch, aber mit Einschränkungen
        else:
            print_colored(f"\n❌ Keine Services verfügbar!", Colors.RED)
            print_colored("Überprüfen Sie die Docker-Container:", Colors.YELLOW)

            # Zeige Server-Status statt Docker-Befehle
            print_colored("\nÜberprüfen Sie die Server-Services:", Colors.YELLOW)
            print_colored("WhisperX API: http://141.72.16.242:8500/health", Colors.BLUE)
            print_colored("Summarization Service: http://141.72.16.242:8501/health", Colors.BLUE)
            print_colored("Ollama Service: http://localhost:11434/api/tags", Colors.BLUE)

            return False, False  # Services down, aber nicht kritisch für Audio

    except ImportError as e:
        print_colored(f"⚠️ Service-Check nicht verfügbar: {e}", Colors.YELLOW)
        return True, False
    except Exception as e:
        print_colored(f"⚠️ Fehler beim Service-Check: {e}", Colors.YELLOW)
        return True, False


def main():
    """Hauptfunktion für den Startup-Check"""
    print_colored(f"{Colors.BOLD}ATA Audio-Aufnahme - Detaillierter Check{Colors.ENDC}", Colors.BLUE)
    print_colored("=" * 50, Colors.BLUE)

    # Hinweis dass start.sh bereits system-deps installiert hat
    print_colored("Hinweis: System-Dependencies wurden bereits von start.sh geprüft", Colors.BLUE)
    print_colored("-" * 50, Colors.BLUE)

    # Überprüfe nur noch App-spezifische Sachen
    files_ok = check_file_structure()

    # Python-Requirements (should be installed by start.sh)
    requirements_ok = check_requirements()
    if not requirements_ok:
        print_colored("Warnung: Python-Dependencies nicht vollständig", Colors.YELLOW)
        print_colored("start.sh sollte diese installiert haben", Colors.YELLOW)

    # Leichte System-Checks (ohne Installation)
    system_ok, critical_issues = check_system_requirements()

    # Service checks
    services_ok, services_critical = check_service_health()

    # Zusammenfassung
    print_header("Zusammenfassung")

    # Bewerte kritische vs. nicht-kritische Probleme (Docker entfernt)
    core_systems_ok = files_ok and requirements_ok and (system_ok or not critical_issues)

    if core_systems_ok:
        print_colored("✓ Alle kritischen Komponenten sind verfügbar!", Colors.GREEN)

        # Zeige Service-Status
        if not services_ok:
            print_colored("⚠️ Einige API-Services sind nicht verfügbar", Colors.YELLOW)
            print_colored("  → Grund-Funktionen (Audio-Aufnahme) funktionieren trotzdem", Colors.BLUE)
            print_colored("  → Erweiterte Features (Transkription, Zusammenfassung) möglicherweise begrenzt",
                          Colors.BLUE)
            print_colored("  → Überprüfen Sie die Server-Verbindung", Colors.BLUE)

        print_colored("\nStarte Hauptprogramm...\n", Colors.BLUE)

        # Starte das Hauptprogramm
        try:
            result = subprocess.run([sys.executable, 'main.py'])
            return result.returncode
        except Exception as e:
            print_colored(f"✗ Fehler beim Start des Hauptprogramms: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
            return 1

    else:
        if not critical_issues:
            print_colored("⚠️ Einige Überprüfungen sind fehlgeschlagen, aber keine kritischen Probleme!", Colors.YELLOW)
            response = input("\nMöchten Sie das Programm trotzdem starten? (j/n): ")
            if response.lower() == 'j':
                print_colored("\nStarte Hauptprogramm...\n", Colors.BLUE)
                result = subprocess.run([sys.executable, 'main.py'])
                return result.returncode
        else:
            print_colored("✗ Einige kritische Überprüfungen sind fehlgeschlagen!", Colors.RED)
            print_colored("Das Programm kann ohne diese Komponenten nicht ordnungsgemäß funktionieren.", Colors.RED)

        if not requirements_ok:
            response = input("\nMöchten Sie die fehlenden Pakete jetzt installieren? (j/n): ")
            if response.lower() == 'j':
                if install_missing_requirements():
                    print_colored("\nPakete wurden installiert. Starte Programm neu...", Colors.GREEN)
                    return main()  # Rekursiver Aufruf nach Installation
                else:
                    print_colored("\nInstallation fehlgeschlagen. Bitte installieren Sie die Pakete manuell.",
                                  Colors.RED)

        # Zeige Hilfe für Service-Probleme (ohne Docker-Befehle)
        if not services_ok:
            print_colored("\nTipp: Überprüfen Sie die Server-Services:", Colors.BLUE)
            print_colored("  WhisperX API: http://141.72.16.242:8500/health", Colors.BLUE)
            print_colored("  Summarization Service: http://141.72.16.242:8501/health", Colors.BLUE)
            print_colored("  Kontaktieren Sie den Administrator bei anhaltenden Problemen", Colors.BLUE)

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())