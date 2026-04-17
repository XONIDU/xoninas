#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS - Lanzador Universal con autoreinicio
Sistema NAS Local con Carpetas Protegidas

Ahora con soporte para Cloudflare Tunnel (acceso remoto gratuito)

Desarrollado por: Darian Alberto Camacho Salas
Organización: XONIDU
"""

import subprocess
import sys
import os
import time
import platform
import shutil
import importlib.util
import signal
import threading
import webbrowser

# ============================================================================
# Colores para terminal
# ============================================================================
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
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
                if 'ubuntu' in content or 'debian' in content or 'mint' in content or 'antix' in content:
                    return 'debian-based'
                elif 'arch' in content or 'manjaro' in content:
                    return 'arch-based'
                elif 'fedora' in content:
                    return 'fedora'
                elif 'centos' in content or 'rhel' in content:
                    return 'centos'
                elif 'opensuse' in content:
                    return 'opensuse'
        if shutil.which('apt'):
            return 'debian-based'
        elif shutil.which('pacman'):
            return 'arch-based'
        elif shutil.which('dnf'):
            return 'fedora'
        elif shutil.which('yum'):
            return 'centos'
        elif shutil.which('zypper'):
            return 'opensuse'
        return 'linux-generico'
    except:
        return 'linux-generico'

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
║                     XONINAS 2026 v1.0.0                    ║
║              NAS Local con Carpetas Protegidas              ║
║                                                            ║
║               Sistema detectado: {sistema_texto:<27} ║
║                                                            ║
║               Desarrollado por: Darian Alberto             ║
║                      Camacho Salas                         ║
║                      Organización: XONIDU                  ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}
    """
    print(banner)

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
    try:
        cmd = get_pip_command() + ['--version']
        subprocess.run(cmd, capture_output=True, check=True)
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
    elif distro == 'fedora':
        try:
            subprocess.run(['sudo', 'dnf', 'install', '-y', 'python3-pip'], check=True)
            return True
        except:
            return False
    elif distro == 'centos':
        try:
            subprocess.run(['sudo', 'yum', 'install', '-y', 'python3-pip'], check=True)
            return True
        except:
            return False
    elif distro == 'opensuse':
        try:
            subprocess.run(['sudo', 'zypper', 'install', '-y', 'python3-pip'], check=True)
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
        try:
            import urllib.request
            urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')
            subprocess.run([sys.executable, 'get-pip.py'], check=True)
            os.remove('get-pip.py')
            return True
        except:
            return False

# ============================================================================
# Dependencias de Python
# ============================================================================
REQUISITOS = ['flask==2.3.3', 'werkzeug==2.3.0', 'waitress==2.1.2', 'requests==2.31.0']

def check_dependencies():
    print(f"\n{Colors.BOLD}📦 Verificando dependencias...{Colors.END}")
    missing = []
    for req in REQUISITOS:
        pkg = req.split('==')[0]
        try:
            __import__(pkg)
            print(f"{Colors.GREEN}  ✓ {pkg} ya instalado{Colors.END}")
        except ImportError:
            print(f"{Colors.YELLOW}  ✗ {pkg} (faltante){Colors.END}")
            missing.append(req)
    return missing

def install_dependencies(missing):
    if not missing:
        return True
    print(f"\n{Colors.BOLD}Instalando dependencias faltantes...{Colors.END}")
    pip_cmd = get_pip_command()
    flags = get_install_flags()
    success = True
    for req in missing:
        try:
            cmd = pip_cmd + ['install', req] + flags
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"{Colors.GREEN}    ✓ {req}{Colors.END}")
        except:
            try:
                cmd2 = pip_cmd + ['install', req]
                subprocess.run(cmd2, check=True)
                print(f"{Colors.GREEN}    ✓ {req} (sin flags){Colors.END}")
            except:
                print(f"{Colors.RED}    ✗ {req}{Colors.END}")
                success = False
    return success

# ============================================================================
# Configuración inicial (ruta y clave maestra)
# ============================================================================
def run_initial_setup():
    """Ejecuta la configuración inicial si no existe master.csv o config.csv"""
    # Configurar ruta de almacenamiento si no existe
    if not os.path.exists('config.csv'):
        print("\n" + "="*60)
        print("   CONFIGURACIÓN DE RUTA DE ALMACENAMIENTO")
        print("="*60)
        default = str(os.path.abspath('storage'))
        print(f"Ruta por defecto: {default}")
        ruta = input("\nNueva ruta (deja vacío para usar la de defecto): ").strip()
        if not ruta:
            ruta = default
        else:
            ruta = str(os.path.abspath(os.path.expanduser(ruta)))
        os.makedirs(ruta, exist_ok=True)
        with open('config.csv', 'w') as f:
            f.write(f"storage_path,{ruta}\n")
        print(f"{Colors.GREEN}✅ Ruta guardada: {ruta}{Colors.END}")
    
    # Configurar clave maestra si no existe
    if not os.path.exists('master.csv'):
        print("\n" + "="*50)
        print("    CONFIGURACIÓN INICIAL - CLAVE MAESTRA")
        print("="*50)
        pwd = input("Clave maestra: ").strip()
        if not pwd:
            pwd = "admin"
            print("Usando 'admin'")
        import hashlib
        hashed = hashlib.sha256(pwd.encode()).hexdigest()
        with open('master.csv', 'w') as f:
            f.write(hashed)
        print(f"{Colors.GREEN}✅ Clave guardada.{Colors.END}")
        print(f"{Colors.YELLOW}▶️  Vuelve a ejecutar 'python3 start.py' para iniciar.{Colors.END}")
        sys.exit(0)

