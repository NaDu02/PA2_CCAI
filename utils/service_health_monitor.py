# utils/service_health_monitor.py - NEUE DATEI ERSTELLEN
"""
Service Health Monitor für alle API-Services
Zentrale Klasse für Health Checks und Service-Monitoring
"""
import requests
import time
import threading
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from config import settings


@dataclass
class ServiceStatus:
    name: str
    url: str
    healthy: bool
    response_time: float
    last_check: float
    details: Dict
    error_message: Optional[str] = None


class ServiceHealthMonitor:
    """Überwacht den Status aller API-Services"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.services = self._initialize_services()
        self.status_cache = {}
        self.auto_check_enabled = False
        self.auto_check_interval = 30  # Sekunden
        self.auto_check_thread = None
        
    def _initialize_services(self) -> Dict[str, Dict]:
        """Initialisiert die Service-Konfigurationen"""
        return {
            "whisperx": {
                "name": "WhisperX API",
                "base_url": settings.WHISPERX_API_URL.replace('/transcribe', ''),
                "health_endpoint": "/health",
                "test_endpoint": "/transcribe",
                "timeout": getattr(settings, 'HEALTH_CHECK_TIMEOUT', 10),
                "type": "whisperx"
            },
            "summarization": {
                "name": "Summarization Service", 
                "base_url": getattr(settings, 'SUMMARIZATION_SERVICE_URL', "http://141.72.16.242:8501"),
                "health_endpoint": "/health",
                "test_endpoint": "/summarize",
                "timeout": getattr(settings, 'HEALTH_CHECK_TIMEOUT', 10),
                "type": "summarization"
            },
            "ollama": {
                "name": "Ollama LLM",
                "base_url": getattr(settings, 'OLLAMA_SERVICE_URL', "http://localhost:11434"),
                "health_endpoint": "/api/tags",
                "test_endpoint": "/api/generate", 
                "timeout": getattr(settings, 'HEALTH_CHECK_TIMEOUT', 10),
                "type": "ollama"
            }
        }
    
    def _log(self, message: str, level: str = "INFO"):
        """Zentrale Logging-Methode"""
        if self.logger:
            self.logger.log_message(message, level)
    
    def check_all_services(self, detailed: bool = True) -> Dict[str, ServiceStatus]:
        """Führt Health Checks für alle Services durch"""
        self._log("=== Service Health Check gestartet ===", "INFO")
        results = {}
        
        for service_id, config in self.services.items():
            self._log(f"\nTeste {config['name']}...", "INFO")
            status = self.check_single_service(service_id, detailed)
            results[service_id] = status
            
            # Log Ergebnis
            if status.healthy:
                self._log(f"✅ {config['name']}: OK ({status.response_time:.2f}s)", "SUCCESS")
            else:
                self._log(f"❌ {config['name']}: Fehler - {status.error_message}", "ERROR")
        
        # Cache aktualisieren
        self.status_cache = results
        
        # Zusammenfassung
        healthy_count = sum(1 for status in results.values() if status.healthy)
        total_count = len(results)
        
        self._log(f"\n=== Zusammenfassung: {healthy_count}/{total_count} Services OK ===", 
                 "SUCCESS" if healthy_count == total_count else "WARNING")
        
        return results
    
    def check_single_service(self, service_id: str, detailed: bool = True) -> ServiceStatus:
        """Führt Health Check für einen einzelnen Service durch"""
        config = self.services.get(service_id)
        if not config:
            return ServiceStatus(
                name=service_id,
                url="unknown",
                healthy=False,
                response_time=0,
                last_check=time.time(),
                details={},
                error_message="Service nicht konfiguriert"
            )
        
        start_time = time.time()
        
        try:
            # Health Check durchführen
            health_url = f"{config['base_url']}{config['health_endpoint']}"
            
            response = requests.get(
                health_url,
                timeout=config['timeout']
            )
            
            response_time = time.time() - start_time
            
            if response.ok:
                # Service-spezifische Details extrahieren
                details = self._extract_service_details(service_id, response, detailed)
                
                return ServiceStatus(
                    name=config['name'],
                    url=health_url,
                    healthy=True,
                    response_time=response_time,
                    last_check=time.time(),
                    details=details
                )
            else:
                return ServiceStatus(
                    name=config['name'],
                    url=health_url,
                    healthy=False,
                    response_time=response_time,
                    last_check=time.time(),
                    details={},
                    error_message=f"HTTP {response.status_code}"
                )
                
        except requests.exceptions.ConnectionError:
            return ServiceStatus(
                name=config['name'],
                url=health_url,
                healthy=False,
                response_time=time.time() - start_time,
                last_check=time.time(),
                details={},
                error_message="Connection refused"
            )
        except requests.exceptions.Timeout:
            return ServiceStatus(
                name=config['name'],
                url=health_url,
                healthy=False,
                response_time=time.time() - start_time,
                last_check=time.time(),
                details={},
                error_message="Timeout"
            )
        except Exception as e:
            return ServiceStatus(
                name=config['name'],
                url=health_url,
                healthy=False,
                response_time=time.time() - start_time,
                last_check=time.time(),
                details={},
                error_message=str(e)
            )

    def _extract_service_details(self, service_id: str, response: requests.Response,
                                 detailed: bool) -> Dict:
        """Extrahiert service-spezifische Details aus der Health-Response"""
        details = {}

        try:
            data = response.json()

            if service_id == "whisperx":
                details.update({
                    "device": data.get("device", "unknown"),
                    "model_loaded": data.get("model_loaded", False),
                    "gpu_memory": data.get("gpu_memory"),
                    "model_name": data.get("model_name"),
                    "queue_size": data.get("queue_size", 0)
                })

                if detailed:
                    # Log wichtige Details
                    device = details.get("device", "unknown")
                    model_loaded = details.get("model_loaded", False)
                    self._log(f"   Device: {device}, Model: {'Geladen' if model_loaded else 'Nicht geladen'}", "INFO")

            elif service_id == "summarization":
                # KORRIGIERT: Verwende die tatsächlichen Health Check Felder
                details.update({
                    "status": data.get("status", "unknown"),
                    "service_initialized": data.get("service_initialized", False),
                    "ollama_model": data.get("ollama_model", "unknown"),
                    "ollama_status": data.get("ollama_status", "unknown"),
                    "timestamp": data.get("timestamp", "unknown")
                })

                # KORRIGIERT: Bewerte Ollama-Verbindung basierend auf ollama_status
                ollama_healthy = data.get("ollama_status") == "available"
                details["ollama_connection"] = ollama_healthy

                if detailed:
                    status = details.get("status", "unknown")
                    ollama_status = details.get("ollama_status", "unknown")
                    model = details.get("ollama_model", "unknown")

                    self._log(f"   Status: {status}", "INFO")
                    self._log(f"   Ollama: {ollama_status} (Model: {model})",
                              "INFO" if ollama_healthy else "WARNING")

                    if details.get("service_initialized"):
                        self._log(f"   Service vollständig initialisiert", "INFO")

            elif service_id == "ollama":
                # Ollama /api/tags gibt Modell-Liste zurück
                models = data.get("models", [])
                details.update({
                    "model_count": len(models),
                    "available_models": [m.get("name") for m in models[:5]],  # Top 5 Modelle
                    "total_size": sum(m.get("size", 0) for m in models)
                })

                if detailed and models:
                    self._log(f"   Verfügbare Modelle: {len(models)}", "INFO")
                    for model in models[:3]:  # Zeige erste 3
                        name = model.get("name", "unknown")
                        size_gb = round(model.get("size", 0) / (1024 ** 3), 1)
                        self._log(f"   - {name} ({size_gb}GB)", "INFO")

        except (ValueError, KeyError) as e:
            details["parse_error"] = str(e)

        return details
    
    def get_service_summary(self) -> Dict:
        """Gibt eine Zusammenfassung aller Service-Status zurück"""
        if not self.status_cache:
            self.check_all_services(detailed=False)
        
        healthy_services = [s for s in self.status_cache.values() if s.healthy]
        total_services = len(self.status_cache)
        
        return {
            "healthy_count": len(healthy_services),
            "total_count": total_services,
            "all_healthy": len(healthy_services) == total_services,
            "services": self.status_cache,
            "last_check": max(s.last_check for s in self.status_cache.values()) if self.status_cache else 0
        }
    
    def start_auto_monitoring(self, interval: int = 30):
        """Startet automatisches Monitoring im Hintergrund"""
        self.auto_check_interval = interval
        self.auto_check_enabled = True
        
        if self.auto_check_thread and self.auto_check_thread.is_alive():
            return
        
        self.auto_check_thread = threading.Thread(target=self._auto_check_loop, daemon=True)
        self.auto_check_thread.start()
        self._log(f"Automatisches Monitoring gestartet (Intervall: {interval}s)", "INFO")
    
    def stop_auto_monitoring(self):
        """Stoppt automatisches Monitoring"""
        self.auto_check_enabled = False
        self._log("Automatisches Monitoring gestoppt", "INFO")
    
    def _auto_check_loop(self):
        """Hintergrund-Thread für automatische Health Checks"""
        while self.auto_check_enabled:
            try:
                self.check_all_services(detailed=False)
                time.sleep(self.auto_check_interval)
            except Exception as e:
                self._log(f"Fehler im Auto-Monitoring: {e}", "ERROR")
                time.sleep(self.auto_check_interval)
    
    def get_docker_commands(self) -> Dict[str, List[str]]:
        """Gibt Docker-Befehle für Management der Services zurück"""
        return {
            "status": [
                "docker ps --filter name=whisperx-api",
                "docker ps --filter name=summarization-api", 
                "docker ps --filter name=ollama"
            ],
            "start": [
                "docker start whisperx-api",
                "docker start summarization-api",
                "docker start ollama"
            ],
            "restart": [
                "docker restart whisperx-api",
                "docker restart summarization-api",
                "docker restart ollama"
            ],
            "logs": [
                "docker logs whisperx-api --tail 50",
                "docker logs summarization-api --tail 50",
                "docker logs ollama --tail 50"
            ]
        }
