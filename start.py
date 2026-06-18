#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS 2026 - Lanzador Ultrarrobusto
NAS Local con Carpetas Protegidas
Incluye gestión automática de STORAGE_FOLDER, pip, dependencias y Cloudflare Tunnel

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
# Gestión de STORAGE_FOLDER (Robusto)
# ============================================================================
def ensure_storage_folder():
    """
    Asegura que STORAGE_FOLDER esté definido y configurado correctamente.
    Si falta config.csv, lo crea con la ruta por defecto.
    """
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
            print(f"{Colors.YELLOW}⚠️ Error leyendo config.csv: {e}{Colors.END}")
    
    # 2. Si no se encontró, usar ruta por defecto y crear config.csv
    if not storage_path:
        default_path = os.path.join(script_dir, 'storage')
        storage_path = str(Path(default_path).resolve())
        print(f"{Colors.YELLOW}⚠️ config.csv no encontrado o sin storage_path. Usando ruta por defecto: {storage_path}{Colors.END}")
        # Crear config.csv
        try:
            with open(config_path, 'w') as f:
                f.write(f"storage_path,{storage_path}\n")
            print(f"{Colors.GREEN}✅ config.csv creado con ruta: {storage_path}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}❌ No se pudo crear config.csv: {e}{Colors.END}")
            # Usar la ruta por defecto aunque no se pueda escribir
            storage_path = default_path
    
    # 3. Crear el directorio si no existe
    try:
        Path(storage_path).mkdir(parents=True, exist_ok=True)
        print(f"{Colors.GREEN}📁 Directorio de almacenamiento listo: {storage_path}{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}❌ No se pudo crear el directorio de almacenamiento: {e}{Colors.END}")
        # Fallback a ./storage en el directorio actual
        storage_path = os.path.join(os.getcwd(), 'storage')
        Path(storage_path).mkdir(parents=True, exist_ok=True)
        print(f"{Colors.YELLOW}⚠️ Usando fallback: {storage_path}{Colors.END}")
    
    # 4. Establecer variable de entorno para que xoninas.py la use
    os.environ['STORAGE_FOLDER'] = storage_path
    print(f"{Colors.CYAN}🔧 STORAGE_FOLDER establecido como variable de entorno{Colors.END}")
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
    print(f"\n{Colors.BOLD}📦 Verificando dependencias...{Colors.END}")
    dependencies = ['flask', 'werkzeug', 'waitress', 'requests']
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
    print(f"{Colors.YELLOW}  No se pudo instalar cloudflared automáticamente. Descárgalo manualmente si lo necesitas.{Colors.END}")
    return False

# ============================================================================
# Configuración inicial (clave maestra)
# ============================================================================
def ensure_master_key(xoninas_dir):
    """Crea la clave maestra si no existe"""
    master_path = os.path.join(xoninas_dir, 'master.csv')
    if os.path.exists(master_path):
        return True
    
    print("\n" + "="*50)
    print("    CONFIGURACIÓN DE CLAVE MAESTRA")
    print("="*50)
    pwd = input("Clave maestra (deja vacío para 'admin'): ").strip()
    if not pwd:
        pwd = "admin"
        print("Usando 'admin' como clave maestra")
    import hashlib
    hashed = hashlib.sha256(pwd.encode()).hexdigest()
    with open(master_path, 'w') as f:
        f.write(hashed)
    print(f"{Colors.GREEN}✅ Clave maestra guardada.{Colors.END}")
    return True

