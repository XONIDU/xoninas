# XONINAS 2026 v1.5.0

**Sistema NAS Local con Carpetas Protegidas y Almacenamiento en Ruta Elegida**

Desarrollado por: Darian Alberto Camacho Salas  
Organización: XONIDU  
Email: xonidu@gmail.com  
GitHub: @XONIDU

---

## 📋 Descripción

**XONINAS** es una aplicación web que convierte tu ordenador en un **servidor NAS (Network Attached Storage)** completo, permitiéndote:

- Crear **carpetas protegidas por contraseña** (o sin contraseña)
- Subir, descargar y eliminar archivos desde cualquier dispositivo de tu red local
- Elegir **dónde guardar físicamente los archivos** (disco externo, unidad de red, carpeta personalizada)
- Acceder desde cualquier navegador en la misma red

Ideal para uso doméstico, pequeñas oficinas, Raspberry Pi o como almacenamiento personal seguro. Todo el código es abierto y funciona completamente **sin servicios en la nube**.

El proyecto es una iniciativa de **XONIDU**, organización dedicada al código abierto, automatización y democratización del acceso tecnológico.

---

## ✨ Características Principales

| Característica | Descripción |
|----------------|-------------|
| 🗂️ **Carpetas con o sin contraseña** | Cada carpeta puede tener su propia clave (hash SHA-256) |
| 📁 **Selección de ruta de almacenamiento** | Elige dónde guardar los archivos (disco externo, red, etc.) |
| 🌐 **Acceso en red local** | Comparte archivos con cualquier dispositivo de tu WiFi/Ethernet |
| 🔐 **Clave maestra de acceso** | Protege todo el NAS con una única contraseña |
| 🚀 **Subida sin límite práctico** | Por defecto hasta 10 GB por archivo (ajustable) |
| 📱 **Diseño responsive** | Funciona en móviles, tablets y ordenadores |
| 🛡️ **Autoreinicio y healthcheck** | El servidor se recupera automáticamente si falla |
| 💾 **Almacenamiento en CSV** | Configuración ligera, fácil de respaldar y editar |
| ⚡ **Sin base de datos externa** | Solo archivos planos, mínimo consumo de recursos |

---

## 📁 Estructura del Proyecto

```
xoninas/
├── start.py                 # 🟢 LANZADOR UNIVERSAL (¡EJECUTA ESTE!)
├── xoninas.py               # 🔵 PROGRAMA PRINCIPAL (servidor Flask)
├── README.md                # Este archivo
├── templates/               # Interfaz web (HTML con CSS inline)
│   ├── login.html           # Pantalla de entrada (clave maestra)
│   ├── index.html           # Listado de carpetas
│   ├── folder_auth.html     # Solicitar contraseña de carpeta
│   └── folder_contents.html # Gestor de archivos dentro de carpeta
├── config.csv               # Ruta de almacenamiento elegida por el usuario
├── master.csv               # Clave maestra (hash SHA-256)
├── folders.csv              # Lista de carpetas y sus hashes de contraseña
└── (la ruta que elijas)     # Directorio raíz donde se guardan los archivos
```

---

## 🚀 ASÍ DE FÁCIL: SOLO EJECUTA `start.py`

El archivo `start.py` hace TODO por ti:

✅ Detecta tu sistema operativo y distribución (Windows, Linux, macOS)  
✅ Instala **pip automáticamente** si no está presente (usa apt, pacman, dnf, yum, zypper o ensurepip)  
✅ Instala las dependencias con los flags correctos (`--break-system-packages` en Arch/Fedora, `--user` en otros)  
✅ Te pregunta la **ruta de almacenamiento** (puedes usar un disco externo o ruta de red)  
✅ Configura la **clave maestra**  
✅ Inicia el servidor con autoreinicio y healthcheck  
✅ Hace el NAS accesible en toda tu red local (IP `0.0.0.0`)

### 🪟 Para Windows

```cmd
python start.py
```

### 🐧 Para Linux / 🍎 macOS

```bash
python3 start.py
```

---

## 🎨 CÓMO USAR XONINAS

