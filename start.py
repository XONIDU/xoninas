#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS 2026 - Lanzador Ultrarrobusto
NAS Local con Carpetas Protegidas
Incluye gestion automatica de STORAGE_FOLDER, pip, dependencias y Cloudflare Tunnel

Desarrollado por: Darian Alberto Camacho Salas
Organizacion: XONIDU
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
import csv
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
# Deteccion del sistema
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
# Gestion de STORAGE_FOLDER (Robusto)
# ============================================================================
def ensure_storage_folder():
    """Asegura que STORAGE_FOLDER este definido y configurado correctamente."""
    script_dir = get_script_dir()
    config_path = os.path.join(script_dir, 'config.csv')
    storage_path = None
    
    # 1. Intentar leer config.csv
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0] == 'storage_path':
                        storage_path = row[1].strip()
                        break
        except Exception as e:
            print(f"{Colors.YELLOW}Error leyendo config.csv: {e}{Colors.END}")
    
    # 2. Si no se encontro, usar ruta por defecto y crear config.csv
    if not storage_path:
        default_path = os.path.join(script_dir, 'storage')
        storage_path = str(Path(default_path).resolve())
        print(f"{Colors.YELLOW}config.csv no encontrado. Usando ruta por defecto: {storage_path}{Colors.END}")
        try:
            with open(config_path, 'w') as f:
                f.write(f"storage_path,{storage_path}\n")
            print(f"{Colors.GREEN}config.csv creado{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}No se pudo crear config.csv: {e}{Colors.END}")
            storage_path = default_path
    
    # 3. Crear el directorio si no existe
    try:
        Path(storage_path).mkdir(parents=True, exist_ok=True)
        print(f"{Colors.GREEN}Directorio de almacenamiento listo: {storage_path}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}No se pudo crear el directorio: {e}{Colors.END}")
        storage_path = os.path.join(os.getcwd(), 'storage')
        Path(storage_path).mkdir(parents=True, exist_ok=True)
        print(f"{Colors.YELLOW}Usando fallback: {storage_path}{Colors.END}")
    
    # 4. Establecer variable de entorno
    os.environ['STORAGE_FOLDER'] = storage_path
    print(f"{Colors.CYAN}STORAGE_FOLDER establecido como variable de entorno{Colors.END}")
    return storage_path

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
    print(f"\n{Colors.BOLD}Verificando dependencias...{Colors.END}")
    dependencies = ['flask', 'werkzeug', 'waitress', 'requests', 'qrcode']
    missing = []
    for dep in dependencies:
        if check_python_module(dep):
            print(f"{Colors.GREEN}  {dep} OK{Colors.END}")
        else:
            print(f"{Colors.YELLOW}  {dep} (faltante){Colors.END}")
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
            print(f"{Colors.GREEN}    {dep} instalado{Colors.END}")
        except:
            try:
                cmd = get_pip_command() + ['install', dep]
                subprocess.run(cmd, check=True)
                print(f"{Colors.GREEN}    {dep} instalado{Colors.END}")
            except:
                print(f"{Colors.RED}    Error instalando {dep}{Colors.END}")
                success = False
    return success

def check_cloudflared():
    return shutil.which('cloudflared') is not None

def install_cloudflared():
    sistema = get_system()
    print(f"\n{Colors.BOLD}Instalando Cloudflare Tunnel...{Colors.END}")
    if sistema == 'linux':
        distro = get_linux_distro()
        if distro == 'arch-based':
            try:
                subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'cloudflared'], check=True)
                print(f"{Colors.GREEN}  cloudflared instalado{Colors.END}")
                return True
            except:
                pass
        elif distro == 'debian-based':
            try:
                subprocess.run(['sudo', 'apt', 'update'], check=False)
                subprocess.run(['sudo', 'apt', 'install', '-y', 'cloudflared'], check=True)
                print(f"{Colors.GREEN}  cloudflared instalado{Colors.END}")
                return True
            except:
                pass
    print(f"{Colors.YELLOW}  No se pudo instalar cloudflared automaticamente.{Colors.END}")
    return False

# ============================================================================
# Configuracion inicial (clave maestra)
# ============================================================================
def ensure_master_key(xoninas_dir):
    master_path = os.path.join(xoninas_dir, 'master.csv')
    if os.path.exists(master_path):
        return True
    
    print("\n" + "="*50)
    print("    CONFIGURACION DE CLAVE MAESTRA")
    print("="*50)
    pwd = input("Clave maestra (deja vacio para 'admin'): ").strip()
    if not pwd:
        pwd = "admin"
        print("Usando 'admin' como clave maestra")
    import hashlib
    hashed = hashlib.sha256(pwd.encode()).hexdigest()
    with open(master_path, 'w') as f:
        f.write(hashed)
    print(f"{Colors.GREEN}Clave maestra guardada.{Colors.END}")
    return True