# ============================================================================
# Cloudflare Tunnel (cloudflared)
# ============================================================================
def check_cloudflared():
    return shutil.which('cloudflared') is not None

def install_cloudflared():
    """Instala cloudflared según el sistema operativo (sin cuenta, solo binary)"""
    sistema = get_system()
    print(f"\n{Colors.BOLD}🌐 Instalando Cloudflare Tunnel (cloudflared)...{Colors.END}")
    
    if sistema == 'windows':
        # Descargar el ejecutable de Windows
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        dest = os.path.join(os.path.dirname(sys.executable), 'cloudflared.exe')
        try:
            import urllib.request
            print(f"  Descargando de {url}...")
            urllib.request.urlretrieve(url, dest)
            os.chmod(dest, 0o755)
            # Agregar al PATH? mejor lo movemos a la carpeta actual
            shutil.copy(dest, 'cloudflared.exe')
            print(f"{Colors.GREEN}  cloudflared instalado en carpeta local{Colors.END}")
            return True
        except Exception as e:
            print(f"{Colors.RED}  Error: {e}{Colors.END}")
            return False
    
    elif sistema == 'linux':
        distro = get_linux_distro()
        if distro == 'debian-based':
            # Añadir repo de Cloudflare
            try:
                subprocess.run(['sudo', 'mkdir', '-p', '--mode=0755', '/usr/share/keyrings'], check=False)
                cmd = 'curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null'
                subprocess.run(cmd, shell=True, check=True)
                echo_cmd = 'echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list'
                subprocess.run(echo_cmd, shell=True, check=True)
                subprocess.run(['sudo', 'apt', 'update'], check=False)
                subprocess.run(['sudo', 'apt', 'install', '-y', 'cloudflared'], check=True)
                print(f"{Colors.GREEN}  cloudflared instalado vía apt{Colors.END}")
                return True
            except:
                # Fallback: descargar binario
                return install_cloudflared_binary()
        elif distro == 'arch-based':
            try:
                subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'cloudflared'], check=True)
                print(f"{Colors.GREEN}  cloudflared instalado vía pacman{Colors.END}")
                return True
            except:
                return install_cloudflared_binary()
        elif distro == 'fedora':
            try:
                subprocess.run(['sudo', 'dnf', 'install', '-y', 'cloudflared'], check=True)
                print(f"{Colors.GREEN}  cloudflared instalado vía dnf{Colors.END}")
                return True
            except:
                return install_cloudflared_binary()
        else:
            return install_cloudflared_binary()
    
    elif sistema == 'darwin':
        if shutil.which('brew'):
            try:
                subprocess.run(['brew', 'install', 'cloudflared'], check=True)
                print(f"{Colors.GREEN}  cloudflared instalado vía Homebrew{Colors.END}")
                return True
            except:
                return install_cloudflared_binary()
        else:
            return install_cloudflared_binary()
    return False

def install_cloudflared_binary():
    """Descarga el binario directamente desde GitHub"""
    sistema = get_system()
    print(f"  Descargando binario cloudflared...")
    if sistema == 'linux':
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        dest = 'cloudflared'
    elif sistema == 'darwin':
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64"
        dest = 'cloudflared'
    else:
        return False
    try:
        import urllib.request
        urllib.request.urlretrieve(url, dest)
        os.chmod(dest, 0o755)
        # Mover a /usr/local/bin si se puede
        try:
            subprocess.run(['sudo', 'mv', dest, '/usr/local/bin/cloudflared'], check=True)
            print(f"{Colors.GREEN}  cloudflared instalado en /usr/local/bin{Colors.END}")
        except:
            # Dejar en carpeta actual y usar ./cloudflared
            print(f"{Colors.GREEN}  cloudflared descargado en carpeta actual{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}  Error descargando binario: {e}{Colors.END}")
        return False

