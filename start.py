#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS - Lanzador Universal con autoreinicio
Sistema NAS Local con Carpetas Protegidas

Este script:
- Detecta el sistema operativo y distribución
- Instala pip si no existe (Linux con gestor de paquetes)
- Instala las dependencias (Flask, Werkzeug, Waitress, requests)
- Ejecuta la configuración inicial (clave maestra)
- Inicia el servidor con autoreinicio y healthcheck

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

# ============================================================================
# Colores para terminal (con detección automática)
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
    """Detecta la distribución de Linux (para instalar pip correctamente)"""
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
        # Fallback por comandos
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
    """Devuelve el comando Python correcto (python3 en Linux/Mac, python en Windows)"""
    if get_system() == 'windows':
        return ['python']
    else:
        try:
            subprocess.run(['python3', '--version'], capture_output=True, check=True)
            return ['python3']
        except:
            return ['python']

def get_pip_command():
    """Devuelve el comando pip correcto usando -m pip"""
    return [sys.executable, '-m', 'pip']

def get_install_flags():
    """Devuelve los flags apropiados para pip según el sistema y distribución"""
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
    # Windows no necesita flags especiales
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
# Verificación e instalación de Python y pip
# ============================================================================
def check_python():
    """Verifica que Python esté instalado y accesible"""
    try:
        cmd = get_python_command() + ['--version']
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except:
        return False

def check_pip():
    """Verifica que pip esté instalado y funcione"""
    try:
        cmd = get_pip_command() + ['--version']
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except:
        return False

def install_pip_linux():
    """Instala pip en Linux usando el gestor de paquetes de la distribución"""
    distro = get_linux_distro()
    print(f"{Colors.YELLOW}Instalando pip en Linux ({distro})...{Colors.END}")
    
    if distro == 'debian-based':
        try:
            subprocess.run(['sudo', 'apt', 'update'], check=False)
            subprocess.run(['sudo', 'apt', 'install', '-y', 'python3-pip'], check=True)
            print(f"{Colors.GREEN}Pip instalado correctamente{Colors.END}")
            return True
        except:
            print(f"{Colors.RED}Error instalando pip con apt{Colors.END}")
            return False
    
    elif distro == 'arch-based':
        try:
            subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'python-pip'], check=True)
            print(f"{Colors.GREEN}Pip instalado correctamente{Colors.END}")
            return True
        except:
            print(f"{Colors.RED}Error instalando pip con pacman{Colors.END}")
            return False
    
    elif distro == 'fedora':
        try:
            subprocess.run(['sudo', 'dnf', 'install', '-y', 'python3-pip'], check=True)
            print(f"{Colors.GREEN}Pip instalado correctamente{Colors.END}")
            return True
        except:
            print(f"{Colors.RED}Error instalando pip con dnf{Colors.END}")
            return False
    
    elif distro == 'centos':
        try:
            subprocess.run(['sudo', 'yum', 'install', '-y', 'python3-pip'], check=True)
            print(f"{Colors.GREEN}Pip instalado correctamente{Colors.END}")
            return True
        except:
            print(f"{Colors.RED}Error instalando pip con yum{Colors.END}")
            return False
    
    elif distro == 'opensuse':
        try:
            subprocess.run(['sudo', 'zypper', 'install', '-y', 'python3-pip'], check=True)
            print(f"{Colors.GREEN}Pip instalado correctamente{Colors.END}")
            return True
        except:
            print(f"{Colors.RED}Error instalando pip con zypper{Colors.END}")
            return False
    
    else:
        print(f"{Colors.RED}No se pudo detectar el gestor de paquetes. Instala pip manualmente.{Colors.END}")
        print("  Para Debian/Ubuntu: sudo apt install python3-pip")
        print("  Para Arch: sudo pacman -S python-pip")
        print("  Para Fedora: sudo dnf install python3-pip")
        return False

