#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS 2026 - NAS Local con Carpetas Protegidas
Lanzador Universal con múltiples estrategias de instalación
Incluye autoreinicio, Cloudflare Tunnel y healthcheck

Desarrollado por: Darian Alberto Camacho Salas
Organización: XONIDU
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
import threading
import webbrowser
from pathlib import Path

# ============================================================================
# Colores para terminal
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
    """Detecta la distribución de Linux específica"""
    if get_system() != 'linux':
        return None
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                if 'ubuntu' in content or 'debian' in content or 'mint' in content or 'antix' in content:
                    return 'debian-based'
                elif 'arch' in content or 'manjaro' in content or 'endeavouros' in content:
                    return 'arch-based'
                elif 'fedora' in content or 'rhel' in content:
                    return 'fedora-based'
                elif 'opensuse' in content:
                    return 'opensuse-based'
                elif 'alpine' in content:
                    return 'alpine-based'
        if shutil.which('apt'):
            return 'debian-based'
        elif shutil.which('pacman'):
            return 'arch-based'
        elif shutil.which('dnf'):
            return 'fedora-based'
        elif shutil.which('yum'):
            return 'rhel-based'
        elif shutil.which('zypper'):
            return 'opensuse-based'
        elif shutil.which('apk'):
            return 'alpine-based'
        return 'linux-generic'
    except:
        return 'linux-generic'

def get_python_command():
    if get_system() == 'windows':
        return ['python']
    else:
        for cmd in ['python3', 'python']:
            try:
                subprocess.run([cmd, '--version'], capture_output=True, check=True)
                return [cmd]
            except:
                continue
        return ['python3']

def get_pip_command():
    """Devuelve el mejor comando pip disponible"""
    python_cmd = get_python_command()
    return [sys.executable, '-m', 'pip']

def get_install_flags():
    flags = []
    sistema = get_system()
    distro = get_linux_distro()
    if sistema == 'linux':
        if distro in ['arch-based', 'fedora-based']:
            flags.append('--break-system-packages')
        else:
            flags.append('--user')
    elif sistema == 'darwin':
        flags.append('--user')
    return flags

def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))

def get_xoninas_path():
    """Detecta la ruta de xoninas.py en múltiples ubicaciones"""
    script_dir = get_script_dir()
    rutas = [
        os.path.join(script_dir, 'xoninas.py'),
        os.path.join(script_dir, '..', 'xoninas', 'xoninas.py'),
        '/usr/share/xoninas/xoninas.py',
        '/usr/local/share/xoninas/xoninas.py',
        os.path.join(os.path.expanduser("~"), 'xoninas', 'xoninas.py'),
        os.path.join(os.getcwd(), 'xoninas.py')
    ]
    for r in rutas:
        if os.path.exists(r):
            return r
    return None

def get_xoninas_dir():
    ruta = get_xoninas_path()
    return os.path.dirname(ruta) if ruta else None

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

def mostrar_ayuda():
    ayuda = f"""
{Colors.BOLD}XONINAS - NAS LOCAL CON CARPETAS PROTEGIDAS{Colors.END}

{Colors.BOLD}USO:{Colors.END}
  python start.py [options]

{Colors.BOLD}OPCIONES:{Colors.END}
  --host HOST     Host al que vincularse (por defecto: 0.0.0.0)
  --port PORT     Puerto (por defecto: 5000)
  --no-cloud      Desactivar Cloudflare Tunnel
  --no-auto       Desactivar autoreinicio

{Colors.BOLD}EJEMPLOS:{Colors.END}
  python start.py
  python start.py --host 192.168.1.100 --port 8080
  python start.py --no-cloud

{Colors.BOLD}COMANDOS DENTRO DEL PROGRAMA:{Colors.END}
  Ctrl+C          Detener el servidor

{Colors.BOLD}CLAVE POR DEFECTO:{Colors.END}
  admin (se puede cambiar en la primera ejecución)
"""
    print(ayuda)

# ============================================================================
# Verificación e instalación de pip
# ============================================================================
def check_python():
    try:
        cmd = get_python_command() + ['--version']
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except:
        return False

