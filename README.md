# XONINAS 2026 v1.0.0

**Sistema NAS Local con Carpetas Protegidas**

Desarrollado por: Darian Alberto Camacho Salas  
Organización: XONIDU  
Email: xonidu@gmail.com  
GitHub: @XONIDU

---

## 📋 Descripción

**XONINAS** es una aplicación web desarrollada en Python con Flask que convierte tu ordenador en un **NAS (Network Attached Storage) local**, permitiéndote crear carpetas protegidas por contraseña, subir y descargar archivos, todo desde una interfaz moderna y elegante con temática oscura (negro, verde neón y morado).

Ideal para uso doméstico, pequeñas oficinas o como almacenamiento personal seguro. No requiere servicios en la nube ni configuración compleja: todo se ejecuta localmente en tu red.

El proyecto es una iniciativa de **XONIDU**, una organización dedicada al desarrollo de código abierto con énfasis en automatización, optimización de recursos y democratización del acceso a herramientas tecnológicas.

---

## ✨ Características Principales

- **Configuración inicial por terminal**: Al ejecutar por primera vez, solicita la **clave maestra** de acceso al NAS.
- **Autenticación robusta**: Clave maestra para acceder al sistema + contraseñas opcionales por carpeta.
- **Gestión de carpetas**: Crea, elimina y protege carpetas con contraseña (o déjalas abiertas).
- **Subida y descarga de archivos**: Sube cualquier tipo de archivo (sin límite práctico de tamaño, hasta 10 GB por defecto).
- **Protección por carpeta**: Cada carpeta puede tener su propia contraseña, almacenada de forma segura (hash SHA-256).
- **Almacenamiento en CSV**: Las carpetas y sus hashes se guardan en `folders.csv`; la clave maestra en `master.csv`.
- **Interfaz bonita y responsive**: Diseño inspirado en openmediavault, totalmente adaptable a móvil y escritorio.
- **Servidor robusto**: Usa Waitress con autoreinicio y healthcheck para manejar múltiples conexiones.
- **Sin dependencias externas**: Todo el almacenamiento es local, sin necesidad de bases de datos ni servicios cloud.

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
├── storage/                 # Directorio donde se guardan las carpetas y archivos
├── master.csv               # Clave maestra (hash SHA-256)
└── folders.csv              # Lista de carpetas y sus hashes de contraseña
```

---

## 🚀 ASÍ DE FÁCIL: SOLO EJECUTA `start.py`

¡Ya no necesitas hacer nada más! El archivo `start.py` hace TODO por ti:

✅ Detecta automáticamente tu sistema operativo  
✅ Verifica qué dependencias faltan (Flask, Werkzeug, Waitress)  
✅ Las instala con los comandos correctos (soporta Arch Linux con `--break-system-packages`)  
✅ Ejecuta la configuración inicial si no existe `master.csv`  
✅ Inicia el servidor con autoreinicio y healthcheck  
✅ Abre el navegador automáticamente en `http://127.0.0.1:5000`

### 🪟 Para Windows

```cmd
python start.py
```

### 🐧 Para Linux / 🍎 macOS

```bash
python3 start.py
```

---

## 📦 ¿QUÉ HACE `start.py` POR DENTRO?

Cuando ejecutas `start.py`, automáticamente:

1. 🔍 Detecta si estás en Windows, Linux o Mac  
2. 📋 Verifica que las dependencias (Flask, Werkzeug, Waitress) estén instaladas  
3. 📥 Las instala con el comando `pip` adecuado (en Arch usa `--break-system-packages`)  
4. ⚙️ Ejecuta la configuración inicial si no existe `master.csv` (te pedirá la clave maestra por terminal)  
5. 🚀 Inicia el servidor con Waitress (4 threads, timeout largo)  
6. 🔄 Monitoriza el servidor y lo reinicia si falla  
7. 🌐 Abre el navegador automáticamente en `http://127.0.0.1:5000`

---

## 🎨 CÓMO USAR XONINAS

### Primera ejecución (configuración)

Al ejecutar por primera vez, el sistema te pedirá por **terminal**:

```
==================================================
    CONFIGURACIÓN INICIAL - CLAVE MAESTRA
==================================================
Clave maestra: ************
```

Introduce una contraseña que usarás para acceder al NAS (ej: `admin123`).  
La aplicación se cerrará después de guardar la clave. **Vuelve a ejecutar `python3 start.py`** para iniciar el servidor.

### Acceso al NAS

1. Abre tu navegador en `http://127.0.0.1:5000` (usa **127.0.0.1** en lugar de `localhost` para evitar problemas con cookies).
2. Introduce la **clave maestra** que configuraste.
3. Ya estás dentro del panel principal.

### Pantalla principal (listado de carpetas)

