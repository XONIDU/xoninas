<div align="center">

<img src="static/logo.jpg" alt="XONINAS" width="180">

# XONINAS

**Tu nube privada: un NAS local con carpetas protegidas y acceso remoto gratuito.**

![Versión](https://img.shields.io/badge/versi%C3%B3n-5.0.0-2ea44f)
![Python](https://img.shields.io/badge/python-3.8%2B-3776ab)
![Plataformas](https://img.shields.io/badge/plataformas-Linux%20%C2%B7%20Windows%20%C2%B7%20macOS-444)
![Licencia](https://img.shields.io/badge/licencia-personalizada%20(no%20comercial)-7a3cff)

</div>

---

## Índice

- [Descripción](#descripción)
- [Características](#características)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Primer arranque](#primer-arranque)
- [Uso](#uso)
- [Acceso remoto con Cloudflare](#acceso-remoto-con-cloudflare)
- [Inicio automático](#inicio-automático)
- [Notificaciones por correo](#notificaciones-por-correo)
- [Arquitectura](#arquitectura)
- [Referencia de comandos](#referencia-de-comandos)
- [Seguridad](#seguridad)
- [Solución de problemas](#solución-de-problemas)
- [Licencia](#licencia)
- [Autor y contacto](#autor-y-contacto)

---

## Descripción

XONINAS convierte cualquier equipo (laptop, PC, Raspberry Pi o servidor doméstico) en un almacenamiento en red accesible desde el navegador, sin base de datos ni servicios externos de pago. Está escrito en Python con Flask y se configura por completo desde la web.

Pensado para uso personal y educativo: guardar y compartir archivos en casa, en el aula o en un laboratorio, con la opción de abrirlo a Internet mediante un túnel Cloudflare gratuito.

## Características

| Área | Detalle |
|------|---------|
| **Carpetas protegidas** | Carpetas abiertas o con clave propia. La clave se pide una vez por sesión. |
| **Archivos** | Subida de archivos sueltos y carpetas completas, subcarpetas, descarga individual o en ZIP. |
| **Impresión** | Módulo de impresión desde el navegador (menú *Impresión*). |
| **Acceso remoto** | Túnel Cloudflare gratuito (`*.trycloudflare.com`), activable desde `/admin`. |
| **Supervisión** | El lanzador reinicia el servidor si cae, vigila la red y rehace el túnel si deja de responder. |
| **Avisos por correo** | Correo al encender el NAS y cuando cambia la URL del túnel. |
| **Códigos QR** | QR de la red local y del túnel directamente en la terminal. |
| **Inicio automático** | Servicio de usuario `systemd` (Linux), LaunchAgent (macOS) o carpeta Inicio (Windows). |
| **Instancia única** | Bloqueo `start.lock` que impide dos lanzadores simultáneos. |
| **Sin sudo** | `cloudflared` se descarga a `bin/` automáticamente, sin contraseña de administrador. |
| **Interfaz** | Diseño responsive con tema claro, oscuro o automático. |

## Requisitos

- Python 3.8 o superior
- Conexión a Internet solo para el túnel remoto y el correo (la red local funciona sin ella)
- Dependencias de Python: `flask`, `werkzeug`, `waitress`, `qrcode` (el lanzador las instala si faltan)

## Instalación

### Con Git

```bash
git clone https://github.com/XONIDU/xoninas.git
cd xoninas
python3 start.py
```

### Con `xoninstall` (ecosistema XONIDU)

Agrega la función a tu `~/.bashrc`:

```bash
echo 'xoninstall() { if [ -z "$1" ]; then echo "Uso: xoninstall <repo>"; else git clone "https://github.com/XONIDU/$1.git"; fi; }' >> ~/.bashrc && source ~/.bashrc
```

Después:

```bash
xoninstall xoninas
cd xoninas
python3 start.py
```

### Dependencias manuales

Si prefieres instalarlas tú:

```bash
pip install -r requirements.txt
# En distribuciones con Python gestionado por el sistema:
pip install --user --break-system-packages -r requirements.txt
```

### Windows

```bat
cd xoninas
python start.py
```

## Primer arranque

1. Ejecuta `python3 start.py`. El lanzador libera el puerto, comprueba dependencias y levanta el servidor.
2. En la primera ejecución se abre automáticamente `http://localhost:5000/setup` en el navegador.
3. En `/setup` creas tu usuario y configuras el NAS (almacenamiento, túnel, correo).
4. Terminada la configuración, el panel de administración queda disponible en `/admin`.

Toda la configuración se guarda en `config.json`; no hace falta editar código.

## Uso

### Acceso local

Al arrancar, la terminal muestra las direcciones y sus códigos QR:

```
Red local                          Túnel Cloudflare
[QR]                               [QR]
http://192.168.1.45:5000           https://xxxx.trycloudflare.com
```

Abre la dirección de red local desde cualquier dispositivo conectado a la misma red.

### Gestión de carpetas

- **Crear carpeta:** nombre y clave opcional. Sin clave, la carpeta es accesible para cualquier usuario con sesión.
- **Abrir carpeta:** si está protegida, solicita su clave una vez por sesión.
- **Subir contenido:** archivos múltiples o carpetas completas, con barra de progreso.
- **Descargar:** archivos individuales o carpetas completas en ZIP.
- **Eliminar:** pide confirmación y no se puede deshacer.

### Administración

`/admin` concentra la configuración posterior al primer arranque: túnel, correo y destinatarios, inicio automático, reinicio del servidor y generación de un túnel nuevo.

## Acceso remoto con Cloudflare

XONINAS usa los *quick tunnels* de Cloudflare: no requieren cuenta ni dominio.

- Se activan o desactivan desde `/admin`.
- La URL (`https://xxxx.trycloudflare.com`) **cambia cada vez que se abre un túnel nuevo**. Si el correo está configurado, recibirás la dirección actualizada automáticamente.
- Cada 10 minutos el lanzador hace un ping al túnel; si no responde, lo cierra y abre uno nuevo.
- Si se pierde la red, el túnel se cierra y se vuelve a abrir al recuperarla.
- El binario `cloudflared` se descarga en `bin/` la primera vez que hace falta. Si ya lo tienes instalado en el sistema, se usa ese.

> En macOS instala `cloudflared` con `brew install cloudflared`.

## Inicio automático

Actívalo desde `/admin` o por línea de comandos:

```bash
python3 start.py --autostart on       # activar
python3 start.py --autostart off      # desactivar
python3 start.py --autostart status   # consultar
```

| Sistema | Mecanismo |
|---------|-----------|
| Linux | Servicio de usuario `systemd` (con *linger*, arranca sin iniciar sesión). Si no hay `systemctl`, entrada `.desktop` de autostart. |
| macOS | LaunchAgent (`com.xonidu.xoninas`) |
| Windows | Script en la carpeta Inicio |

Gestión del servicio en Linux:

```bash
systemctl --user status xoninas
systemctl --user stop xoninas
journalctl --user -u xoninas -f
```

> Usa **una sola** forma de arranque a la vez: el servicio o el lanzamiento manual. Si ya hay un lanzador activo, el segundo avisa y se cierra.

## Notificaciones por correo

El NAS puede avisarte por correo (Gmail) al encender y cuando cambia la URL del túnel.

1. Activa la verificación en dos pasos en tu cuenta de Google.
2. Genera una **clave de aplicación** en la configuración de seguridad de tu cuenta.
3. En `/setup` o `/admin`, introduce el remitente, la clave de aplicación y los destinatarios.
4. Comprueba la configuración:

```bash
python3 start.py --test-email
```

Si al encender el equipo la red tarda en estar lista, el envío se reintenta en segundo plano.

## Arquitectura

```
┌──────────────────────────── start.py (lanzador) ────────────────────────────┐
│  bloqueo de instancia · dependencias · QR · correo · inicio automático      │
│                                                                              │
│   ┌──────────────┐     ┌───────────────────┐     ┌───────────────────┐      │
│   │ xoninas.py   │◄────│ supervisor        │────►│ cloudflared       │      │
│   │ (Flask)      │     │ reinicio · red ·  │     │ (túnel opcional)  │      │
│   │ :5000        │     │ ping al túnel     │     │                   │      │
│   └──────┬───────┘     └───────────────────┘     └───────────────────┘      │
└──────────┼──────────────────────────────────────────────────────────────────┘
           │ lee / escribe
     config.json · runtime.json · command.json
```

El lanzador no guarda datos propios: lee `config.json` (que escribe la web) y se comunica con el servidor mediante `runtime.json` y `command.json`.

### Estructura del proyecto

```
xoninas/
├── start.py            Lanzador y supervisor
├── xoninas.py          Servidor web (Flask)
├── requirements.txt    Dependencias de Python
├── static/             style.css, app.js, logo.jpg
├── templates/          Plantillas HTML (Jinja2)
├── bin/                cloudflared descargado (se crea solo)
├── LICENSE             Licencia
└── LICENSE.custom      Condiciones de uso no comercial
```

### Archivos generados en ejecución

| Archivo | Propósito |
|---------|-----------|
| `config.json` | Configuración completa (puerto, túnel, correo, inicio automático) |
| `runtime.json` | Estado en vivo: URL del túnel, red, direcciones |
| `command.json` | Órdenes de la web al lanzador (por ejemplo, nuevo túnel) |
| `start.lock` | PID del lanzador activo |
| `xoninas_startup.log` | Registro del lanzador (rota al superar 1 MB) |

## Referencia de comandos

```bash
python3 start.py                          # arranque normal
python3 start.py --service                # sin limpiar pantalla (uso con servicio)
python3 start.py --autostart on|off|status
python3 start.py --test-email             # envía un correo de prueba
```

Para cambiar el puerto, edita el valor `port` en `config.json` con el servidor detenido (por defecto `5000`).

## Seguridad

XONINAS está pensado para uso doméstico y educativo. Antes de exponerlo a Internet ten en cuenta:

- **El túnel es público.** Cualquiera con la URL llega a la pantalla de acceso. Usa un usuario con clave robusta y claves distintas en las carpetas sensibles.
- **`config.json` contiene la clave de aplicación del correo.** Restringe sus permisos: `chmod 600 config.json`. No lo subas a un repositorio.
- **Firewall.** Para acceso en red local abre solo el puerto necesario (`sudo ufw allow 5000/tcp` en Linux).
- **No es un sistema de respaldo.** Mantén copias de seguridad de lo importante.
- **Solo tráfico local sin cifrar.** En la red local el acceso es por HTTP; el túnel de Cloudflare sí usa HTTPS.

## Solución de problemas

| Síntoma | Causa probable y solución |
|---------|---------------------------|
| El servidor se reinicia en bucle con `código -15` | Hay **dos lanzadores** corriendo (por ejemplo, el servicio y un arranque manual). Ejecuta `systemctl --user stop xoninas`, `pkill -f start.py`, `rm -f start.lock` y arranca solo uno. |
| «Ya hay otro lanzador activo» | El bloqueo detectó una instancia viva. Detenla con el comando que indica el mensaje, o elimina `start.lock` si quedó huérfano. |
| El puerto 5000 sigue ocupado | Linux: `sudo fuser -k 5000/tcp`. Windows: `netstat -ano \| findstr :5000` y cierra ese proceso. |
| No accesible desde otros dispositivos | Verifica que estén en la misma red y que el firewall permita el puerto. |
| El túnel no se abre | Comprueba la conexión a Internet y los mensajes en `xoninas_startup.log`. Si falla la descarga, baja `cloudflared` manualmente a `bin/` desde [github.com/cloudflare/cloudflared](https://github.com/cloudflare/cloudflared/releases). |
| «Gmail rechazó la clave» | Genera una clave de aplicación nueva y verifica que el remitente sea la cuenta correcta. |
| El logo o los estilos no cambian | Recarga sin caché con `Ctrl+Shift+R`. |

Revisa siempre el registro para más detalle:

```bash
tail -f xoninas_startup.log
```

## Licencia

**Licencia personalizada, no comercial.** Copyright © 2026 Darian Alberto Camacho Salas.

El software puede usarse, copiarse y modificarse **solo con fines educativos y personales**. Quedan prohibidos sin permiso previo y por escrito del autor la venta del software o de obras derivadas, su uso dentro de un servicio o producto comercial y su uso para actividades que generen ingresos. Toda copia o derivado debe conservar el aviso de copyright y la licencia, y acreditar a **Darian Alberto Camacho Salas** y a **XONIDU**.

El software se proporciona «tal cual», sin garantía de ningún tipo. Consulta los archivos [`LICENSE`](LICENSE) y [`LICENSE.custom`](LICENSE.custom) para el texto completo.

Consultas comerciales: [xonidu@gmail.com](mailto:xonidu@gmail.com)

## Autor y contacto

**Darian Alberto Camacho Salas** · [XONIDU](https://github.com/XONIDU) · #SomosXONIDU

- Correo: [xonidu@gmail.com](mailto:xonidu@gmail.com)
- GitHub: [@XONIDU](https://github.com/XONIDU)

---

<div align="center">

**XONINAS** · Tu nube privada, simple y segura.

</div>