<div align="center">
<img src="static/logo.jpg" alt="XONINAS" width="180">
XONINAS
Tu nube privada: un NAS local con carpetas protegidas, impresión remota y acceso remoto gratuito.
!Versión
!Python
!Plataformas
![Licencia](https://img.shields.io/badge/licencia-MIT%20(no%20comercial)-7a3cff)
</div>

Índice
Descripción
Características
Seguridad y monitoreo
Requisitos
Instalación
Primer arranque
Uso
Impresión remota
Acceso remoto con Cloudflare
Inicio automático
Notificaciones por correo
Arquitectura
Referencia de comandos
Seguridad
Solución de problemas
Licencia
Autor y contacto

Descripción
XONINAS convierte cualquier equipo (laptop, PC, Raspberry Pi o servidor doméstico) en un almacenamiento en red accesible desde el navegador, sin base de datos ni servicios externos de pago. Está escrito en Python con Flask y se configura por completo desde la web.
Pensado para uso personal y educativo: guardar y compartir archivos en casa, en el aula o en un laboratorio, con la opción de abrirlo a Internet mediante un túnel Cloudflare gratuito.
Características
Área
Detalle
Carpetas protegidas
Carpetas abiertas o con clave propia. La clave se pide una vez por sesión.
Archivos
Subida de archivos sueltos y carpetas completas (también en ZIP, que se descomprime solo), subcarpetas, descarga individual o en ZIP.
Impresión remota
Imprime archivos del NAS, archivos subidos o texto directo, desde cualquier dispositivo. Ver Impresión remota.
Seguridad y monitoreo
Panel en /admin/security: estado del equipo, detección de DDoS, bloqueo por fuerza bruta y geobloqueo por país. Ver Seguridad y monitoreo.
Acceso remoto
Túnel Cloudflare gratuito (*.trycloudflare.com), activable desde /admin.
Supervisión
El lanzador reinicia el servidor si cae, vigila la red y rehace el túnel si deja de responder.
Avisos por correo
Correo al encender el NAS y cuando cambia la URL del túnel. Varios destinatarios.
Códigos QR
QR de la red local, del túnel y de la página de impresión en la terminal y como SVG (/qr/local.svg, /qr/tunnel.svg, /qr/print.svg).
Inicio automático
Servicio de usuario systemd (Linux), LaunchAgent (macOS), carpeta Inicio o tarea programada (Windows).
Instancia única
Bloqueo start.lock que impide dos lanzadores simultáneos.
Sin sudo
cloudflared se descarga a bin/ automáticamente, sin contraseña de administrador.
Interfaz
Diseño responsive con tema claro, oscuro (por defecto) o automático.
Seguridad y monitoreo
El panel de seguridad está en /admin/security (también desde /admin). Cada módulo se puede activar o desactivar por separado.
Estado del equipo
Muestra en vivo:
Temperatura del equipo (sensores disponibles)
Uso de RAM (total, usada, libre, porcentaje)
Uso de disco (total, usado, libre, porcentaje)
Uso de CPU y número de núcleos
Tiempo de actividad (uptime)
Detección de posible DDoS
Cuenta las conexiones activas por IP. Si una IP supera el umbral configurado (por defecto 50 conexiones), el servidor le responde 429 Demasiadas conexiones hasta que baje. El panel muestra las IPs con más conexiones.
Protección contra fuerza bruta
Tras 5 intentos fallidos de inicio de sesión desde la misma IP, esa IP queda bloqueada 60 segundos.
Un inicio de sesión correcto limpia el contador.
El panel muestra los intentos recientes y las IPs bloqueadas.
Geobloqueo por país
Bloquea o permite el acceso según el país de origen de la IP (códigos ISO 3166-1 alpha-2, por ejemplo MX, US, BR).
Dos modos: denegar los países de la lista, o permitir solo los países de la lista.
La detección del país se hace por IP; si no se puede determinar, el acceso se permite.
Protección de formularios
Todos los formularios usan token CSRF: si la sesión expiró, el servidor rechaza el envío y pide recargar la página. El inicio de sesión detrás de un túnel Cloudflare identifica la IP real con el encabezado CF-Connecting-IP.
Requisitos
Python 3.8 o superior
Conexión a Internet solo para el túnel remoto y el correo (la red local funciona sin ella)
Dependencias de Python: flask, waitress, qrcode (el lanzador las instala si faltan)
Para imprimir documentos de Office (.doc, .docx, .odt, .rtf): LibreOffice instalado en el equipo
Instalación
Con Git
git clone https://github.com/XONIDU/xoninas.git
cd xoninas
python3 start.py
Con xoninstall (ecosistema XONIDU)
Agrega la función a tu ~/.bashrc:
echo 'xoninstall() { if [ -z "$1" ]; then echo "Uso: xoninstall <repo>"; else git clone "https://github.com/XONIDU/$1.git"; fi; }' >> ~/.bashrc && source ~/.bashrc
Después:
xoninstall xoninas
cd xoninas
python3 start.py
Dependencias manuales
Si prefieres instalarlas tú:
pip install -r requirements.txt
# En distribuciones con Python gestionado por el sistema:
pip install --user --break-system-packages -r requirements.txt
Windows
Doble clic en INICIAR_XONINAS.bat, o desde la terminal:
cd xoninas
python start.py
El .bat muestra un menú (inicia solo a los 10 segundos si no eliges nada) y permite activar el inicio automático con una tarea programada. También acepta INICIAR_XONINAS.bat /auto on|off|status. Usa el venv del proyecto si existe, y si no, el Python del PATH.
Primer arranque
Ejecuta python3 start.py. El lanzador libera el puerto, comprueba dependencias y levanta el servidor.
En la primera ejecución se abre automáticamente http://localhost:5000/setup en el navegador.
En /setup creas tu usuario y configuras el NAS: carpeta de almacenamiento, puerto, túnel, correo y apariencia.
Terminada la configuración, el panel de administración queda disponible en /admin.
Toda la configuración se guarda en config.json; no hace falta editar código.
Uso
Acceso local
Al arrancar, la terminal muestra las direcciones y sus códigos QR:
Red local                          Túnel Cloudflare
[QR]                               [QR]
http://192.168.1.45:5000           https://xxxx.trycloudflare.com
Abre la dirección de red local desde cualquier dispositivo conectado a la misma red.
Gestión de carpetas
Crear carpeta: nombre y clave opcional. Sin clave, la carpeta es accesible para cualquier usuario con sesión.
Abrir carpeta: si está protegida, solicita su clave una vez por sesión.
Subir contenido: archivos múltiples o carpetas completas, con barra de progreso. Un ZIP subido se descomprime automáticamente.
Descargar: archivos individuales o carpetas completas en ZIP.
Eliminar: pide confirmación y no se puede deshacer.
Administración
/admin concentra la configuración posterior al primer arranque: acceso al NAS, túnel, correo y destinatarios, inicio automático, reinicio del servidor, generación de un túnel nuevo y apariencia. El panel de seguridad vive en /admin/security.
Impresión remota
El módulo de impresión está en el menú Impresión (/print). Funciona desde cualquier dispositivo con acceso al NAS, incluido el móvil.
Archivos del NAS: elige un archivo guardado e imprímelo sin descargarlo.
Subir e imprimir: sube un archivo y se imprime directamente.
Imprimir texto: escribe o pega texto y se imprime como documento.
Cola de impresión: consulta los trabajos en curso en /print/queue.json.
Formatos que se pueden imprimir
PDF, TXT e imágenes (JPG, PNG, GIF, BMP). Los documentos de Office (DOC, DOCX, ODT, RTF) se convierten a PDF automáticamente con LibreOffice antes de imprimirse.
Opciones de impresión
Copias: de 1 a 99.
Páginas: todas, o un rango como 1-3,5,8-10.
Paridad: todas, solo impares o solo pares.
Escala de grises: imprime en blanco y negro.
Acceso remoto con Cloudflare
XONINAS usa los quick tunnels de Cloudflare: no requieren cuenta ni dominio.
Se activan o desactivan desde /admin.
La URL (https://xxxx.trycloudflare.com) cambia cada vez que se abre un túnel nuevo. Si el correo está configurado, recibirás la dirección actualizada automáticamente.
Cada 10 minutos el lanzador hace un ping al túnel; si no responde, lo cierra y abre uno nuevo. El intervalo, los reintentos y el tiempo de espera se pueden ajustar en la configuración.
Si se pierde la red, el túnel se cierra y se vuelve a abrir al recuperarla. También se puede configurar para que intente rescatar el túnel anterior antes de crear uno nuevo.
El binario cloudflared se descarga en bin/ la primera vez que hace falta. Si ya lo tienes instalado en el sistema, se usa ese.
En macOS instala cloudflared con brew install cloudflared.
Inicio automático
Actívalo desde /admin o por línea de comandos:
python3 start.py --autostart on       # activar
python3 start.py --autostart off      # desactivar
python3 start.py --autostart status   # consultar
Sistema
Mecanismo
Linux
Servicio de usuario systemd (con linger, arranca sin iniciar sesión). Si no hay systemctl, entrada .desktop de autostart.
macOS
LaunchAgent (com.xonidu.xoninas)
Windows
Tarea programada con INICIAR_XONINAS.bat /auto on, o script en la carpeta Inicio
Gestión del servicio en Linux:
systemctl --user status xoninas
systemctl --user stop xoninas
journalctl --user -u xoninas -f
Usa una sola forma de arranque a la vez: el servicio o el lanzamiento manual. Si ya hay un lanzador activo, el segundo avisa y se cierra.
Notificaciones por correo
El NAS puede avisarte por correo (Gmail) al encender y cuando cambia la URL del túnel.
Activa la verificación en dos pasos en tu cuenta de Google.
Genera una clave de aplicación en la configuración de seguridad de tu cuenta.
En /setup o /admin, introduce el remitente, la clave de aplicación y los destinatarios. Puedes agregar varios y activar o desactivar cada uno.
Comprueba la configuración:
python3 start.py --test-email
Si al encender el equipo la red tarda en estar lista, el envío se reintenta en segundo plano.
Arquitectura
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
El lanzador no guarda datos propios: lee config.json (que escribe la web) y se comunica con el servidor mediante runtime.json y command.json. El módulo xninas_security.py aporta las estadísticas del equipo, la detección de DDoS, el geobloqueo y el registro de fuerza bruta.
Estructura del proyecto
xoninas/

├── start.py            Lanzador y supervisor
├── xoninas.py          Servidor web (Flask)
├── xninas_security.py  Estadísticas, DDoS, geobloqueo y fuerza bruta
├── requirements.txt    Dependencias de Python
├── INICIAR_XONINAS.bat Lanzador con menú para Windows
├── static/             style.css, app.js, logo.jpg
├── templates/          Plantillas HTML (Jinja2)
├── bin/                cloudflared descargado (se crea solo)
├── data/               folders.json (carpetas y claves)
├── LICENSE             Licencia
└── LICENSE.custom      Condiciones de uso no comercial
Archivos generados en ejecución
Archivo
Propósito
config.json
Configuración completa (puerto, túnel, correo, seguridad, inicio automático)
runtime.json
Estado en vivo: URL del túnel, red, direcciones
command.json
Órdenes de la web al lanzador (por ejemplo, nuevo túnel)
start.lock
PID del lanzador activo
data/folders.json
Carpetas creadas y sus claves
xoninas_startup.log
Registro del lanzador (rota al superar 1 MB)
Endpoints principales
Ruta
Qué hace
/
Lista de carpetas
/setup
Configuración inicial (solo la primera vez)
/login, /logout
Sesión de administrador
/admin
Panel de administración
/admin/security
Seguridad y monitoreo
/admin/status
Estado del servidor en JSON
/print
Impresión remota
/print/queue.json
Cola de impresión en JSON
/qr/local.svg, /qr/tunnel.svg, /qr/print.svg
Códigos QR en SVG (red local, túnel, impresión)
/health
Salud del servidor (ok)
Referencia de comandos
python3 start.py                          # arranque normal
python3 start.py --service                # sin limpiar pantalla (uso con servicio)
python3 start.py --autostart on|off|status
python3 start.py --test-email             # envía un correo de prueba
python3 start.py --install-cloudflared   # descarga cloudflared a bin/
Para cambiar el puerto, edita el valor port en config.json con el servidor detenido (por defecto 5000).
Seguridad
XONINAS está pensado para uso doméstico y educativo. Antes de exponerlo a Internet ten en cuenta:
El túnel es público. Cualquiera con la URL llega a la pantalla de acceso. Usa un usuario con clave robusta y claves distintas en las carpetas sensibles.
Activa el panel de seguridad (/admin/security) si vas a exponer el túnel: DDoS, fuerza bruta y geobloqueo están apagados por defecto.
config.json contiene la clave de aplicación del correo. Restringe sus permisos: chmod 600 config.json. No lo subas a un repositorio.
Firewall. Para acceso en red local abre solo el puerto necesario (sudo ufw allow 5000/tcp en Linux).
No es un sistema de respaldo. Mantén copias de seguridad de lo importante.
Solo tráfico local sin cifrar. En la red local el acceso es por HTTP; el túnel de Cloudflare sí usa HTTPS.
Solución de problemas
Síntoma
Causa probable y solución
El servidor se reinicia en bucle con código -15
Hay dos lanzadores corriendo (por ejemplo, el servicio y un arranque manual). Ejecuta systemctl --user stop xoninas, pkill -f start.py, rm -f start.lock y arranca solo uno.
«Ya hay otro lanzador activo»
El bloqueo detectó una instancia viva. Detenla con el comando que indica el mensaje, o elimina start.lock si quedó huérfano.
El puerto 5000 sigue ocupado
Linux: sudo fuser -k 5000/tcp. Windows: `netstat -ano
findstr :5000` y cierra ese proceso.
No accesible desde otros dispositivos
Verifica que estén en la misma red y que el firewall permita el puerto.
El túnel no se abre
Comprueba la conexión a Internet y los mensajes en xoninas_startup.log. Si falla la descarga, baja cloudflared manualmente a bin/ desde github.com/cloudflare/cloudflared.
«Gmail rechazó la clave»
Genera una clave de aplicación nueva y verifica que el remitente sea la cuenta correcta.
«La sesión expiró» al enviar un formulario
El token CSRF venció. Recarga la página e inténtalo de nuevo.
El logo o los estilos no cambian
Recarga sin caché con Ctrl+Shift+R.
Revisa siempre el registro para más detalle:
tail -f xoninas_startup.log
Licencia
Licencia MIT con cláusula no comercial. Copyright © 2026 Darian Alberto Camacho Salas.
El software puede usarse, copiarse y modificarse solo con fines educativos y personales. Quedan prohibidos sin permiso previo y por escrito del autor la venta, el uso comercial y la distribución con fines de lucro. Ver LICENSE y LICENSE.custom para el texto completo.
Autor y contacto
Darian Alberto Camacho Salas — github.com/XONIDU
