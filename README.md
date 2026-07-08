# 📀 XONINAS

**Sistema NAS local con carpetas protegidas y acceso remoto gratuito**  
Optimizado para equipos domésticos, Raspberry Pi y servidores personales.  
Desarrollado por Darian Alberto Camacho Salas – [XONIDU](https://github.com/XONIDU)

---

## 📋 Descripción

XONINAS es un servidor NAS (Network Attached Storage) basado en Python/Flask que convierte cualquier ordenador en un almacenamiento centralizado con:

- Carpetas con o sin contraseña (hash SHA‑256)
- Acceso desde cualquier dispositivo en la red local
- Túnel Cloudflare gratuito para acceso remoto (`*.trycloudflare.com`)
- Subida de archivos y carpetas completas
- Subcarpetas ilimitadas
- Interfaz moderna responsive (negro/verde/morado)
- Configuración en CSV (sin base de datos)

---

## 📦 Instalación

### 1. Clonado manual (Linux/macOS)

```bash
git clone https://github.com/XONIDU/xoninas.git
cd xoninas
python3 start.py
```

### 2. Comando `xoninstall` (recomendado para ecosistema XONI)

Agrega la función a tu `~/.bashrc`:

```bash
echo 'xoninstall() { if [ -z "$1" ]; then echo "Uso: xoninstall <repo>"; else git clone "https://github.com/XONIDU/$1.git"; fi; }' >> ~/.bashrc && source ~/.bashrc
```

Instala XONINAS:

```bash
xoninstall xoninas
cd xoninas
python3 start.py
```

### 3. Instalación con pip

```bash
pip install -r requisitos.txt
# o con --user / --break-system-packages según tu sistema
python3 start.py
```

### 4. Script para Windows (`INICIAR_XONINAS.bat`)

Guarda este contenido como `INICIAR_XONINAS.bat` junto a `start.py` y ejecútalo con doble clic:

```batch
@echo off
title XONINAS 2026 - NAS Local con Carpetas Protegidas
color 0A

cd /d "%~dp0"

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de administrador...
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B
)

if not exist "%~dp0start.py" (
    echo [ERROR] No se encuentra start.py en esta carpeta
    pause
    exit /B
)

cls
echo ============================================================
echo           XONINAS 2026 - NAS Local
echo              (Modo Administrador)
echo ============================================================
echo.
echo [OK] Permisos de administrador obtenidos
echo [INFO] Directorio de trabajo: %~dp0
echo.
echo Iniciando XONINAS...
echo [INFO] Accede a: http://localhost:5000
echo [INFO] Desde tu red local: http://<TU-IP>:5000
echo.
python start.py
pause
```

---

## ⚙️ Configuración inicial

Al ejecutar `start.py` por primera vez, el asistente te guiará:

1. **Ruta de almacenamiento** – Por defecto `./storage`, o personalizada.
2. **Clave maestra** – Contraseña de acceso. Si se deja vacía, se usa `admin`.
3. **Túnel Cloudflare** – Activa acceso remoto gratuito (opcional).

> Tras la configuración, el programa se cierra. **Vuelve a ejecutar `python3 start.py`** para iniciar el servidor.

---

## 🚀 Uso

### Acceso local

```bash
# Obtén tu IP local
hostname -I   # Linux/macOS
ipconfig       # Windows
```

Abre el navegador en: `http://<TU-IP>:5000` (ej: `http://192.168.1.45:5000`).  
Introduce la clave maestra (por defecto: `admin`).

### Acceso remoto (Cloudflare)

Si activaste el túnel, verás una URL como `https://xxxx.trycloudflare.com`. Compártela para acceso desde cualquier lugar.

### Gestión

- **Crear carpeta** – Nombre + contraseña opcional.
- **Entrar a carpeta** – Si está protegida, pide su contraseña una vez por sesión.
- **Subir archivos** – Múltiples archivos o carpetas completas.
- **Descargar** – Archivos individuales o carpetas como ZIP.
- **Cerrar sesión** – Botón en la barra de navegación.

---

## 🛠️ Configuración avanzada

| Archivo | Propósito |
|---------|-----------|
| `config.csv` | `storage_path,<ruta>` – Cambia con el servidor detenido. |
| `master.csv` | Hash de la clave maestra. Elimínalo para resetear. |
| `folders.csv` | Lista de carpetas: `name,password_hash,created`. |

### Cambiar puerto

Edita `xoninas.py` y `start.py`, cambia `port=5000` por el deseado.

### Cambiar límite de subida

En `xoninas.py`, modifica `MAX_CONTENT_LENGTH` (valor en bytes).

---

## 🐛 Problemas comunes y soluciones

| Problema | Solución |
|----------|----------|
| **pip no instalado** | `start.py` lo instala automáticamente. En Linux: `sudo apt install python3-pip` |
| **Puerto 5000 en uso** | Linux: `sudo fuser -k 5000/tcp` – Windows: `netstat -ano | findstr :5000` y mata el proceso |
| **No accesible en red** | Abre el firewall: `sudo ufw allow 5000/tcp` (Linux) o permite la app en Windows |
| **KeyError: 'STORAGE_FOLDER'** | Ejecuta `python3 start.py`, no `xoninas.py` directamente |
| **Cloudflare no funciona** | Asegura conexión a Internet; prueba `--protocol http2` o descarga manual `cloudflared` |

---

## 📄 Licencia

**Licencia Personalizada (no comercial)**

Copyright (c) 2026 Darian Alberto Camacho Salas 


Se concede permiso, de forma gratuita, a cualquier persona que obtenga una copia
de este software y los archivos de documentación asociados (el "Software"), para
usar el Software sin restricción, incluyendo sin limitación los derechos de uso,
copia, modificación, fusión, publicación, distribución, sublicencia y/o venta
de copias del Software, y para permitir a las personas a quienes se les
proporcione el Software hacerlo, sujeto a las siguientes condiciones:

1. El aviso de copyright anterior y este aviso de permiso deberán incluirse en
   todas las copias o partes sustanciales del Software.

2. Este software se proporciona **solo para fines educativos y personales**.
   El uso comercial está estrictamente prohibido sin el permiso previo por escrito
   del autor. El uso comercial incluye, entre otros:
   - Vender el software o cualquier obra derivada
   - Usar el software como parte de un servicio o producto comercial
   - Usar el software para actividades que generen ingresos

3. Cualquier modificación o trabajo derivado debe conservar el aviso de copyright
   original, esta licencia, y dar el crédito adecuado al autor original
   (Darian Alberto Camacho Salas).

4. El nombre del autor "Darian Alberto Camacho Salas" y la organización "XONIDU"
   deben ser acreditados en cualquier distribución pública o exhibición del
   software o sus derivados.

EL SOFTWARE SE PROPORCIONA "TAL CUAL", SIN GARANTÍA DE NINGÚN TIPO, EXPRESA O
IMPLÍCITA, INCLUYENDO PERO NO LIMITADO A LAS GARANTÍAS DE COMERCIABILIDAD,
ADECUACIÓN PARA UN PROPÓSITO PARTICULAR Y NO INFRACCIÓN. EN NINGÚN CASO LOS
AUTORES O TITULARES DE LOS DERECHOS DE AUTOR SERÁN RESPONSABLES DE NINGUNA
RECLAMACIÓN, DAÑO U OTRA RESPONSABILIDAD, YA SEA EN UNA ACCIÓN DE CONTRATO,
AGRAVIO O DE OTRO TIPO, QUE SURJA DE, O EN CONEXIÓN CON EL SOFTWARE O EL USO
U OTRO TIPO DE ACCIONES EN EL SOFTWARE.


Para consultas comerciales: [xonidu@gmail.com](mailto:xonidu@gmail.com)

---

## ✉️ Contacto

- **Autor:** Darian Alberto Camacho Salas  
- **Email:** xonidu@gmail.com  
- **GitHub:** [@XONIDU](https://github.com/XONIDU)  

---

**XONINAS** – Tu nube privada, simple y segura.
