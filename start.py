#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS 2026 - Lanzador Universal (Robusto)
Sistema NAS Local con Carpetas Protegidas
Incluye instalación automática de pip, dependencias, Cloudflare Tunnel y autoreinicio

Desarrollado por: Darian Alberto Camacho Salas
Organización: XONIDU
"""

import subprocess
import sys
import os
import platform
import shutil
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

def get_script_dir():
    """Obtiene el directorio donde está guardado este script (start.py)"""
    return os.path.dirname(os.path.abspath(__file__))

def get_fixed_xoninas_dir():
    """Devuelve la ruta fija /home/usuario/xoninas/"""
    usuario = os.path.expanduser("~")
    nombre_usuario = os.path.basename(usuario)
    return os.path.join('/home', nombre_usuario, 'xoninas')

def get_xoninas_path():
    """
    Detecta la ruta de xoninas.py:
    1. Primero busca en el mismo directorio que start.py
    2. Si no, busca en /home/usuario/xoninas/
    3. Si no, busca en el directorio actual
    """
    script_dir = get_script_dir()
    
    # Buscar en el mismo directorio que start.py
    ruta_local = os.path.join(script_dir, 'xoninas.py')
    if os.path.exists(ruta_local):
        return ruta_local, 'local'
    
    # Buscar en la ruta fija /home/usuario/xoninas/
    ruta_fija = os.path.join(get_fixed_xoninas_dir(), 'xoninas.py')
    if os.path.exists(ruta_fija):
        return ruta_fija, 'fija'
    
    # Buscar en el directorio actual
    ruta_actual = os.path.join(os.getcwd(), 'xoninas.py')
    if os.path.exists(ruta_actual):
        return ruta_actual, 'actual'
    
    # Si no existe en ningún lado, devolvemos la local como predeterminada
    return ruta_local, 'ninguna'

def get_xoninas_dir():
    """Devuelve el directorio donde está xoninas.py"""
    ruta, _ = get_xoninas_path()
    return os.path.dirname(ruta)

def print_banner():
    sistema = get_system()
    distro = get_linux_distro()
    ruta_xoninas, origen = get_xoninas_path()
    sistema_texto = {
        'windows': 'WINDOWS',
        'linux': f'LINUX ({distro.upper()})' if distro else 'LINUX',
        'darwin': 'MACOS'
    }.get(sistema, 'DESCONOCIDO')
    
    origen_texto = {
        'local': 'MISMO DIRECTORIO',
        'fija': '/HOME/USUARIO/XONINAS',
        'actual': 'DIRECTORIO ACTUAL',
        'ninguna': 'NO ENCONTRADO'
    }.get(origen, 'DESCONOCIDO')
    
    banner = f"""
{Colors.PURPLE}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║                    XONINAS 2026 v4.2.0                    ║
║              NAS Local con Carpetas Protegidas              ║
║                                                            ║
║               Sistema detectado: {sistema_texto:<27} ║
║               Origen xoninas.py: {origen_texto:<27} ║
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
REQUISITOS = [
    ('flask', 'flask==2.3.3'),
    ('werkzeug', 'werkzeug==2.3.0'),
    ('waitress', 'waitress==2.1.2'),
    ('requests', 'requests==2.31.0')
]

def check_dependency(modulo):
    try:
        __import__(modulo)
        return True
    except ImportError:
        return False

def install_dependency(paquete):
    """Instala una dependencia usando pip con los flags adecuados"""
    flags = get_install_flags()
    try:
        cmd = get_pip_command() + ['install', paquete] + flags
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except:
        try:
            cmd = get_pip_command() + ['install', paquete]
            subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            print(f"{Colors.RED}Error instalando {paquete}: {e}{Colors.END}")
            return False