### Primera ejecución (configuración)

Al ejecutar por primera vez, el sistema te guiará paso a paso:

1. **Selección de ruta de almacenamiento**  
   Puedes dejar la ruta por defecto (`storage`) o escribir otra, por ejemplo:
   ```
   /media/usb/nas
   D:\NAS_Archivos
   \\192.168.1.100\shared_folder
   ```
   > **Nota**: Las rutas de red deben estar montadas previamente en el sistema.

2. **Establecimiento de clave maestra**  
   Elige una contraseña para acceder al NAS.

3. **Inicio del servidor**  
   Tras configurar, el programa se cierra. **Vuelve a ejecutar `start.py`** para lanzar el servidor.

### Acceso desde la red local

1. Averigua la **IP de tu ordenador**:
   ```bash
   # Linux/macOS
   hostname -I
   # Windows
   ipconfig
   ```
   Normalmente será algo como `192.168.1.45` o `10.0.0.5`.

2. Desde **cualquier otro dispositivo** (móvil, tablet, otro PC) en la misma red, abre el navegador y ve a:
   ```
   http://192.168.1.45:5000
   ```

3. Introduce la **clave maestra** y ya puedes crear carpetas y subir archivos.

### Pantalla principal (listado de carpetas)

- **Crear carpeta**: escribe un nombre y (opcionalmente) una contraseña.  
  - Si dejas la contraseña vacía → carpeta **pública** (sin restricción).  
  - Si pones contraseña → carpeta **protegida** (pedirá la clave al entrar).
- **Entrar a una carpeta**: si está protegida, se te pedirá la contraseña una sola vez por sesión.
- **Eliminar carpeta**: borra la carpeta y todo su contenido (no se puede recuperar).

### Dentro de una carpeta

- **Subir archivos**: botón "Subir archivo". El límite por defecto es 10 GB (ajustable en `xoninas.py`).
- **Descargar archivos**: clic en "Descargar" junto al archivo.
- **Eliminar archivos**: clic en "Eliminar" (confirmación previa).

### Cierre de sesión

Usa el botón **"Cerrar sesión"** para salir. Se borrará el acceso a la clave maestra y los permisos temporales de carpetas protegidas.

---

## 🛠️ CONFIGURACIÓN MANUAL (archivos CSV)

### `config.csv` – Ruta de almacenamiento

```csv
storage_path,/home/usuario/XONINAS_DATA
```

Puedes editar este archivo (con el servidor detenido) para cambiar la ubicación donde se guardan todos los archivos.

### `master.csv` – Clave maestra

Contiene el hash SHA-256 de la clave maestra. Si pierdes la clave, elimina este archivo y reinicia para crear una nueva (perderás el acceso a las carpetas protegidas).

### `folders.csv` – Lista de carpetas

| Campo           | Descripción                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| `name`          | Nombre de la carpeta (visible en la web)                                    |
| `password_hash` | Hash SHA-256 de la contraseña (vacío si no tiene)                          |
| `created`       | Fecha y hora de creación                                                    |

Puedes editar este CSV manualmente para añadir o quitar carpetas.

---

## 📂 ¿DÓNDE SE GUARDAN LOS ARCHIVOS?

Todos los archivos se guardan en la **ruta que elegiste durante la configuración inicial**.  
Dentro de esa ruta, cada carpeta creada desde la web es un subdirectorio con su nombre.

Ejemplo:
```
Ruta elegida: /media/disco_externo/XONINAS
Contenido:
  /media/disco_externo/XONINAS/
    ├── Documentos/
    ├── Fotos/
    └── Videos/
```

Puedes copiar archivos directamente en esas carpetas usando el explorador de archivos del sistema; aparecerán automáticamente en la interfaz web.

---

## 🔧 PROBLEMAS COMUNES (Y SOLUCIONES)

### ❌ "Python no está instalado"