def check_pip():
    """Verifica si pip está instalado usando múltiples métodos"""
    # Método 1: python -m pip
    try:
        subprocess.run(get_pip_command() + ['--version'], capture_output=True, check=True)
        return True
    except:
        pass
    
    # Método 2: pip3 directamente
    if get_system() != 'windows':
        try:
            subprocess.run(['pip3', '--version'], capture_output=True, check=True)
            return True
        except:
            pass
    
    # Método 3: pip directamente
    try:
        subprocess.run(['pip', '--version'], capture_output=True, check=True)
        return True
    except:
        pass
    
    return False

def install_pip_linux():
    """Instala pip en Linux usando el gestor de paquetes de la distribución"""
    distro = get_linux_distro()
    print(f"{Colors.YELLOW}Instalando pip en Linux ({distro})...{Colors.END}")
    
    estrategias = []
    if distro == 'debian-based':
        estrategias = [
            ['sudo', 'apt', 'update'],
            ['sudo', 'apt', 'install', '-y', 'python3-pip'],
            ['sudo', 'apt', 'install', '-y', 'python3-pip', '--fix-missing'],
        ]
    elif distro == 'arch-based':
        estrategias = [
            ['sudo', 'pacman', '-S', '--noconfirm', 'python-pip'],
            ['sudo', 'pacman', '-S', '--noconfirm', 'python-pip', '--overwrite', '*'],
        ]
    elif distro == 'fedora-based':
        estrategias = [
            ['sudo', 'dnf', 'install', '-y', 'python3-pip'],
            ['sudo', 'dnf', 'install', '-y', 'python3-pip', '--allowerasing'],
        ]
    elif distro == 'rhel-based':
        estrategias = [
            ['sudo', 'yum', 'install', '-y', 'python3-pip'],
            ['sudo', 'yum', 'install', '-y', 'python3-pip', '--skip-broken'],
        ]
    elif distro == 'opensuse-based':
        estrategias = [
            ['sudo', 'zypper', 'install', '-y', 'python3-pip'],
            ['sudo', 'zypper', 'install', '-y', 'python3-pip', '--auto-agree-with-licenses'],
        ]
    elif distro == 'alpine-based':
        estrategias = [
            ['sudo', 'apk', 'add', 'py3-pip'],
            ['sudo', 'apk', 'add', 'python3', 'py3-pip'],
        ]
    else:
        # Intento genérico con python -m ensurepip
        try:
            subprocess.run([sys.executable, '-m', 'ensurepip', '--upgrade'], check=True)
            print(f"{Colors.GREEN}Pip instalado con ensurepip{Colors.END}")
            return True
        except:
            pass
        print(f"{Colors.RED}No se pudo instalar pip automáticamente.{Colors.END}")
        print("Instala pip manualmente según tu distribución:")
        print("  Debian/Ubuntu: sudo apt install python3-pip")
        print("  Arch/Manjaro: sudo pacman -S python-pip")
        print("  Fedora: sudo dnf install python3-pip")
        return False
    
    for estrategia in estrategias:
        try:
            subprocess.run(estrategia, check=True, timeout=120)
            if 'install' in estrategia:
                print(f"{Colors.GREEN}Pip instalado correctamente{Colors.END}")
                return True
        except:
            continue
    return False

