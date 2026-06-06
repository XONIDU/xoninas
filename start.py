#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS 2026 - NAS Local con Carpetas Protegidas
Lanzador Universal con múltiples estrategias de instalación
Desarrollado por: Darian Alberto Camacho Salas
#Somos XONIDU
"""

import subprocess
import sys
import os
import platform
import shutil
import importlib.util
import time
import signal
import webbrowser
from pathlib import Path

# ============================================================================
# Colores
# ============================================================================
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'
    
    @staticmethod
    def supports_color():
        if platform.system() == 'Windows':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                return kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except:
                return False
        return True

if not Colors.supports_color():
    for attr in dir(Colors):
        if not attr.startswith('_') and attr != 'supports_color':
            setattr(Colors, attr, '')

# ============================================================================
# Detección del sistema
# ============================================================================
def get_system():
    return platform.system().lower()

def get_linux_distro():
    if get_system() != 'linux':
        return None
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                if 'ubuntu' in content or 'debian' in content or 'mint' in content:
                    return 'debian-based'
                elif 'arch' in content or 'manjaro' in content:
                    return 'arch-based'
                elif 'fedora' in content:
                    return 'fedora'
        if shutil.which('apt'):
            return 'debian-based'
        elif shutil.which('pacman'):
            return 'arch-based'
        return 'linux-generic'
    except:
        return 'linux-generic'

def get_python_command():
    if get_system() == 'windows':
        return ['python']
    else:
        try:
            subprocess.run(['python3', '--version'], capture_output=True, check=True)
            return ['python3']
        except:
            return ['python']

def get_pip_command():
    return [sys.executable, '-m', 'pip']

def get_install_flags():
    flags = []
    sistema = get_system()
    distro = get_linux_distro()
    if sistema == 'linux':
        if distro in ['arch-based', 'fedora']:
            flags.append('--break-system-packages')
        else:
            flags.append('--user')
    elif sistema == 'darwin':
        flags.append('--user')
    return flags

def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))

def get_xoninas_path():
    script_dir = get_script_dir()
    rutas = [
        os.path.join(script_dir, 'xoninas.py'),
        os.path.join(script_dir, '..', 'xoninas', 'xoninas.py'),
        '/usr/share/xoninas/xoninas.py',
        os.path.join(os.path.expanduser("~"), 'xoninas', 'xoninas.py'),
        os.path.join(os.getcwd(), 'xoninas.py')
    ]
    for r in rutas:
        if os.path.exists(r):
            return r
    return None

def print_banner():
    sistema = get_system()
    distro = get_linux_distro()
    sistema_texto = {
        'windows': 'WINDOWS',
        'linux': f'LINUX ({distro.upper()})' if distro else 'LINUX',
        'darwin': 'MACOS'
    }.get(sistema, 'DESCONOCIDO')
    
    banner = f"""
{Colors.PURPLE}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║                    XONINAS 2026 v4.2.0                    ║
║              NAS Local con Carpetas Protegidas              ║
║                                                            ║
║               Sistema detectado: {sistema_texto:<27} ║
║                                                            ║
║               Desarrollado por: Darian Alberto             ║
║                      Camacho Salas                         ║
║                      #Somos XONIDU                         ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}
    """
    print(banner)

# ============================================================================
# Dependencias
# ============================================================================
def check_python():
    try:
        cmd = get_python_command() + ['--version']
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except:
        return False

def check_pip():
    try:
        subprocess.run(get_pip_command() + ['--version'], capture_output=True, check=True)
        return True
    except:
        return False

def install_pip_linux():
    distro = get_linux_distro()
    print(f"{Colors.YELLOW}Instalando pip en Linux ({distro})...{Colors.END}")
    if distro == 'debian-based':
        try:
            subprocess.run(['sudo', 'apt', 'update'], check=False)
            subprocess.run(['sudo', 'apt', 'install', '-y', 'python3-pip'], check=True)
            return True
        except:
            return False
    elif distro == 'arch-based':
        try:
            subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'python-pip'], check=True)
            return True
        except:
            return False
    return False

def install_pip_windows():
    print(f"{Colors.YELLOW}Instalando pip en Windows...{Colors.END}")
    try:
        subprocess.run([sys.executable, '-m', 'ensurepip', '--upgrade'], check=True)
        return True
    except:
        return False

def check_python_module(module_name):
    return importlib.util.find_spec(module_name) is not None

def check_dependencies():
    print(f"\n{Colors.BOLD}📦 Verificando dependencias...{Colors.END}")
    dependencies = ['flask', 'werkzeug', 'waitress', 'requests', 'qrcode']
    missing = []
    for dep in dependencies:
        if check_python_module(dep):
            print(f"{Colors.GREEN}  ✓ {dep} OK{Colors.END}")
        else:
            print(f"{Colors.YELLOW}  ✗ {dep} (faltante){Colors.END}")
            missing.append(dep)
    return missing

def install_dependencies(missing):
    if not missing:
        return True
    print(f"\n{Colors.BOLD}Instalando dependencias...{Colors.END}")
    flags = get_install_flags()
    success = True
    for dep in missing:
        print(f"  Instalando {dep}...")
        try:
            cmd = get_pip_command() + ['install', dep] + flags
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"{Colors.GREEN}    ✓ {dep}{Colors.END}")
        except:
            try:
                cmd = get_pip_command() + ['install', dep]
                subprocess.run(cmd, check=True)
                print(f"{Colors.GREEN}    ✓ {dep}{Colors.END}")
            except:
                print(f"{Colors.RED}    ✗ {dep}{Colors.END}")
                success = False
    return success

def check_cloudflared():
    return shutil.which('cloudflared') is not None

def install_cloudflared():
    sistema = get_system()
    print(f"\n{Colors.BOLD}🌐 Instalando Cloudflare Tunnel...{Colors.END}")
    if sistema == 'linux':
        try:
            subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'cloudflared'], check=True)
            print(f"{Colors.GREEN}  cloudflared instalado{Colors.END}")
            return True
        except:
            pass
    print(f"{Colors.YELLOW}  No se pudo instalar cloudflared{Colors.END}")
    return False

# ============================================================================
# Configuración inicial
# ============================================================================
def run_initial_setup(xoninas_dir):
    if not xoninas_dir:
        return False
    
    os.chdir(xoninas_dir)
    
    if os.path.exists('config.csv') and os.path.exists('master.csv'):
        return True
    
    print("\n" + "="*60)
    print("   CONFIGURACIÓN INICIAL DE XONINAS")
    print("="*60)
    
    if not os.path.exists('config.csv'):
        default = str(os.path.abspath('storage'))
        print(f"\nRuta de almacenamiento por defecto: {default}")
        ruta = input("Nueva ruta (deja vacío para usar la de defecto): ").strip()
        if not ruta:
            ruta = default
        else:
            ruta = str(os.path.abspath(os.path.expanduser(ruta)))
        os.makedirs(ruta, exist_ok=True)
        with open('config.csv', 'w') as f:
            f.write(f"storage_path,{ruta}\n")
        print(f"{Colors.GREEN}✅ Ruta guardada: {ruta}{Colors.END}")
    
    if not os.path.exists('master.csv'):
        print("\n" + "="*50)
        print("    CONFIGURACIÓN DE CLAVE MAESTRA")
        print("="*50)
        pwd = input("Clave maestra (deja vacío para 'admin'): ").strip()
        if not pwd:
            pwd = "admin"
            print("Usando 'admin' como clave maestra")
        import hashlib
        hashed = hashlib.sha256(pwd.encode()).hexdigest()
        with open('master.csv', 'w') as f:
            f.write(hashed)
        print(f"{Colors.GREEN}✅ Clave maestra guardada.{Colors.END}")
    
    print(f"\n{Colors.GREEN}✅ Configuración completada.{Colors.END}")
    print(f"{Colors.YELLOW}▶️  Vuelve a ejecutar 'python3 start.py' para iniciar el servidor.{Colors.END}")
    return False

# ============================================================================
# Servidor
# ============================================================================
def is_server_alive(port=5000):
    try:
        import requests
        r = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
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
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except:
                    pass
            time.sleep(2)
    except:
        pass

def run_cloudflare_tunnel(port=5000):
    cloudflared_cmd = shutil.which('cloudflared')
    if not cloudflared_cmd:
        return None
    print(f"{Colors.CYAN}Iniciando túnel Cloudflare...{Colors.END}")
    cmd = [cloudflared_cmd, 'tunnel', '--url', f'http://localhost:{port}']
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        url = None
        for line in process.stdout:
            if 'https://' in line and '.trycloudflare.com' in line:
                import re
                match = re.search(r'(https://[a-zA-Z0-9\-]+\.trycloudflare\.com)', line)
                if match:
                    url = match.group(1)
                    print(f"\n{Colors.GREEN}🌍 Túnel Cloudflare: {url}{Colors.END}")
                    break
        return process
    except:
        return None

def run_server(xoninas_dir, cloudflare_enabled=False):
    print(f"\n{Colors.BOLD}🚀 Iniciando servidor XONINAS (Waitress)...{Colors.END}")
    print(f"  Directorio: {xoninas_dir}")
    print(f"  Threads: 6")
    print(f"  Puerto: 5000")
    print(f"  Autoreinicio: activado")
    print(f"{Colors.YELLOW}  Para detener: Ctrl+C{Colors.END}")
    print("-" * 60)
    
    cleanup_port(5000)
    
    # Iniciar túnel si se solicita
    cloudflare_process = None
    if cloudflare_enabled:
        cloudflare_process = run_cloudflare_tunnel(5000)
    
    # Ejecutar xoninas.py directamente (que mostrará el QR y abrirá el navegador)
    cmd = get_python_command() + [os.path.join(xoninas_dir, 'xoninas.py')]
    try:
        subprocess.run(cmd, cwd=xoninas_dir)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Servidor detenido{Colors.END}")
    finally:
        if cloudflare_process:
            cloudflare_process.terminate()

# ============================================================================
# Main
# ============================================================================
def main():
    if get_system() == 'windows':
        os.system('cls')
    else:
        os.system('clear')
    
    print_banner()
    
    sistema = get_system()
    distro = get_linux_distro()
    script_dir = get_script_dir()
    xoninas_path = get_xoninas_path()
    xoninas_dir = os.path.dirname(xoninas_path) if xoninas_path else script_dir
    
    print(f"{Colors.BOLD}Sistema operativo:{Colors.END} {sistema}")
    if distro:
        print(f"{Colors.BOLD}Distribución:{Colors.END} {distro}")
    print(f"{Colors.BOLD}Directorio de start.py:{Colors.END} {script_dir}")
    print(f"{Colors.BOLD}Ruta de xoninas.py:{Colors.END} {xoninas_path or 'NO ENCONTRADO'}")
    
    if not check_python():
        print(f"\n{Colors.RED}❌ Python no está instalado{Colors.END}")
        sys.exit(1)
    
    ver_py = subprocess.run(get_python_command() + ['--version'], capture_output=True, text=True).stdout.strip()
    print(f"{Colors.BOLD}Python:{Colors.END} {ver_py}")
    
    if not check_pip():
        print(f"\n{Colors.YELLOW}⚠️ Pip no encontrado. Instalando...{Colors.END}")
        if sistema == 'linux':
            if not install_pip_linux():
                print(f"{Colors.RED}No se pudo instalar pip{Colors.END}")
                sys.exit(1)
        elif sistema == 'windows':
            if not install_pip_windows():
                print(f"{Colors.RED}No se pudo instalar pip{Colors.END}")
                sys.exit(1)
    else:
        print(f"{Colors.GREEN}✓ Pip disponible{Colors.END}")
    
    missing = check_dependencies()
    if missing:
        print(f"\n{Colors.YELLOW}Faltan {len(missing)} dependencias.{Colors.END}")
        resp = input("¿Instalar automáticamente? (s/n): ")
        if resp.lower() == 's':
            install_dependencies(missing)
    
    if not xoninas_path:
        print(f"\n{Colors.RED}❌ No se encuentra xoninas.py{Colors.END}")
        sys.exit(1)
    
    if not run_initial_setup(xoninas_dir):
        sys.exit(0)
    
    cloudflare_enabled = False
    resp = input(f"\n{Colors.BOLD}🌐 ¿Activar túnel Cloudflare? (s/n): {Colors.END}")
    if resp.lower() == 's':
        cloudflare_enabled = True
        if not check_cloudflared():
            install_cloudflared()
    
    try:
        run_server(xoninas_dir, cloudflare_enabled)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Servidor detenido{Colors.END}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Saliendo...{Colors.END}")