# ============================================================================
# Ejecución del servidor (directamente, sin subproceso)
# ============================================================================
def run_server_directly(xoninas_path, storage_path):
    """
    Ejecuta xoninas.py directamente pero con la variable STORAGE_FOLDER ya establecida.
    Esto evita el KeyError porque la app leerá la variable de entorno.
    """
    print(f"\n{Colors.BOLD}🚀 Iniciando servidor XONINAS (modo directo)...{Colors.END}")
    print(f"  Almacenamiento: {storage_path}")
    print(f"  Puerto: 5000")
    print(f"{Colors.YELLOW}  Para detener: Ctrl+C{Colors.END}")
    print("-" * 60)
    
    # Establecer la variable de entorno para el subproceso
    env = os.environ.copy()
    env['STORAGE_FOLDER'] = storage_path
    env['XONINAS_CONFIG_DIR'] = os.path.dirname(xoninas_path)
    
    # Ejecutar xoninas.py con el entorno modificado
    cmd = get_python_command() + [xoninas_path]
    try:
        subprocess.run(cmd, env=env, cwd=os.path.dirname(xoninas_path))
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Servidor detenido por el usuario{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}❌ Error al ejecutar xoninas.py: {e}{Colors.END}")

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
        print(f"{Colors.BOLD}Distribución:{Colors.END} {distro}")
    print(f"{Colors.BOLD}Directorio de start.py:{Colors.END} {script_dir}")
    print(f"{Colors.BOLD}Ruta de xoninas.py:{Colors.END} {xoninas_path or 'NO ENCONTRADO'}")
    
    # ====================================================================
    # PASO 1: Verificar Python
    # ====================================================================
    if not check_python():
        print(f"\n{Colors.RED}❌ Python no está instalado{Colors.END}")
        sys.exit(1)
    
    ver_py = subprocess.run(get_python_command() + ['--version'], capture_output=True, text=True).stdout.strip()
    print(f"{Colors.BOLD}Python:{Colors.END} {ver_py}")
    
    # ====================================================================
    # PASO 2: Verificar pip e instalarlo si falta
    # ====================================================================
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
    
    # ====================================================================
    # PASO 3: Verificar e instalar dependencias
    # ====================================================================
    missing = check_dependencies()
    if missing:
        print(f"\n{Colors.YELLOW}Faltan {len(missing)} dependencias.{Colors.END}")
        resp = input("¿Instalar automáticamente? (s/n): ")
        if resp.lower() == 's':
            if not install_dependencies(missing):
                print(f"{Colors.YELLOW}Continuando a pesar de errores...{Colors.END}")
        else:
            print(f"{Colors.YELLOW}No se instalarán. El programa podría fallar.{Colors.END}")
    
    # ====================================================================
    # PASO 4: Asegurar STORAGE_FOLDER (robusto)
    # ====================================================================
    storage_path = ensure_storage_folder()
    
    # ====================================================================
    # PASO 5: Verificar que existe xoninas.py
    # ====================================================================
    if not xoninas_path or not os.path.exists(xoninas_path):
        print(f"\n{Colors.RED}❌ No se encuentra xoninas.py{Colors.END}")
        print(f"   Buscado en: {xoninas_path}")
        sys.exit(1)
    
    # ====================================================================
    # PASO 6: Asegurar clave maestra
    # ====================================================================
    xoninas_dir = os.path.dirname(xoninas_path)
    if not ensure_master_key(xoninas_dir):
        print(f"{Colors.RED}❌ No se pudo configurar la clave maestra.{Colors.END}")
        sys.exit(1)
    
    # ====================================================================
    # PASO 7: (Opcional) Cloudflare Tunnel
    # ====================================================================
    cloudflare_enabled = False
    resp = input(f"\n{Colors.BOLD}🌐 ¿Activar túnel Cloudflare para acceso remoto? (s/n): {Colors.END}")
    if resp.lower() == 's':
        cloudflare_enabled = True
        if not check_cloudflared():
            install_cloudflared()
        if check_cloudflared():
            print(f"{Colors.GREEN}✅ cloudflared disponible. El túnel se iniciará junto con XONINAS.{Colors.END}")
            # Lanzar cloudflared en segundo plano
            try:
                subprocess.Popen(['cloudflared', 'tunnel', '--url', 'http://localhost:5000'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"{Colors.CYAN}🔗 Túnel Cloudflare iniciado (trycloudflare.com){Colors.END}")
            except:
                print(f"{Colors.YELLOW}⚠️ No se pudo iniciar cloudflared automáticamente.{Colors.END}")
        else:
            print(f"{Colors.YELLOW}⚠️ cloudflared no disponible. No se activará el túnel.{Colors.END}")
            cloudflare_enabled = False
    
    # ====================================================================
    # PASO 8: Ejecutar XONINAS
    # ====================================================================
    try:
        run_server_directly(xoninas_path, storage_path)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Servidor detenido por el usuario{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}❌ Error inesperado: {e}{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Saliendo...{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error inesperado: {e}{Colors.END}")