def install_pip_windows():
    """Instala pip en Windows usando múltiples métodos"""
    print(f"{Colors.YELLOW}Instalando pip en Windows...{Colors.END}")
    
    # Método 1: ensurepip
    try:
        subprocess.run([sys.executable, '-m', 'ensurepip', '--upgrade'], check=True, timeout=60)
        print(f"{Colors.GREEN}Pip instalado con ensurepip{Colors.END}")
        return True
    except:
        pass
    
    # Método 2: descargar get-pip.py
    try:
        import urllib.request
        print("  Descargando get-pip.py...")
        urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')
        subprocess.run([sys.executable, 'get-pip.py'], check=True, timeout=60)
        os.remove('get-pip.py')
        print(f"{Colors.GREEN}Pip instalado con get-pip.py{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return False

def check_python_module(module_name):
    return importlib.util.find_spec(module_name) is not None

# ============================================================================
# Dependencias de Python con múltiples estrategias
# ============================================================================
REQUISITOS = [
    ('flask', 'flask==2.3.3'),
    ('werkzeug', 'werkzeug==2.3.0'),
    ('waitress', 'waitress==2.1.2'),
    ('requests', 'requests==2.31.0'),
]

def check_dependencies():
    """Verifica las dependencias de Python necesarias"""
    print(f"\n{Colors.BOLD}📦 Verificando dependencias...{Colors.END}")
    missing = []
    for modulo, paquete in REQUISITOS:
        if check_python_module(modulo):
            print(f"{Colors.GREEN}  ✓ {modulo} OK{Colors.END}")
        else:
            print(f"{Colors.YELLOW}  ✗ {modulo} (faltante){Colors.END}")
            missing.append(paquete)
    return missing

def install_with_multiple_strategies(packages):
    """Intenta instalar paquetes con múltiples estrategias"""
    sistema = get_system()
    distro = get_linux_distro()
    
    # Colección de estrategias de instalación
    estrategias = []
    
    # Estrategia 1: python -m pip con flags
    python_cmd = sys.executable
    estrategias.append([python_cmd, '-m', 'pip', 'install'])
    
    # Estrategia 2: con --user (evita problemas de permisos)
    if sistema != 'windows':
        estrategias.append([python_cmd, '-m', 'pip', 'install', '--user'])
    
    # Estrategia 3: con --break-system-packages (Arch, Fedora)
    if sistema == 'linux' and distro in ['arch-based', 'fedora-based']:
        estrategias.append([python_cmd, '-m', 'pip', 'install', '--break-system-packages'])
        estrategias.append([python_cmd, '-m', 'pip', 'install', '--user', '--break-system-packages'])
    
    # Estrategia 4: pip3 directamente
    if check_command('pip3'):
        estrategias.append(['pip3', 'install'])
        if sistema == 'linux' and distro in ['arch-based', 'fedora-based']:
            estrategias.append(['pip3', 'install', '--break-system-packages'])
            estrategias.append(['pip3', 'install', '--user', '--break-system-packages'])
        else:
            estrategias.append(['pip3', 'install', '--user'])
    
    # Estrategia 5: pip directamente
    if check_command('pip'):
        estrategias.append(['pip', 'install'])
        if sistema == 'linux' and distro in ['arch-based', 'fedora-based']:
            estrategias.append(['pip', 'install', '--break-system-packages'])
            estrategias.append(['pip', 'install', '--user', '--break-system-packages'])
        else:
            estrategias.append(['pip', 'install', '--user'])
    
    # Estrategia 6: sin verificación de dependencias
    if sistema == 'linux':
        estrategias.append([python_cmd, '-m', 'pip', 'install', '--no-deps'])
    
    # Intentar cada estrategia
    for paquete in packages:
        print(f"\n  Instalando {paquete}...")
        exito = False
        for idx, strategy in enumerate(estrategias, 1):
            cmd = strategy + [paquete]
            print(f"    Intento {idx}: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                if result.returncode == 0:
                    print(f"{Colors.GREEN}    ✓ Instalado{Colors.END}")
                    exito = True
                    break
                else:
                    error_msg = result.stderr[:100] if result.stderr else "Error desconocido"
                    print(f"    ✗ Falló: {error_msg}")
            except subprocess.TimeoutExpired:
                print(f"    ✗ Timeout")
            except Exception as e:
                print(f"    ✗ Error: {str(e)[:100]}")
        
        if not exito:
            print(f"{Colors.RED}  No se pudo instalar {paquete}{Colors.END}")
            return False
    
    return True

def check_command(command):
    return shutil.which(command) is not None

def verify_imports():
    """Verifica que las importaciones funcionen correctamente"""
    print(f"\n{Colors.BOLD}Verificando importaciones...{Colors.END}")
    all_ok = True
    for modulo, _ in REQUISITOS:
        try:
            __import__(modulo)
            print(f"{Colors.GREEN}  - {modulo}: OK{Colors.END}")
        except ImportError:
            print(f"{Colors.RED}  - {modulo}: FAILED{Colors.END}")
            all_ok = False
    return all_ok

# ============================================================================
# Cloudflare Tunnel
# ============================================================================
def check_cloudflared():
    return shutil.which('cloudflared') is not None

def install_cloudflared():
    """Instala cloudflared según el sistema operativo con múltiples estrategias"""
    sistema = get_system()
    distro = get_linux_distro()
    print(f"\n{Colors.BOLD}🌐 Instalando Cloudflare Tunnel (cloudflared)...{Colors.END}")
    
    if sistema == 'windows':
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        dest = os.path.join(get_script_dir(), 'cloudflared.exe')
        try:
            import urllib.request
            print(f"  Descargando de {url}...")
            urllib.request.urlretrieve(url, dest)
            os.chmod(dest, 0o755)
            print(f"{Colors.GREEN}  cloudflared instalado en carpeta local{Colors.END}")
            return True
        except Exception as e:
            print(f"{Colors.RED}  Error: {e}{Colors.END}")
            return False
    
    elif sistema == 'linux':
        # Estrategias según distribución
        if distro == 'debian-based':
            estrategias = [
                lambda: subprocess.run(['sudo', 'apt', 'update'], check=False),
                lambda: subprocess.run(['sudo', 'apt', 'install', '-y', 'cloudflared'], check=True),
            ]
        elif distro == 'arch-based':
            estrategias = [
                lambda: subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'cloudflared'], check=True),
            ]
        elif distro == 'fedora-based':
            estrategias = [
                lambda: subprocess.run(['sudo', 'dnf', 'install', '-y', 'cloudflared'], check=True),
            ]
        else:
            estrategias = []
        
        for estrategia in estrategias:
            try:
                estrategia()
                print(f"{Colors.GREEN}  cloudflared instalado vía gestor{Colors.END}")
                return True
            except:
                continue
        
        # Fallback: descarga binario
        return install_cloudflared_binary()
    
    elif sistema == 'darwin':
        if check_command('brew'):
            try:
                subprocess.run(['brew', 'install', 'cloudflared'], check=True)
                print(f"{Colors.GREEN}  cloudflared instalado vía Homebrew{Colors.END}")
                return True
            except:
                pass
        return install_cloudflared_binary()
    
    return False