- Descarga Python desde [python.org](https://www.python.org/downloads/)
- En Windows, **marca "Add Python to PATH"** durante la instalación.

### ❌ Error "pip no encontrado" en Linux

El script `start.py` intenta instalar pip automáticamente. Si falla, instálalo manualmente:

```bash
# Debian/Ubuntu/Mint
sudo apt update && sudo apt install python3-pip

# Arch/Manjaro
sudo pacman -S python-pip

# Fedora
sudo dnf install python3-pip

# CentOS/RHEL
sudo yum install python3-pip
```

### ❌ El servidor no es accesible desde otros dispositivos

- Asegúrate de que el servidor se inició con `host='0.0.0.0'` (por defecto en el nuevo código).
- Verifica el **firewall** del equipo que ejecuta XONINAS:
  - Linux (ufw): `sudo ufw allow 5000/tcp`
  - Windows: permite la aplicación en el Firewall de Windows Defender
- Comprueba que los dispositivos están en la **misma red** (mismo router, mismo rango IP).

### ❌ La ruta de almacenamiento elegida no se puede escribir

El script intentará crearla, pero si no tiene permisos, el servidor fallará. Asegúrate de que el usuario que ejecuta XONINAS tenga permisos de lectura/escritura en esa ruta.

### ❌ Error "Address already in use" (puerto 5000 ocupado)

```bash
# Linux/macOS
sudo fuser -k 5000/tcp

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### ❌ La sesión no se guarda (vuelve a pedir login)

- Usa `http://127.0.0.1:5000` o `http://<tu-ip>:5000` (no `localhost`).
- Prueba en modo incógnito o con otro navegador.
- Borra las cookies del sitio.

### ❌ No puedo subir archivos grandes

El límite por defecto es 10 GB. Para cambiarlo, edita en `xoninas.py` la línea:

```python
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # Cambia el 10 por el valor deseado (en GB)
```

---

## ✅ LO QUE PUEDES HACER (Y LO QUE NO)

| ✅ SÍ                                               | ❌ NO                                                       |
|----------------------------------------------------|-------------------------------------------------------------|
| Usar XONINAS como NAS personal o en oficina       | Distribuir malware o contenido ilegal                      |
| Compartir el acceso a carpetas con contraseña     | Eliminar los créditos de XONIDU                            |
| Almacenar cualquier tipo de archivo               | Exponer el NAS a Internet sin HTTPS                        |
| Modificar el código y adaptarlo a tus necesidades | Vender el código como propio                               |
| Usar discos externos o unidades de red            | Usar rutas de red no montadas previamente                  |

---

## 📋 REQUISITOS TÉCNICOS

- Python 3.8 o superior
- Flask 2.3.3
- Werkzeug 2.3.0
- Waitress 2.1.2 (servidor de producción)
- Espacio en disco suficiente en la ruta elegida
- Permisos de escritura en la ruta de almacenamiento

---

## 📞 ¿NECESITAS AYUDA?

- 📸 Instagram: [@xonidu](https://instagram.com/xonidu)
- 📧 Email: xonidu@gmail.com
- 💻 GitHub: [XONIDU/xoninas](https://github.com/XONIDU/xoninas)

---

## 👤 CRÉDITOS

**Autor:** Darian Alberto Camacho Salas  
**Organización:** XONIDU  
**Email:** xonidu@gmail.com  
**GitHub:** [@XONIDU](https://github.com/XONIDU)  
**Web:** https://xonipage.xonidu.com/

---

## 📄 LICENCIA

Este proyecto es de código abierto. Siéntete libre de modificarlo, adaptarlo y distribuirlo según tus necesidades. El autor no se hace responsable del mal uso del software.

---

```
╔══════════════════════════════════════════════════════════╗
║                     XONINAS 2026 v1.0.0                  ║
║              NAS Local con Carpetas Protegidas            ║
║                Almacenamiento en ruta elegida             ║
║                                                           ║
║               Desarrollado por: Darian Alberto            ║
║                      Camacho Salas                        ║
║                      Organización: XONIDU                 ║
╚════════════════════════════════════════════════════════════╝
```

**XONINAS** – Tu almacenamiento local, simple y seguro.  
**XONIDU** – Distribuyendo conocimiento, construyendo comunidad.
