#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XONINAS 2026 - Lanzador
=======================
Se encarga de todo lo que rodea al servidor web (xoninas.py):

  * libera el puerto, comprueba dependencias y levanta xoninas.py (y lo reinicia si cae)
  * abre/cierra el túnel Cloudflare según config.json (se puede activar desde /admin)
  * muestra en la terminal el QR de la red local y el QR del túnel
  * envía el correo de aviso al encender el NAS y cuando cambia la URL del túnel
  * instala o quita el inicio automático con el sistema
  * impide que haya dos lanzadores a la vez (bloqueo start.lock)
  * descarga cloudflared a la carpeta bin/ (sin sudo, sin contraseña)

No tiene datos propios: lee config.json, que se edita en la web (/setup y /admin).

Uso:
  python3 start.py                      arranque normal
  python3 start.py --service            sin limpiar pantalla (inicio automático)
  python3 start.py --autostart on|off|status
  python3 start.py --test-email

Desarrollado por: Darian Alberto Camacho Salas - XONIDU (#SomosXONIDU)
"""

import argparse
import copy
import importlib.util
import json
import os
import platform
import re
import shutil
import signal
import smtplib
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / 'config.json'
RUNTIME_PATH = BASE_DIR / 'runtime.json'
COMMAND_PATH = BASE_DIR / 'command.json'
LOG_FILE = BASE_DIR / 'xoninas_startup.log'
SERVER_PY = BASE_DIR / 'xoninas.py'
LOCK_PATH = BASE_DIR / 'start.lock'
BIN_DIR = BASE_DIR / 'bin'

DEFAULTS = {
    'setup_done': False, 'port': 5000, 'tunnel': {'enabled': True}, 'autostart': False,
    'email': {'enabled': False, 'sender': '', 'app_password': '', 'recipients': [],
              'on_start': True, 'on_tunnel_change': True},
}
SMTP_SERVER, SMTP_PORT = 'smtp.gmail.com', 587
NET_RETRY = 5                 # s entre reintentos cuando NO hay red
NET_CHECK = 5                 # s entre chequeos cuando sí hay red (detecta la caída rápido)
TUNNEL_CHECK_INTERVAL = 600   # s (10 min) entre pings al túnel
TUNNEL_CHECK_ATTEMPTS = 5     # pings por verificación; basta uno que responda
TUNNEL_RESTART_DELAY = 5      # s de espera antes de abrir un túnel nuevo tras una caída
TUNNEL_URL_TIMEOUT = 60       # s para que cloudflared entregue la URL
STARTUP_MAIL_WAIT = 90        # s máximos esperando el túnel antes de mandar el correo de arranque
SERVICE = False
STOPPING = False


# ============================================================================
# Registro
# ============================================================================
class C:
    G, Y, R, B, P, X, BOLD = '\033[92m', '\033[93m', '\033[91m', '\033[94m', '\033[95m', '\033[0m', '\033[1m'


if platform.system() == 'Windows':
    os.system('')             # activa secuencias ANSI en Windows 10+

_log_lock = threading.Lock()


def log(msg, level='INFO'):
    color = {'INFO': C.B, 'OK': C.G, 'WARN': C.Y, 'ERROR': C.R}.get(level, C.X)
    stamp = datetime.now().strftime('%H:%M:%S')
    with _log_lock:
        print(f'{color}[{stamp}] {msg}{C.X}', flush=True)
        try:
            if LOG_FILE.exists() and LOG_FILE.stat().st_size > 1_000_000:
                LOG_FILE.replace(LOG_FILE.with_suffix('.old'))
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] [{level}] {msg}\n')
        except OSError:
            pass


# ============================================================================
# Instancia única (evita dos lanzadores matándose el servidor entre sí)
# ============================================================================
def pid_alive(pid):
    """True si pid es un start.py vivo (evita falsos positivos por PIDs reciclados)."""
    if platform.system() == 'Windows':
        out = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except PermissionError:
        pass
    except OSError:
        return False
    cmd = Path(f'/proc/{pid}/cmdline')
    if cmd.exists():
        try:
            return b'start.py' in cmd.read_bytes()
        except OSError:
            return False
    return True


def acquire_lock():
    """Devuelve el PID de otro lanzador activo, o None si logramos el bloqueo."""
    try:
        old = int(LOCK_PATH.read_text().strip())
        if old != os.getpid() and pid_alive(old):
            return old
    except (OSError, ValueError):
        pass
    LOCK_PATH.write_text(str(os.getpid()))
    return None


# ============================================================================
# Configuración (solo lectura; la escribe la web)
# ============================================================================
def load_config():
    cfg = copy.deepcopy(DEFAULTS)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    except (OSError, ValueError):
        pass
    return cfg


def cfg_mtime():
    try:
        return CONFIG_PATH.stat().st_mtime
    except OSError:
        return 0


# ============================================================================
# Red
# ============================================================================
def internet_ok():
    for host in (('1.1.1.1', 53), ('8.8.8.8', 53)):
        try:
            socket.create_connection(host, timeout=2).close()
            return True
        except OSError:
            continue
    return False


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return '127.0.0.1'


def server_ok(port, timeout=4):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=timeout) as r:
            return r.status == 200
    except Exception:                                  # noqa: BLE001
        return False


def tunnel_responds(url, attempts, timeout=8):
    """Cualquier respuesta real del NAS cuenta; los errores 5xx de Cloudflare no."""
    for i in range(attempts):
        try:
            req = urllib.request.Request(url + '/health', headers={'User-Agent': 'XONINAS-Monitor/5'})
            with urllib.request.urlopen(req, timeout=timeout):
                return True
        except urllib.error.HTTPError as e:
            if e.code < 500:
                return True
        except Exception:                              # noqa: BLE001
            pass
        if i < attempts - 1:
            time.sleep(2)
    return False


def kill_port(port):
    """Cierra lo que esté usando el puerto antes de iniciar."""
    killed = False
    try:
        if platform.system() == 'Windows':
            out = subprocess.run(f'netstat -ano | findstr :{port}', capture_output=True, text=True, shell=True).stdout
            pids = {l.split()[-1] for l in out.splitlines() if 'LISTENING' in l}
            for pid in pids:
                subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                killed = True
        else:
            pids = set()
            if shutil.which('lsof'):
                out = subprocess.run(['lsof', '-ti', f'tcp:{port}', '-sTCP:LISTEN'], capture_output=True, text=True).stdout
                pids = {p for p in out.split() if p.isdigit()}
            elif shutil.which('fuser'):
                out = subprocess.run(['fuser', f'{port}/tcp'], capture_output=True, text=True).stdout
                pids = {p for p in out.split() if p.isdigit()}
            for pid in pids:
                if int(pid) == os.getpid():
                    continue
                log(f'Cerrando el proceso {pid} que ocupa el puerto {port}', 'WARN')
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except OSError:
                    pass
                killed = True
    except Exception as exc:                           # noqa: BLE001
        log(f'No se pudo revisar el puerto: {exc}', 'WARN')
    if killed:
        time.sleep(2)
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) != 0


# ============================================================================
# QR en terminal (fondo blanco, legible en cualquier tema de terminal)
# ============================================================================
def qr_lines(data):
    try:
        import qrcode
        qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(data)
        qr.make(fit=True)
        m = qr.get_matrix()
    except Exception:                                  # noqa: BLE001
        return None
    chars = {(1, 1): '█', (1, 0): '▀', (0, 1): '▄', (0, 0): ' '}
    lines = []
    for y in range(0, len(m), 2):
        row = ''
        for x in range(len(m[0])):
            top = 1 if m[y][x] else 0
            bot = 1 if y + 1 < len(m) and m[y + 1][x] else 0
            row += chars[(top, bot)]
        lines.append(f'\033[47;30m{row}\033[0m')
    return lines, len(m[0])


def print_qrs(local_url, tunnel_url):
    blocks = []
    for title, url in (('Red local', local_url), ('Túnel Cloudflare', tunnel_url)):
        if not url:
            continue
        q = qr_lines(url)
        blocks.append((title, url, q))
    print()
    if all(b[2] for b in blocks) and len(blocks) == 2:
        (t1, u1, (l1, w1)), (t2, u2, (l2, w2)) = blocks
        width = max(w1, w2)
        print(f'{C.BOLD}{t1:<{width + 4}}{t2}{C.X}')
        for i in range(max(len(l1), len(l2))):
            a = l1[i] if i < len(l1) else ' ' * w1
            b = l2[i] if i < len(l2) else ''
            pad = ' ' * (width + 4 - w1)
            print(a + pad + b)
        print(f'{u1:<{width + 4}}{u2}')
    else:
        for title, url, q in blocks:
            print(f'{C.BOLD}{title}{C.X}')
            if q:
                print('\n'.join(q[0]))
            print(url)
            print()
    print(flush=True)


# ============================================================================
# Correo
# ============================================================================
def build_mail(cfg, subject_prefix, local_url, lan_url, tunnel_url):
    body = [f'{subject_prefix}', '', f'Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}',
            f'Equipo: {socket.gethostname()} ({platform.system()} {platform.release()})', '',
            'Direcciones de acceso', f'  Este equipo:  {local_url}', f'  Red local:    {lan_url}']
    body.append(f'  Túnel:        {tunnel_url}' if tunnel_url else '  Túnel:        no activo')
    body += ['', '--', 'XONINAS · #SomosXONIDU']
    return '\n'.join(body)


def send_mail(cfg, subject, body):
    em = cfg['email']
    to = [r['address'] for r in em.get('recipients', []) if r.get('active')]
    if not (em.get('sender') and em.get('app_password')):
        return False, 'Falta el correo remitente o la clave de aplicación.'
    if not to:
        return False, 'No hay destinatarios marcados.'
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'], msg['To'], msg['Subject'] = em['sender'], ', '.join(to), subject
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as s:
            s.starttls()
            s.login(em['sender'], em['app_password'].replace(' ', ''))
            s.send_message(msg)
        return True, f'Correo enviado a {len(to)} destinatario(s).'
    except smtplib.SMTPAuthenticationError:
        return False, 'Gmail rechazó la clave. Genera una clave de aplicación nueva y verifica el remitente.'
    except Exception as exc:                           # noqa: BLE001
        return False, f'No se pudo enviar el correo: {exc}'


def send_mail_retry(cfg, subject, body, tries=8, delay=30):
    """Al encender la laptop el WiFi tarda: reintenta en segundo plano."""
    def worker():
        for i in range(1, tries + 1):
            ok, msg = send_mail(cfg, subject, body)
            log(msg, 'OK' if ok else 'WARN')
            if ok or 'rechazó' in msg or 'Falta' in msg or 'destinatarios' in msg:
                return
            time.sleep(delay)
        log('Se agotaron los reintentos del correo.', 'ERROR')
    threading.Thread(target=worker, daemon=True).start()


def cli_test_email():
    cfg = load_config()
    port = cfg['port']
    ok, msg = send_mail(cfg, 'XONINAS · correo de prueba',
                        build_mail(cfg, 'Correo de prueba de XONINAS.', f'http://localhost:{port}',
                                   f'http://{lan_ip()}:{port}', None))
    print(msg)
    return 0 if ok else 1


# ============================================================================
# Inicio automático
# ============================================================================
def autostart_paths():
    home = Path.home()
    return {
        'unit': home / '.config/systemd/user/xoninas.service',
        'desktop': home / '.config/autostart/xoninas.desktop',
        'plist': home / 'Library/LaunchAgents/com.xonidu.xoninas.plist',
        'win': Path(os.environ.get('APPDATA', str(home))) / 'Microsoft/Windows/Start Menu/Programs/Startup/xoninas.vbs',
    }


def sh(*cmd):
    try:
        return subprocess.run(list(cmd), capture_output=True, text=True, timeout=20).returncode == 0
    except Exception:                                  # noqa: BLE001
        return False


def autostart_status():
    p = autostart_paths()
    return any(p[k].exists() for k in (('win',) if platform.system() == 'Windows' else
                                       ('plist',) if platform.system() == 'Darwin' else ('unit', 'desktop')))


def autostart_set(enable):
    system, p = platform.system(), autostart_paths()
    py, me = sys.executable, str(Path(__file__).resolve())
    try:
        if system == 'Linux':
            if enable:
                p['unit'].parent.mkdir(parents=True, exist_ok=True)
                p['unit'].write_text(
                    '[Unit]\nDescription=XONINAS NAS local\n\n[Service]\nType=simple\n'
                    f'WorkingDirectory={BASE_DIR}\nExecStart={py} {me} --service\n'
                    'Restart=on-failure\nRestartSec=10\n\n[Install]\nWantedBy=default.target\n', encoding='utf-8')
                if shutil.which('systemctl') and sh('systemctl', '--user', 'daemon-reload') \
                        and sh('systemctl', '--user', 'enable', 'xoninas.service'):
                    sh('loginctl', 'enable-linger', os.environ.get('USER', ''))   # arranca sin iniciar sesión
                    return True, 'Inicio automático activado (servicio de usuario systemd).'
                p['unit'].unlink(missing_ok=True)
                p['desktop'].parent.mkdir(parents=True, exist_ok=True)
                p['desktop'].write_text(
                    f'[Desktop Entry]\nType=Application\nName=XONINAS\nExec={py} {me} --service\n'
                    f'Path={BASE_DIR}\nTerminal=false\nX-GNOME-Autostart-enabled=true\n', encoding='utf-8')
                return True, 'Inicio automático activado (al iniciar sesión en el escritorio).'
            if shutil.which('systemctl'):
                sh('systemctl', '--user', 'disable', 'xoninas.service')
            p['unit'].unlink(missing_ok=True)
            p['desktop'].unlink(missing_ok=True)
            return True, 'Inicio automático desactivado.'
        if system == 'Windows':
            if enable:
                pyw = Path(py).with_name('pythonw.exe')
                runner = str(pyw if pyw.exists() else py)
                p['win'].write_text(
                    'Set sh = CreateObject("WScript.Shell")\n'
                    f'sh.CurrentDirectory = "{BASE_DIR}"\n'
                    f'sh.Run """{runner}"" ""{me}"" --service", 0, False\n', encoding='utf-8')
                return True, 'Inicio automático activado (carpeta Inicio de Windows).'
            p['win'].unlink(missing_ok=True)
            return True, 'Inicio automático desactivado.'
        if system == 'Darwin':
            if enable:
                p['plist'].parent.mkdir(parents=True, exist_ok=True)
                p['plist'].write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0"><dict>\n'
                    '<key>Label</key><string>com.xonidu.xoninas</string>\n'
                    f'<key>ProgramArguments</key><array><string>{py}</string><string>{me}</string><string>--service</string></array>\n'
                    f'<key>WorkingDirectory</key><string>{BASE_DIR}</string>\n'
                    '<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>\n</dict></plist>\n', encoding='utf-8')
                sh('launchctl', 'load', str(p['plist']))
                return True, 'Inicio automático activado (LaunchAgent de macOS).'
            sh('launchctl', 'unload', str(p['plist']))
            p['plist'].unlink(missing_ok=True)
            return True, 'Inicio automático desactivado.'
    except OSError as exc:
        return False, f'No se pudo configurar el inicio automático: {exc}'
    return False, 'Sistema no compatible con el inicio automático.'


