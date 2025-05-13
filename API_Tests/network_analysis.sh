#!/bin/bash
# network_analysis.sh - Netzwerkanalyse für WhisperX-Server

echo "=== Netzwerkanalyse für WhisperX-Server ==="

# 1. Ping-Test
echo -e "\n1. Ping-Test:"
ping -c 5 141.72.16.242

# 2. Port-Test
echo -e "\n2. Port-Test (8500):"
nc -zv 141.72.16.242 8500

# 3. Traceroute
echo -e "\n3. Traceroute:"
traceroute 141.72.16.242

# 4. MTU Discovery
echo -e "\n4. MTU Test:"
ping -D -s 1472 -c 1 141.72.16.242  # Test für MTU 1500
ping -D -s 8972 -c 1 141.72.16.242  # Test für Jumbo Frames

# 5. TCP-Connection Test
echo -e "\n5. TCP-Verbindungstest:"
timeout 10 telnet 141.72.16.242 8500 <<EOF
GET /health HTTP/1.1
Host: 141.72.16.242:8500

EOF

# 6. DNS-Auflösung
echo -e "\n6. DNS-Auflösung:"
nslookup 141.72.16.242

echo -e "\n=== Netzwerkanalyse abgeschlossen ==="