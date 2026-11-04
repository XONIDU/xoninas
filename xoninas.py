#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XONINAS 2026 - NAS local con carpetas protegidas
=================================================
Este archivo es solo la aplicación web. No contiene datos configurables:
todo (usuario, clave, almacenamiento, puerto, túnel, inicio automático,
correo y tema) se guarda en config.json y se edita desde la web:

  * Primera vez  -> /setup   (asistente inicial)
  * Después      -> /admin   (panel de administración)

El túnel Cloudflare, el aviso por correo y el inicio automático los ejecuta
start.py, que lee el mismo config.json.

Desarrollado por: Darian Alberto Camacho Salas - XONIDU (#SomosXONIDU)
"""

import copy
import io
import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, send_file, session, url_for, Response)
from werkzeug.security import check_password_hash, generate_password_hash

VERSION = '5.0.0'
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / 'config.json'
RUNTIME_PATH = BASE_DIR / 'runtime.json'      # lo escribe start.py (estado del túnel)
COMMAND_PATH = BASE_DIR / 'command.json'      # la web le pide cosas a start.py
DATA_DIR = BASE_DIR / 'data'
FOLDERS_DB = DATA_DIR / 'folders.json'
START_PY = BASE_DIR / 'start.py'

DEFAULT_CONFIG = {
    'setup_done': False,
    'secret_key': '',
    'admin_user': '',
    'admin_hash': '',
    'storage_path': str(BASE_DIR / 'storage'),
    'host': '0.0.0.0',
    'port': 5000,
    'theme_default': 'dark',            # dark | light | auto
    'tunnel': {'enabled': True},
    'autostart': False,
    'email': {
        'enabled': False,
        'sender': '',
        'app_password': '',
        'recipients': [],               # [{'address': str, 'active': bool}]
        'on_start': True,
        'on_tunnel_change': True,
    },
    'monitor': {'interval': 600, 'attempts': 5},
}

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
USER_RE = re.compile(r'^[A-Za-z0-9._-]{3,32}$')
PAGES_RE = re.compile(r'^\d+(-\d+)?(,\d+(-\d+)?)*$')
PRINTABLE = {'pdf', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'doc', 'docx', 'odt', 'rtf'}
OFFICE = {'doc', 'docx', 'odt', 'rtf'}

_cfg_lock = threading.Lock()


# ============================================================================
# Configuración
# ============================================================================
def deep_update(base, new):
    for k, v in new.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = v
    return base


def save_config(cfg):
    with _cfg_lock:
        tmp = CONFIG_PATH.with_suffix('.tmp')
        tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')
        try:
            os.chmod(tmp, 0o600)          # contiene la clave de aplicación del correo
        except OSError:
            pass
        os.replace(tmp, CONFIG_PATH)


def load_config():
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            deep_update(cfg, json.loads(CONFIG_PATH.read_text(encoding='utf-8')))
        except (OSError, ValueError):
            pass
    if not cfg['secret_key']:
        cfg['secret_key'] = secrets.token_hex(32)
        save_config(cfg)
    return cfg


app = Flask(__name__)
app.secret_key = load_config()['secret_key']
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7,
    MAX_CONTENT_LENGTH=None,
)


# ============================================================================
# Utilidades
# ============================================================================
def fmt_size(n):
    n = float(n)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024 or unit == 'TB':
            return f'{int(n)} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024


def fmt_time(ts):
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')


def clean_name(name):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', (name or '').strip())
    return name.strip('. ')[:120]


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return '127.0.0.1'


def read_runtime():
    try:
        data = json.loads(RUNTIME_PATH.read_text(encoding='utf-8'))
        data['fresh'] = (time.time() - data.get('updated', 0)) < 90
        return data
    except (OSError, ValueError):
        return {'fresh': False}


def get_urls():
    port = g.cfg['port']
    rt = read_runtime()
    tunnel = rt.get('tunnel_url') if rt.get('fresh') and rt.get('tunnel_state') == 'active' else None
    return {
        'local': f'http://localhost:{port}',
        'lan': f'http://{lan_ip()}:{port}',
        'tunnel': tunnel,
        'tunnel_state': rt.get('tunnel_state', 'unknown') if rt.get('fresh') else 'unknown',
        'launcher': rt.get('fresh', False),
    }


def run_start_cli(*args, timeout=45):
    """Ejecuta start.py en modo de una sola acción (inicio automático, correo de prueba)."""
    try:
        r = subprocess.run([sys.executable, str(START_PY), *args], capture_output=True,
                           text=True, timeout=timeout, cwd=str(BASE_DIR))
        lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
        msg = lines[-1] if lines else (r.stderr.strip()[-200:] or 'Sin respuesta')
        return r.returncode == 0, msg
    except Exception as exc:                      # noqa: BLE001
        return False, str(exc)


# ============================================================================
# Seguridad: CSRF, intentos fallidos, sesión
# ============================================================================
def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_urlsafe(24)
    return session['_csrf']


app.jinja_env.globals['csrf_token'] = csrf_token

_FAILS = {}
_FAILS_LOCK = threading.Lock()


def client_key():
    ip = request.remote_addr or '?'
    if ip in ('127.0.0.1', '::1'):                # detrás de cloudflared
        ip = request.headers.get('CF-Connecting-IP', ip)
    return ip


def locked_seconds():
    with _FAILS_LOCK:
        rec = _FAILS.get(client_key())
        if rec and rec['until'] > time.time():
            return int(rec['until'] - time.time()) + 1
    return 0


def register_fail():
    with _FAILS_LOCK:
        rec = _FAILS.setdefault(client_key(), {'n': 0, 'until': 0})
        rec['n'] += 1
        if rec['n'] >= 5:
            rec['n'] = 0
            rec['until'] = time.time() + 60


def register_ok():
    with _FAILS_LOCK:
        _FAILS.pop(client_key(), None)


@app.before_request
def guard():
    g.cfg = load_config()
    ep = request.endpoint
    if ep in (None, 'static', 'health'):
        return None
    if not g.cfg['setup_done'] and ep != 'setup':
        return redirect(url_for('setup'))
    if request.method == 'POST':
        sent = request.form.get('_csrf') or request.headers.get('X-CSRF-Token') or ''
        if not sent or not secrets.compare_digest(sent, session.get('_csrf', '')):
            abort(400, 'La sesión expiró. Recarga la página e inténtalo de nuevo.')
    return None


@app.after_request
def headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'SAMEORIGIN'
    resp.headers['Referrer-Policy'] = 'same-origin'
    return resp


@app.context_processor
def inject():
    return {
        'theme_default': g.cfg['theme_default'] if 'cfg' in g else 'dark',
        'current_user': session.get('user'),
        'version': VERSION,
    }


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if not session.get('user'):
            return redirect(url_for('login', next=request.full_path.rstrip('?')))
        return view(*a, **kw)
    return wrapped


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
def http_error(err):
    return render_template('error.html', code=err.code, message=getattr(err, 'description', '')), err.code


# ============================================================================
# Carpetas
# ============================================================================
def storage_root():
    root = Path(g.cfg['storage_path']).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def load_db():
    try:
        return json.loads(FOLDERS_DB.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_db(db):
    DATA_DIR.mkdir(exist_ok=True)
    FOLDERS_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding='utf-8')


def list_folders():
    """Sincroniza data/folders.json con las carpetas reales del disco."""
    root = storage_root()
    db = load_db()
    names = sorted((d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith('.')), key=str.lower)
    changed = False
    out = []
    for n in names:
        if n not in db:
            db[n] = {'created': fmt_time((root / n).stat().st_ctime), 'password_hash': ''}
            changed = True
        try:
            items = sum(1 for _ in os.scandir(root / n))
        except OSError:
            items = 0
        out.append({'name': n, 'created': db[n].get('created', ''),
                    'protected': bool(db[n].get('password_hash')), 'items': items})
    for stale in [k for k in db if k not in names]:
        del db[stale]
        changed = True
    if changed:
        save_db(db)
    return out


def resolve_in(base, rel=''):
    base = base.resolve()
    target = (base / rel).resolve() if rel else base
    if target != base and base not in target.parents:
        abort(404)
    return target


def folder_base(name, need_unlock=True):
    if not name or clean_name(name) != name or name.startswith('.'):
        abort(404)
    base = storage_root() / name
    if not base.is_dir():
        abort(404)
    entry = load_db().get(name, {})
    if need_unlock and entry.get('password_hash') and name not in session.get('unlocked', []):
        abort(redirect(url_for('folder_auth', name=name)))
    return base.resolve()


def unique_path(path):
    if not path.exists():
        return path
    n = 1
    while True:
        cand = path.with_name(f'{path.stem} ({n}){path.suffix}')
        if not cand.exists():
            return cand
        n += 1


def list_dir(base, rel=''):
    d = resolve_in(base, rel)
    subs, files = [], []
    with os.scandir(d) as it:
        for e in sorted(it, key=lambda x: x.name.lower()):
            if e.name.startswith('.'):
                continue
            st = e.stat()
            erel = f'{rel}/{e.name}'.strip('/')
            if e.is_dir():
                try:
                    count = sum(1 for _ in os.scandir(e.path))
                except OSError:
                    count = 0
                subs.append({'name': e.name, 'rel': erel, 'items': count, 'modified': fmt_time(st.st_mtime)})
            else:
                ext = e.name.rsplit('.', 1)[-1].lower() if '.' in e.name else ''
                files.append({'name': e.name, 'rel': erel, 'size': st.st_size, 'size_formatted': fmt_size(st.st_size),
                              'modified': fmt_time(st.st_mtime), 'ext': ext[:5], 'printable': ext in PRINTABLE})
    return subs, files


def extract_zip(fileobj, dest):
    count = 0
    with zipfile.ZipFile(fileobj) as z:
        for m in z.infolist():
            parts = [clean_name(p) for p in re.split(r'[\\/]+', m.filename) if p not in ('', '.', '..')]
            parts = [p for p in parts if p]
            if not parts:
                continue
            target = resolve_in(dest, '/'.join(parts))
            if m.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(m) as src, open(unique_path(target), 'wb') as out:
                shutil.copyfileobj(src, out)
            count += 1
    return count


def zip_dir(path, arcroot):
    tmp = tempfile.TemporaryFile()
    root = path.resolve()
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in root.rglob('*'):
            if p.is_file() and not any(part.startswith('.') for part in p.relative_to(root).parts):
                rp = p.resolve()
                if root in rp.parents:
                    z.write(rp, Path(arcroot) / p.relative_to(root))
    tmp.seek(0)
    return tmp


# ============================================================================
# Acceso: setup, login, logout
# ============================================================================
def form_recipients(form):
    act = {x.strip() for x in form.getlist('rcpt_active')}
    out = []
    for a in form.getlist('rcpt_addr'):
        a = a.strip()
        if a:
            out.append({'address': a, 'active': a in act})
    return out


def parse_email_form(form, old):
    em = dict(old)
    em['enabled'] = form.get('email_enabled') == 'on'
    em['sender'] = form.get('email_sender', '').strip()
    pw = re.sub(r'\s+', '', form.get('app_password', ''))
    if pw:
        if not re.fullmatch(r'[A-Za-z0-9]{16}', pw):
            return None, 'La clave de aplicación debe tener 16 caracteres (letras o números, sin espacios).'
        em['app_password'] = pw
    rec, seen = [], set()
    for r in form_recipients(form):
        if not EMAIL_RE.match(r['address']):
            return None, f'El correo «{r["address"]}» no es válido.'
        if r['address'].lower() not in seen:
            seen.add(r['address'].lower())
            rec.append(r)
    em['recipients'] = rec
    em['on_start'] = form.get('on_start') == 'on'
    em['on_tunnel_change'] = form.get('on_tunnel_change') == 'on'
    if em['enabled']:
        if not EMAIL_RE.match(em['sender']):
            return None, 'Indica el correo remitente (Gmail) para enviar los avisos.'
        if not em['app_password']:
            return None, 'Falta la clave de aplicación de 16 caracteres.'
        if not any(r['active'] for r in rec):
            return None, 'Marca al menos un destinatario para los avisos.'
    return em, None


def check_storage(path_str):
    try:
        p = Path(path_str).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        probe = p / '.xoninas_probe'
        probe.write_text('ok')
        probe.unlink()
        return str(p.resolve()), None
    except OSError as exc:
        return None, f'No se puede usar esa ruta de almacenamiento: {exc.strerror or exc}'


def parse_port(value):
    try:
        port = int(value)
        if 1024 <= port <= 65535:
            return port, None
    except (TypeError, ValueError):
        pass
    return None, 'El puerto debe ser un número entre 1024 y 65535.'


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if g.cfg['setup_done']:
        return redirect(url_for('index'))
    values = {'storage_path': g.cfg['storage_path'], 'port': g.cfg['port'], 'tunnel_enabled': True,
              'autostart': False, 'theme_default': 'dark', 'recipients': [], 'on_start': True,
              'on_tunnel_change': True}
    if request.method == 'POST':
        f = request.form
        values.update({'admin_user': f.get('admin_user', '').strip(), 'storage_path': f.get('storage_path', '').strip(),
                       'port': f.get('port', ''), 'tunnel_enabled': f.get('tunnel_enabled') == 'on',
                       'autostart': f.get('autostart') == 'on', 'theme_default': f.get('theme_default', 'dark'),
                       'email_enabled': f.get('email_enabled') == 'on', 'email_sender': f.get('email_sender', '').strip(),
                       'recipients': form_recipients(f), 'on_start': f.get('on_start') == 'on',
                       'on_tunnel_change': f.get('on_tunnel_change') == 'on'})
        error = None
        if not USER_RE.match(values['admin_user']):
            error = 'El usuario debe tener entre 3 y 32 caracteres (letras, números, punto, guion o guion bajo).'
        elif len(f.get('password', '')) < 8:
            error = 'La clave debe tener al menos 8 caracteres.'
        elif f.get('password') != f.get('password2'):
            error = 'Las dos claves no coinciden.'
        port, perr = parse_port(f.get('port'))
        error = error or perr
        storage, serr = (None, None) if error else check_storage(values['storage_path'])
        error = error or serr
        email, eerr = (None, None) if error else parse_email_form(f, g.cfg['email'])
        error = error or eerr
        if values['theme_default'] not in ('dark', 'light', 'auto'):
            values['theme_default'] = 'dark'
        if error:
            flash(error, 'error')
            return render_template('setup.html', values=values), 400
        cfg = g.cfg
        cfg.update({'setup_done': True, 'admin_user': values['admin_user'],
                    'admin_hash': generate_password_hash(f.get('password')), 'storage_path': storage,
                    'port': port, 'theme_default': values['theme_default'], 'autostart': False})
        cfg['tunnel']['enabled'] = values['tunnel_enabled']
        cfg['email'] = email
        if values['autostart']:
            ok, msg = run_start_cli('--autostart', 'on')
            cfg['autostart'] = ok
            if not ok:
                flash(f'No se pudo activar el inicio automático: {msg}', 'error')
        save_config(cfg)
        session.clear()
        session['user'] = cfg['admin_user']
        session.permanent = True
        flash('Configuración guardada. El servidor está listo.', 'ok')
        return redirect(url_for('admin'))
    return render_template('setup.html', values=values)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user'):
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        wait = locked_seconds()
        if wait:
            error = f'Demasiados intentos. Espera {wait} s e inténtalo otra vez.'
        else:
            user = request.form.get('username', '').strip()
            pwd = request.form.get('password', '')
            if user == g.cfg['admin_user'] and check_password_hash(g.cfg['admin_hash'], pwd):
                register_ok()
                session.clear()
                session['user'] = user
                session.permanent = True
                nxt = request.args.get('next', '')
                return redirect(nxt if nxt.startswith('/') and not nxt.startswith('//') else url_for('index'))
            register_fail()
            error = 'Usuario o clave incorrectos.'
    return render_template('login.html', error=error), (401 if error else 200)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/health')
def health():
    return 'ok', 200, {'Content-Type': 'text/plain'}


# ============================================================================
# Panel principal y carpetas
# ============================================================================
@app.route('/')
@login_required
def index():
    return render_template('index.html', folders=list_folders(), storage_path=str(storage_root()), urls=get_urls())


@app.post('/create_folder')
@login_required
def create_folder():
    name = clean_name(request.form.get('folder_name', ''))
    pwd = request.form.get('folder_password', '')
    if not name or name.startswith('.'):
        flash('Escribe un nombre de carpeta válido.', 'error')
    elif (storage_root() / name).exists():
        flash(f'Ya existe una carpeta llamada «{name}».', 'error')
    else:
        (storage_root() / name).mkdir(parents=True)
        db = load_db()
        db[name] = {'created': fmt_time(time.time()), 'password_hash': generate_password_hash(pwd) if pwd else ''}
        save_db(db)
        flash(f'Carpeta «{name}» creada.', 'ok')
    return redirect(url_for('index'))


@app.route('/folder_auth/<name>', methods=['GET', 'POST'])
@login_required
def folder_auth(name):
    base = folder_base(name, need_unlock=False)
    entry = load_db().get(name, {})
    if not entry.get('password_hash') or name in session.get('unlocked', []):
        return redirect(url_for('folder_view', name=name))
    error = None
    if request.method == 'POST':
        wait = locked_seconds()
        if wait:
            error = f'Demasiados intentos. Espera {wait} s.'
        elif check_password_hash(entry['password_hash'], request.form.get('folder_password', '')):
            register_ok()
            session['unlocked'] = session.get('unlocked', []) + [name]
            return redirect(url_for('folder_view', name=name))
        else:
            register_fail()
            error = 'Clave de carpeta incorrecta.'
    return render_template('folder_auth.html', folder_name=name, error=error), (401 if error else 200)


@app.post('/delete_folder/<name>')
@login_required
def delete_folder(name):
    base = folder_base(name)
    shutil.rmtree(base, ignore_errors=True)
    db = load_db()
    db.pop(name, None)
    save_db(db)
    flash(f'Carpeta «{name}» eliminada.', 'ok')
    return redirect(url_for('index'))


@app.route('/folder/<name>')
@app.route('/folder/<name>/<path:sub>')
@login_required
def folder_view(name, sub=''):
    base = folder_base(name)
    d = resolve_in(base, sub)
    if not d.is_dir():
        abort(404)
    subs, files = list_dir(base, sub)
    crumbs, acc = [], ''
    for part in [p for p in sub.split('/') if p]:
        acc = f'{acc}/{part}'.strip('/')
        crumbs.append({'label': part, 'rel': acc})
    parent = '/'.join(sub.split('/')[:-1]) if sub else None
    return render_template('folder_contents.html', folder_name=name, sub=sub, crumbs=crumbs, parent=parent,
                           folders=subs, files=files)


@app.post('/upload/<name>')
@login_required
def upload(name):
    base = folder_base(name)
    dest = resolve_in(base, request.form.get('path', '').strip('/'))
    if not dest.is_dir():
        abort(404)
    saved = 0
    files = request.files.getlist('files')
    rels = request.form.getlist('relpaths')
    for i, f in enumerate(files):
        raw = rels[i] if i < len(rels) and rels[i] else f.filename
        parts = [clean_name(p) for p in re.split(r'[\\/]+', raw or '') if p not in ('', '.', '..')]
        parts = [p for p in parts if p and not p.startswith('.')]
        if not parts:
            continue
        target = unique_path(resolve_in(dest, '/'.join(parts)))
        target.parent.mkdir(parents=True, exist_ok=True)
        f.save(target)
        saved += 1
    z = request.files.get('folder_zip')
    if z and z.filename:
        try:
            saved += extract_zip(z.stream, dest)
        except zipfile.BadZipFile:
            return jsonify(ok=False, error='El archivo no es un ZIP válido.'), 400
    return jsonify(ok=True, saved=saved)


@app.post('/create_subfolder/<name>')
@login_required
def create_subfolder(name):
    base = folder_base(name)
    dest = resolve_in(base, request.form.get('path', '').strip('/'))
    sub = clean_name(request.form.get('subfolder_name', ''))
    if not sub or sub.startswith('.'):
        return jsonify(ok=False, error='Nombre no válido.'), 400
    (dest / sub).mkdir(exist_ok=True)
    return jsonify(ok=True)


@app.route('/download/<name>/<path:rel>')
@login_required
def download(name, rel):
    path = resolve_in(folder_base(name), rel)
    if not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name=path.name)


@app.route('/download_folder/<name>')
@app.route('/download_subfolder/<name>/<path:rel>')
@login_required
def download_zip(name, rel=''):
    base = folder_base(name)
    path = resolve_in(base, rel)
    if not path.is_dir():
        abort(404)
    label = path.name if rel else name
    return send_file(zip_dir(path, label), mimetype='application/zip', as_attachment=True, download_name=f'{label}.zip')


@app.post('/delete_file/<name>/<path:rel>')
@login_required
def delete_file(name, rel):
    path = resolve_in(folder_base(name), rel)
    if path.is_file():
        path.unlink()
        flash(f'Archivo «{path.name}» eliminado.', 'ok')
    parent = '/'.join(rel.split('/')[:-1])
    return redirect(url_for('folder_view', name=name, sub=parent) if parent else url_for('folder_view', name=name))


@app.post('/delete_subfolder/<name>/<path:rel>')
@login_required
def delete_subfolder(name, rel):
    base = folder_base(name)
    path = resolve_in(base, rel)
    if path.is_dir() and path != base:
        shutil.rmtree(path, ignore_errors=True)
        flash(f'Carpeta «{path.name}» eliminada.', 'ok')
    parent = '/'.join(rel.split('/')[:-1])
    return redirect(url_for('folder_view', name=name, sub=parent) if parent else url_for('folder_view', name=name))


# ============================================================================
# Impresión (CUPS: lp / lpstat)
# ============================================================================
_printer_cache = {'t': 0, 'data': []}


def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, '', str(exc)


def list_printers(force=False):
    if not force and time.time() - _printer_cache['t'] < 30:
        return _printer_cache['data']
    printers = []
    if platform.system() == 'Windows':
        rc, out, _ = _run(['powershell', '-NoProfile', '-Command',
                           'Get-CimInstance Win32_Printer | Select-Object Name,Default | ConvertTo-Json'])
        if rc == 0 and out:
            try:
                data = json.loads(out)
                for p in (data if isinstance(data, list) else [data]):
                    printers.append({'name': p['Name'], 'default': bool(p.get('Default')), 'state': ''})
            except (ValueError, KeyError):
                pass
    elif shutil.which('lpstat'):
        _, dout, _ = _run(['lpstat', '-d'])
        default = dout.split(':')[-1].strip() if ':' in dout else ''
        _, pout, _ = _run(['lpstat', '-p'])
        for line in pout.splitlines():
            m = re.match(r'printer (\S+) (.*)', line)
            if m:
                printers.append({'name': m.group(1), 'default': m.group(1) == default,
                                 'state': 'deshabilitada' if 'disabled' in m.group(2) else 'disponible'})
    _printer_cache.update(t=time.time(), data=printers)
    return printers


def parse_print_options(form):
    printers = [p['name'] for p in list_printers()]
    printer = form.get('printer_name', '').strip()
    if printer and printers and printer not in printers:
        return None, 'La impresora seleccionada no existe.'
    try:
        copies = max(1, min(99, int(form.get('copies', '1'))))
    except ValueError:
        copies = 1
    pages = re.sub(r'\s+', '', form.get('pages', ''))
    if pages and not PAGES_RE.match(pages):
        return None, 'Las páginas deben escribirse así: 1-3,5,8-10.'
    parity = form.get('parity', 'all')
    if parity not in ('all', 'odd', 'even'):
        parity = 'all'
    return {'printer': printer, 'copies': copies, 'pages': pages, 'parity': parity,
            'gray': form.get('grayscale') == 'true'}, None


def print_result(ok, title, message, opts=None, job='', extra=None):
    details = []
    if opts:
        details = [('Impresora', opts['printer'] or 'Predeterminada'), ('Copias', str(opts['copies'])),
                   ('Páginas', opts['pages'] or 'Todas'),
                   ('Selección', {'all': 'Todas', 'odd': 'Solo impares', 'even': 'Solo pares'}[opts['parity']]),
                   ('Color', 'Blanco y negro' if opts['gray'] else 'Color')]
    details += extra or []
    return render_template('print_result.html', ok=ok, title=title, message=message, details=details,
                           job=job, printer=(opts or {}).get('printer', ''))


def convert_to_pdf(path, outdir):
    office = shutil.which('soffice') or shutil.which('libreoffice')
    if not office:
        return None
    _run([office, '--headless', '--convert-to', 'pdf', '--outdir', str(outdir), str(path)], timeout=120)
    pdf = Path(outdir) / (path.stem + '.pdf')
    return pdf if pdf.exists() else None


def send_to_printer(path, opts, title):
    """Devuelve (ok, mensaje, job_id)."""
    tmpdir = None
    try:
        if path.suffix.lower().lstrip('.') in OFFICE:
            tmpdir = tempfile.mkdtemp(prefix='xoninas_')
            pdf = convert_to_pdf(path, tmpdir)
            if not pdf:
                return False, 'Para imprimir documentos de Office instala LibreOffice (soffice).', ''
            path = pdf
        if platform.system() == 'Windows' and not shutil.which('lp'):
            os.startfile(str(path), 'print')       # noqa: S606  (sin opciones avanzadas)
            return True, 'Enviado a la impresora predeterminada de Windows (sin opciones avanzadas).', ''
        if not shutil.which('lp'):
            return False, 'No se encontró el comando «lp». Instala CUPS (cups / cups-client).', ''
        if not list_printers():
            return False, 'No hay impresoras configuradas en CUPS.', ''
        cmd = ['lp', '-t', title[:60], '-n', str(opts['copies']), '-o', 'fit-to-page']
        if opts['printer']:
            cmd += ['-d', opts['printer']]
        if opts['pages']:
            cmd += ['-P', opts['pages']]
        if opts['parity'] != 'all':
            cmd += ['-o', f'page-set={opts["parity"]}']
        if opts['gray']:
            cmd += ['-o', 'print-color-mode=monochrome', '-o', 'ColorModel=Gray']
        rc, out, err = _run(cmd + [str(path)], timeout=60)
        if rc != 0:
            return False, err or 'La impresora rechazó el trabajo.', ''
        m = re.search(r'request id is (\S+)', out)
        return True, 'El trabajo se envió a la cola de impresión.', (m.group(1) if m else '')
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def printable_files(limit=1500):
    root = storage_root()
    unlocked = set(session.get('unlocked', []))
    out, locked = [], 0
    for f in list_folders():
        if f['protected'] and f['name'] not in unlocked:
            locked += 1
            continue
        base = root / f['name']
        for p in base.rglob('*'):
            if len(out) >= limit:
                break
            rel_parts = p.relative_to(base).parts
            if not p.is_file() or any(x.startswith('.') for x in rel_parts):
                continue
            ext = p.suffix.lower().lstrip('.')
            st = p.stat()
            out.append({'name': p.name, 'folder': f['name'], 'rel': '/'.join(rel_parts),
                        'size_formatted': fmt_size(st.st_size), 'mtime': st.st_mtime,
                        'ext': ext[:5], 'printable': ext in PRINTABLE})
    out.sort(key=lambda x: x['mtime'], reverse=True)
    return out, locked


@app.route('/print')
@login_required
def print_page():
    files, locked = printable_files()
    return render_template('print.html', printers=list_printers(), files=files, locked=locked, urls=get_urls())


@app.route('/print/refresh')
@login_required
def print_refresh():
    list_printers(force=True)
    return redirect(url_for('print_page'))


@app.post('/print/file')
@login_required
def print_file():
    base = folder_base(request.form.get('folder_name', ''))
    path = resolve_in(base, request.form.get('filename', ''))
    if not path.is_file():
        abort(404)
    opts, err = parse_print_options(request.form)
    if err:
        return print_result(False, 'No se pudo imprimir', err), 400
    ok, msg, job = send_to_printer(path, opts, path.name)
    return print_result(ok, 'Trabajo enviado' if ok else 'No se pudo imprimir', msg, opts, job,
                        [('Archivo', path.name)])


@app.post('/print/upload')
@login_required
def print_upload():
    f = request.files.get('file')
    opts, err = parse_print_options(request.form)
    if err or not f or not f.filename:
        return print_result(False, 'No se pudo imprimir', err or 'Selecciona un archivo.'), 400
    name = clean_name(f.filename) or 'archivo'
    if name.rsplit('.', 1)[-1].lower() not in PRINTABLE:
        return print_result(False, 'Formato no admitido', 'Usa PDF, TXT, imágenes o documentos de Office.'), 400
    tmpdir = tempfile.mkdtemp(prefix='xoninas_up_')
    try:
        path = Path(tmpdir) / name
        f.save(path)
        ok, msg, job = send_to_printer(path, opts, name)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return print_result(ok, 'Trabajo enviado' if ok else 'No se pudo imprimir', msg, opts, job, [('Archivo', name)])


@app.post('/print/text')
@login_required
def print_text():
    text = request.form.get('text', '').strip()
    opts, err = parse_print_options(request.form)
    if err or not text:
        return print_result(False, 'No se pudo imprimir', err or 'Escribe el texto a imprimir.'), 400
    tmpdir = tempfile.mkdtemp(prefix='xoninas_tx_')
    try:
        path = Path(tmpdir) / 'texto.txt'
        path.write_text(text, encoding='utf-8')
        ok, msg, job = send_to_printer(path, opts, 'Texto XONINAS')
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return print_result(ok, 'Trabajo enviado' if ok else 'No se pudo imprimir', msg, opts, job,
                        [('Contenido', f'{len(text)} caracteres')])


@app.route('/print/queue.json')
@login_required
def print_queue():
    if not shutil.which('lpstat'):
        return jsonify(jobs=[])
    _, out, _ = _run(['lpstat', '-o'])
    return jsonify(jobs=[l for l in out.splitlines() if l.strip()])


# ============================================================================
# QR
# ============================================================================
@app.route('/qr/<kind>.svg')
@login_required
def qr(kind):
    urls = get_urls()
    target = {'local': urls['lan'], 'tunnel': urls['tunnel'],
              'print': (urls['tunnel'] or urls['lan']) + '/print'}.get(kind)
    if not target:
        abort(404)
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        abort(404)
    img = qrcode.make(target, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return Response(buf.getvalue(), mimetype='image/svg+xml', headers={'Cache-Control': 'no-store'})


# ============================================================================
# Administración
# ============================================================================
def admin_redirect(anchor=''):
    return redirect(url_for('admin') + (f'#{anchor}' if anchor else ''))


@app.route('/admin')
@login_required
def admin():
    cfg = copy.deepcopy(g.cfg)
    has_pw = bool(cfg['email'].get('app_password'))
    cfg['email']['app_password'] = ''
    cfg['admin_hash'] = ''
    cfg['secret_key'] = ''
    try:
        import qrcode  # noqa: F401
        has_qr = True
    except ImportError:
        has_qr = False
    return render_template('admin.html', cfg=cfg, has_pw=has_pw, urls=get_urls(), has_qr=has_qr,
                           storage_path=str(storage_root()), system=platform.system(),
                           supervised=bool(os.environ.get('XONINAS_SUPERVISED')))


@app.get('/admin/status')
@login_required
def admin_status():
    return jsonify(get_urls())


@app.post('/admin/save/<section>')
@login_required
def admin_save(section):
    cfg, f = g.cfg, request.form
    if section == 'account':
        if not check_password_hash(cfg['admin_hash'], f.get('current_password', '')):
            flash('La clave actual no es correcta.', 'error')
            return admin_redirect('cuenta')
        new_user = f.get('new_user', '').strip() or cfg['admin_user']
        if not USER_RE.match(new_user):
            flash('El usuario debe tener entre 3 y 32 caracteres (letras, números, . _ -).', 'error')
            return admin_redirect('cuenta')
        if f.get('new_password'):
            if len(f['new_password']) < 8:
                flash('La nueva clave debe tener al menos 8 caracteres.', 'error')
                return admin_redirect('cuenta')
            if f['new_password'] != f.get('new_password2'):
                flash('Las dos claves nuevas no coinciden.', 'error')
                return admin_redirect('cuenta')
            cfg['admin_hash'] = generate_password_hash(f['new_password'])
        cfg['admin_user'] = new_user
        session['user'] = new_user
        flash('Cuenta actualizada.', 'ok')
        anchor = 'cuenta'
    elif section == 'server':
        port, perr = parse_port(f.get('port'))
        storage, serr = check_storage(f.get('storage_path', '').strip())
        if perr or serr:
            flash(perr or serr, 'error')
            return admin_redirect('servidor')
        changed = (port != cfg['port']) or (storage != cfg['storage_path'])
        cfg['port'], cfg['storage_path'] = port, storage
        flash('Servidor actualizado.' + (' Reinicia el servidor para aplicar el puerto o la ruta nuevos.' if changed else ''), 'ok')
        anchor = 'servidor'
    elif section == 'tunnel':
        cfg['tunnel']['enabled'] = f.get('tunnel_enabled') == 'on'
        flash('Túnel activado: start.py lo abrirá en unos segundos.' if cfg['tunnel']['enabled']
              else 'Túnel desactivado: start.py lo cerrará en unos segundos.', 'ok')
        anchor = 'tunel'
    elif section == 'autostart':
        want = f.get('autostart') == 'on'
        ok, msg = run_start_cli('--autostart', 'on' if want else 'off')
        if ok:
            cfg['autostart'] = want
            flash(msg, 'ok')
        else:
            flash(f'No se pudo cambiar el inicio automático: {msg}', 'error')
        anchor = 'inicio'
    elif section == 'email':
        email, err = parse_email_form(f, cfg['email'])
        if err:
            flash(err, 'error')
            return admin_redirect('correo')
        cfg['email'] = email
        save_config(cfg)
        if f.get('action') == 'test':
            if not email['enabled']:
                flash('Activa los avisos por correo para enviar la prueba.', 'error')
            else:
                ok, msg = run_start_cli('--test-email', timeout=60)
                flash(msg, 'ok' if ok else 'error')
        else:
            flash('Configuración de correo guardada.', 'ok')
        return admin_redirect('correo')
    elif section == 'appearance':
        theme = f.get('theme_default', 'dark')
        cfg['theme_default'] = theme if theme in ('dark', 'light', 'auto') else 'dark'
        flash('Apariencia actualizada.', 'ok')
        anchor = 'apariencia'
    else:
        abort(404)
    save_config(cfg)
    return admin_redirect(anchor)


@app.post('/admin/tunnel/restart')
@login_required
def admin_tunnel_restart():
    COMMAND_PATH.write_text(json.dumps({'cmd': 'restart_tunnel', 'ts': time.time()}), encoding='utf-8')
    flash('Se pidió a start.py que genere un túnel nuevo.', 'ok')
    return admin_redirect('tunel')


@app.post('/admin/server/restart')
@login_required
def admin_server_restart():
    if not os.environ.get('XONINAS_SUPERVISED'):
        flash('Este servidor no se inició con start.py; reinícialo manualmente.', 'error')
        return admin_redirect('servidor')
    threading.Timer(1.0, lambda: os._exit(3)).start()     # start.py lo vuelve a levantar
    return render_template('restarting.html')


# ============================================================================
# Arranque
# ============================================================================
def main():
    cfg = load_config()
    host, port = cfg['host'], int(cfg['port'])
    print(f'XONINAS {VERSION} escuchando en http://{host}:{port}')
    try:
        from waitress import serve
        serve(app, host=host, port=port, threads=8, max_request_body_size=20 * 1024 ** 3,
              channel_timeout=600)
    except ImportError:
        app.run(host=host, port=port, threaded=True)


if __name__ == '__main__':
    main()
