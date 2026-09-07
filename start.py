#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS 2026 - Lanzador Ultrarrobusto
NAS Local con Carpetas Protegidas
Incluye gestion automatica de STORAGE_FOLDER, pip, dependencias y Cloudflare Tunnel
Captura la URL del tunel y la pasa a xoninas.py
Soporte para conversión a blanco y negro (Ghostscript + Pillow + PyMuPDF)

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
import re
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
                if 'ubuntu' in content or 'debian' in content or 'mint' in content or 'antix' in content:
                    return 'debian-based'
                elif 'arch' in content or 'manjaro' in content:
                    return 'arch-based'
                elif 'fedora' in content:
                    return 'fedora'
                elif 'centos' in content or 'rhel' in content:
                    return 'rhel-based'
                elif 'opensuse' in content:
                    return 'opensuse-based'
        if shutil.which('apt'):
            return 'debian-based'
        elif shutil.which('pacman'):
            return 'arch-based'
        elif shutil.which('dnf'):
            return 'fedora'
        elif shutil.which('yum'):
            return 'rhel-based'
        elif shutil.which('zypper'):
            return 'opensuse-based'
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
# Verificacion e instalacion de Ghostscript
# ============================================================================
def check_ghostscript():
    """Verifica si Ghostscript está instalado en el sistema"""
    return shutil.which('gs') is not None

def install_ghostscript_linux():
    """Instala Ghostscript en Linux según la distribución"""
    distro = get_linux_distro()
    print(f"{Colors.YELLOW}Instalando Ghostscript en Linux ({distro})...{Colors.END}")
    
    if distro == 'debian-based':
        try:
            subprocess.run(['sudo', 'apt', 'update'], check=False)
            subprocess.run(['sudo', 'apt', 'install', '-y', 'ghostscript'], check=True)
            print(f"{Colors.GREEN}Ghostscript instalado correctamente{Colors.END}")
            return True
        except:
            return False
    elif distro == 'arch-based':
        try:
            subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'ghostscript'], check=True)
            print(f"{Colors.GREEN}Ghostscript instalado correctamente{Colors.END}")
            return True
        except:
            return False
    elif distro == 'fedora':
        try:
            subprocess.run(['sudo', 'dnf', 'install', '-y', 'ghostscript'], check=True)
            print(f"{Colors.GREEN}Ghostscript instalado correctamente{Colors.END}")
            return True
        except:
            return False
    elif distro == 'rhel-based':
        try:
            subprocess.run(['sudo', 'yum', 'install', '-y', 'ghostscript'], check=True)
            print(f"{Colors.GREEN}Ghostscript instalado correctamente{Colors.END}")
            return True
        except:
            return False
    elif distro == 'opensuse-based':
        try:
            subprocess.run(['sudo', 'zypper', 'install', '-y', 'ghostscript'], check=True)
            print(f"{Colors.GREEN}Ghostscript instalado correctamente{Colors.END}")
            return True
        except:
            return False
    else:
        print(f"{Colors.RED}Distribución no reconocida. Instala Ghostscript manualmente.{Colors.END}")
        return False

def install_ghostscript_mac():
    """Instala Ghostscript en macOS usando Homebrew"""
    if shutil.which('brew'):
        try:
            subprocess.run(['brew', 'install', 'ghostscript'], check=True)
            print(f"{Colors.GREEN}Ghostscript instalado correctamente{Colors.END}")
            return True
        except:
            return False
    else:
        print(f"{Colors.YELLOW}Homebrew no encontrado. Instala Ghostscript manualmente desde: https://www.ghostscript.com/{Colors.END}")
        return False

def install_ghostscript_windows():
    """Instrucciones para instalar Ghostscript en Windows"""
    print(f"{Colors.YELLOW}Ghostscript en Windows:{Colors.END}")
    print(f"  1. Descarga desde: https://www.ghostscript.com/releases/gsdnld.html")
    print(f"  2. Ejecuta el instalador y selecciona 'Agregar al PATH'")
    print(f"  3. Reinicia la terminal")
    return False

def ensure_ghostscript():
    """Asegura que Ghostscript esté instalado"""
    if check_ghostscript():
        print(f"{Colors.GREEN}✅ Ghostscript disponible{Colors.END}")
        return True
    
    sistema = get_system()
    print(f"\n{Colors.YELLOW}⚠️ Ghostscript no está instalado (necesario para conversión B/N){Colors.END}")
    resp = input("¿Deseas instalarlo automáticamente? (s/n): ")
    
    if resp.lower() != 's':
        print(f"{Colors.YELLOW}Ghostscript no instalado. La conversión a blanco y negro NO funcionará.{Colors.END}")
        return False
    
    if sistema == 'linux':
        return install_ghostscript_linux()
    elif sistema == 'darwin':
        return install_ghostscript_mac()
    elif sistema == 'windows':
        return install_ghostscript_windows()
    else:
        print(f"{Colors.RED}Sistema no soportado para instalación automática{Colors.END}")
        return False

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
    dependencies = [
        ('flask', 'flask'),
        ('werkzeug', 'werkzeug'),
        ('waitress', 'waitress'),
        ('requests', 'requests'),
        ('qrcode', 'qrcode'),
        ('PIL', 'Pillow'),
        ('fitz', 'PyMuPDF'),
        ('docx', 'python-docx'),
    ]
    missing = []
    for module, package in dependencies:
        # PIL se importa como 'PIL' pero el paquete es 'Pillow'
        if check_python_module(module):
            print(f"{Colors.GREEN}  {package} OK{Colors.END}")
        else:
            print(f"{Colors.YELLOW}  {package} (faltante){Colors.END}")
            missing.append(package)
    return missing

