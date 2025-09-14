#!/usr/bin/env python3
"""
MuseTalk Progress Monitor - Real-time monitoring for PresGen-Training pipeline
Run this in a separate terminal to monitor progress when the pipeline is stuck
"""

import os
import time
import psutil
import sys
from pathlib import Path
import argparse

def monitor_musetalk_progress():
    """Monitor MuseTalk and PresGen-Training progress"""
    
    print("🔍 MuseTalk Progress Monitor - M1 Pro Optimized")
    print("=" * 60)
    
    # Check for running MuseTalk processes
    musetalk_processes = []
    presgen_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                
                if 'musetalk' in cmdline.lower() or 'inference.py' in cmdline:
                    musetalk_processes.append(proc)
                elif 'presgen_training' in cmdline:
                    presgen_processes.append(proc)
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    print(f"🎯 Found {len(musetalk_processes)} MuseTalk processes")
    print(f"🎯 Found {len(presgen_processes)} PresGen-Training processes")
    
    if not musetalk_processes and not presgen_processes:
        print("❌ No active MuseTalk or PresGen-Training processes found")
        return
    
    # Monitor loop
    start_time = time.time()
    
    while True:
        try:
            elapsed = time.time() - start_time
            
            print(f"\n⏰ Monitor Time: {elapsed/60:.1f} minutes")
            
            # Check system resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            print(f"💻 System Status:")
            print(f"   CPU Usage: {cpu_percent:.1f}%")
            print(f"   Memory Usage: {memory.percent:.1f}% ({memory.used/1024**3:.1f}GB/{memory.total/1024**3:.1f}GB)")
            
            # Check process status
            active_musetalk = 0
            active_presgen = 0
            
            for proc in musetalk_processes:
                try:
                    if proc.is_running():
                        active_musetalk += 1
                        proc_cpu = proc.cpu_percent()
                        proc_memory = proc.memory_info().rss / 1024**2  # MB
                        print(f"   🧠 MuseTalk PID {proc.pid}: CPU {proc_cpu:.1f}%, RAM {proc_memory:.0f}MB")
                except:
                    pass
            
            for proc in presgen_processes:
                try:
                    if proc.is_running():
                        active_presgen += 1
                        proc_cpu = proc.cpu_percent()
                        proc_memory = proc.memory_info().rss / 1024**2  # MB
                        print(f"   🎬 PresGen PID {proc.pid}: CPU {proc_cpu:.1f}%, RAM {proc_memory:.0f}MB")
                except:
                    pass
            
            # Check for temp files (indicates progress)
            temp_dirs = ["/tmp", "/var/folders"]
            musetalk_temp_files = 0
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for item in Path(temp_dir).rglob("musetalk_*"):
                        if item.is_dir():
                            musetalk_temp_files += len(list(item.iterdir()))
            
            if musetalk_temp_files > 0:
                print(f"📁 Found {musetalk_temp_files} MuseTalk temp files (processing active)")
            
            # Check output directory for progress
            output_dir = Path("presgen-training/outputs")
            if output_dir.exists():
                recent_files = sorted(output_dir.glob("*"), key=os.path.getmtime, reverse=True)[:3]
                if recent_files:
                    print(f"📺 Recent outputs:")
                    for file in recent_files:
                        mtime = os.path.getmtime(file)
                        age = time.time() - mtime
                        print(f"   {file.name} ({age/60:.1f} min ago)")
            
            # Status assessment
            if active_musetalk == 0 and active_presgen == 0:
                print("⚠️  No active processes - pipeline may have completed or failed")
                break
            elif cpu_percent < 10 and active_musetalk > 0:
                print("🐌 Low CPU usage - process may be stuck or waiting")
            elif cpu_percent > 80:
                print("🔥 High CPU usage - processing actively")
            else:
                print("✅ Normal processing")
            
            print("-" * 60)
            time.sleep(30)  # Update every 30 seconds
            
        except KeyboardInterrupt:
            print("\n👋 Monitor stopped by user")
            break
        except Exception as e:
            print(f"❌ Monitor error: {e}")
            time.sleep(10)

def check_pipeline_health():
    """Quick health check of the pipeline"""
    
    print("🩺 Pipeline Health Check")
    print("=" * 40)
    
    # Check MuseTalk installation
    musetalk_dir = Path("MuseTalk")
    if musetalk_dir.exists():
        print("✅ MuseTalk directory found")
        
        if (musetalk_dir / "scripts" / "inference.py").exists():
            print("✅ MuseTalk inference script found")
        else:
            print("❌ MuseTalk inference script missing")
            
        if (musetalk_dir / "models").exists():
            model_count = len(list((musetalk_dir / "models").iterdir()))
            print(f"📦 Found {model_count} model files")
        else:
            print("❌ MuseTalk models directory missing")
    else:
        print("❌ MuseTalk directory not found")
    
    # Check Python environment
    try:
        import torch
        print(f"✅ PyTorch available: {torch.__version__}")
        
        if torch.backends.mps.is_available():
            print("✅ MPS (Metal Performance Shaders) available")
        else:
            print("⚠️  MPS not available - using CPU")
            
    except ImportError:
        print("❌ PyTorch not installed")
    
    # Check system resources
    memory = psutil.virtual_memory()
    if memory.available > 8 * 1024**3:  # 8GB
        print(f"✅ Sufficient RAM: {memory.available/1024**3:.1f}GB available")
    else:
        print(f"⚠️  Low RAM: {memory.available/1024**3:.1f}GB available")
    
    cpu_count = psutil.cpu_count()
    print(f"✅ CPU cores: {cpu_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor MuseTalk progress")
    parser.add_argument("--check", action="store_true", help="Run health check only")
    parser.add_argument("--watch", action="store_true", help="Continuously monitor progress")
    
    args = parser.parse_args()
    
    if args.check:
        check_pipeline_health()
    elif args.watch:
        monitor_musetalk_progress()
    else:
        # Default behavior
        check_pipeline_health()
        print("\n" + "="*60)
        monitor_musetalk_progress()