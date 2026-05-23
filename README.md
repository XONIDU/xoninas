# 📀 XONINAS

**Sistema NAS local con carpetas protegidas y acceso remoto gratuito**  
Optimizado para equipos domésticos, Raspberry Pi y servidores personales.  
Desarrollado por Darian Alberto Camacho Salas – [XONIDU](https://github.com/XONIDU)

---

## 📋 Características

- ✅ **Carpetas con o sin contraseña** – Cada carpeta puede tener su propia clave (hash SHA‑256)  
- ✅ **Selección de ruta de almacenamiento** – Usa discos externos, unidades de red o cualquier carpeta del sistema  
- ✅ **Acceso en red local** – Comparte archivos con cualquier dispositivo de tu WiFi/Ethernet  
- ✅ **Túnel Cloudflare gratuito** – URL pública `*.trycloudflare.com` para acceso remoto sin necesidad de abrir puertos  
- ✅ **Subida sin límite práctico** – Por defecto hasta 10 GB por archivo (ajustable)  
- ✅ **Interfaz moderna** – Temática oscura (negro, verde neón y morado), totalmente responsive  
- ✅ **Autoreinicio y healthcheck** – El servidor se recupera automáticamente si falla  
- ✅ **Configuración en CSV** – Sin base de datos, fácil de respaldar y editar  
- ✅ **Instalación automática de dependencias** – Detecta el sistema operativo, instala pip, `cloudflared` y las librerías necesarias  

---

## 📦 Instalación

### Opción 1 – Clonado manual

```bash
git clone https://github.com/XONIDU/xoninas.git
cd xoninas
python3 start.py
```

### Opción 2 – Comando `xoninstall` (recomendado para futuras herramientas XONI)

Agrega la siguiente función a tu `~/.bashrc` con un solo comando:

```bash
echo 'xoninstall() { if [ -z "$1" ]; then echo "Uso: xoninstall <repo>"; echo "Ej: xoninstall xoniran"; else git clone "https://github.com/XONIDU/$1.git"; fi; }' >> ~/.bashrc && source ~/.bashrc && echo "✅ Listo. Usa: xoninstall xoninas"
```

Luego simplemente escribe:

```bash
xoninstall xoninas
cd xoninas
python3 start.py
```

> **Nota:** Esta función te servirá para instalar cualquier otra herramienta futura de XONIDU (por ejemplo `xoninstall xoniran`, `xoninstall xonicli`).

---

## 🔧 Configuración inicial

La **primera ejecución** de `start.py` te guiará paso a paso:

1. **Ruta de almacenamiento** – Puedes dejar la ruta por defecto (`storage`) o escribir una personalizada (ej: `/media/usb/nas`).  
2. **Clave maestra** – Contraseña para acceder al NAS. Si la dejas vacía, se usará `admin`.  
3. **Túnel Cloudflare** – Pregunta si quieres activar acceso remoto gratuito (URL `*.trycloudflare.com`).  

> Una vez completados estos pasos, el programa se cerrará. **Vuelve a ejecutar `python3 start.py`** para iniciar el servidor.

---

## 🚀 Uso

### Acceso desde la red local

1. Averigua la IP de tu ordenador:  
   ```bash
   hostname -I   # Linux/macOS
   ipconfig       # Windows
   ```
2. En cualquier otro dispositivo de la misma red, abre un navegador y ve a `http://<TU-IP>:5000` (ej: `http://192.168.1.45:5000`).  
3. Introduce la **clave maestra** (por defecto `admin`).

### Acceso remoto con Cloudflare

Si activaste el túnel, verás en la terminal una URL como `https://xxxx.trycloudflare.com`.  
Compártela (junto con la clave maestra) para acceder desde cualquier lugar.

### Gestión de carpetas y archivos

- **Crear carpeta** – Escribe un nombre y (opcionalmente) una contraseña.  
- **Entrar a una carpeta** – Si está protegida, se pedirá la contraseña una sola vez por sesión.  
- **Subir archivos** – Botón “Subir archivo” (límite por defecto 10 GB).  
- **Descargar / eliminar archivos** – Botones junto a cada archivo.  
- **Cerrar sesión** – Botón “Cerrar sesión” (borra la clave maestra y los permisos de carpetas).

---

## 📁 Estructura del paquete

| Archivo / Directorio       | Ubicación                               |
|----------------------------|------------------------------------------|
| `xoninas.py`               | Directorio de instalación (donde se clonó) |
| `start.py`                 | Mismo directorio                         |
| `templates/`               | Mismo directorio (HTML de la interfaz)   |
| `config.csv`               | Mismo directorio (ruta de almacenamiento) |
| `master.csv`               | Mismo directorio (hash de la clave maestra) |
| `folders.csv`              | Mismo directorio (lista de carpetas)     |
| Ruta de almacenamiento     | La que elijas (ej: `/home/usuario/nas_data`) |

---

## 🛠️ Configuración manual (archivos CSV)

- **`config.csv`** – Contiene `storage_path,<ruta>`. Cambia la ruta con el servidor detenido.  
- **`master.csv`** – Almacena el hash SHA‑256 de la clave maestra. Elimínalo para resetear la clave.  
- **`folders.csv`** – Lista de carpetas: `name`, `password_hash` (vacío = sin contraseña), `created`.

---

## 🧪 Pruebas

Ejecuta directamente el servidor:

```bash
python3 xoninas.py
```

Si todo funciona, verás `🚀 XONINAS NAS iniciado en http://0.0.0.0:5000`.

---

## 🐛 Problemas comunes y soluciones

| Problema | Solución |
|----------|----------|
| **`pip` no instalado** | El script lo instala automáticamente. Si falla, instálalo manualmente (ej: `sudo apt install python3-pip`). |
| **Puerto 5000 en uso** | Linux/macOS: `sudo fuser -k 5000/tcp` – Windows: `netstat -ano | findstr :5000` y mata el proceso. |
| **No accesible en la red** | Abre el firewall: `sudo ufw allow 5000/tcp` (Linux) o permite la aplicación en Windows Defender. |
| **La sesión no se guarda** | Usa `http://127.0.0.1:5000` o `http://<IP>` en lugar de `localhost`; prueba otro navegador. |
| **Subida de archivos grandes** | Edita `MAX_CONTENT_LENGTH` en `xoninas.py` (valor en bytes). |
| **Cloudflare no funciona** | Asegúrate de tener Internet; descarga `cloudflared` manualmente desde [GitHub](https://github.com/cloudflare/cloudflared/releases) si falla. |

---

## 📄 Licencia

© 2026 Darian Alberto Camacho Salas (XONIDU)  
Todos los derechos reservados. No se permite la copia, distribución o modificación sin autorización explícita.

---

## ✉️ Contacto

- **Creador:** Darian Alberto Camacho Salas  
- **Email:** xonidu@gmail.com  
- **GitHub:** [@XONIDU](https://github.com/XONIDU)  

---

Hecho con 🖥️ y código para los amantes del almacenamiento autogestionado.  
**XONINAS** – Tu nube privada, simple y segura.


