#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS 2026 v4.2.0 - NAS Local con Carpetas Protegidas y Soporte de Impresión
Soporte para subida multiple, subcarpetas, QR, IP y autoapertura del navegador
Soporte para impresión remota (puente entre dispositivos e impresora)

Desarrollado por: Darian Alberto Camacho Salas
Organizacion: XONIDU
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
import time
import sys
import zipfile
import tempfile
import mimetypes
import subprocess
import platform
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, send_file

# Intentar importar qrcode
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Archivos de configuracion
MASTER_CSV = 'master.csv'
FOLDERS_CSV = 'folders.csv'
CONFIG_CSV = 'config.csv'
PRINTERS_CSV = 'printers.csv'
PRINT_QUEUE_DIR = 'print_queue'

STORAGE_PATH = os.environ.get('STORAGE_FOLDER', None)
TUNNEL_URL = os.environ.get('TUNNEL_URL', None)

# Crear directorio de cola de impresión
Path(PRINT_QUEUE_DIR).mkdir(parents=True, exist_ok=True)

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

# ============================================================================
# Funciones de utilidad
# ============================================================================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"

def get_all_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith('127.'):
                ips.append(ip)
    except:
        pass
    if '127.0.0.1' not in ips:
        ips.append('127.0.0.1')
    main_ip = get_local_ip()
    if main_ip not in ips and not main_ip.startswith('127.'):
        ips.insert(0, main_ip)
    return ips

def generate_qr_code(url):
    if not QR_AVAILABLE:
        return None
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                           box_size=2, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        return qr
    except:
        return None

def print_qr_in_terminal(url):
    if not QR_AVAILABLE:
        print(f"{Colors.YELLOW}  (Instala 'qrcode' para ver el QR: pip install qrcode[pil]){Colors.END}")
        return False
    try:
        qr = generate_qr_code(url)
        if qr:
            print(f"{Colors.CYAN}")
            for row in range(qr.modules_count):
                line = ""
                for col in range(qr.modules_count):
                    line += "██" if qr.modules[row][col] else "  "
                print(line)
            print(f"{Colors.END}")
            return True
    except:
        print(f"{Colors.YELLOW}  No se pudo generar el QR en esta terminal{Colors.END}")
    return False

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def verify_password(pwd, hash_val):
    return hash_password(pwd) == hash_val

def init_storage_path():
    global STORAGE_PATH
    if STORAGE_PATH:
        app.config['STORAGE_FOLDER'] = STORAGE_PATH
        Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)
        return True
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
    Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    return False

def init_master():
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

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"

def get_folder_size(folder_path):
    total = 0
    for item in Path(folder_path).rglob('*'):
        if item.is_file():
            total += item.stat().st_size
    return total