def install_pip_windows():
    """Instala pip en Windows usando ensurepip o get-pip.py"""
    print(f"{Colors.YELLOW}Instalando pip en Windows...{Colors.END}")
    try:
        # Primero intentar con ensurepip
        subprocess.run([sys.executable, '-m', 'ensurepip', '--upgrade'], check=True)
        print(f"{Colors.GREEN}Pip instalado correctamente (ensurepip){Colors.END}")
        return True
    except:
        try:
            # Descargar get-pip.py
            import urllib.request
            print("  Descargando get-pip.py...")
            urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')
            subprocess.run([sys.executable, 'get-pip.py'], check=True)
            os.remove('get-pip.py')
            print(f"{Colors.GREEN}Pip instalado correctamente (get-pip.py){Colors.END}")
            return True
        except Exception as e:
            print(f"{Colors.RED}Error instalando pip: {e}{Colors.END}")
            return False

# ============================================================================
# Gestión de dependencias
# ============================================================================
REQUISITOS = [
    'flask==2.3.3',
    'werkzeug==2.3.0',
    'waitress==2.1.2',
    'requests==2.31.0'
]

def check_dependencies():
    """Verifica qué dependencias faltan"""
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
    """Instala las dependencias faltantes usando pip con los flags correctos"""
    if not missing:
        return True
    
    print(f"\n{Colors.BOLD}Instalando dependencias faltantes...{Colors.END}")
    pip_cmd = get_pip_command()
    flags = get_install_flags()
    
    if flags:
        print(f"{Colors.CYAN}Usando flags: {' '.join(flags)}{Colors.END}")
    
    success = True
    for req in missing:
        print(f"  Instalando {req}...")
        try:
            cmd = pip_cmd + ['install', req] + flags
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"{Colors.GREEN}    ✓ {req} instalado{Colors.END}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}    ✗ Error instalando {req}{Colors.END}")
            # Intentar sin flags (último recurso)
            try:
                cmd2 = pip_cmd + ['install', req]
                subprocess.run(cmd2, check=True)
                print(f"{Colors.GREEN}    ✓ {req} instalado (sin flags){Colors.END}")
            except:
                success = False
    
    if success:
        print(f"{Colors.GREEN}✅ Todas las dependencias instaladas correctamente.{Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️ Algunas dependencias no se instalaron. Puedes instalarlas manualmente:{Colors.END}")
        print(f"   {get_pip_command()} install {' '.join(missing)} {' '.join(flags)}")
    
    return success

# ============================================================================
# Configuración inicial (clave maestra)
# ============================================================================
def run_initial_config():
    """Ejecuta xoninas.py para crear master.csv si no existe"""
    if not os.path.exists('master.csv'):
        print(f"\n{Colors.YELLOW}⚠️  No se encontró clave maestra. Ejecutando configuración inicial...{Colors.END}")
        print(f"{Colors.CYAN}   Sigue las instrucciones para establecer la clave maestra del NAS.{Colors.END}\n")
        
        try:
            subprocess.run([sys.executable, 'xoninas.py'], check=True)
        except subprocess.CalledProcessError:
            print(f"{Colors.RED}Error durante la configuración inicial{Colors.END}")
            sys.exit(1)
        
        print(f"\n{Colors.GREEN}✅ Clave maestra guardada correctamente.{Colors.END}")
        print(f"{Colors.YELLOW}▶️  Vuelve a ejecutar 'python3 start.py' para iniciar el servidor NAS.{Colors.END}")
        sys.exit(0)

# ============================================================================
# Autoreinicio y healthcheck
# ============================================================================
def is_server_alive(port=5000):
    """Verifica si el servidor responde en /health"""
    try:
        import requests
        r = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
        return r.status_code == 200
    except:
        return False

