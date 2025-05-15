# audio/device_manager.py
"""
Geräte-Management für die ATA Audio-Aufnahme
Ermittlung verfügbarer Audiogeräte + Überprüfung Verfügbarkeit von der Software BlackHole
"""
import sounddevice as sd
from typing import List, Tuple, Optional


class DeviceManager:
    """Verwaltet Audio-Geräte für Aufnahme und Loopback"""

    # Bekannte Loopback-Geräte (erweiterbar)
    LOOPBACK_KEYWORDS = ['BlackHole', 'Loopback', 'SoundflowerBed']

    def __init__(self, logger=None):
        self.logger = logger
        self._devices_cache = None

    def _log(self, message: str, level: str = "INFO"):
        """Zentrale Logging-Methode"""
        if self.logger:
            self.logger.log_message(message, level)

    def get_audio_devices(self) -> Tuple[List[Tuple], List[Tuple]]:
        """
        Ermittelt alle verfügbaren Audiogeräte und gibt sie als Listen zurück.

        Returns:
            Tuple[loopback_devices, microphones]:
            - loopback_devices: [(device_id, name, channels, sample_rate), ...]
            - microphones: [(device_id, name, channels, sample_rate), ...]
        """
        loopback_devices = []
        microphones = []

        try:
            devices = sd.query_devices()
            self._devices_cache = devices

            for i, device in enumerate(devices):
                name = device['name']
                max_input_channels = device.get('max_input_channels', 0)
                max_output_channels = device.get('max_output_channels', 0)
                default_samplerate = device.get('default_samplerate', 44100)

                # Log alle Geräte für Debug
                self._log(
                    f"Gerät {i}: {name} "
                    f"(Input: {max_input_channels}, Output: {max_output_channels}, "
                    f"SR: {default_samplerate}Hz)",
                    "INFO"
                )

                # Erweiterte Loopback-Erkennung
                if self._is_loopback_device(name, max_input_channels):
                    loopback_devices.append((i, name, max_input_channels, default_samplerate))
                    self._log(f"✅ Loopback-Gerät erkannt: {name}", "SUCCESS")

                # Mikrofon-Erkennung (nur Input-Geräte, keine Loopback)
                elif max_input_channels > 0:
                    microphones.append((i, name, max_input_channels, default_samplerate))
                    self._log(f"🎤 Mikrofon erkannt: {name}", "INFO")

        except Exception as e:
            self._log(f"Fehler beim Abrufen der Audiogeräte: {e}", "ERROR")
            return [], []

        # Zusammenfassung loggen
        self._log(f"Gefunden: {len(loopback_devices)} Loopback-Geräte, "
                  f"{len(microphones)} Mikrofone", "SUCCESS")

        return loopback_devices, microphones

    def _is_loopback_device(self, name: str, input_channels: int) -> bool:
        """
        Prüft, ob ein Gerät ein Loopback-Gerät ist

        Args:
            name: Gerätename
            input_channels: Anzahl Input-Kanäle

        Returns:
            True wenn es ein Loopback-Gerät ist
        """
        if input_channels <= 0:
            return False

        # Prüfe gegen bekannte Loopback-Keywords
        name_lower = name.lower()
        return any(keyword.lower() in name_lower for keyword in self.LOOPBACK_KEYWORDS)

    def check_blackhole(self) -> Tuple[bool, Optional[str]]:
        """
        Überprüft, ob BlackHole installiert ist.

        Returns:
            Tuple[is_installed, device_name]:
            - is_installed: True wenn BlackHole gefunden
            - device_name: Name des gefundenen BlackHole-Geräts oder None
        """
        try:
            devices = self._devices_cache or sd.query_devices()

            for device in devices:
                if 'BlackHole' in device['name']:
                    name = device['name']
                    channels = device.get('max_input_channels', 0)
                    self._log(f"✅ BlackHole gefunden: {name} ({channels} Kanäle)", "SUCCESS")
                    return True, name

            self._log("❌ BlackHole nicht gefunden", "WARNING")
            return False, None

        except Exception as e:
            self._log(f"Fehler bei BlackHole-Prüfung: {e}", "ERROR")
            return False, None

    def get_device_info(self, device_id: int) -> Optional[dict]:
        """
        Holt detaillierte Informationen zu einem spezifischen Gerät

        Args:
            device_id: ID des Geräts

        Returns:
            Device-Info Dictionary oder None bei Fehler
        """
        try:
            devices = self._devices_cache or sd.query_devices()
            if 0 <= device_id < len(devices):
                return devices[device_id]
            else:
                self._log(f"Ungültige Device-ID: {device_id}", "ERROR")
                return None
        except Exception as e:
            self._log(f"Fehler beim Abrufen der Device-Info: {e}", "ERROR")
            return None

    def refresh_devices(self):
        """Aktualisiert die Geräte-Liste (Cache invalidieren)"""
        self._devices_cache = None
        self._log("Geräte-Cache geleert, wird bei nächstem Aufruf aktualisiert", "INFO")