def install_cloudflared_binary():
    """Descarga el binario directamente desde GitHub"""
    sistema = get_system()
    script_dir = get_script_dir()
    print(f"  Descargando binario cloudflared...")
    
    urls = {
        'linux': 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64',
        'darwin': 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64',
    }
    
    if sistema not in urls:
        return False
    
    dest = os.path.join(script_dir, 'cloudflared')
    try:
        import urllib.request
        urllib.request.urlretrieve(urls[sistema], dest)
        os.chmod(dest, 0o755)
        print(f"{Colors.GREEN}  cloudflared descargado en {dest}{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}  Error descargando binario: {e}{Colors.END}")
        return False

def run_cloudflare_tunnel(port=5000):
    """Inicia un túnel rápido de Cloudflare (trycloudflare.com)"""
    script_dir = get_script_dir()
    cloudflared_cmd = shutil.which('cloudflared')
    
    if not cloudflared_cmd:
        local_cmd = os.path.join(script_dir, 'cloudflared')
        if os.path.exists(local_cmd):
            cloudflared_cmd = local_cmd
        elif os.path.exists(local_cmd + '.exe'):
            cloudflared_cmd = local_cmd + '.exe'
    
    if not cloudflared_cmd:
        print(f"{Colors.RED}No se encontró cloudflared. No se puede crear túnel.{Colors.END}")
        return None
    
    print(f"{Colors.CYAN}Iniciando túnel Cloudflare...{Colors.END}")
    cmd = [cloudflared_cmd, 'tunnel', '--url', f'http://localhost:{port}']
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        url = None
        for line in process.stdout:
            print(f"[cloudflared] {line.strip()}")
            if 'https://' in line and '.trycloudflare.com' in line:
                import re
                match = re.search(r'(https://[a-zA-Z0-9\-]+\.trycloudflare\.com)', line)
                if match:
                    url = match.group(1)
                    break
        if url:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🌍 Túnel Cloudflare activo: {url}{Colors.END}")
            print(f"   Comparte esta URL para acceder remotamente a XONINAS\n")
            webbrowser.open(url)
        else:
            print(f"{Colors.YELLOW}No se pudo detectar la URL del túnel.{Colors.END}")
        return process
    except Exception as e:
        print(f"{Colors.RED}Error al iniciar cloudflared: {e}{Colors.END}")
        return None