def check_and_install_dependencies():
    """Verifica e instala todas las dependencias necesarias"""
    print(f"\n{Colors.BOLD}📦 Verificando dependencias...{Colors.END}")
    
    missing = []
    for modulo, paquete in REQUISITOS:
        if check_dependency(modulo):
            print(f"{Colors.GREEN}  ✓ {modulo} disponible{Colors.END}")
        else:
            print(f"{Colors.YELLOW}  ✗ {modulo} (faltante){Colors.END}")
            missing.append(paquete)
    
    if missing:
        print(f"\n{Colors.YELLOW}⚠️ Faltan {len(missing)} dependencias.{Colors.END}")
        respuesta = input("¿Deseas instalarlas automáticamente? (s/n): ")
        if respuesta.lower() == 's':
            success = True
            for paquete in missing:
                if not install_dependency(paquete):
                    success = False
            if success:
                print(f"{Colors.GREEN}✅ Todas las dependencias instaladas correctamente.{Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠️ Algunas dependencias no se instalaron. El programa podría fallar.{Colors.END}")
        else:
            print(f"{Colors.YELLOW}No se instalarán las dependencias. El programa podría fallar.{Colors.END}")
    
    return True

# ============================================================================
# Cloudflare Tunnel
# ============================================================================
def check_cloudflared():
    return shutil.which('cloudflared') is not None

def install_cloudflared():
    """Instala cloudflared según el sistema operativo"""
    sistema = get_system()
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
        distro = get_linux_distro()
        if distro == 'debian-based':
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
                return install_cloudflared_binary()
        elif distro == 'arch-based':
            try:
                subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'cloudflared'], check=True)
                print(f"{Colors.GREEN}  cloudflared instalado vía pacman{Colors.END}")
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
    script_dir = get_script_dir()
    print(f"  Descargando binario cloudflared...")
    if sistema == 'linux':
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        dest = os.path.join(script_dir, 'cloudflared')
    elif sistema == 'darwin':
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64"
        dest = os.path.join(script_dir, 'cloudflared')
    else:
        return False
    try:
        import urllib.request
        urllib.request.urlretrieve(url, dest)
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
            print(f"{Colors.YELLOW}No se pudo detectar la URL del túnel. Revisa la salida arriba.{Colors.END}")
        return process
    except Exception as e:
        print(f"{Colors.RED}Error al iniciar cloudflared: {e}{Colors.END}")
        return None

# ============================================================================
# Configuración inicial (ruta y clave maestra)
# ============================================================================
def run_initial_setup():
    """Ejecuta la configuración inicial si no existe master.csv o config.csv"""
    xoninas_dir = get_xoninas_dir()
    
    # Cambiar al directorio de xoninas.py
    if xoninas_dir:
        os.chdir(xoninas_dir)
        print(f"{Colors.GREEN}✓ Cambiando al directorio: {xoninas_dir}{Colors.END}")
    
    # Verificar si ya existe configuración
    if os.path.exists('config.csv') and os.path.exists('master.csv'):
        return True
    
    print("\n" + "="*60)
    print("   CONFIGURACIÓN INICIAL DE XONINAS")
    print("="*60)
    
    # Configurar ruta de almacenamiento si no existe
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
    
    # Configurar clave maestra si no existe
    if not os.path.exists('master.csv'):
        print("\n" + "="*50)
        print("    CONFIGURACIÓN DE CLAVE MAESTRA")
        print("="*50)
        pwd = input("Clave maestra: ").strip()
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

