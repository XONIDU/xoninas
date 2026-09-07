#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS 2026 v4.2.0 - NAS Local con Carpetas Protegidas y Soporte de Impresión
Soporte para subida multiple, subcarpetas, QR, IP y autoapertura del navegador
Soporte para impresión remota con conversión a blanco y negro (Ghostscript principal)

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
import re
import io
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
CONVERT_DIR = 'convertidos'

STORAGE_PATH = os.environ.get('STORAGE_FOLDER', None)
TUNNEL_URL = os.environ.get('TUNNEL_URL', None)

# Crear directorios necesarios
Path(PRINT_QUEUE_DIR).mkdir(parents=True, exist_ok=True)
Path(CONVERT_DIR).mkdir(parents=True, exist_ok=True)

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
# FUNCIONES DE CONVERSIÓN A BLANCO Y NEGRO (Ghostscript como principal)
# ============================================================================

def check_ghostscript():
    """Verifica si Ghostscript está instalado"""
    return shutil.which('gs') is not None

def convert_pdf_to_grayscale_gs(input_path, output_path):
    """Método 1: Ghostscript (PRINCIPAL) - Más rápido y confiable"""
    if not check_ghostscript():
        return False, "Ghostscript no instalado. Ejecuta: sudo apt install ghostscript (o el gestor de tu distro)"
    
    try:
        cmd = [
            'gs', '-sDEVICE=pdfwrite',
            '-sColorConversionStrategy=Gray',
            '-dProcessColorModel=/DeviceGray',
            '-dCompatibilityLevel=1.4',
            '-dNOPAUSE', '-dQUIET', '-dBATCH',
            f'-sOutputFile={output_path}',
            input_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, "PDF convertido con Ghostscript"
        else:
            return False, f"Ghostscript error: {result.stderr[:200] if result.stderr else 'Error desconocido'}"
    except subprocess.TimeoutExpired:
        return False, "Tiempo de espera agotado (3 minutos)"
    except Exception as e:
        return False, f"Error: {str(e)}"

def convert_pdf_to_grayscale_fallback(input_path, output_path):
    """Método 2: PyMuPDF (fallback) - Si Ghostscript falla"""
    try:
        import fitz
        from PIL import Image
        import io
        
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            gray_img = img.convert('L')
            img_bytes = io.BytesIO()
            gray_img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=img_bytes.getvalue())
        
        new_doc.save(output_path)
        new_doc.close()
        doc.close()
        return True, "PDF convertido con PyMuPDF (fallback)"
    except ImportError:
        return False, "PyMuPDF no instalado (fallback no disponible)"
    except Exception as e:
        return False, f"Error en fallback: {str(e)[:100]}"

def convert_pdf_to_grayscale(input_path, output_path):
    """Convierte PDF a escala de grises - Ghostscript como principal"""
    print(f"{Colors.CYAN}🔄 Convirtiendo PDF a blanco y negro...{Colors.END}")
    
    # Primero intentar con Ghostscript (método principal)
    success, message = convert_pdf_to_grayscale_gs(input_path, output_path)
    if success:
        return True, message
    
    # Si falla, intentar con PyMuPDF (fallback)
    print(f"{Colors.YELLOW}  Ghostscript falló: {message}{Colors.END}")
    print(f"{Colors.YELLOW}  Intentando con PyMuPDF (fallback)...{Colors.END}")
    success, message = convert_pdf_to_grayscale_fallback(input_path, output_path)
    if success:
        return True, message
    
    return False, message

def convert_image_to_grayscale(input_path, output_path):
    """Convierte una imagen a escala de grises usando Pillow"""
    try:
        from PIL import Image
        img = Image.open(input_path)
        grayscale_img = img.convert('L')
        
        ext = os.path.splitext(output_path)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            grayscale_img.save(output_path, 'JPEG', quality=90)
        elif ext == '.png':
            grayscale_img.save(output_path, 'PNG')
        else:
            grayscale_img.save(output_path)
        return True, "Imagen convertida a blanco y negro"
    except ImportError:
        return False, "Pillow no instalado"
    except Exception as e:
        return False, f"Error: {str(e)}"