def install_with_multiple_strategies(packages):
    """Intenta instalar paquetes con múltiples estrategias"""
    sistema = get_system()
    distro = get_linux_distro()
    
    estrategias = []
    
    # Estrategia 1: python -m pip
    estrategias.append([sys.executable, '-m', 'pip', 'install'])
    
    # Estrategia 2: con --user
    if sistema != 'windows':
        estrategias.append([sys.executable, '-m', 'pip', 'install', '--user'])
    
    # Estrategia 3: con --break-system-packages (Arch, Fedora)
    if sistema == 'linux' and distro in ['arch-based', 'fedora']:
        estrategias.append([sys.executable, '-m', 'pip', 'install', '--break-system-packages'])
        estrategias.append([sys.executable, '-m', 'pip', 'install', '--user', '--break-system-packages'])
    
    # Estrategia 4: pip3 directamente
    if shutil.which('pip3'):
        estrategias.append(['pip3', 'install'])
        if sistema == 'linux' and distro in ['arch-based', 'fedora']:
            estrategias.append(['pip3', 'install', '--break-system-packages'])
            estrategias.append(['pip3', 'install', '--user'])
    
    # Estrategia 5: pip directamente
    if shutil.which('pip'):
        estrategias.append(['pip', 'install'])
        if sistema == 'linux' and distro in ['arch-based', 'fedora']:
            estrategias.append(['pip', 'install', '--break-system-packages'])
            estrategias.append(['pip', 'install', '--user'])
    
    for paquete in packages:
        print(f"\n  Instalando {paquete}...")
        exito = False
        for idx, strategy in enumerate(estrategias, 1):
            cmd = strategy + [paquete]
            print(f"    Intento {idx}: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
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

def install_dependencies(missing):
    if not missing:
        return True
    print(f"\n{Colors.BOLD}Instalando dependencias faltantes...{Colors.END}")
    return install_with_multiple_strategies(missing)

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

def start_cloudflare_tunnel(port=5000):
    """Inicia cloudflared, captura la URL y la guarda en variable de entorno"""
    cloudflared_cmd = shutil.which('cloudflared')
    if not cloudflared_cmd:
        print(f"{Colors.RED}cloudflared no encontrado.{Colors.END}")
        return None
    
    print(f"{Colors.CYAN}Iniciando tunel Cloudflare...{Colors.END}")
    cmd = [cloudflared_cmd, 'tunnel', '--url', f'http://localhost:{port}']
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   universal_newlines=True, bufsize=1)
        url = None
        for line in process.stdout:
            print(f"[cloudflared] {line.strip()}")
            if 'https://' in line and '.trycloudflare.com' in line:
                match = re.search(r'(https://[a-zA-Z0-9\-]+\.trycloudflare\.com)', line)
                if match:
                    url = match.group(1)
                    break
        if url:
            print(f"{Colors.GREEN}Tunel Cloudflare activo: {url}{Colors.END}")
            os.environ['TUNNEL_URL'] = url
        else:
            print(f"{Colors.YELLOW}No se pudo detectar la URL del tunel.{Colors.END}")
        return process
    except Exception as e:
        print(f"{Colors.RED}Error al iniciar cloudflared: {e}{Colors.END}")
        return None

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
    if 'TUNNEL_URL' in os.environ:
        env['TUNNEL_URL'] = os.environ['TUNNEL_URL']
    
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
    
    # Dependencias Python
    missing = check_dependencies()
    if missing:
        print(f"\n{Colors.YELLOW}Faltan {len(missing)} dependencias.{Colors.END}")
        print(f"  {Colors.CYAN}Estas librerías son necesarias para la conversión a blanco y negro{Colors.END}")
        resp = input("Instalar automaticamente? (s/n): ")
        if resp.lower() == 's':
            if not install_dependencies(missing):
                print(f"{Colors.YELLOW}Continuando a pesar de errores...{Colors.END}")
                print(f"{Colors.YELLOW}  La conversión a blanco y negro puede no funcionar correctamente.{Colors.END}")
        else:
            print(f"{Colors.YELLOW}No se instalaran. El programa podria fallar.{Colors.END}")
            print(f"{Colors.YELLOW}  La conversión a blanco y negro NO estará disponible.{Colors.END}")
    
    # Ghostscript (necesario para conversión B/N)
    ensure_ghostscript()
    
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
    
    # Cloudflare Tunnel
    resp = input(f"\n{Colors.BOLD}Activar tunel Cloudflare para acceso remoto? (s/n): {Colors.END}")
    if resp.lower() == 's':
        if not check_cloudflared():
            install_cloudflared()
        if check_cloudflared():
            tunnel_process = start_cloudflare_tunnel(5000)
            time.sleep(2)
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