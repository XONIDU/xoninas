#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XONINAS - NAS local con carpetas protegidas
Versión con selección de ruta de almacenamiento
"""

import os
import csv
import hashlib
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, send_file

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
CONFIG_CSV = 'config.csv'   # Nuevo: guarda la ruta de almacenamiento

# Variable que contendrá la ruta absoluta de almacenamiento (se define en init_storage_path)
STORAGE_PATH = None

def init_storage_path():
    """Pregunta al usuario la ruta de almacenamiento si no está configurada."""
    global STORAGE_PATH
    
    if os.path.exists(CONFIG_CSV):
        with open(CONFIG_CSV, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0] == 'storage_path':
                    STORAGE_PATH = row[1]
                    break
        if STORAGE_PATH:
            # Convertir a Path absoluto
            STORAGE_PATH = str(Path(STORAGE_PATH).expanduser().resolve())
            Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)
            app.config['STORAGE_FOLDER'] = STORAGE_PATH
            return True
    
    # No existe configuración → preguntar al usuario
    print("\n" + "="*60)
    print("   CONFIGURACIÓN DE RUTA DE ALMACENAMIENTO")
    print("="*60)
    print("Actualmente los archivos se guardan en la carpeta 'storage'")
    print("Puedes elegir otra ubicación (disco externo, red, etc.)\n")
    
    default = str(Path('storage').resolve())
    print(f"Ruta por defecto: {default}")
    ruta = input(f"\nNueva ruta (deja vacío para usar la de defecto): ").strip()
    
    if not ruta:
        ruta = default
    else:
        ruta = str(Path(ruta).expanduser().resolve())
    
    # Crear directorio si no existe
    Path(ruta).mkdir(parents=True, exist_ok=True)
    
    # Guardar en config.csv
    with open(CONFIG_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['storage_path', ruta])
    
    STORAGE_PATH = ruta
    app.config['STORAGE_FOLDER'] = STORAGE_PATH
    print(f"\n✅ Ruta de almacenamiento configurada: {ruta}")
    print("   Puedes cambiar esta ruta eliminando el archivo config.csv y reiniciando.\n")
    return True

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def verify_password(pwd, hash_val):
    return hash_password(pwd) == hash_val

def init_master():
    """Configura la clave maestra si no existe."""
    if not os.path.exists(MASTER_CSV):
        print("\n" + "="*50)
        print("    CONFIGURACIÓN INICIAL - CLAVE MAESTRA")
        print("="*50)
        pwd = input("Clave maestra: ").strip()
        if not pwd:
            pwd = "admin"
            print("Usando 'admin'")
        with open(MASTER_CSV, 'w') as f:
            f.write(hash_password(pwd))
        print("✅ Clave guardada. Reinicia la aplicación.\n")
        return False
    return True

def load_folders():
    """Carga la lista de carpetas desde folders.csv."""
    if not os.path.exists(FOLDERS_CSV):
        return []
    with open(FOLDERS_CSV, 'r') as f:
        return list(csv.DictReader(f))

def save_folder(name, pwd_hash):
    """Guarda una nueva carpeta en el CSV."""
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
    """Elimina una carpeta del CSV (no el directorio físico)."""
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

# ----------------------------------------------------------------------
# Rutas web
# ----------------------------------------------------------------------
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
    # Crear directorio dentro de la ruta de almacenamiento
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

# ----------------------------------------------------------------------
# Inicio
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # 1. Configurar ruta de almacenamiento (pregunta si no existe)
    init_storage_path()
    
    # 2. Configurar clave maestra (pregunta si no existe)
    if not init_master():
        exit(0)
    
    # 3. Iniciar servidor
    try:
        from waitress import serve
        print(f"\n🚀 XONINAS NAS iniciado en http://0.0.0.0:5000")
        print(f"   Almacenamiento: {app.config['STORAGE_FOLDER']}")
        print("   Acceso desde la red local: http://<tu-ip>:5000")
        serve(app, host='0.0.0.0', port=5000, threads=4)
    except ImportError:
        app.run(host='0.0.0.0', port=5000, debug=True)
