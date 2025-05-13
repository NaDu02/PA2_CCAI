# test_whisperx_api.py
import os
import requests
import time
import numpy as np
import soundfile as sf

WHISPERX_API_URL = "http://141.72.16.242:8500/transcribe"


def test_api_health():
    """Teste ob die API grundsätzlich erreichbar ist"""
    print("=== API Health Check ===")
    health_url = WHISPERX_API_URL.replace('/transcribe', '/health')

    try:
        print(f"Teste: {health_url}")
        resp = requests.get(health_url, timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        return resp.ok
    except Exception as e:
        print(f"Fehler beim Health Check: {e}")
        return False


def test_small_file():
    """Teste mit einer sehr kleinen Datei"""
    print("\n=== Test mit kleiner Datei ===")

    # 1 Sekunde Stille bei 16kHz
    audio_data = np.zeros(16000, dtype=np.float32)
    test_file = "test_small.wav"
    sf.write(test_file, audio_data, 16000)

    try:
        file_size = os.path.getsize(test_file)
        print(f"Test-Datei erstellt: {test_file} ({file_size} Bytes)")

        start_time = time.time()

        with open(test_file, "rb") as f:
            files = {"file": (test_file, f, "audio/wav")}
            data = {
                "language": "de",
                "compute_type": "float16",
                "enable_diarization": "false"
            }

            print("Sende kleine Datei...")
            resp = requests.post(WHISPERX_API_URL, files=files, data=data, timeout=30)

        duration = time.time() - start_time
        print(f"Upload-Dauer: {duration:.2f} Sekunden")
        print(f"Status: {resp.status_code}")

        if resp.ok:
            print("✅ Kleine Datei erfolgreich übertragen")
            print(f"Response: {resp.text[:200]}...")
        else:
            print(f"❌ Fehler: {resp.text}")

        os.remove(test_file)
        return resp.ok

    except Exception as e:
        print(f"Fehler: {e}")
        if os.path.exists(test_file):
            os.remove(test_file)
        return False


def test_medium_file():
    """Teste mit mittlerer Datei (wie die Original-Aufnahme)"""
    print("\n=== Test mit mittlerer Datei ===")

    # 5 Sekunden bei 44.1kHz Stereo (ca. 1.8MB)
    audio_data = np.zeros((44100 * 5, 2), dtype=np.float32)
    test_file = "test_medium.wav"
    sf.write(test_file, audio_data, 44100)

    try:
        file_size = os.path.getsize(test_file)
        print(f"Test-Datei erstellt: {test_file} ({file_size / 1024 / 1024:.2f} MB)")

        timeouts = [30, 60, 120]

        for timeout in timeouts:
            print(f"\nTeste mit Timeout: {timeout}s")
            start_time = time.time()

            try:
                with open(test_file, "rb") as f:
                    files = {"file": (test_file, f, "audio/wav")}
                    data = {
                        "language": "de",
                        "compute_type": "float16",
                        "enable_diarization": "false"
                    }

                    resp = requests.post(WHISPERX_API_URL, files=files, data=data, timeout=timeout)

                duration = time.time() - start_time
                print(f"Upload-Dauer: {duration:.2f} Sekunden")
                print(f"Status: {resp.status_code}")

                if resp.ok:
                    print(f"✅ Erfolgreich mit Timeout {timeout}s")
                    print(f"Response: {resp.text[:200]}...")
                    break
                else:
                    print(f"❌ Fehler: {resp.text[:200]}...")

            except requests.Timeout:
                print(f"❌ Timeout nach {timeout}s")
            except Exception as e:
                print(f"❌ Fehler: {e}")

        os.remove(test_file)

    except Exception as e:
        print(f"Fehler: {e}")
        if os.path.exists(test_file):
            os.remove(test_file)


def test_multiple_requests():
    """Teste mehrere aufeinanderfolgende Requests"""
    print("\n=== Test mehrere Requests ===")

    # Kleine Testdatei
    audio_data = np.zeros(16000, dtype=np.float32)
    test_file = "test_multiple.wav"
    sf.write(test_file, audio_data, 16000)

    try:
        for i in range(3):
            print(f"\nRequest {i + 1}/3")
            start_time = time.time()

            try:
                with open(test_file, "rb") as f:
                    files = {"file": (test_file, f, "audio/wav")}
                    data = {
                        "language": "de",
                        "compute_type": "float16",
                        "enable_diarization": "false"
                    }

                    resp = requests.post(WHISPERX_API_URL, files=files, data=data, timeout=30)

                duration = time.time() - start_time
                print(f"Request {i + 1}: {duration:.2f}s, Status: {resp.status_code}")

                if not resp.ok:
                    print(f"❌ Fehler bei Request {i + 1}: {resp.text[:100]}...")

                # Kurze Pause zwischen Requests
                time.sleep(2)

            except Exception as e:
                print(f"❌ Fehler bei Request {i + 1}: {e}")

        os.remove(test_file)

    except Exception as e:
        print(f"Fehler: {e}")
        if os.path.exists(test_file):
            os.remove(test_file)


def main():
    print("WhisperX API Test Suite")
    print("======================")

    # 1. Health Check
    if not test_api_health():
        print("\n❌ API nicht erreichbar - weitere Tests übersprungen")
        return

    # 2. Kleine Datei
    test_small_file()

    # 3. Mittlere Datei
    test_medium_file()

    # 4. Mehrere Requests
    test_multiple_requests()

    print("\n=== Test abgeschlossen ===")


if __name__ == "__main__":
    main()