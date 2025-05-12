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
        'audio/whisperx_processor.py',  # Neue Datei
        'gui/__init__.py',
        'gui/dialogs.py',
        'gui/components.py',
        'utils/__init__.py',
        'utils/logger.py',
        'tests/__init__.py',
        'tests/test_recording.py',
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
                # Spezielle Behandlung für whisperx, da es möglicherweise direkt von GitHub installiert wurde
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
        from config.settings import USE_WHISPERX, USE_WHISPERX_API, WHISPERX_API_URL

        if USE_WHISPERX and USE_WHISPERX_API:
            # Bei API-Nutzung nur prüfen, ob URL konfiguriert ist
            if WHISPERX_API_URL:
                print_colored(f"✓ WhisperX API URL konfiguriert: {WHISPERX_API_URL}", Colors.GREEN)
            else:
                print_colored("✗ WhisperX API URL nicht konfiguriert", Colors.RED)
                issues.append("WhisperX API URL fehlt in settings.py")
                critical_issues = True
        elif USE_WHISPERX:
            # Bei lokaler Nutzung WhisperX prüfen
            try:
                import whisperx
                print_colored("✓ WhisperX ist lokal installiert", Colors.GREEN)
            except ImportError:
                print_colored("✗ WhisperX nicht gefunden - wird für lokale Sprechererkennung benötigt", Colors.YELLOW)
                if python_version.major == 3 and python_version.minor > 12:
                    print_colored(
                        "  Hinweis: Python 3.13+ ist nicht mit WhisperX kompatibel. Verwenden Sie Python 3.9-3.12 oder die API.",
                        Colors.YELLOW)
                issues.append("WhisperX nicht installiert (nur für lokale Verarbeitung nötig)")
    except (ImportError, AttributeError):
        print_colored("✗ WhisperX-Konfiguration unvollständig in settings.py", Colors.RED)
        issues.append("WhisperX-Konfiguration fehlt oder ist unvollständig")
        critical_issues = True

    # Hugging Face Token prüfen (nur bei lokaler Verarbeitung wichtig)
    try:
        from config.settings import HUGGINGFACE_TOKEN, USE_WHISPERX_API

        if not USE_WHISPERX_API and HUGGINGFACE_TOKEN:
            print_colored("✓ Hugging Face Token gefunden", Colors.GREEN)
        elif not USE_WHISPERX_API and not HUGGINGFACE_TOKEN:
            print_colored("✗ Hugging Face Token fehlt in settings.py (nur für lokale Verarbeitung nötig)",
                          Colors.YELLOW)
            issues.append("Hugging Face Token fehlt - erforderlich für lokale pyannote.audio")
        else:
            # Bei API-Nutzung nicht relevant
            print_colored("✓ Hugging Face Token gefunden", Colors.GREEN)
    except (ImportError, AttributeError):
        print_colored("✗ Hugging Face Token nicht in settings.py definiert", Colors.YELLOW)
        issues.append("Hugging Face Token fehlt - erforderlich für lokale pyannote.audio")

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
            # Optional: WhisperX Prüfung - nur wenn lokale Verarbeitung konfiguriert ist
            try:
                from config.settings import USE_WHISPERX_API
                if not USE_WHISPERX_API:
                    print_colored("Installiere WhisperX für lokale Verarbeitung...", Colors.BLUE)
                    whisperx_result = subprocess.run(
                        [sys.executable, '-m', 'pip', 'install', 'git+https://github.com/m-bain/whisperX.git'],
                        capture_output=True, text=True
                    )

                    if whisperx_result.returncode == 0:
                        print_colored("✓ WhisperX erfolgreich installiert!", Colors.GREEN)
                    else:
                        print_colored(f"✗ Fehler bei der WhisperX-Installation: {whisperx_result.stderr}", Colors.RED)
                        return False
            except (ImportError, AttributeError):
                # Wenn Einstellung nicht gefunden wird, nichts tun
                pass

            print_colored("✓ Pakete erfolgreich installiert!", Colors.GREEN)
            return True
        else:
            print_colored(f"✗ Fehler bei der Installation: {result.stderr}", Colors.RED)
            return False
    except Exception as e:
        print_colored(f"✗ Installationsfehler: {e}", Colors.RED)
        return False


def main():
    """Hauptfunktion für den Startup-Check"""
    print_colored(f"{Colors.BOLD}ATA Audio-Aufnahme - Startup Check{Colors.ENDC}", Colors.BLUE)
    print_colored("================================", Colors.BLUE)

    # Überprüfe Dateistruktur
    files_ok = check_file_structure()

    # Überprüfe Requirements
    requirements_ok = check_requirements()

    # Überprüfe Systemvoraussetzungen
    system_ok, critical_issues = check_system_requirements()

    # Zusammenfassung
    print_header("Zusammenfassung")

    if files_ok and requirements_ok and (system_ok or not critical_issues):
        print_colored("✓ Alle kritischen Überprüfungen erfolgreich!", Colors.GREEN)
        print_colored("\nStarte Hauptprogramm...\n", Colors.BLUE)

        # Starte das Hauptprogramm
        try:
            # Verwende subprocess um main.py direkt auszuführen
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
                # Verwende subprocess um main.py direkt auszuführen
                result = subprocess.run([sys.executable, 'main.py'])
                return result.returncode
        else:
            print_colored("✗ Einige kritische Überprüfungen sind fehlgeschlagen!", Colors.RED)

        if not requirements_ok:
            response = input("\nMöchten Sie die fehlenden Pakete jetzt installieren? (j/n): ")
            if response.lower() == 'j':
                if install_missing_requirements():
                    print_colored("\nPakete wurden installiert. Starte Programm neu...", Colors.GREEN)
                    # Rekursiver Aufruf nach Installation
                    return main()
                else:
                    print_colored("\nInstallation fehlgeschlagen. Bitte installieren Sie die Pakete manuell.",
                                  Colors.RED)

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())