def zip_folder(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(extract_to)

def secure_filename(filename):
    filename = filename.replace('/', '_').replace('\\', '_')
    filename = filename.replace(':', '_').replace('?', '_')
    filename = filename.replace('*', '_').replace('|', '_')
    filename = filename.replace('"', '_').replace('<', '_').replace('>', '_')
    return filename

def get_file_icon(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
        return '🖼️'
    elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']:
        return '🎬'
    elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma']:
        return '🎵'
    elif ext in ['.pdf']:
        return '📄'
    elif ext in ['.doc', '.docx']:
        return '📝'
    elif ext in ['.xls', '.xlsx']:
        return '📊'
    elif ext in ['.ppt', '.pptx']:
        return '📑'
    elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
        return '📦'
    else:
        return '📎'

# ============================================================================
# Funciones de impresión
# ============================================================================
def get_system_printers():
    """Obtiene lista de impresoras disponibles en el sistema"""
    printers = []
    sistema = platform.system()
    
    try:
        if sistema == 'Windows':
            result = subprocess.run(
                ['wmic', 'printer', 'get', 'name,default'],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            printers.append({
                                'name': ' '.join(parts[:-1]) if len(parts) > 1 else parts[0],
                                'default': 'TRUE' in line if 'TRUE' in line else False
                            })
        else:
            # Linux/macOS: usar lpstat
            result = subprocess.run(
                ['lpstat', '-p', '-d'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'printer' in line and 'enabled' in line:
                        name = line.split(' ')[1] if len(line.split(' ')) > 1 else line
                        printers.append({
                            'name': name.strip(),
                            'default': 'default' in line
                        })
    except Exception as e:
        print(f"Error obteniendo impresoras: {e}")
    
    return printers

def load_printers():
    """Carga la lista de impresoras desde CSV o del sistema"""
    if not os.path.exists(PRINTERS_CSV):
        printers = get_system_printers()
        if printers:
            with open(PRINTERS_CSV, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'default'])
                writer.writeheader()
                for p in printers:
                    writer.writerow({'name': p['name'], 'default': str(p.get('default', False))})
        return printers
    
    with open(PRINTERS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        return [{'name': row['name'], 'default': row.get('default', 'False') == 'True'} for row in reader]

def refresh_printers():
    """Actualiza la lista de impresoras desde el sistema"""
    printers = get_system_printers()
    if printers:
        with open(PRINTERS_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'default'])
            writer.writeheader()
            for p in printers:
                writer.writerow({'name': p['name'], 'default': str(p.get('default', False))})
    return printers

def print_file(file_path, printer_name=None):
    """Envía un archivo a la impresora"""
    sistema = platform.system()
    
    try:
        if not os.path.exists(file_path):
            return False, "Archivo no encontrado"
        
        if sistema == 'Windows':
            if printer_name:
                cmd = ['print', '/D:' + printer_name, file_path]
            else:
                cmd = ['print', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        else:
            cmd = ['lp']
            if printer_name:
                cmd.extend(['-d', printer_name])
            cmd.append(file_path)
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, result.stdout or "Impresión enviada correctamente"
        else:
            return False, result.stderr or "Error al imprimir"
            
    except Exception as e:
        return False, str(e)

def print_text(text, printer_name=None):
    """Imprime texto directamente"""
    sistema = platform.system()
    
    try:
        if sistema == 'Windows':
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(text)
                temp_file = f.name
            if printer_name:
                cmd = ['print', '/D:' + printer_name, temp_file]
            else:
                cmd = ['print', temp_file]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            os.unlink(temp_file)
        else:
            cmd = ['lp']
            if printer_name:
                cmd.extend(['-d', printer_name])
            result = subprocess.run(cmd, input=text, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, result.stdout or "Texto impreso correctamente"
        else:
            return False, result.stderr or "Error al imprimir"
            
    except Exception as e:
        return False, str(e)

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
    return redirect(url_for('index'))

@app.route('/')
def index():
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    folders = load_folders()
    return render_template('index.html', folders=folders, storage_path=app.config.get('STORAGE_FOLDER', ''))

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
    folders = []
    for item in folder_path.iterdir():
        if item.is_file():
            s = item.stat()
            files.append({
                'name': item.name,
                'size': s.st_size,
                'size_formatted': format_size(s.st_size),
                'modified': datetime.fromtimestamp(s.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'icon': get_file_icon(item.name)
            })
        elif item.is_dir():
            folder_size = get_folder_size(item)
            folders.append({
                'name': item.name,
                'size': folder_size,
                'size_formatted': format_size(folder_size),
                'modified': datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'is_subfolder': True
            })
    
    files.sort(key=lambda x: x['name'].lower())
    folders.sort(key=lambda x: x['name'].lower())
    
    return render_template('folder_contents.html', 
                          folder_name=folder_name, 
                          files=files, 
                          folders=folders)

@app.route('/upload/<folder_name>', methods=['POST'])
def upload_file(folder_name):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    if not folder_allowed(folder_name):
        return redirect(url_for('folder_auth', folder_name=folder_name))
    
    folder_path = Path(app.config['STORAGE_FOLDER']) / folder_name
    
    if 'files' in request.files:
        uploaded_files = request.files.getlist('files')
        for file in uploaded_files:
            if file and file.filename:
                filename = secure_filename(file.filename.replace(' ', '_'))
                file.save(folder_path / filename)
    
    if 'folder_zip' in request.files:
        zip_file = request.files['folder_zip']
        if zip_file and zip_file.filename:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                zip_file.save(tmp.name)
                tmp_path = tmp.name
            try:
                extract_zip(tmp_path, folder_path)
                os.unlink(tmp_path)
            except Exception as e:
                print(f"Error extrayendo ZIP: {e}")
    
    return redirect(url_for('folder_contents', folder_name=folder_name))

@app.route('/create_subfolder/<folder_name>', methods=['POST'])
def create_subfolder(folder_name):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    if not folder_allowed(folder_name):
        return redirect(url_for('folder_auth', folder_name=folder_name))
    
    subfolder_name = request.form.get('subfolder_name', '').strip()
    if not subfolder_name:
        return redirect(url_for('folder_contents', folder_name=folder_name))
    
    safe_name = subfolder_name.replace(' ', '_')
    if any(c in safe_name for c in '/\\?%*:|"<>'):
        return redirect(url_for('folder_contents', folder_name=folder_name))
    
    folder_path = Path(app.config['STORAGE_FOLDER']) / folder_name / safe_name
    folder_path.mkdir(parents=True, exist_ok=True)
    
    return redirect(url_for('folder_contents', folder_name=folder_name))

@app.route('/delete_subfolder/<folder_name>/<subfolder_name>')
def delete_subfolder(folder_name, subfolder_name):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    if not folder_allowed(folder_name):
        return redirect(url_for('folder_auth', folder_name=folder_name))
    
    folder_path = Path(app.config['STORAGE_FOLDER']) / folder_name / subfolder_name
    if folder_path.exists() and folder_path.is_dir():
        shutil.rmtree(folder_path)
    
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

@app.route('/download_folder/<folder_name>')
def download_folder_as_zip(folder_name):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    if not folder_allowed(folder_name):
        return redirect(url_for('folder_auth', folder_name=folder_name))
    
    folder_path = Path(app.config['STORAGE_FOLDER']) / folder_name
    if not folder_path.exists():
        return "Carpeta no encontrada", 404
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
        zip_path = tmp.name
    
    zip_folder(folder_path, zip_path)
    
    return send_file(zip_path, as_attachment=True, download_name=f"{folder_name}.zip")

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

# ============================================================================
# RUTAS DE IMPRESIÓN
# ============================================================================
@app.route('/print')
def print_page():
    """Página de impresión remota"""
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    printers = load_printers()
    return render_template('print.html', printers=printers)

@app.route('/print/refresh')
def print_refresh():
    """Actualiza la lista de impresoras y redirige a print"""
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    refresh_printers()
    return redirect(url_for('print_page'))

@app.route('/print/file', methods=['POST'])
def print_file_route():
    """Imprime un archivo desde el NAS"""
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    
    folder_name = request.form.get('folder_name')
    filename = request.form.get('filename')
    printer_name = request.form.get('printer_name', '')
    
    if not folder_name or not filename:
        return "Faltan parámetros", 400
    
    if not folder_allowed(folder_name):
        return "Sin acceso a la carpeta", 403
    
    file_path = Path(app.config['STORAGE_FOLDER']) / folder_name / filename
    if not file_path.exists():
        return "Archivo no encontrado", 404
    
    # Verificar formato imprimible
    ext = os.path.splitext(filename)[1].lower()
    print_extensions = ['.pdf', '.txt', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp']
    if ext not in print_extensions:
        return f"Formato no imprimible: {ext}", 400
    
    success, message = print_file(str(file_path), printer_name if printer_name else None)
    
    if success:
        return render_template('print_result.html', success=True, message=message)
    else:
        return render_template('print_result.html', success=False, error=message)

@app.route('/print/text', methods=['POST'])
def print_text_route():
    """Imprime texto directamente"""
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    
    text = request.form.get('text', '')
    printer_name = request.form.get('printer_name', '')
    
    if not text:
        return "Texto vacío", 400
    
    success, message = print_text(text, printer_name if printer_name else None)
    
    if success:
        return render_template('print_result.html', success=True, message=message)
    else:
        return render_template('print_result.html', success=False, error=message)

@app.route('/print/upload', methods=['POST'])
def print_upload_route():
    """Sube un archivo y lo imprime"""
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    
    if 'file' not in request.files:
        return "No hay archivo", 400
    
    file = request.files['file']
    printer_name = request.form.get('printer_name', '')
    
    if file.filename == '':
        return "Nombre de archivo vacío", 400
    
    # Guardar en cola de impresión
    filename = secure_filename(file.filename.replace(' ', '_'))
    queue_path = Path(PRINT_QUEUE_DIR) / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
    file.save(queue_path)
    
    # Intentar imprimir
    success, message = print_file(str(queue_path), printer_name if printer_name else None)
    
    # Eliminar después de intentar imprimir (o mantener para debug)
    try:
        os.unlink(queue_path)
    except:
        pass
    
    if success:
        return render_template('print_result.html', success=True, message=message)
    else:
        return render_template('print_result.html', success=False, error=message)

# ============================================================================
# Inicio con informacion completa
# ============================================================================
def print_startup_info():
    print()
    print(f"{Colors.PURPLE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}XONINAS NAS INICIADO (con soporte de impresión){Colors.END}")
    print(f"{Colors.PURPLE}{'='*60}{Colors.END}")
    
    print(f"\n{Colors.CYAN}Almacenamiento:{Colors.END} {app.config['STORAGE_FOLDER']}")
    
    ips = get_all_ips()
    print(f"\n{Colors.BOLD}Acceso en red local:{Colors.END}")
    qr_url = None
    for ip in ips:
        if ip.startswith('127.'):
            local_url = f"http://{ip}:5000"
            print(f"   {Colors.GREEN}{local_url}{Colors.END} (este equipo)")
        else:
            local_url = f"http://{ip}:5000"
            print(f"   {Colors.GREEN}{local_url}{Colors.END}")
            if qr_url is None:
                qr_url = local_url
    
    if TUNNEL_URL:
        print(f"\n{Colors.BOLD}Tunel Cloudflare (acceso remoto):{Colors.END}")
        print(f"   {Colors.GREEN}{TUNNEL_URL}{Colors.END}")
        if qr_url is None:
            qr_url = TUNNEL_URL
    
    # Mostrar impresoras
    printers = load_printers()
    print(f"\n{Colors.BOLD}🖨️ Impresoras disponibles:{Colors.END}")
    if printers:
        for p in printers[:5]:
            print(f"   {Colors.GREEN}• {p['name']}{Colors.END}{' (por defecto)' if p.get('default') else ''}")
        if len(printers) > 5:
            print(f"   {Colors.YELLOW}... y {len(printers) - 5} más{Colors.END}")
    else:
        print(f"   {Colors.YELLOW}No se detectaron impresoras{Colors.END}")
        print(f"   {Colors.YELLOW}Usa /print/refresh para buscar impresoras{Colors.END}")
    
    if qr_url:
        print(f"\n{Colors.BOLD}Codigo QR para escanear:{Colors.END}")
        print_qr_in_terminal(qr_url)
        print(f"{Colors.YELLOW}   Escanea con tu movil para acceder automaticamente{Colors.END}")
    
    print(f"\n{Colors.BOLD}Subida multiple:{Colors.END} Puedes seleccionar varios archivos a la vez")
    print(f"{Colors.BOLD}Subida de carpetas:{Colors.END} Arrastra carpetas completas (se suben como ZIP)")
    print(f"{Colors.BOLD}Impresión remota:{Colors.END} Envía archivos a la impresora desde cualquier dispositivo")
    print(f"{Colors.BOLD}Clave por defecto:{Colors.END} admin (si no la cambiaste)")
    print(f"{Colors.BOLD}Para detener:{Colors.END} Ctrl+C")
    print(f"{Colors.PURPLE}{'='*60}{Colors.END}\n")

def open_browser():
    try:
        ip = get_local_ip()
        if ip.startswith('127.'):
            url = "http://localhost:5000"
        else:
            url = f"http://{ip}:5000"
        webbrowser.open(url)
        print(f"{Colors.GREEN}Navegador abierto en {url}{Colors.END}")
    except:
        pass

# ============================================================================
# Ejecucion principal
# ============================================================================
if __name__ == '__main__':
    init_storage_path()
    
    if not init_master():
        print(f"{Colors.RED}Configuracion incompleta. Ejecuta start.py primero.{Colors.END}")
        sys.exit(1)
    
    print_startup_info()
    
    threading.Timer(2.0, open_browser).start()
    
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000, threads=6)
    except ImportError:
        app.run(host='0.0.0.0', port=5000, debug=False)