# ============================================================================
# Configuración inicial
# ============================================================================
def run_initial_setup(xoninas_dir):
    """Ejecuta la configuración inicial si no existe master.csv o config.csv"""
    if not xoninas_dir:
        return False
    
    os.chdir(xoninas_dir)
    print(f"{Colors.GREEN}✓ Cambiando al directorio: {xoninas_dir}{Colors.END}")
    
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
# Servidor y autoreinicio
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

def run_server(xoninas_dir, cloudflare_enabled=False, auto_restart=True):
    """Ejecuta el servidor con autoreinicio opcional"""
    print(f"\n{Colors.BOLD}🚀 Iniciando servidor XONINAS (Waitress)...{Colors.END}")
    print(f"  Directorio: {xoninas_dir}")
    print(f"  Threads: 6")
    print(f"  Puerto: 5000")
    print(f"  Autoreinicio: {'activado' if auto_restart else 'desactivado'}")
    print(f"{Colors.YELLOW}  Para detener: Ctrl+C{Colors.END}")
    print("-" * 60)
    
    cleanup_port(5000)
    
    cmd = [
        sys.executable, '-m', 'waitress',
        '--host=0.0.0.0',
        '--port=5000',
        '--threads=6',
        '--connection-limit=100',
        '--channel-timeout=300',
        'xoninas:app'
    ]
    
    process = None
    cloudflare_process = None
    restart_count = 0
    
    if cloudflare_enabled:
        cloudflare_process = run_cloudflare_tunnel(5000)
    
    while True:
        if process is None or process.poll() is not None:
            restart_count += 1
            print(f"{Colors.CYAN}[INFO] Lanzando servidor (intento #{restart_count})...{Colors.END}")
            process = subprocess.Popen(cmd, cwd=xoninas_dir)
            time.sleep(5)
        
        if auto_restart and not is_server_alive():
            print(f"{Colors.RED}[ERROR] El servidor no responde. Reiniciando...{Colors.END}")
            if process:
                process.terminate()
                process.wait()
            process = None
            time.sleep(5)
        else:
            time.sleep(10)

# ============================================================================
# Crear accesos directos
# ============================================================================
def create_shortcuts():
    sistema = get_system()
    if sistema == 'windows':
        with open('INICIAR_XONINAS.bat', 'w') as f:
            f.write("""@echo off
title XONINAS 2026 - NAS Local
color 1F
echo ========================================
echo      XONINAS 2026 - NAS Local
echo      Desarrollado por Darian Alberto Camacho Salas
echo      #Somos XONIDU
echo ========================================
echo.
python start.py
pause
""")
        print(f"{Colors.GREEN}Creado INICIAR_XONINAS.bat{Colors.END}")
    elif sistema == 'linux':
        with open('INICIAR_XONINAS.sh', 'w') as f:
            f.write("""#!/bin/bash
echo "========================================"
echo "      XONINAS 2026 - NAS Local"
echo "      Desarrollado por Darian Alberto Camacho Salas"
echo "      #Somos XONIDU"
echo "========================================"
echo ""
python3 start.py
read -p "Presiona Enter para salir"
""")
        os.chmod('INICIAR_XONINAS.sh', 0o755)
        print(f"{Colors.GREEN}Creado INICIAR_XONINAS.sh{Colors.END}")
    elif sistema == 'darwin':
        with open('INICIAR_XONINAS.command', 'w') as f:
            f.write("""#!/bin/bash
cd "$(dirname "$0")"
echo "========================================"
echo "      XONINAS 2026 - NAS Local"
echo "      Desarrollado por Darian Alberto Camacho Salas"
echo "      #Somos XONIDU"
echo "========================================"
echo ""
python3 start.py
""")
        os.chmod('INICIAR_XONINAS.command', 0o755)
        print(f"{Colors.GREEN}Creado INICIAR_XONINAS.command{Colors.END}")

