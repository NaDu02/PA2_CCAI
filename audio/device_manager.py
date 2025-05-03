# audio/device_manager.py
"""
Geräte-Management für die ATA Audio-Aufnahme
"""
import sounddevice as sd


class DeviceManager:
    def __init__(self, logger=None):
        self.logger = logger

    def get_audio_devices(self):
        """Ermittelt alle verfügbaren Audiogeräte und gibt sie als Listen zurück."""
        loopback_devices = []
        microphones = []

        try:
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                name = device['name']
                max_input_channels = device.get('max_input_channels', 0)
                max_output_channels = device.get('max_output_channels', 0)

                if self.logger:
                    self.logger.log_message(
                        f"Gerät {i}: {name} (Input: {max_input_channels}, Output: {max_output_channels})", "INFO")

                if 'BlackHole' in name:
                    if max_input_channels > 0:
                        loopback_devices.append((i, name, max_input_channels))
                elif max_input_channels > 0:
                    microphones.append((i, name, max_input_channels))

        except Exception as e:
            if self.logger:
                self.logger.log_message(f"Fehler beim Abrufen der Audiogeräte: {e}", "ERROR")

        return loopback_devices, microphones

    def check_blackhole(self):
        """Überprüft, ob BlackHole installiert ist."""
        try:
            devices = sd.query_devices()
            for device in devices:
                if 'BlackHole' in device['name']:
                    return True, device['name']
            return False, None
        except Exception as e:
            if self.logger:
                self.logger.log_message(f"Fehler bei BlackHole-Prüfung: {e}", "ERROR")
            return False, None