# ============================================================================
# Dependencias y cloudflared
# ============================================================================
def ensure_dependencies():
    wanted = {'flask': 'flask', 'werkzeug': 'werkzeug', 'waitress': 'waitress', 'qrcode': 'qrcode'}
    missing = [pkg for mod, pkg in wanted.items() if importlib.util.find_spec(mod) is None]
    if not missing:
        return
    log(f'Instalando dependencias faltantes: {", ".join(missing)}', 'WARN')
    base = [sys.executable, '-m', 'pip', 'install', '-q'] + missing
    for extra in ([], ['--user'], ['--break-system-packages'], ['--user', '--break-system-packages']):
        if subprocess.run(base + extra, capture_output=True).returncode == 0:
            log('Dependencias instaladas.', 'OK')
            importlib.invalidate_caches()
            return
    log('No se pudieron instalar: ' + ', '.join(missing) + '. Instálalas con pip o con tu gestor de paquetes.', 'ERROR')
    sys.exit(1)


def cloudflared_exe():
    """Prefiere el binario local de bin/; si no existe, usa el del sistema."""
    local = BIN_DIR / ('cloudflared.exe' if platform.system() == 'Windows' else 'cloudflared')
    return str(local) if local.exists() else shutil.which('cloudflared')


def ensure_cloudflared():
    """Descarga cloudflared a bin/ si no está. No requiere sudo ni contraseña."""
    if cloudflared_exe():
        return True
    system, m = platform.system(), platform.machine().lower()
    arch = ('arm64' if m in ('aarch64', 'arm64') else 'arm' if m.startswith('arm')
            else '386' if m in ('i386', 'i686', 'x86') else 'amd64')
    if system == 'Linux':
        name, dest = f'cloudflared-linux-{arch}', BIN_DIR / 'cloudflared'
    elif system == 'Windows':
        name, dest = f'cloudflared-windows-{arch}.exe', BIN_DIR / 'cloudflared.exe'
    else:
        log('En macOS instala cloudflared con: brew install cloudflared', 'ERROR')
        return False
    log('Descargando cloudflared a la carpeta bin/ (no requiere contraseña)...', 'WARN')
    try:
        BIN_DIR.mkdir(exist_ok=True)
        tmp = dest.with_suffix('.part')
        urllib.request.urlretrieve(
            f'https://github.com/cloudflare/cloudflared/releases/latest/download/{name}', tmp)
        tmp.chmod(0o755)
        os.replace(tmp, dest)
        ok = subprocess.run([str(dest), '--version'], capture_output=True, timeout=15).returncode == 0
        if not ok:
            dest.unlink(missing_ok=True)
            log('El cloudflared descargado no funciona en este equipo.', 'ERROR')
            return False
        log('cloudflared instalado en bin/.', 'OK')
        return True
    except Exception as exc:                           # noqa: BLE001
        log(f'No se pudo descargar cloudflared: {exc}', 'ERROR')
        return False