# ============================================================================
# Ejecucion del servidor
# ============================================================================
def run_server_directly(xoninas_path, storage_path):
    print(f"\n{Colors.BOLD}Iniciando servidor XONINAS (modo directo)...{Colors.END}")
    print(f"  Almacenamiento: {storage_path}")
    print(f"  Puerto: 5000")
    print(f"{Colors.YELLOW}  Para detener: Ctrl+C{Colors.END}")
    print("-" * 60)
    
    env = os.environ.copy()
    env['STORAGE_FOLDER'] = storage_path
    env['XONINAS_CONFIG_DIR'] = os.path.dirname(xoninas_path)
    
    cmd = get_python_command() + [xoninas_path]
    try:
        subprocess.run(cmd, env=env, cwd=os.path.dirname(xoninas_path))
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Servidor detenido por el usuario{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")

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
    
    print(f"{Colors.BOLD}Sistema operativo:{Colors.END} {sistema}")
    if distro:
        print(f"{Colors.BOLD}Distribucion:{Colors.END} {distro}")
    print(f"{Colors.BOLD}Directorio de start.py:{Colors.END} {script_dir}")
    print(f"{Colors.BOLD}Ruta de xoninas.py:{Colors.END} {xoninas_path or 'NO ENCONTRADO'}")
    
    # Python
    if not check_python():
        print(f"\n{Colors.RED}Python no esta instalado{Colors.END}")
        sys.exit(1)
    
    ver_py = subprocess.run(get_python_command() + ['--version'], capture_output=True, text=True).stdout.strip()
    print(f"{Colors.BOLD}Python:{Colors.END} {ver_py}")
    
    # Pip
    if not check_pip():
        print(f"\n{Colors.YELLOW}Pip no encontrado. Instalando...{Colors.END}")
        if sistema == 'linux':
            if not install_pip_linux():
                print(f"{Colors.RED}No se pudo instalar pip.{Colors.END}")
                sys.exit(1)
        elif sistema == 'windows':
            if not install_pip_windows():
                print(f"{Colors.RED}No se pudo instalar pip.{Colors.END}")
                sys.exit(1)
        else:
            print(f"{Colors.YELLOW}Instala pip manualmente: python -m ensurepip --upgrade{Colors.END}")
            sys.exit(1)
    else:
        print(f"{Colors.GREEN}Pip disponible{Colors.END}")
    
    # Dependencias
    missing = check_dependencies()
    if missing:
        print(f"\n{Colors.YELLOW}Faltan {len(missing)} dependencias.{Colors.END}")
        resp = input("Instalar automaticamente? (s/n): ")
        if resp.lower() == 's':
            if not install_dependencies(missing):
                print(f"{Colors.YELLOW}Continuando a pesar de errores...{Colors.END}")
        else:
            print(f"{Colors.YELLOW}No se instalaran. El programa podria fallar.{Colors.END}")
    
    # STORAGE_FOLDER
    storage_path = ensure_storage_folder()
    
    # Verificar xoninas.py
    if not xoninas_path or not os.path.exists(xoninas_path):
        print(f"\n{Colors.RED}No se encuentra xoninas.py{Colors.END}")
        sys.exit(1)
    
    # Clave maestra
    xoninas_dir = os.path.dirname(xoninas_path)
    if not ensure_master_key(xoninas_dir):
        print(f"{Colors.RED}No se pudo configurar la clave maestra.{Colors.END}")
        sys.exit(1)
    
    # Cloudflare Tunnel (opcional)
    resp = input(f"\n{Colors.BOLD}Activar tunel Cloudflare para acceso remoto? (s/n): {Colors.END}")
    if resp.lower() == 's':
        if not check_cloudflared():
            install_cloudflared()
        if check_cloudflared():
            try:
                subprocess.Popen(['cloudflared', 'tunnel', '--url', 'http://localhost:5000'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"{Colors.CYAN}Tunel Cloudflare iniciado (trycloudflare.com){Colors.END}")
            except:
                print(f"{Colors.YELLOW}No se pudo iniciar cloudflared.{Colors.END}")
        else:
            print(f"{Colors.YELLOW}cloudflared no disponible.{Colors.END}")
    
    # Ejecutar
    try:
        run_server_directly(xoninas_path, storage_path)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Servidor detenido por el usuario{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Error inesperado: {e}{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Saliendo...{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error inesperado: {e}{Colors.END}")