def run_cloudflare_tunnel(port=5000):
    """Inicia un túnel rápido de Cloudflare (trycloudflare.com)"""
    cloudflared_cmd = shutil.which('cloudflared')
    if not cloudflared_cmd:
        cloudflared_cmd = './cloudflared' if os.path.exists('./cloudflared') else None
    if not cloudflared_cmd:
        print(f"{Colors.RED}No se encontró cloudflared. No se puede crear túnel.{Colors.END}")
        return None
    
    print(f"{Colors.CYAN}Iniciando túnel Cloudflare...{Colors.END}")
    # Comando para túnel rápido (sin autenticación, URL aleatoria)
    cmd = [cloudflared_cmd, 'tunnel', '--url', f'http://localhost:{port}']
    try:
        # Lanzar en segundo plano y capturar salida para extraer URL
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        # Leer líneas hasta encontrar la URL
        url = None
        for line in process.stdout:
            print(f"[cloudflared] {line.strip()}")
            if 'https://' in line and '.trycloudflare.com' in line:
                # Extraer URL
                import re
                match = re.search(r'(https://[a-zA-Z0-9\-]+\.trycloudflare\.com)', line)
                if match:
                    url = match.group(1)
                    break
        if url:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🌍 Túnel Cloudflare activo: {url}{Colors.END}")
            print(f"   Comparte esta URL para acceder remotamente a XONINAS\n")
            # Abrir navegador con la URL
            webbrowser.open(url)
        else:
            print(f"{Colors.YELLOW}No se pudo detectar la URL del túnel. Revisa la salida arriba.{Colors.END}")
        return process
    except Exception as e:
        print(f"{Colors.RED}Error al iniciar cloudflared: {e}{Colors.END}")
        return None

# ============================================================================
# Autoreinicio y healthcheck
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
                os.kill(int(pid), signal.SIGTERM)
            time.sleep(2)
    except:
        pass

def run_server(cloudflare_enabled=False):
    print(f"\n{Colors.BOLD}🚀 Iniciando servidor XONINAS (Waitress)...{Colors.END}")
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
    
    # Iniciar túnel si se solicita
    if cloudflare_enabled:
        cloudflare_process = run_cloudflare_tunnel(5000)
    
    while True:
        if process is None or process.poll() is not None:
            restart_count += 1
            print(f"{Colors.CYAN}[INFO] Lanzando servidor (intento #{restart_count})...{Colors.END}")
            process = subprocess.Popen(cmd)
            time.sleep(5)
        
        if not is_server_alive():
            print(f"{Colors.RED}[ERROR] El servidor no responde. Reiniciando...{Colors.END}")
            if process:
                process.terminate()
                process.wait()
            process = None
            time.sleep(5)
        else:
            time.sleep(10)

# ============================================================================
# Menú principal
# ============================================================================
def main():
    os.system('clear' if get_system() != 'windows' else 'cls')
    print_banner()
    
    sistema = get_system()
    distro = get_linux_distro()
    print(f"{Colors.BOLD}Sistema operativo:{Colors.END} {sistema}")
    if distro:
        print(f"{Colors.BOLD}Distribución:{Colors.END} {distro}")
    print(f"{Colors.BOLD}Python:{Colors.END} {sys.version.split()[0]}")
    print(f"{Colors.BOLD}Directorio:{Colors.END} {os.getcwd()}")
    
    # Verificar xoninas.py
    if not os.path.exists('xoninas.py'):
        print(f"\n{Colors.RED}❌ Error: No se encuentra xoninas.py{Colors.END}")
        sys.exit(1)
    
    # Verificar Python
    if not check_python():
        print(f"\n{Colors.RED}❌ Python no instalado{Colors.END}")
        sys.exit(1)
    
    # Verificar pip
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
            print(f"{Colors.YELLOW}Instala pip manualmente y vuelve a ejecutar.{Colors.END}")
            sys.exit(1)
    
    # Dependencias
    missing = check_dependencies()
    if missing:
        print(f"\n{Colors.YELLOW}Faltan {len(missing)} dependencias.{Colors.END}")
        resp = input("¿Instalar automáticamente? (s/n): ")
        if resp.lower() == 's':
            if not install_dependencies(missing):
                print(f"{Colors.YELLOW}Continuando a pesar de errores...{Colors.END}")
        else:
            print(f"{Colors.YELLOW}No se instalarán. El programa podría fallar.{Colors.END}")
    
    # Configuración inicial (ruta y clave maestra)
    run_initial_setup()
    
    # Preguntar por Cloudflare Tunnel
    print(f"\n{Colors.BOLD}🌐 ¿Quieres exponer XONINAS a Internet mediante Cloudflare Tunnel?{Colors.END}")
    print("   (Generará una URL pública como https://xxxx.trycloudflare.com, sin registro)")
    resp = input("¿Activar túnel Cloudflare? (s/n): ")
    cloudflare_enabled = resp.lower() == 's'
    
    if cloudflare_enabled and not check_cloudflared():
        print(f"\n{Colors.YELLOW}Cloudflared no está instalado. Instalando...{Colors.END}")
        if install_cloudflared():
            print(f"{Colors.GREEN}Cloudflared listo.{Colors.END}")
        else:
            print(f"{Colors.RED}No se pudo instalar cloudflared. El túnel no estará disponible.{Colors.END}")
            cloudflare_enabled = False
    elif cloudflare_enabled and check_cloudflared():
        print(f"{Colors.GREEN}Cloudflared ya instalado.{Colors.END}")
    
    # Iniciar servidor (con o sin túnel)
    try:
        run_server(cloudflare_enabled)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Servidor detenido por el usuario{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}❌ Error inesperado: {e}{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    main()