# ============================================================================
# Túnel Cloudflare
# ============================================================================
class Tunnel:
    def __init__(self):
        self.proc = None
        self.url = None
        self.started = 0.0
        self.port = None

    @property
    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, port):
        self.stop()
        exe = cloudflared_exe()
        if not exe:
            return False
        self.url, self.port, self.started = None, port, time.time()
        log('Abriendo túnel Cloudflare...', 'INFO')
        self.proc = subprocess.Popen(
            [exe, 'tunnel', '--no-autoupdate', '--protocol', 'http2', '--url', f'http://localhost:{port}'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()
        return True

    def _reader(self, proc):
        # Debe seguir leyendo siempre: si la tubería se llena, cloudflared se congela.
        for line in proc.stdout:
            if self.proc is proc and not self.url:
                m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if m:
                    self.url = m.group(0)

    def exit_code(self):
        return self.proc.poll() if self.proc else None

    def stop(self):
        p, self.proc, self.url = self.proc, None, None
        if p and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()


# ============================================================================
# Supervisor principal
# ============================================================================
class Supervisor:
    def __init__(self):
        self.server = None
        self.tunnel = Tunnel()
        self.cfg = load_config()
        self.cfg_seen = cfg_mtime()
        self.state = 'off'
        self.internet = True
        self.started = time.time()
        self.startup_mail_done = False
        self.mailed_url = None
        self.shown_url = object()
        self.last_check = time.time()
        self.next_tunnel_try = 0
        self.browser_opened = False
        self.last_write = 0
        self.last_runtime = None
        self.crashes = []

    # --- servidor -----------------------------------------------------------
    def start_server(self):
        port = self.cfg['port']
        if not kill_port(port):
            log(f'El puerto {port} sigue ocupado.', 'ERROR')
        env = dict(os.environ, XONINAS_SUPERVISED='1', PYTHONUNBUFFERED='1')
        self.server = subprocess.Popen([sys.executable, str(SERVER_PY)], cwd=str(BASE_DIR), env=env)
        self.server_port = port
        log(f'Servidor XONINAS iniciado (PID {self.server.pid}) en el puerto {port}', 'OK')

    def check_server_proc(self):
        code = self.server.poll()
        if code is None:
            return
        if code == 0:
            log('El servidor se cerró normalmente. Saliendo.', 'WARN')
            raise KeyboardInterrupt
        if code == 3:
            log('Reinicio solicitado desde el panel de administración.', 'INFO')
        else:
            now = time.time()
            self.crashes = [t for t in self.crashes if now - t < 60] + [now]
            wait = 30 if len(self.crashes) > 5 else 3
            log(f'El servidor se detuvo (código {code}). Reiniciando en {wait} s...', 'ERROR')
            time.sleep(wait)
        self.cfg = load_config()
        self.start_server()
        if self.tunnel.alive and self.tunnel.port != self.cfg['port']:
            self.tunnel.stop()

    # --- estado compartido con la web ------------------------------------------
    def write_runtime(self, force=False):
        port = self.cfg['port']
        data = {'pid': os.getpid(), 'tunnel_url': self.tunnel.url, 'tunnel_state': self.state,
                'internet': self.internet, 'local_url': f'http://localhost:{port}',
                'lan_url': f'http://{lan_ip()}:{port}'}
        if force or data != self.last_runtime or time.time() - self.last_write > 15:
            self.last_runtime = data
            self.last_write = time.time()
            tmp = RUNTIME_PATH.with_suffix('.tmp')
            tmp.write_text(json.dumps(dict(data, updated=time.time())), encoding='utf-8')
            os.replace(tmp, RUNTIME_PATH)

    # --- túnel -------------------------------------------------------------------
    def tunnel_wanted(self):
        return bool(self.cfg.get('setup_done') and self.cfg['tunnel'].get('enabled'))

    def set_state(self, new):
        if new != self.state:
            msgs = {'no_internet': ('Sin red: reintentando cada %d s.' % NET_RETRY, 'WARN'),
                    'active': ('Túnel activo: %s' % self.tunnel.url, 'OK'),
                    'starting': ('Abriendo el túnel...', 'INFO'),
                    'off': ('Túnel desactivado.', 'INFO')}
            if new in msgs:
                log(*msgs[new])
            self.state = new

    def manage_tunnel(self):
        t, port = self.tunnel, self.cfg['port']
        if not self.tunnel_wanted():
            if t.proc:
                log('Túnel desactivado desde la configuración. Cerrándolo.', 'INFO')
                t.stop()
            self.set_state('waiting_setup' if not self.cfg.get('setup_done') else 'off')
            return
        if not self.internet:
            if t.proc:
                log('Se perdió la red: se cierra el túnel y se abrirá uno nuevo al volver.', 'WARN')
                t.stop()
            self.next_tunnel_try = 0
            self.set_state('no_internet')
            return
        if t.proc and not t.alive:                      # cloudflared murió solo
            log(f'cloudflared se cerró (código {t.exit_code()}). Se abrirá uno nuevo.', 'WARN')
            t.stop()
            self.next_tunnel_try = time.time() + TUNNEL_RESTART_DELAY
        if t.alive and t.url:
            if self.state != 'active':
                self.last_check = time.time()           # los 10 min cuentan desde que el túnel quedó activo
            self.set_state('active')
            return
        if t.alive:                                     # esperando la URL
            self.set_state('starting')
            if time.time() - t.started > TUNNEL_URL_TIMEOUT:
                log('cloudflared no entregó una URL a tiempo. Reintentando.', 'WARN')
                t.stop()
                self.next_tunnel_try = time.time() + TUNNEL_RESTART_DELAY
            return
        if time.time() < self.next_tunnel_try:
            return
        if not server_ok(port):
            self.set_state('starting')
            return
        if not ensure_cloudflared():
            self.set_state('cloudflared_missing')
            self.next_tunnel_try = time.time() + 120
            return
        self.set_state('starting')
        t.start(port)
        self.next_tunnel_try = time.time() + TUNNEL_RESTART_DELAY

    def verify_tunnel(self):
        """Cada 10 min hace ping (GET /health) al túnel; si no responde lo apaga y abre otro."""
        t = self.tunnel
        if not (t.alive and t.url) or time.time() - self.last_check < TUNNEL_CHECK_INTERVAL:
            return
        self.last_check = time.time()
        if not self.internet:
            return                                      # sin red ya se rehace el túnel al volver
        if not server_ok(self.cfg['port']):
            log('Ping al túnel omitido: el servidor local no responde.', 'WARN')
            return
        log(f'Ping al túnel ({TUNNEL_CHECK_INTERVAL // 60} min): {t.url}', 'INFO')
        if tunnel_responds(t.url, TUNNEL_CHECK_ATTEMPTS):
            log('El túnel respondió.', 'OK')
        elif not self.internet:
            log('Ping fallido por falta de red; se reintentará al volver.', 'WARN')
        else:
            log('El túnel NO respondió. Se apaga y se abre uno nuevo.', 'ERROR')
            t.stop()
            self.next_tunnel_try = 0

    def handle_command(self):
        try:
            cmd = json.loads(COMMAND_PATH.read_text(encoding='utf-8'))
            COMMAND_PATH.unlink()
        except (OSError, ValueError):
            return
        if cmd.get('cmd') == 'restart_tunnel':
            log('Nuevo túnel solicitado desde el panel de administración.', 'INFO')
            self.tunnel.stop()
            self.next_tunnel_try = 0

    # --- avisos ------------------------------------------------------------------
    def announce(self):
        port = self.cfg['port']
        url = self.tunnel.url
        ready = server_ok(port)
        if not ready:
            return
        local, lan = f'http://localhost:{port}', f'http://{lan_ip()}:{port}'
        if url != self.shown_url and (url or not self.tunnel_wanted() or time.time() - self.started > STARTUP_MAIL_WAIT):
            self.shown_url = url
            print_qrs(lan, url)
            if not self.cfg.get('setup_done'):
                log(f'Primera vez: abre {local}/setup para crear tu usuario y configurar el NAS.', 'WARN')
        if not self.cfg.get('setup_done') and not self.browser_opened and not SERVICE:
            self.browser_opened = True
            try:
                webbrowser.open(f'{local}/setup')
            except Exception:                          # noqa: BLE001
                pass
        em = self.cfg['email']
        if not (em.get('enabled') and self.cfg.get('setup_done')):
            return
        waited = time.time() - self.started
        if not self.startup_mail_done and em.get('on_start') and (url or not self.tunnel_wanted() or waited > STARTUP_MAIL_WAIT):
            self.startup_mail_done = True
            self.mailed_url = url
            send_mail_retry(self.cfg, 'XONINAS · servidor iniciado',
                            build_mail(self.cfg, 'El servidor XONINAS se inició.', local, lan, url))
        elif self.startup_mail_done and url and url != self.mailed_url and em.get('on_tunnel_change'):
            self.mailed_url = url
            send_mail_retry(self.cfg, 'XONINAS · nuevo enlace del túnel',
                            build_mail(self.cfg, 'El túnel de XONINAS se actualizó. Usa esta dirección nueva.', local, lan, url))
        elif not self.startup_mail_done and not em.get('on_start'):
            self.startup_mail_done = True
            self.mailed_url = url

    # --- bucle ---------------------------------------------------------------
    def run(self):
        self.start_server()
        threading.Thread(target=self._net_watch, daemon=True).start()
        while True:
            time.sleep(2)
            try:
                self.check_server_proc()
                if cfg_mtime() != self.cfg_seen:
                    self.cfg_seen = cfg_mtime()
                    self.cfg = load_config()
                self.handle_command()
                self.manage_tunnel()
                self.verify_tunnel()
                self.announce()
                self.write_runtime()
            except KeyboardInterrupt:
                raise
            except Exception as exc:                    # noqa: BLE001  el supervisor nunca debe caerse
                log(f'Error interno (continúa): {exc!r}', 'ERROR')
                time.sleep(3)

    def _net_watch(self):
        """Sin red reintenta cada 5 s; con red comprueba cada 10 s. Va en su hilo para no frenar el bucle."""
        while not STOPPING:
            t0 = time.time()
            try:
                was, self.internet = self.internet, internet_ok()
            except Exception:                           # noqa: BLE001
                was, self.internet = self.internet, False
            if self.internet and not was:
                log('Red recuperada.', 'OK')
                self.next_tunnel_try = 0
            elif not self.internet and was:
                log('Red perdida.', 'WARN')
            wait = NET_CHECK if self.internet else NET_RETRY
            time.sleep(max(0.5, wait - (time.time() - t0)))

    def shutdown(self):
        global STOPPING
        STOPPING = True
        log('Cerrando XONINAS...', 'WARN')
        self.tunnel.stop()
        if self.server and self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.server.kill()
        RUNTIME_PATH.unlink(missing_ok=True)
        try:
            if LOCK_PATH.read_text().strip() == str(os.getpid()):
                LOCK_PATH.unlink()
        except OSError:
            pass


# ============================================================================
# Main
# ============================================================================
def banner():
    print(f'{C.P}{C.BOLD}XONINAS 2026{C.X}  NAS local con carpetas protegidas')
    print(f'Sistema: {platform.system()} {platform.release()}   Carpeta: {BASE_DIR}')
    print('Configuración: desde el navegador (/setup la primera vez, luego /admin)\n')


def main():
    global SERVICE
    ap = argparse.ArgumentParser(description='Lanzador de XONINAS')
    ap.add_argument('--service', action='store_true')
    ap.add_argument('--autostart', choices=['on', 'off', 'status'])
    ap.add_argument('--test-email', action='store_true')
    args = ap.parse_args()

    if args.autostart:
        if args.autostart == 'status':
            print('on' if autostart_status() else 'off')
            return 0
        ok, msg = autostart_set(args.autostart == 'on')
        print(msg)
        return 0 if ok else 1
    if args.test_email:
        return cli_test_email()

    SERVICE = args.service
    if not SERVICE:
        os.system('cls' if platform.system() == 'Windows' else 'clear')
    banner()
    other = acquire_lock()
    if other:
        log(f'Ya hay otro lanzador de XONINAS activo (PID {other}). '
            'Si es el servicio: systemctl --user stop xoninas   (o: kill ' + str(other) + ')', 'ERROR')
        return 0 if SERVICE else 1
    if not SERVER_PY.exists():
        log('No se encuentra xoninas.py junto a start.py.', 'ERROR')
        try:
            LOCK_PATH.unlink()
        except OSError:
            pass
        return 1
    ensure_dependencies()

    def _term(*_):
        if not STOPPING:
            raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _term)
    sup = Supervisor()
    try:
        sup.run()
    except KeyboardInterrupt:
        pass
    finally:
        sup.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