def convert_word_to_grayscale(input_path, output_path):
    """Convierte Word a PDF (con Ghostscript si es posible)"""
    try:
        # Intentar convertir Word a PDF primero (con unoconv o libreoffice)
        if shutil.which('unoconv'):
            temp_pdf = output_path.replace('.pdf', '_temp.pdf')
            result = subprocess.run(['unoconv', '-f', 'pdf', '-o', temp_pdf, input_path],
                                   capture_output=True, timeout=120)
            if result.returncode == 0 and os.path.exists(temp_pdf):
                # Convertir PDF a escala de grises
                success, message = convert_pdf_to_grayscale(temp_pdf, output_path)
                try:
                    os.unlink(temp_pdf)
                except:
                    pass
                return success, message
        # Fallback: usar python-docx para convertir a texto
        try:
            from docx import Document
            doc = Document(input_path)
            # Crear PDF simple con ReportLab (solo texto)
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            
            c = canvas.Canvas(output_path, pagesize=A4)
            width, height = A4
            y = height - 20
            
            for para in doc.paragraphs:
                if para.text.strip():
                    c.drawString(20, y, para.text[:100])
                    y -= 15
                    if y < 20:
                        c.showPage()
                        y = height - 20
            c.save()
            return True, "Word convertido a PDF (texto)"
        except ImportError:
            pass
        
        return False, "No se pudo convertir Word a PDF. Instala: unoconv o libreoffice"
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"

def convert_to_grayscale(input_path, output_path):
    """Detecta el tipo de archivo y lo convierte a escala de grises"""
    ext = os.path.splitext(input_path)[1].lower()
    
    print(f"{Colors.CYAN}🔄 Convirtiendo a blanco y negro: {os.path.basename(input_path)}{Colors.END}")
    
    if ext == '.pdf':
        return convert_pdf_to_grayscale(input_path, output_path)
    elif ext in ['.docx', '.doc']:
        output_path = output_path.replace(ext, '.pdf')
        return convert_word_to_grayscale(input_path, output_path)
    elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']:
        return convert_image_to_grayscale(input_path, output_path)
    else:
        return False, f"Formato no soportado para conversión B/N: {ext}"

# ============================================================================
# FUNCIONES DE DETECCIÓN DE IMPRESORAS
# ============================================================================
def get_system_printers():
    printers = []
    sistema = platform.system()
    
    print(f"{Colors.CYAN}🔍 Detectando impresoras en {sistema}...{Colors.END}")
    
    if sistema == 'Windows':
        printers = get_windows_printers()
    elif sistema == 'Linux':
        printers = get_linux_printers()
    elif sistema == 'Darwin':
        printers = get_mac_printers()
    
    seen = set()
    unique_printers = []
    for p in printers:
        name = p.get('name', '').strip()
        if name and name not in seen:
            seen.add(name)
            unique_printers.append(p)
    
    if unique_printers:
        print(f"{Colors.GREEN}✅ Detectadas {len(unique_printers)} impresoras{Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️ No se detectaron impresoras{Colors.END}")
    
    return unique_printers