# ============================================================================
# Función principal
# ============================================================================
def main():
    if get_system() == 'windows':
        os.system('cls')
    else:
        os.system('clear')
    
    print_banner()
    
    # Argumentos de ayuda
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', '/?']:
        mostrar_ayuda()
        if get_system() != 'windows':
            input(f"\n{Colors.YELLOW}Presiona Enter para salir...{Colors.END}")
        return
    
    sistema = get_system()
    distro = get_linux_distro()
    script_dir = get_script_dir()
    xoninas_path = get_xoninas_path()
    xoninas_dir = get_xoninas_dir()
    
    print(f"{Colors.BOLD}Sistema operativo:{Colors.END} {sistema}")
    if distro:
        print(f"{Colors.BOLD}Distribución:{Colors.END} {distro}")
    print(f"{Colors.BOLD}Directorio de start.py:{Colors.END} {script_dir}")
    print(f"{Colors.BOLD}Ruta de xoninas.py:{Colors.END} {xoninas_path or 'NO ENCONTRADO'}")
    
    # Crear directorio si es necesario
    if not xoninas_dir:
        xoninas_dir = script_dir
        print(f"{Colors.YELLOW}Usando directorio actual como fallback{Colors.END}")
    
    # Verificar Python
    if not check_python():
        print(f"\n{Colors.RED}❌ Python no está instalado{Colors.END}")
        print("Descarga Python desde: https://www.python.org/downloads/")
        sys.exit(1)
    
    ver_py = subprocess.run(get_python_command() + ['--version'], capture_output=True, text=True).stdout.strip()
    print(f"{Colors.BOLD}Python:{Colors.END} {ver_py}")
    
    # Verificar e instalar pip si es necesario
    if not check_pip():
        print(f"\n{Colors.YELLOW}⚠️ Pip no encontrado. Instalando...{Colors.END}")
        if sistema == 'linux':
            if not install_pip_linux():
                print(f"{Colors.RED}No se pudo instalar pip. Instálalo manualmente.{Colors.END}")
                sys.exit(1)
        elif sistema == 'windows':
            if not install_pip_windows():
                print(f"{Colors.RED}No se pudo instalar pip. Ejecuta como administrador.{Colors.END}")
                sys.exit(1)
        else:
            print(f"{Colors.YELLOW}Instala pip manualmente con: python -m ensurepip --upgrade{Colors.END}")
            sys.exit(1)
    else:
        print(f"{Colors.GREEN}✓ Pip disponible{Colors.END}")
    
    # Verificar e instalar dependencias
    missing = check_dependencies()
    if missing:
        print(f"\n{Colors.YELLOW}Faltan {len(missing)} dependencias.{Colors.END}")
        resp = input("¿Instalar automáticamente? (s/n): ")
        if resp.lower() == 's':
            if not install_with_multiple_strategies(missing):
                print(f"{Colors.YELLOW}Continuando a pesar de errores...{Colors.END}")
        else:
            print(f"{Colors.YELLOW}No se instalarán. El programa podría fallar.{Colors.END}")
    
    # Verificar que xoninas.py existe
    if not xoninas_path or not os.path.exists(xoninas_path):
        print(f"\n{Colors.RED}❌ Error: No se encuentra xoninas.py{Colors.END}")
        sys.exit(1)
    
    # Configuración inicial
    if not run_initial_setup(xoninas_dir):
        sys.exit(0)
    
    # Preguntar por Cloudflare Tunnel
    cloudflare_enabled = False
    resp = input(f"\n{Colors.BOLD}🌐 ¿Activar túnel Cloudflare para acceso remoto? (s/n): {Colors.END}")
    if resp.lower() == 's':
        cloudflare_enabled = True
        if not check_cloudflared():
            print(f"{Colors.YELLOW}Instalando cloudflared...{Colors.END}")
            if install_cloudflared():
                print(f"{Colors.GREEN}Cloudflared listo.{Colors.END}")
            else:
                print(f"{Colors.RED}No se pudo instalar cloudflared.{Colors.END}")
                cloudflare_enabled = False
        else:
            print(f"{Colors.GREEN}Cloudflared ya instalado.{Colors.END}")
    
    # Iniciar servidor
    try:
        run_server(xoninas_dir, cloudflare_enabled, auto_restart=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Servidor detenido por el usuario{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}❌ Error inesperado: {e}{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        create_shortcuts()
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Saliendo...{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error inesperado: {e}{Colors.END}")