- **Crear carpeta**: Escribe un nombre y (opcionalmente) una contraseña. Si dejas la contraseña vacía, la carpeta será pública (sin acceso restringido).
- **Entrar a una carpeta**: Si está protegida, se te pedirá la contraseña. Una vez ingresada, la sesión recuerda el acceso.
- **Eliminar carpeta**: Borra la carpeta y todo su contenido (no se puede deshacer).

### Dentro de una carpeta

- **Subir archivos**: Botón "Subir archivo" – puedes subir cualquier tipo de archivo (el límite por defecto es 10 GB).
- **Descargar archivos**: Haz clic en "Descargar" junto al archivo.
- **Eliminar archivos**: Botón "Eliminar" (confirmación previa).

### Cierre de sesión

Usa el botón **"Cerrar sesión"** en la parte superior. Se borrará tanto la clave maestra como los accesos temporales a carpetas protegidas.

---

## 🛠️ CONFIGURACIÓN MANUAL (archivos CSV)

### `master.csv`

Almacena la **clave maestra** en forma de hash SHA-256.  
Si pierdes esta clave, elimina el archivo y reinicia el programa para crear una nueva.

### `folders.csv`

| Campo           | Descripción                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| `name`          | Nombre de la carpeta (visible en la web)                                    |
| `password_hash` | Hash SHA-256 de la contraseña de la carpeta (vacío si no tiene contraseña) |
| `created`       | Fecha y hora de creación                                                    |

Puedes editar este archivo manualmente (con un editor de texto) mientras el servidor no esté corriendo.

---

## 📂 ¿DÓNDE SE GUARDAN LOS ARCHIVOS?

Todos los archivos subidos se almacenan en la carpeta `storage/` dentro del directorio de XONINAS. Cada carpeta creada desde la web corresponde a un subdirectorio dentro de `storage/`.  
Puedes copiar archivos directamente a esas carpetas usando el explorador de archivos de tu sistema; aparecerán automáticamente en la interfaz web.

---

## 🔧 PROBLEMAS COMUNES (Y SOLUCIONES)

### ❌ "Python no está instalado"

- Descarga Python desde [python.org](https://www.python.org/downloads/)
- En Windows, **marca "Add Python to PATH"** durante la instalación.

### ❌ El servidor no responde o "Address already in use"

```bash
# Detener el proceso que usa el puerto 5000 (Linux/macOS)
sudo fuser -k 5000/tcp

# Reiniciar el servidor
python3 start.py
```

### ❌ No se encuentra `master.csv`

Ejecuta `python3 start.py` de nuevo. Si no aparece la configuración inicial, elimina `master.csv` manualmente y vuelve a ejecutar.

### ❌ Error de permisos en Linux

```bash
chmod +x start.py
python3 start.py
```

### ❌ Puerto 5000 en uso

Cambia el puerto en `start.py` (línea `--port=5000`) y en `xoninas.py` (línea `serve(app, host='127.0.0.1', port=5000, ...)`). Luego reinicia.

### ❌ La sesión no se guarda (vuelve a pedir login)

- Usa **`http://127.0.0.1:5000`** en lugar de `localhost`.
- Prueba en modo incógnito o con otro navegador.
- Verifica que las cookies no estén bloqueadas para `127.0.0.1`.

### ❌ No puedo subir archivos grandes

El límite por defecto es 10 GB. Si necesitas más, edita en `xoninas.py` la línea:

```python
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # Cambia el 10 por el valor deseado (en GB)
```

---

## ✅ LO QUE PUEDES HACER (Y LO QUE NO)

| ✅ SÍ                                               | ❌ NO                                                       |
|----------------------------------------------------|-------------------------------------------------------------|
| Usar XONINAS como NAS personal o en oficina       | Distribuir malware o contenido ilegal                      |
| Compartir el acceso a carpetas con contraseña     | Eliminar los créditos de XONIDU                            |
| Modificar el código y adaptarlo a tus necesidades | Vender el código como propio                               |
| Almacenar cualquier tipo de archivo               | Usar en entornos donde se requiera cifrado de extremo a extremo (no incluye HTTPS por defecto) |

---

## 📋 REQUISITOS TÉCNICOS

- Python 3.8 o superior
- Flask 2.3.3
- Werkzeug 2.3.0
- Waitress 2.1.2 (para el servidor)
- Espacio en disco para almacenar los archivos subidos

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
║                                                           ║
║               Desarrollado por: Darian Alberto            ║
║                      Camacho Salas                        ║
║                      Organización: XONIDU                 ║
╚════════════════════════════════════════════════════════════╝
```

**XONINAS** – Tu almacenamiento local, simple y seguro.  
**XONIDU** – Distribuyendo conocimiento, construyendo comunidad.