def cleanup_port(port=5000):
    """Limpia el puerto si está en uso (Linux/macOS)"""
    if get_system() == 'windows':
        return
    try:
        result = subprocess.run(f"lsof -ti:{port}", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                print(f"{Colors.YELLOW}  Deteniendo proceso PID {pid} en puerto {port}{Colors.END}")
                os.kill(int(pid), signal.SIGTERM)
            time.sleep(2)
    except:
        pass

def run_server():
    """Ejecuta el servidor con autoreinicio"""
    print(f"\n{Colors.BOLD}🚀 Iniciando servidor XONINAS (Waitress)...{Colors.END}")
    print(f"  Threads: 6")
    print(f"  Puerto: 5000")
    print(f"  Healthcheck: /health cada 10 segundos")
    print(f"  Autoreinicio: activado")
    print(f"{Colors.YELLOW}  Para detener: Ctrl+C{Colors.END}")
    print("-" * 60)

    cleanup_port(5000)

    cmd = [
        sys.executable, '-m', 'waitress',
        '--host=127.0.0.1',
        '--port=5000',
        '--threads=6',
        '--connection-limit=100',
        '--channel-timeout=300',
        'xoninas:app'
    ]

    process = None
    restart_count = 0
    
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
# Función principal
# ============================================================================
def main():
    # Limpiar pantalla
    os.system('clear' if get_system() != 'windows' else 'cls')
    
    # Banner
    print_banner()
    
    # Mostrar información del sistema
    sistema = get_system()
    distro = get_linux_distro()
    print(f"{Colors.BOLD}Sistema operativo:{Colors.END} {sistema}")
    if distro:
        print(f"{Colors.BOLD}Distribución:{Colors.END} {distro}")
    print(f"{Colors.BOLD}Python:{Colors.END} {sys.version.split()[0]}")
    print(f"{Colors.BOLD}Directorio:{Colors.END} {os.getcwd()}")
    
    # Verificar que existe xoninas.py
    if not os.path.exists('xoninas.py'):
        print(f"\n{Colors.RED}❌ Error: No se encuentra xoninas.py{Colors.END}")
        print("   Asegúrate de que xoninas.py está en la misma carpeta.")
        sys.exit(1)
    
    # Verificar Python
    if not check_python():
        print(f"\n{Colors.RED}❌ Python no está instalado o no está en el PATH{Colors.END}")
        print("   Descarga Python desde: https://www.python.org/downloads/")
        if sistema == 'windows':
            print("   IMPORTANTE: Marca 'Add Python to PATH' durante la instalación.")
        sys.exit(1)
    
    # Verificar pip e instalarlo si falta
    if not check_pip():
        print(f"\n{Colors.YELLOW}⚠️ Pip no está instalado. Intentando instalarlo...{Colors.END}")
        if sistema == 'linux':
            if not install_pip_linux():
                print(f"{Colors.RED}No se pudo instalar pip automáticamente.{Colors.END}")
                print("   Instala pip manualmente según tu distribución y vuelve a ejecutar.")
                sys.exit(1)
        elif sistema == 'windows':
            if not install_pip_windows():
                print(f"{Colors.RED}No se pudo instalar pip automáticamente.{Colors.END}")
                print("   Ejecuta el script como administrador o instala pip manualmente.")
                sys.exit(1)
        elif sistema == 'darwin':
            print(f"{Colors.YELLOW}En macOS, instala pip con: python3 -m ensurepip --upgrade{Colors.END}")
            respuesta = input("¿Intentar instalarlo ahora? (s/n): ")
            if respuesta.lower() == 's':
                try:
                    subprocess.run([sys.executable, '-m', 'ensurepip', '--upgrade'], check=True)
                    print(f"{Colors.GREEN}Pip instalado correctamente{Colors.END}")
                except:
                    print(f"{Colors.RED}Error instalando pip. Instálalo manualmente con: brew install python3{Colors.END}")
                    sys.exit(1)
            else:
                print("No se puede continuar sin pip. Saliendo.")
                sys.exit(1)
    
    # Verificar dependencias
    missing = check_dependencies()
    if missing:
        print(f"\n{Colors.YELLOW}⚠️ Faltan {len(missing)} dependencias.{Colors.END}")
        respuesta = input("¿Deseas instalarlas automáticamente? (s/n): ")
        if respuesta.lower() == 's':
            if not install_dependencies(missing):
                print(f"{Colors.YELLOW}Continuando a pesar de errores...{Colors.END}")
        else:
            print(f"{Colors.YELLOW}No se instalarán las dependencias. El programa podría fallar.{Colors.END}")
            print("   Puedes instalarlas manualmente con:")
            print(f"   {get_pip_command()} install {' '.join(REQUISITOS)} {' '.join(get_install_flags())}")
    
    # Configuración inicial (clave maestra)
    run_initial_config()
    
    # Iniciar servidor
    try:
        run_server()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Servidor detenido por el usuario{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}❌ Error inesperado: {e}{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    main()