def run_server(cloudflare_enabled=False):
    """Ejecuta el servidor con autoreinicio"""
    xoninas_dir = get_xoninas_dir()
    
    print(f"\n{Colors.BOLD}🚀 Iniciando servidor XONINAS (Waitress)...{Colors.END}")
    print(f"  Directorio: {xoninas_dir}")
    print(f"  Threads: 6")
    print(f"  Puerto: 5000")
    print(f"  Healthcheck: /health cada 10 segundos")
    print(f"  Autoreinicio: activado")
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
    
    # Iniciar túnel si se solicita
    if cloudflare_enabled:
        cloudflare_process = run_cloudflare_tunnel(5000)
    
    while True:
        if process is None or process.poll() is not None:
            restart_count += 1
            print(f"{Colors.CYAN}[INFO] Lanzando servidor (intento #{restart_count})...{Colors.END}")
            process = subprocess.Popen(cmd, cwd=xoninas_dir)
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
# Función principal
# ============================================================================
def mostrar_ayuda():
    ayuda = f"""
{Colors.BOLD}USO DE XONINAS:{Colors.END}

  python start.py

{Colors.BOLD}DESCRIPCIÓN:{Colors.END}

  XONINAS es un servidor NAS local que permite:
  - Crear carpetas con o sin contraseña
  - Subir, descargar y eliminar archivos
  - Acceso desde toda la red local
  - (Opcional) Acceso remoto mediante Cloudflare Tunnel

{Colors.BOLD}CONTROLES:{Colors.END}

  - Para detener el servidor: Ctrl+C
  - Acceso web: http://127.0.0.1:5000 (o la IP de tu equipo)

{Colors.BOLD}CONFIGURACIÓN:{Colors.END}

  - La primera ejecución te guiará paso a paso
  - Puedes elegir la ruta de almacenamiento
  - Puedes activar el túnel Cloudflare para acceso remoto
    """
    print(ayuda)

def main():
    # Limpiar pantalla
    if get_system() == 'windows':
        os.system('cls')
    else:
        os.system('clear')
    
    print_banner()
    
    # Verificar argumentos de ayuda
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', '/?']:
        mostrar_ayuda()
        if get_system() != 'windows':
            input(f"\n{Colors.YELLOW}Presiona Enter para salir...{Colors.END}")
        return
    
    sistema = get_system()
    distro = get_linux_distro()
    script_dir = get_script_dir()
    ruta_xoninas, origen = get_xoninas_path()
    xoninas_dir = get_xoninas_dir()
    
    print(f"{Colors.BOLD}Sistema operativo:{Colors.END} {sistema}")
    if distro:
        print(f"{Colors.BOLD}Distribución:{Colors.END} {distro}")
    print(f"{Colors.BOLD}Directorio de start.py:{Colors.END} {script_dir}")
    print(f"{Colors.BOLD}Origen de xoninas.py:{Colors.END} {origen}")
    print(f"{Colors.BOLD}Ruta de xoninas.py:{Colors.END} {ruta_xoninas}")
    
    # Crear directorio si es necesario (solo para ruta fija)
    if origen == 'ninguna' and not os.path.exists(xoninas_dir):
        print(f"\n{Colors.YELLOW}⚠️ El directorio {xoninas_dir} no existe. Creándolo...{Colors.END}")
        os.makedirs(xoninas_dir, exist_ok=True)
        print(f"{Colors.GREEN}✓ Directorio creado: {xoninas_dir}{Colors.END}")
    
    # Verificar Python
    if not check_python():
        print(f"\n{Colors.RED}❌ Python no está instalado o no está en el PATH.{Colors.END}")
        sys.exit(1)
    
    ver_py = subprocess.run(get_python_command() + ['--version'], capture_output=True, text=True).stdout.strip()
    print(f"{Colors.BOLD}Python:{Colors.END} {ver_py}")
    
    # Verificar pip e instalarlo si falta
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
    check_and_install_dependencies()
    
    # Verificar que existe xoninas.py
    if not os.path.exists(ruta_xoninas):
        print(f"\n{Colors.RED}❌ Error crítico: No se encuentra xoninas.py{Colors.END}")
        if origen == 'ninguna':
            print(f"   Puedes copiar xoninas.py a:")
            print(f"     - {script_dir} (donde está start.py)")
            print(f"     - O a {get_fixed_xoninas_dir()}")
        sys.exit(1)
    
    # Configuración inicial (primera ejecución)
    if not run_initial_setup():
        # Si run_initial_setup devuelve False, significa que se configuró y hay que salir
        sys.exit(0)
    
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
    
    # Iniciar servidor
    try:
        run_server(cloudflare_enabled)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Servidor detenido por el usuario{Colors.END}")
        sys.exit(0)
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
