#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS 2026 v4.2.0 - NAS Local con Carpetas Protegidas
Sistema NAS con acceso en red local, QR y auto-apertura del navegador

Desarrollado por: Darian Alberto Camacho Salas
Organización: XONIDU
#Somos XONIDU
"""

import os
import csv
import hashlib
import secrets
import shutil
import socket
import webbrowser
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, send_file

# Intentar importar qrcode (opcional, para mostrar QR)
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10 GB
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400

# Archivos de configuración
MASTER_CSV = 'master.csv'
FOLDERS_CSV = 'folders.csv'
CONFIG_CSV = 'config.csv'

# Variable global para la ruta de almacenamiento
STORAGE_PATH = None

# ============================================================================
# Funciones de utilidad
# ============================================================================
def get_local_ip():
    """Obtiene la IP local de la máquina en la red"""
    try:
        # Crear un socket para determinar la IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        # Fallback: obtener IP de hostname
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"

def get_all_ips():
    """Obtiene todas las IPs locales disponibles"""
    ips = []
    try:
        hostname = socket.gethostname()
        # Obtener todas las IPs del hostname
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith('127.'):
                ips.append(ip)
    except:
        pass
    
    # Añadir localhost
    if '127.0.0.1' not in ips:
        ips.append('127.0.0.1')
    
    # Añadir la IP principal
    main_ip = get_local_ip()
    if main_ip not in ips and not main_ip.startswith('127.'):
        ips.insert(0, main_ip)
    
    return ips

def generate_qr_code(url):
    """Genera un código QR a partir de una URL"""
    if not QR_AVAILABLE:
        return None
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=2,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        return qr
    except Exception as e:
        print(f"Error generando QR: {e}")
        return None

def print_qr_in_terminal(url):
    """Intenta mostrar el QR en la terminal (compatible con Linux/Mac)"""
    if not QR_AVAILABLE:
        return
    
    try:
        qr = generate_qr_code(url)
        if qr:
            # Convertir QR a ASCII
            qr_blocks = []
            for row in range(qr.modules_count):
                line = ""
                for col in range(qr.modules_count):
                    line += "█" * 2 if qr.modules[row][col] else "  "
                qr_blocks.append(line)
            
            # Mostrar QR en la terminal
            print(f"{Colors.CYAN}")
            for line in qr_blocks:
                print(line)
            print(f"{Colors.END}")
            return True
    except:
        pass
    return False

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def verify_password(pwd, hash_val):
    return hash_password(pwd) == hash_val

def init_storage_path():
    """Carga la ruta de almacenamiento desde config.csv"""
    global STORAGE_PATH
    
    if os.path.exists(CONFIG_CSV):
        with open(CONFIG_CSV, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0] == 'storage_path':
                    STORAGE_PATH = row[1]
                    break
        if STORAGE_PATH:
            STORAGE_PATH = str(Path(STORAGE_PATH).expanduser().resolve())
            Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)
            app.config['STORAGE_FOLDER'] = STORAGE_PATH
            return True
    
    STORAGE_PATH = str(Path('storage').resolve())
    app.config['STORAGE_FOLDER'] = STORAGE_PATH
    return False

def init_master():
    """Verifica si existe la clave maestra"""
    return os.path.exists(MASTER_CSV)

def load_folders():
    if not os.path.exists(FOLDERS_CSV):
        return []
    with open(FOLDERS_CSV, 'r') as f:
        return list(csv.DictReader(f))

def save_folder(name, pwd_hash):
    exists = os.path.exists(FOLDERS_CSV)
    with open(FOLDERS_CSV, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['name', 'password_hash', 'created'])
        if not exists:
            w.writeheader()
        w.writerow({
            'name': name,
            'password_hash': pwd_hash,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

def delete_folder_csv(name):
    folders = [f for f in load_folders() if f['name'] != name]
    with open(FOLDERS_CSV, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['name', 'password_hash', 'created'])
        w.writeheader()
        w.writerows(folders)

def get_folder_hash(name):
    for f in load_folders():
        if f['name'] == name:
            return f['password_hash'] if f['password_hash'] else None
    return None

def folder_allowed(name):
    h = get_folder_hash(name)
    if h is None:
        return True
    return session.get('folder_access', {}).get(name, False)

# ============================================================================
# Colores para terminal (en la consola)
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

# ============================================================================
# Rutas web
# ============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pwd = request.form.get('master_password', '')
        if not os.path.exists(MASTER_CSV):
            return "Error: master.csv no encontrado", 500
        with open(MASTER_CSV, 'r') as f:
            stored = f.read().strip()
        if verify_password(pwd, stored):
            session['master_authenticated'] = True
            session.permanent = True
            return redirect(url_for('index'))
        return render_template('login.html', error='Clave incorrecta')
    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    return render_template('index.html', folders=load_folders())

@app.route('/create_folder', methods=['POST'])
def create_folder():
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    name = request.form.get('folder_name', '').strip()
    pwd = request.form.get('folder_password', '').strip()
    if not name:
        return redirect(url_for('index'))
    safe = name.replace(' ', '_')
    if any(c in safe for c in '/\\?%*:|"<>'):
        return redirect(url_for('index'))
    if safe in [f['name'] for f in load_folders()]:
        return redirect(url_for('index'))
    folder_path = Path(app.config['STORAGE_FOLDER']) / safe
    folder_path.mkdir(parents=True, exist_ok=False)
    save_folder(safe, hash_password(pwd) if pwd else '')
    return redirect(url_for('index'))

@app.route('/delete_folder/<name>')
def delete_folder(name):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    folder_path = Path(app.config['STORAGE_FOLDER']) / name
    if folder_path.exists():
        shutil.rmtree(folder_path)
    delete_folder_csv(name)
    session.get('folder_access', {}).pop(name, None)
    return redirect(url_for('index'))

@app.route('/folder_auth/<name>', methods=['GET', 'POST'])
def folder_auth(name):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    h = get_folder_hash(name)
    if h is None:
        return redirect(url_for('folder_contents', folder_name=name))
    if request.method == 'POST':
        pwd = request.form.get('folder_password', '')
        if verify_password(pwd, h):
            session.setdefault('folder_access', {})[name] = True
            session.modified = True
            return redirect(url_for('folder_contents', folder_name=name))
        return render_template('folder_auth.html', folder_name=name, error='Contraseña incorrecta')
    return render_template('folder_auth.html', folder_name=name, error=None)

@app.route('/folder/<folder_name>')
def folder_contents(folder_name):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    if not folder_allowed(folder_name):
        return redirect(url_for('folder_auth', folder_name=folder_name))
    folder_path = Path(app.config['STORAGE_FOLDER']) / folder_name
    if not folder_path.exists():
        return "Carpeta no encontrada", 404
    files = []
    for item in folder_path.iterdir():
        if item.is_file():
            s = item.stat()
            files.append({
                'name': item.name,
                'size': s.st_size,
                'modified': datetime.fromtimestamp(s.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    files.sort(key=lambda x: x['name'])
    return render_template('folder_contents.html', folder_name=folder_name, files=files)

@app.route('/upload/<folder_name>', methods=['POST'])
def upload_file(folder_name):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    if not folder_allowed(folder_name):
        return redirect(url_for('folder_auth', folder_name=folder_name))
    f = request.files.get('file')
    if f and f.filename:
        filename = f.filename.replace(' ', '_')
        path = Path(app.config['STORAGE_FOLDER']) / folder_name / filename
        f.save(path)
    return redirect(url_for('folder_contents', folder_name=folder_name))

@app.route('/download/<folder_name>/<filename>')
def download_file(folder_name, filename):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    if not folder_allowed(folder_name):
        return redirect(url_for('folder_auth', folder_name=folder_name))
    path = Path(app.config['STORAGE_FOLDER']) / folder_name / filename
    if not path.exists():
        return "Archivo no encontrado", 404
    return send_file(path, as_attachment=True, download_name=filename)

@app.route('/delete_file/<folder_name>/<filename>')
def delete_file(folder_name, filename):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    if not folder_allowed(folder_name):
        return redirect(url_for('folder_auth', folder_name=folder_name))
    path = Path(app.config['STORAGE_FOLDER']) / folder_name / filename
    if path.exists():
        path.unlink()
    return redirect(url_for('folder_contents', folder_name=folder_name))

@app.route('/health')
def health():
    return "OK", 200

@app.route('/session_test')
def session_test():
    return str(dict(session))

# ============================================================================
# Inicio de la aplicación
# ============================================================================
def print_startup_info():
    """Muestra información de inicio con IPs y QR"""
    print(f"\n{Colors.PURPLE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}🚀 XONINAS NAS INICIADO{Colors.END}")
    print(f"{Colors.PURPLE}{'='*60}{Colors.END}")
    
    # Mostrar ruta de almacenamiento
    print(f"\n{Colors.CYAN}📁 Almacenamiento:{Colors.END} {app.config['STORAGE_FOLDER']}")
    
    # Mostrar todas las IPs disponibles
    ips = get_all_ips()
    print(f"\n{Colors.BOLD}🌐 Acceso en red local:{Colors.END}")
    for ip in ips:
        if ip.startswith('127.'):
            local_url = f"http://{ip}:5000"
            print(f"   • {Colors.GREEN}{local_url}{Colors.END} (este equipo)")
        else:
            local_url = f"http://{ip}:5000"
            print(f"   • {Colors.GREEN}{local_url}{Colors.END}")
            # Guardar la primera IP no-local para QR
            if not hasattr(print_startup_info, 'qr_url'):
                print_startup_info.qr_url = local_url
    
    # Mostrar QR (usar la primera IP válida)
    if hasattr(print_startup_info, 'qr_url') and QR_AVAILABLE:
        print(f"\n{Colors.BOLD}📱 Código QR para escanear:{Colors.END}")
        print_qr_in_terminal(print_startup_info.qr_url)
        print(f"{Colors.YELLOW}   Escanea con tu móvil para acceder automáticamente{Colors.END}")
    
    print(f"\n{Colors.BOLD}🔐 Clave por defecto:{Colors.END} admin (si no la cambiaste)")
    print(f"{Colors.BOLD}🛑 Para detener:{Colors.END} Ctrl+C")
    print(f"{Colors.PURPLE}{'='*60}{Colors.END}\n")

def open_browser_delayed():
    """Abre el navegador después de un pequeño retraso"""
    time.sleep(1.5)
    url = f"http://{get_local_ip()}:5000"
    if url.startswith('http://127.'):
        url = "http://localhost:5000"
    try:
        webbrowser.open(url)
        print(f"{Colors.GREEN}🌐 Navegador abierto en {url}{Colors.END}")
    except:
        print(f"{Colors.YELLOW}⚠️ No se pudo abrir el navegador automáticamente. Ve a {url}{Colors.END}")

if __name__ == '__main__':
    import time
    
    # Inicializar ruta de almacenamiento
    init_storage_path()
    
    # Verificar configuración inicial
    if not init_master():
        print(f"\n{Colors.RED}❌ Configuración incompleta. Ejecuta start.py primero.{Colors.END}")
        print(f"{Colors.YELLOW}   El lanzador start.py se encargará de la configuración inicial.{Colors.END}")
        exit(1)
    
    # Mostrar información de inicio
    print_startup_info()
    
    # Abrir navegador automáticamente (en un hilo separado)
    browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
    browser_thread.start()
    
    # Iniciar servidor con Waitress (en red local 0.0.0.0)
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000, threads=6)
    except ImportError:
        print(f"{Colors.YELLOW}⚠️ Waitress no instalado. Usando servidor de desarrollo.{Colors.END}")
        app.run(host='0.0.0.0', port=5000, debug=False)
