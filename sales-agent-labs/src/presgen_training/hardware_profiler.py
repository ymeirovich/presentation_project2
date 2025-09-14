"""
Hardware Profiler and Resource Monitor

Validates system capabilities and monitors resources during processing.
Provides automatic quality adjustment and circuit breaker functionality.
"""

import logging
import psutil
import platform
import subprocess
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
import os

from src.common.jsonlog import jlog


@dataclass
class HardwareProfile:
    """System hardware profile"""
    cpu_count: int
    cpu_freq_mhz: float
    total_ram_gb: float
    available_ram_gb: float
    gpu_available: bool
    gpu_memory_gb: float
    disk_space_gb: float
    platform: str
    architecture: str
    python_version: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_count": self.cpu_count,
            "cpu_freq_mhz": self.cpu_freq_mhz, 
            "total_ram_gb": self.total_ram_gb,
            "available_ram_gb": self.available_ram_gb,
            "gpu_available": self.gpu_available,
            "gpu_memory_gb": self.gpu_memory_gb,
            "disk_space_gb": self.disk_space_gb,
            "platform": self.platform,
            "architecture": self.architecture,
            "python_version": self.python_version
        }


class HardwareProfiler:
    """
    Hardware profiling and requirement validation.
    
    Detects system capabilities and recommends optimal processing settings.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training.hardware_profiler")
        
        # Minimum requirements for each quality level
        self.requirements = {
            "fast": {
                "min_ram_gb": 4,
                "min_cpu_cores": 2,
                "min_disk_gb": 2
            },
            "standard": {
                "min_ram_gb": 8, 
                "min_cpu_cores": 4,
                "min_disk_gb": 5
            },
            "high": {
                "min_ram_gb": 16,
                "min_cpu_cores": 8,
                "min_disk_gb": 10
            }
        }

    def detect_hardware(self) -> HardwareProfile:
        """Detect and profile system hardware capabilities"""
        jlog(self.logger, logging.INFO,
             event="hardware_detection_start")
        
        start_time = time.time()
        
        # CPU Information
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_freq_mhz = cpu_freq.current if cpu_freq else 0
        
        # Memory Information  
        memory = psutil.virtual_memory()
        total_ram_gb = memory.total / (1024**3)
        available_ram_gb = memory.available / (1024**3)
        
        # GPU Detection (Metal Performance Shaders on macOS)
        gpu_available, gpu_memory_gb = self._detect_gpu()
        
        # Disk Space
        disk_usage = psutil.disk_usage('/')
        disk_space_gb = disk_usage.free / (1024**3)
        
        # Platform Information
        platform_info = platform.platform()
        architecture = platform.machine()
        python_version = platform.python_version()
        
        profile = HardwareProfile(
            cpu_count=cpu_count,
            cpu_freq_mhz=cpu_freq_mhz,
            total_ram_gb=total_ram_gb,
            available_ram_gb=available_ram_gb,
            gpu_available=gpu_available,
            gpu_memory_gb=gpu_memory_gb,
            disk_space_gb=disk_space_gb,
            platform=platform_info,
            architecture=architecture,
            python_version=python_version
        )
        
        detection_time = time.time() - start_time
        
        jlog(self.logger, logging.INFO,
             event="hardware_detection_complete",
             detection_time_ms=int(detection_time * 1000),
             profile=profile.to_dict())
        
        return profile

    def _detect_gpu(self) -> tuple[bool, float]:
        """Detect GPU availability and memory"""
        gpu_available = False
        gpu_memory_gb = 0.0
        
        try:
            # Check for macOS Metal Performance Shaders
            if platform.system() == "Darwin":
                try:
                    # Try to detect Metal GPU
                    result = subprocess.run(
                        ["system_profiler", "SPDisplaysDataType", "-json"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        # Parse for GPU memory (simplified)
                        output = result.stdout
                        if "Metal" in output or "GPU" in output:
                            gpu_available = True
                            # Estimate GPU memory for Mac (typical values)
                            gpu_memory_gb = 8.0 if "M1" in output or "M2" in output else 4.0
                            
                except subprocess.TimeoutExpired:
                    pass
                    
            # Check for NVIDIA GPU
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if result.returncode == 0:
                    gpu_memory_mb = int(result.stdout.strip())
                    gpu_memory_gb = gpu_memory_mb / 1024
                    gpu_available = True
                    
            except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
                pass
                
        except Exception as e:
            jlog(self.logger, logging.WARNING,
                 event="gpu_detection_failed",
                 error=str(e))
        
        jlog(self.logger, logging.INFO,
             event="gpu_detection_result",
             gpu_available=gpu_available,
             gpu_memory_gb=gpu_memory_gb)
        
        return gpu_available, gpu_memory_gb

    def validate_requirements(self, profile: HardwareProfile) -> bool:
        """Validate hardware meets minimum requirements"""
        jlog(self.logger, logging.INFO,
             event="hardware_validation_start",
             profile=profile.to_dict())
        
        # Check against minimum requirements for 'fast' quality
        min_reqs = self.requirements["fast"]
        
        issues = []
        
        if profile.available_ram_gb < min_reqs["min_ram_gb"]:
            issues.append(f"Insufficient RAM: {profile.available_ram_gb:.1f}GB < {min_reqs['min_ram_gb']}GB")
            
        if profile.cpu_count < min_reqs["min_cpu_cores"]:
            issues.append(f"Insufficient CPU cores: {profile.cpu_count} < {min_reqs['min_cpu_cores']}")
            
        if profile.disk_space_gb < min_reqs["min_disk_gb"]:
            issues.append(f"Insufficient disk space: {profile.disk_space_gb:.1f}GB < {min_reqs['min_disk_gb']}GB")
        
        if issues:
            jlog(self.logger, logging.ERROR,
                 event="hardware_validation_failed",
                 issues=issues)
            return False
            
        jlog(self.logger, logging.INFO,
             event="hardware_validation_passed")
        return True

    def recommend_quality(self, profile: HardwareProfile) -> str:
        """Recommend optimal quality setting based on hardware"""
        
        # Score hardware capabilities
        ram_score = min(profile.available_ram_gb / 8, 2.0)  # 8GB = 1.0, 16GB+ = 2.0
        cpu_score = min(profile.cpu_count / 4, 2.0)         # 4 cores = 1.0, 8+ = 2.0
        gpu_score = 1.5 if profile.gpu_available else 1.0   # GPU bonus
        
        total_score = ram_score + cpu_score + gpu_score
        
        # Determine quality based on total score
        if total_score >= 4.0:
            quality = "high"
        elif total_score >= 3.0:
            quality = "standard"  
        else:
            quality = "fast"
            
        jlog(self.logger, logging.INFO,
             event="quality_recommendation",
             ram_score=ram_score,
             cpu_score=cpu_score,
             gpu_score=gpu_score,
             total_score=total_score,
             recommended_quality=quality)
        
        return quality


class ResourceMonitor:
    """
    Real-time resource monitoring during processing.
    
    Provides circuit breaker functionality to prevent system overload.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training.resource_monitor")
        
        self.monitoring = False
        self.monitor_thread = None
        self.stats = {
            "cpu_percent": [],
            "memory_percent": [],
            "disk_io": [],
            "warnings": []
        }
        
        # Thresholds for circuit breaker
        self.thresholds = {
            "cpu_warning": 80,     # CPU usage warning
            "cpu_critical": 95,    # CPU usage critical
            "memory_warning": 85,   # Memory usage warning  
            "memory_critical": 95   # Memory usage critical
        }
    
    def start_monitoring(self) -> None:
        """Start background resource monitoring"""
        if self.monitoring:
            return
            
        jlog(self.logger, logging.INFO,
             event="resource_monitoring_start")
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ResourceMonitor"
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return final stats"""
        if not self.monitoring:
            return self.stats
            
        self.monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        # Calculate summary statistics
        summary = self._calculate_summary()
        
        jlog(self.logger, logging.INFO,
             event="resource_monitoring_stop",
             summary=summary)
        
        return summary
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop"""
        while self.monitoring:
            try:
                # Collect current stats
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                
                # Store stats
                self.stats["cpu_percent"].append(cpu_percent)
                self.stats["memory_percent"].append(memory.percent)
                
                if disk_io:
                    self.stats["disk_io"].append({
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes
                    })
                
                # Check thresholds and log warnings
                self._check_thresholds(cpu_percent, memory.percent)
                
                # Log periodic stats (every 30 seconds)
                if len(self.stats["cpu_percent"]) % 30 == 0:
                    jlog(self.logger, logging.INFO,
                         event="resource_monitoring_periodic",
                         cpu_percent=cpu_percent,
                         memory_percent=memory.percent,
                         available_memory_gb=memory.available / (1024**3))
                
                time.sleep(1)
                
            except Exception as e:
                jlog(self.logger, logging.ERROR,
                     event="resource_monitoring_error", 
                     error=str(e))
                time.sleep(5)  # Longer sleep on error
    
    def _check_thresholds(self, cpu_percent: float, memory_percent: float) -> None:
        """Check resource thresholds and log warnings"""
        
        # CPU threshold checks
        if cpu_percent > self.thresholds["cpu_critical"]:
            warning = f"CRITICAL: CPU usage {cpu_percent:.1f}% > {self.thresholds['cpu_critical']}%"
            self.stats["warnings"].append(warning)
            jlog(self.logger, logging.ERROR,
                 event="resource_threshold_critical",
                 resource="cpu",
                 current=cpu_percent,
                 threshold=self.thresholds["cpu_critical"])
                 
        elif cpu_percent > self.thresholds["cpu_warning"]:
            warning = f"WARNING: CPU usage {cpu_percent:.1f}% > {self.thresholds['cpu_warning']}%"
            jlog(self.logger, logging.WARNING,
                 event="resource_threshold_warning",
                 resource="cpu", 
                 current=cpu_percent,
                 threshold=self.thresholds["cpu_warning"])
        
        # Memory threshold checks
        if memory_percent > self.thresholds["memory_critical"]:
            warning = f"CRITICAL: Memory usage {memory_percent:.1f}% > {self.thresholds['memory_critical']}%"
            self.stats["warnings"].append(warning)
            jlog(self.logger, logging.ERROR,
                 event="resource_threshold_critical",
                 resource="memory",
                 current=memory_percent,
                 threshold=self.thresholds["memory_critical"])
                 
        elif memory_percent > self.thresholds["memory_warning"]:
            warning = f"WARNING: Memory usage {memory_percent:.1f}% > {self.thresholds['memory_warning']}%"
            jlog(self.logger, logging.WARNING,
                 event="resource_threshold_warning",
                 resource="memory",
                 current=memory_percent,
                 threshold=self.thresholds["memory_warning"])
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics from monitoring data"""
        if not self.stats["cpu_percent"]:
            return {"error": "No monitoring data collected"}
        
        cpu_stats = self.stats["cpu_percent"]
        memory_stats = self.stats["memory_percent"]
        
        return {
            "monitoring_duration_seconds": len(cpu_stats),
            "cpu_usage": {
                "avg": sum(cpu_stats) / len(cpu_stats),
                "max": max(cpu_stats),
                "min": min(cpu_stats)
            },
            "memory_usage": {
                "avg": sum(memory_stats) / len(memory_stats),
                "max": max(memory_stats),
                "min": min(memory_stats)
            },
            "warnings_count": len(self.stats["warnings"]),
            "warnings": self.stats["warnings"][-10:]  # Last 10 warnings
        }
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current resource utilization"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk_usage = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "available_memory_gb": memory.available / (1024**3),
                "disk_free_gb": disk_usage.free / (1024**3),
                "timestamp": time.time()
            }
        except Exception as e:
            return {"error": str(e)}