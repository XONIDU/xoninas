#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XONINAS - Módulo de seguridad y monitoreo del sistema
=====================================================
Funcionalidades:
  * Estado del ordenador: temperatura, RAM, disco, CPU
  * Detección de posibles ataques DDoS (demasiadas conexiones desde una IP)
  * Detección de fuerza bruta (intentos fallidos de login)
  * Geobloqueo por países (permitir/denegar IPs según país)
  * Todo activable/desactivable desde /admin

No guarda registros permanentes en disco: el estado se calcula en caliente.
"""

import os
import re
import socket
import subprocess
import threading
import time
import requests
from pathlib import Path

# --------------------------------------------------------------------------
# Caché de geolocalización (en memoria, nada en disco)
# --------------------------------------------------------------------------

_GEO_CACHE = {}
_GEO_CACHE_LOCK = threading.Lock()
_GEO_TTL = 30 * 60  # 30 minutos

# Rangos de IP privadas y reservadas (nunca se geobloquean)
_PRIVATE_CIDRS = [
    ('10.0.0.0', '255.0.0.0'),
    ('172.16.0.0', '255.240.0.0'),
    ('192.168.0.0', '255.255.0.0'),
    ('127.0.0.0', '255.0.0.0'),
    ('::1', 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'),
    ('fe80::', 'ffff:ffff:ffff:ffff::'),
    ('fc00::', 'ffff:ffff::'),
]


def _ip_in_cidr(ip, net, mask):
    try:
        import struct
        ip_packed = socket.inet_pton(socket.AF_INET6 if ':' in ip else socket.AF_INET, ip)
        net_packed = socket.inet_pton(socket.AF_INET6 if ':' in net else socket.AF_INET, net)
        mask_packed = socket.inet_pton(socket.AF_INET6 if ':' in mask else socket.AF_INET, mask)
        ip_int = struct.unpack('!Q' if ':' in ip else '!I', ip_packed)[0] if ':' not in ip else int.from_bytes(ip_packed, 'big')
        net_int = struct.unpack('!Q' if ':' in net else '!I', net_packed)[0] if ':' not in net else int.from_bytes(net_packed, 'big')
        mask_int = struct.unpack('!Q' if ':' in mask else '!I', mask_packed)[0] if ':' not in mask else int.from_bytes(mask_packed, 'big')
        return (ip_int & mask_int) == (net_int & mask_int)
    except OSError:
        return False


def es_ip_privada(ip):
    for net, mask in _PRIVATE_CIDRS:
        if _ip_in_cidr(ip, net, mask):
            return True
    return False


# --------------------------------------------------------------------------
# Estado del sistema
# --------------------------------------------------------------------------

def _leer_temperatura_zona(zona):
    """Lee la temperatura de una zona térmica de /sys (milígrados Celsius)."""
    try:
        path = Path('/sys/class/thermal') / zona / 'temp'
        if path.exists():
            mil = int(path.read_text().strip())
            return mil / 1000.0
    except (OSError, ValueError):
        pass
    return None


def _nombre_zona(zona):
    try:
        path = Path('/sys/class/thermal') / zona / 'type'
        if path.exists():
            return path.read_text().strip()
    except OSError:
        pass
    return zona


def _temperatura_sensores():
    """Intenta obtener temperatura con el comando sensors."""
    try:
        r = subprocess.run(['sensors'], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            temps = []
            for linea in r.stdout.splitlines():
                m = re.search(r'(\+?\d+\.\d+)\s*°C', linea)
                if m:
                    valor = float(m.group(1))
                    if 20 < valor < 110:
                        temps.append(valor)
            if temps:
                return max(temps)
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_system_stats():
    """Devuelve un diccionario con temperatura, RAM, disco y CPU."""
    import psutil

    stats = {
        'temperatura': None,
        'temperatura_zona': '',
        'ram_total': 0,
        'ram_usada': 0,
        'ram_libre': 0,
        'ram_porcentaje': 0,
        'disco_total': 0,
        'disco_usado': 0,
        'disco_libre': 0,
        'disco_porcentaje': 0,
        'cpu_porcentaje': 0,
        'cpu_count': 0,
        'uptime': 0,
        'uptime_formateado': '',
    }

    # Temperatura
    temp = _temperatura_sensores()
    zona_nombre = ''
    if temp is None:
        # Leer de /sys/class/thermal
        thermal_dir = Path('/sys/class/thermal')
        if thermal_dir.exists():
            for zona in sorted(thermal_dir.iterdir()):
                if zona.name.startswith('thermal_zone'):
                    t = _leer_temperatura_zona(zona.name)
                    if t is not None and 20 < t < 110:
                        temp = t
                        zona_nombre = _nombre_zona(zona.name)
                        break
    if temp is not None:
        stats['temperatura'] = round(temp, 1)
        stats['temperatura_zona'] = zona_nombre or 'sensores'

    # RAM
    try:
        ram = psutil.virtual_memory()
        stats['ram_total'] = ram.total
        stats['ram_usada'] = ram.used
        stats['ram_libre'] = ram.available
        stats['ram_porcentaje'] = round(ram.percent, 1)
    except Exception:
        pass

    # Disco (raíz)
    try:
        disco = psutil.disk_usage('/')
        stats['disco_total'] = disco.total
        stats['disco_usado'] = disco.used
        stats['disco_libre'] = disco.free
        stats['disco_porcentaje'] = round(disco.percent, 1)
    except Exception:
        pass

    # CPU
    try:
        stats['cpu_porcentaje'] = round(psutil.cpu_percent(interval=0.5), 1)
        stats['cpu_count'] = psutil.cpu_count() or 1
    except Exception:
        pass

    # Uptime
    try:
        stats['uptime'] = int(time.time() - psutil.boot_time())
        stats['uptime_formateado'] = _formatear_uptime(stats['uptime'])
    except Exception:
        pass

    return stats


def _formatear_uptime(segundos):
    dias = segundos // 86400
    horas = (segundos % 86400) // 3600
    minutos = (segundos % 3600) // 60
    partes = []
    if dias:
        partes.append(f'{dias} día{"s" if dias != 1 else ""}')
    if horas:
        partes.append(f'{horas} hora{"s" if horas != 1 else ""}')
    if minutos:
        partes.append(f'{minutos} minuto{"s" if minutos != 1 else ""}')
    if not partes:
        partes.append('menos de un minuto')
    return ', '.join(partes)


# --------------------------------------------------------------------------
# Detección de DDoS (conexiones por IP)
# --------------------------------------------------------------------------

def _conexiones_por_ip():
    """Devuelve un dict {ip: num_conexiones} leyendo /proc/net/tcp y /proc/net/tcp6."""
    result = {}
    for archivo in ('/proc/net/tcp', '/proc/net/tcp6'):
        try:
            with open(archivo, 'r') as f:
                lineas = f.readlines()[1:]  # saltar cabecera
        except OSError:
            continue
        for linea in lineas:
            partes = linea.split()
            if len(partes) < 10:
                continue
            estado = partes[3]
            # Estado ESTABLISHED = 06 en /proc/net/tcp
            if estado != '06':
                continue
            remota = partes[2]
            try:
                ip_puerto = remota.split(':')
                ip_hex = ip_puerto[0]
                ip = _hex_a_ip(ip_hex)
                if ip and not es_ip_privada(ip):
                    result[ip] = result.get(ip, 0) + 1
            except (ValueError, IndexError):
                continue
    return result


def _hex_a_ip(h):
    try:
        if len(h) == 8:  # IPv4
            n = int(h, 16)
            return socket.inet_ntoa(n.to_bytes(4, 'big'))
        elif len(h) == 32:  # IPv6
            n = int(h, 16)
            return socket.inet_ntop(socket.AF_INET6, n.to_bytes(16, 'big'))
    except (ValueError, OSError):
        pass
    return None


def check_ddos(umbral=50):
    """Devuelve lista de IPs con conexiones >= umbral, ordenadas."""
    conexiones = _conexiones_por_ip()
    sospechosas = [(ip, n) for ip, n in conexiones.items() if n >= umbral]
    sospechosas.sort(key=lambda x: x[1], reverse=True)
    return sospechosas


# --------------------------------------------------------------------------
# Geolocalización de IP (país)
# --------------------------------------------------------------------------

def get_ip_country(ip):
    """Devuelve el código de país (ISO 3166-1 alpha-2) de una IP.
    Usa caché en memoria. Consulta ip-api.com (gratis, sin clave)."""
    if es_ip_privada(ip):
        return 'LOCAL'

    with _GEO_CACHE_LOCK:
        entrada = _GEO_CACHE.get(ip)
        if entrada and time.time() - entrada['ts'] < _GEO_TTL:
            return entrada['pais']

    try:
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if r.status_code == 200:
            datos = r.json()
            pais = datos.get('countryCode', '--')
            with _GEO_CACHE_LOCK:
                _GEO_CACHE[ip] = {'pais': pais, 'ts': time.time()}
            return pais
    except Exception:
        pass

    with _GEO_CACHE_LOCK:
        _GEO_CACHE[ip] = {'pais': '--', 'ts': time.time()}
    return '--'


# --------------------------------------------------------------------------
# Geobloqueo
# --------------------------------------------------------------------------

def es_pais_bloqueado(ip, cfg):
    """Devuelve (bloqueado: bool, motivo: str, pais: str).
    Revisa cfg['security'] con geo_block_mode, geo_allow_list, geo_deny_list."""
    sec = cfg.get('security', {})
    if not sec.get('geo_block_enabled'):
        return False, '', ''

    pais = get_ip_country(ip)

    # IPs locales nunca se bloquean
    if pais == 'LOCAL' or not pais or pais == '--':
        return False, '', pais

    modo = sec.get('geo_block_mode', 'deny')
    allow = [p.strip().upper() for p in sec.get('geo_allow_list', []) if p.strip()]
    deny = [p.strip().upper() for p in sec.get('geo_deny_list', []) if p.strip()]

    if modo == 'allow':
        # Solo permitir países en la lista allow
        if pais in allow:
            return False, '', pais
        return True, f'País no permitido ({pais})', pais

    if modo == 'deny':
        # Bloquear países en la lista deny
        if pais in deny:
            return True, f'País bloqueado ({pais})', pais
        return False, '', pais

    return False, '', pais


# --------------------------------------------------------------------------
# Fuerza bruta (reutiliza el registro de xoninas.py si está disponible)
# --------------------------------------------------------------------------

_INTENTOS_FAILS = {}
_INTENTOS_LOCK = threading.Lock()


def registrar_fallo_bruteforce(ip):
    with _INTENTOS_LOCK:
        rec = _INTENTOS_FAILS.setdefault(ip, {'n': 0, 'until': 0})
        rec['n'] += 1
        if rec['n'] >= 5:
            rec['n'] = 0
            rec['until'] = time.time() + 300  # bloquear 5 min
        return rec['n'], rec['until']


def registrar_exito_bruteforce(ip):
    with _INTENTOS_LOCK:
        _INTENTOS_FAILS.pop(ip, None)


def esta_bloqueado_bruteforce(ip):
    with _INTENTOS_LOCK:
        rec = _INTENTOS_FAILS.get(ip)
        if rec and rec['until'] > time.time():
            return int(rec['until'] - time.time()) + 1
    return 0


def stats_bruteforce():
    with _INTENTOS_LOCK:
        ahora = time.time()
        activos = {ip: rec for ip, rec in _INTENTOS_FAILS.items()
                   if rec['until'] > ahora or rec['n'] > 0}
        return {
            'ips_sospechosas': len(activos),
            'detalle': sorted(
                [{'ip': ip, 'fallos': rec['n'],
                  'bloqueado_hasta': int(rec['until'] - ahora) if rec['until'] > ahora else 0}
                 for ip, rec in activos.items()],
                key=lambda x: x['fallos'], reverse=True)[:20],
        }
