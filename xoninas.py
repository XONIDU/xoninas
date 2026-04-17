#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
app.config['STORAGE_FOLDER'] = 'storage'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 1 día

Path(app.config['STORAGE_FOLDER']).mkdir(parents=True, exist_ok=True)
Path('templates').mkdir(exist_ok=True)

MASTER_CSV = 'master.csv'
FOLDERS_CSV = 'folders.csv'

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def verify_password(pwd, hash_val):
    return hash_password(pwd) == hash_val

def init_master():
    if not os.path.exists(MASTER_CSV):
        print("\n" + "="*50)
        print("    CONFIGURACIÓN INICIAL - CLAVE MAESTRA")
        print("="*50)
        pwd = input("Clave maestra: ").strip()
        if not pwd:
            pwd = "admin"
        with open(MASTER_CSV, 'w') as f:
            f.write(hash_password(pwd))
        print("✅ Clave guardada. Reinicia la aplicación.\n")
        return False
    return True

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
        w.writerow({'name': name, 'password_hash': pwd_hash, 'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

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
    safe = name.replace(' ', '_')  # simple, sin caracteres raros
    if any(c in safe for c in '/\\?%*:|"<>'):
        return redirect(url_for('index'))
    if safe in [f['name'] for f in load_folders()]:
        return redirect(url_for('index'))
    path = Path(app.config['STORAGE_FOLDER']) / safe
    path.mkdir(parents=True)
    save_folder(safe, hash_password(pwd) if pwd else '')
    return redirect(url_for('index'))

@app.route('/delete_folder/<name>')
def delete_folder(name):
    if not session.get('master_authenticated'):
        return redirect(url_for('login'))
    path = Path(app.config['STORAGE_FOLDER']) / name
    if path.exists():
        shutil.rmtree(path)
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

if __name__ == '__main__':
    if not init_master():
        exit(0)
    try:
        from waitress import serve
        print("\n🚀 XONINAS NAS iniciado en http://127.0.0.1:5000")
        serve(app, host='127.0.0.1', port=5000, threads=4)
    except ImportError:
        app.run(host='127.0.0.1', port=5000, debug=True)
