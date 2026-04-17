#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XONINAS - Lanzador Universal con autoreinicio
Sistema de Almacenamiento NAS local
"""
import subprocess
import sys
import os
import time
import platform
import signal

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def get_system():
    return platform.system().lower()

def is_arch():
    if get_system() != 'linux':
        return False
    try:
        with open('/etc/os-release') as f:
            content = f.read().lower()
            return 'arch' in content or 'manjaro' in content
    except:
        return False

def print_banner():
    banner = f"""
{Colors.PURPLE}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║                     XONINAS 2026 v1.0.0                    ║
║              NAS Local con Carpetas Protegidas              ║
║                                                            ║
║               Desarrollado por: Darian Alberto             ║
║                      Camacho Salas                         ║
║                      Organización: XONIDU                  ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}
    """
    print(banner)

def install_package(pkg_name, version=None):
    pkg_spec = f"{pkg_name}=={version}" if version else pkg_name
    cmd = [sys.executable, '-m', 'pip', 'install', pkg_spec]
    if is_arch():
        cmd.append('--break-system-packages')
    print(f"{Colors.YELLOW}  Instalando {pkg_spec}...{Colors.END}")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"{Colors.GREEN}    ✓ {pkg_name} instalado{Colors.END}")
        return True
    except:
        print(f"{Colors.RED}    ✗ Error instalando {pkg_name}{Colors.END}")
        return False

def install_dependencies():
    print(f"\n{Colors.BOLD}📦 Verificando dependencias...{Colors.END}")
    for pkg, ver in [('waitress', '2.1.2'), ('flask', '2.3.3'), ('werkzeug', '2.3.0')]:
        try:
            __import__(pkg)
            print(f"{Colors.GREEN}  ✓ {pkg} ya instalado{Colors.END}")
        except ImportError:
            install_package(pkg, ver)

def run_initial_config():
    if not os.path.exists('master.csv'):
        print(f"\n{Colors.YELLOW}⚠️  No se encontró clave maestra. Ejecutando configuración inicial...{Colors.END}")
        subprocess.run([sys.executable, 'xoninas.py'], check=True)
        print(f"\n{Colors.GREEN}✅ Clave maestra guardada.{Colors.END}")
        print(f"{Colors.YELLOW}▶️  Vuelve a ejecutar 'python3 start.py'{Colors.END}")
        sys.exit(0)

def is_server_alive(port=5000):
    try:
        import requests
        r = requests.get(f"http://localhost:{port}/health", timeout=5)
        return r.status_code == 200
    except:
        return False

def cleanup_port(port=5000):
    if get_system() == 'windows':
        return
    try:
        result = subprocess.run(f"lsof -ti:{port}", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            for pid in result.stdout.strip().split('\n'):
                os.kill(int(pid), signal.SIGTERM)
            time.sleep(2)
    except:
        pass

def run_server():
    print(f"\n{Colors.BOLD}🚀 Iniciando servidor XONINAS (Waitress)...{Colors.END}")
    cleanup_port(5000)
    cmd = [sys.executable, '-m', 'waitress', '--host=0.0.0.0', '--port=5000', '--threads=6', 'xoninas:app']
    process = None
    while True:
        if process is None or process.poll() is not None:
            process = subprocess.Popen(cmd)
            time.sleep(5)
        if not is_server_alive():
            process.terminate()
            process.wait()
            process = None
            time.sleep(5)
        else:
            time.sleep(10)

def main():
    os.system('clear' if get_system() != 'windows' else 'cls')
    print_banner()
    if not os.path.exists('xoninas.py'):
        print(f"{Colors.RED}❌ Error: No se encuentra xoninas.py{Colors.END}")
        sys.exit(1)
    install_dependencies()
    run_initial_config()
    try:
        run_server()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Servidor detenido{Colors.END}")
        sys.exit(0)

if __name__ == '__main__':
    main()
