#!/bin/bash
# test_whisperx_curl.sh - cURL Tests für WhisperX API

echo "=== WhisperX API cURL Tests ==="

# Erstelle eine kleine Test-Datei
echo "Erstelle Test-Datei..."
ffmpeg -f lavfi -i "sine=frequency=1000:duration=1" -ar 16000 -ac 1 test_curl.wav -y

# Test 1: Health Check
echo -e "\n1. Health Check"
curl -X GET http://141.72.16.242:8500/health -w "\nStatus: %{http_code}\nTime: %{time_total}s\n"

# Test 2: Kleine Datei (schnell)
echo -e "\n2. Upload kleine Datei"
curl -X POST \
  -F "file=@test_curl.wav" \
  -F "language=de" \
  -F "compute_type=float16" \
  -F "enable_diarization=false" \
  http://141.72.16.242:8500/transcribe \
  -w "\nStatus: %{http_code}\nTime: %{time_total}s\nSize uploaded: %{size_upload} bytes\n" \
  --max-time 30

# Test 3: Größere Datei
echo -e "\n3. Erstelle größere Test-Datei..."
ffmpeg -f lavfi -i "sine=frequency=1000:duration=5" -ar 44100 -ac 2 test_large_curl.wav -y

echo -e "\n4. Upload größere Datei"
curl -X POST \
  -F "file=@test_large_curl.wav" \
  -F "language=de" \
  -F "compute_type=float16" \
  -F "enable_diarization=false" \
  http://141.72.16.242:8500/transcribe \
  -w "\nStatus: %{http_code}\nTime: %{time_total}s\nSize uploaded: %{size_upload} bytes\n" \
  --max-time 120 \
  --limit-rate 100k  # Begrenze Upload-Rate für Test

# Test 4: Mit Keep-Alive
echo -e "\n5. Test mit Keep-Alive"
curl -X POST \
  -F "file=@test_curl.wav" \
  -F "language=de" \
  -F "compute_type=float16" \
  -F "enable_diarization=false" \
  -H "Connection: keep-alive" \
  http://141.72.16.242:8500/transcribe \
  -w "\nStatus: %{http_code}\nTime: %{time_total}s\n" \
  --max-time 30

# Aufräumen
rm -f test_curl.wav test_large_curl.wav

echo -e "\n=== Tests abgeschlossen ==="