def get_windows_printers():
    printers = []
    try:
        result = subprocess.run(
            ['wmic', 'printer', 'get', 'name,default'],
            capture_output=True, text=True, shell=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            name = ' '.join(parts[:-1]) if len(parts) > 1 else parts[0]
                            printers.append({
                                'name': name.strip(),
                                'default': 'TRUE' in line if 'TRUE' in line else False,
                                'type': 'Windows'
                            })
    except Exception as e:
        print(f"  wmic falló: {e}")
    return printers

def get_linux_printers():
    printers = []
    
    try:
        result = subprocess.run(
            ['lpstat', '-p', '-d'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            default_printer = None
            for line in result.stdout.split('\n'):
                if 'printer' in line and 'enabled' in line:
                    name_match = re.search(r'printer\s+([^\s]+)', line)
                    if name_match:
                        name = name_match.group(1)
                        if not any(p['name'] == name for p in printers):
                            printers.append({'name': name, 'default': False, 'type': 'CUPS'})
                if 'system default destination' in line:
                    default_match = re.search(r'destination:\s+([^\s]+)', line)
                    if default_match:
                        default_printer = default_match.group(1)
            if default_printer:
                for p in printers:
                    if p['name'] == default_printer:
                        p['default'] = True
    except Exception as e:
        print(f"  lpstat falló: {e}")
    
    if shutil.which('lsusb'):
        try:
            result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'printer' in line.lower() or 'Brother' in line or 'HP' in line or 'Epson' in line:
                        match = re.search(r'Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([0-9a-f:]+)\s+(.+)', line)
                        if match:
                            description = match.group(4).strip()
                            name = description[:40]
                            if not any(p['name'] == name for p in printers):
                                printers.append({'name': name, 'default': False, 'type': 'USB'})
        except Exception as e:
            print(f"  lsusb falló: {e}")
    
    return printers

def get_mac_printers():
    printers = []
    try:
        result = subprocess.run(
            ['lpstat', '-p', '-d'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            default_printer = None
            for line in result.stdout.split('\n'):
                if 'printer' in line and 'enabled' in line:
                    name_match = re.search(r'printer\s+([^\s]+)', line)
                    if name_match:
                        name = name_match.group(1)
                        printers.append({'name': name, 'default': False, 'type': 'CUPS'})
                if 'system default destination' in line:
                    default_match = re.search(r'destination:\s+([^\s]+)', line)
                    if default_match:
                        default_printer = default_match.group(1)
            if default_printer:
                for p in printers:
                    if p['name'] == default_printer:
                        p['default'] = True
    except Exception as e:
        print(f"  lpstat falló: {e}")
    return printers

def refresh_printers():
    printers = get_system_printers()
    if printers:
        with open(PRINTERS_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'default', 'type'])
            writer.writeheader()
            for p in printers:
                writer.writerow({
                    'name': p['name'],
                    'default': str(p.get('default', False)),
                    'type': p.get('type', 'Unknown')
                })
    return printers

def load_printers():
    if not os.path.exists(PRINTERS_CSV):
        return refresh_printers()
    
    printers = []
    try:
        with open(PRINTERS_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                printers.append({
                    'name': row['name'],
                    'default': row.get('default', 'False') == 'True',
                    'type': row.get('type', 'Unknown')
                })
    except:
        return refresh_printers()
    
    if not printers:
        return refresh_printers()
    
    return printers

# ============================================================================
# FUNCIÓN PRINCIPAL DE IMPRESIÓN
# ============================================================================

def print_file(file_path, printer_name=None, grayscale=False):
    """Envía un archivo a la impresora con opción de blanco y negro (Ghostscript)"""
    sistema = platform.system()
    
    try:
        if not os.path.exists(file_path):
            return False, "Archivo no encontrado"
        
        # Si se solicita blanco y negro, convertir primero
        if grayscale:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']:
                print(f"{Colors.CYAN}🔄 Convirtiendo a blanco y negro...{Colors.END}")
                temp_dir = tempfile.mkdtemp()
                output_filename = f"byn_{os.path.basename(file_path)}"
                if ext in ['.docx', '.doc']:
                    output_filename = output_filename.replace(ext, '.pdf')
                output_path = os.path.join(temp_dir, output_filename)
                
                success, message = convert_to_grayscale(file_path, output_path)
                if not success:
                    shutil.rmtree(temp_dir)
                    return False, f"Error en conversión B/N: {message}"
                file_path = output_path
                print(f"{Colors.GREEN}✅ Conversión completada: {output_filename}{Colors.END}")
            else:
                return False, f"Formato no soportado para blanco y negro: {ext}"
        
        # Imprimir
        if sistema == 'Windows':
            if printer_name:
                cmd = ['print', '/D:' + printer_name, file_path]
            else:
                cmd = ['print', file_path]
            print(f"  Comando: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=60)
        else:
            # Linux/macOS: usar lp
            cmd = ['lp']
            if printer_name:
                cmd.extend(['-d', printer_name])
            cmd.append(file_path)
            print(f"  Comando: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # Limpiar archivo temporal si existe
        if grayscale and 'temp_dir' in locals():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        if result.returncode == 0:
            return True, result.stdout or "Impresión enviada correctamente"
        else:
            return False, result.stderr or "Error al imprimir"
            
    except subprocess.TimeoutExpired:
        return False, "Tiempo de espera agotado"
    except Exception as e:
        return False, str(e)

def print_text(text, printer_name=None):
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
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=60)
            os.unlink(temp_file)
        else:
            cmd = ['lp']
            if printer_name:
                cmd.extend(['-d', printer_name])
            result = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return True, result.stdout or "Texto impreso correctamente"
        else:
            return False, result.stderr or "Error al imprimir"
    except Exception as e:
        return False, str(e)

def get_qr_code_image(url):
    if not QR_AVAILABLE:
        return None
    try:
        import io
        import base64
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                           box_size=4, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#00ff88", back_color="#000000")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    except:
        return None

# ============================================================================
# Rutas web (NAS)
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
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    printers = load_printers()
    
    # Obtener archivos del NAS
    all_files = []
    folders = load_folders()
    for folder in folders:
        folder_path = Path(app.config['STORAGE_FOLDER']) / folder['name']
        if folder_path.exists():
            for item in folder_path.iterdir():
                if item.is_file():
                    s = item.stat()
                    ext = os.path.splitext(item.name)[1].lower()
                    printable = ext in ['.pdf', '.txt', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif', '.bmp']
                    all_files.append({
                        'name': item.name,
                        'folder': folder['name'],
                        'size': s.st_size,
                        'size_formatted': format_size(s.st_size),
                        'modified': datetime.fromtimestamp(s.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'icon': get_file_icon(item.name),
                        'printable': printable,
                        'ext': ext
                    })
    
    all_files.sort(key=lambda x: x['name'].lower())
    
    qr_image = None
    qr_url = None
    try:
        ip = get_local_ip()
        if ip.startswith('127.'):
            qr_url = f"http://localhost:5000/print"
        else:
            qr_url = f"http://{ip}:5000/print"
        qr_image = get_qr_code_image(qr_url)
    except:
        pass
    
    return render_template('print.html', 
                          printers=printers, 
                          files=all_files,
                          qr_image=qr_image, 
                          qr_url=qr_url)

@app.route('/print/refresh')
def print_refresh():
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    refresh_printers()
    return redirect(url_for('print_page'))

@app.route('/print/file', methods=['POST'])
def print_file_route():
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    
    folder_name = request.form.get('folder_name')
    filename = request.form.get('filename')
    printer_name = request.form.get('printer_name', '')
    grayscale = request.form.get('grayscale', 'false') == 'true'
    
    print(f"{Colors.CYAN}📤 Imprimiendo archivo: {filename}{Colors.END}")
    print(f"  Impresora: {printer_name if printer_name else '(por defecto)'}")
    print(f"  Blanco y negro: {'Sí' if grayscale else 'No'}")
    
    if not folder_name or not filename:
        return "Faltan parámetros", 400
    
    if not folder_allowed(folder_name):
        return "Sin acceso a la carpeta", 403
    
    file_path = Path(app.config['STORAGE_FOLDER']) / folder_name / filename
    if not file_path.exists():
        return "Archivo no encontrado", 404
    
    success, message = print_file(str(file_path), printer_name if printer_name else None, grayscale)
    
    if success:
        return render_template('print_result.html', success=True, message=message)
    else:
        return render_template('print_result.html', success=False, error=message)

@app.route('/print/text', methods=['POST'])
def print_text_route():
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    
    text = request.form.get('text', '')
    printer_name = request.form.get('printer_name', '')
    
    print(f"{Colors.CYAN}📤 Imprimiendo texto{Colors.END}")
    print(f"  Impresora: {printer_name if printer_name else '(por defecto)'}")
    
    if not text:
        return "Texto vacío", 400
    
    success, message = print_text(text, printer_name if printer_name else None)
    
    if success:
        return render_template('print_result.html', success=True, message=message)
    else:
        return render_template('print_result.html', success=False, error=message)

@app.route('/print/upload', methods=['POST'])
def print_upload_route():
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    
    if 'file' not in request.files:
        return "No hay archivo", 400
    
    file = request.files['file']
    printer_name = request.form.get('printer_name', '')
    grayscale = request.form.get('grayscale', 'false') == 'true'
    
    print(f"{Colors.CYAN}📤 Subiendo e imprimiendo: {file.filename}{Colors.END}")
    print(f"  Impresora: {printer_name if printer_name else '(por defecto)'}")
    print(f"  Blanco y negro: {'Sí' if grayscale else 'No'}")
    
    if file.filename == '':
        return "Nombre de archivo vacío", 400
    
    filename = secure_filename(file.filename.replace(' ', '_'))
    queue_path = Path(PRINT_QUEUE_DIR) / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
    file.save(queue_path)
    
    success, message = print_file(str(queue_path), printer_name if printer_name else None, grayscale)
    
    try:
        os.unlink(queue_path)
    except:
        pass
    
    if success:
        return render_template('print_result.html', success=True, message=message)
    else:
        return render_template('print_result.html', success=False, error=message)

# ============================================================================
# Inicio
# ============================================================================
def print_startup_info():
    print()
    print(f"{Colors.PURPLE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}XONINAS NAS INICIADO{Colors.END}")
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
    
    printers = load_printers()
    print(f"\n{Colors.BOLD}🖨️ Impresoras detectadas:{Colors.END}")
    if printers:
        for p in printers[:8]:
            default_text = " (por defecto)" if p.get('default') else ""
            type_text = f" [{p.get('type', 'Unknown')}]" if p.get('type') else ""
            print(f"   {Colors.GREEN}• {p['name']}{Colors.END}{default_text}{type_text}")
        if len(printers) > 8:
            print(f"   {Colors.YELLOW}... y {len(printers) - 8} más{Colors.END}")
    else:
        print(f"   {Colors.YELLOW}⚠️ No se detectaron impresoras{Colors.END}")
    
    # Verificar Ghostscript
    if check_ghostscript():
        print(f"\n{Colors.GREEN}✅ Ghostscript disponible - Conversión B/N lista{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}⚠️ Ghostscript no instalado. Instala: sudo apt install ghostscript{Colors.END}")
    
    if qr_url:
        print(f"\n{Colors.BOLD}Codigo QR para escanear:{Colors.END}")
        print_qr_in_terminal(qr_url)
        print(f"{Colors.YELLOW}   Escanea con tu movil para acceder automaticamente{Colors.END}")
    
    print(f"\n{Colors.BOLD}Impresión remota:{Colors.END} Con opción de blanco y negro (Ghostscript)")
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