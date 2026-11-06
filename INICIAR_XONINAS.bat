@echo off
setlocal EnableExtensions
title XONINAS 2026 - NAS Local con Carpetas Protegidas
color 0A

:: ============================================================
:: CARPETA DONDE ESTA ESTE .BAT (pushd tambien soporta rutas de red)
:: ============================================================
set "APPDIR=%~dp0"
pushd "%APPDIR%"

:: ============================================================
:: SOLICITAR PERMISOS DE ADMINISTRADOR
:: Al elevar, Windows inicia en System32, por eso se le pasa la
:: carpeta de trabajo (4to parametro de ShellExecute).
:: ============================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de administrador...
    echo.
    set "VBS=%temp%\getadmin_xoninas.vbs"
    > "%temp%\getadmin_xoninas.vbs" echo Set UAC = CreateObject^("Shell.Application"^)
    >> "%temp%\getadmin_xoninas.vbs" echo UAC.ShellExecute "cmd.exe", "/c """"%~f0"""" ", "%APPDIR%", "runas", 1
    cscript //nologo "%temp%\getadmin_xoninas.vbs"
    del "%temp%\getadmin_xoninas.vbs" >nul 2>&1
    exit /B
)

:: Ya somos administrador: volver a la carpeta del script
cd /d "%~dp0"

:: ============================================================
:: VERIFICAR QUE start.py EXISTE
:: ============================================================
if not exist "%~dp0start.py" (
    echo [ERROR] No se encuentra start.py en esta carpeta
    echo.
    echo Ruta actual: %~dp0
    echo.
    echo Asegurate de que start.py esta en la misma carpeta que este .bat
    echo.
    pause
    exit /B 1
)

:: ============================================================
:: ELEGIR PYTHON (venv del proyecto > launcher py > python del PATH)
:: ============================================================
set "PY="
if exist "%~dp0venv\Scripts\python.exe"  set "PY=%~dp0venv\Scripts\python.exe"
if not defined PY if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY (
    where py >nul 2>&1 && set "PY=py"
)
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERROR] No se encontro Python. Instalalo y marca "Add Python to PATH".
    echo.
    pause
    exit /B 1
)

:: ============================================================
:: OBTENER IP LOCAL
:: ============================================================
set "IP=<TU-IP>"
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "IP=%%a"
    goto :ipok
)
:ipok
set "IP=%IP: =%"

:: ============================================================
:: EJECUTAR start.py CON PERMISOS DE ADMINISTRADOR
:: ============================================================
cls
echo ============================================================
echo           XONINAS 2026 - NAS Local
echo              (Modo Administrador)
echo ============================================================
echo.
echo [OK] Permisos de administrador obtenidos
echo.
echo [INFO] Directorio de trabajo: %~dp0
echo [INFO] Python: %PY%
echo.
echo Iniciando XONINAS...
echo.
echo [INFO] Sistema de almacenamiento con carpetas protegidas
echo [INFO] Accede a: http://localhost:5000
echo [INFO] Desde tu red local: http://%IP%:5000
echo.
echo Presiona Ctrl+C para detener el servidor
echo ============================================================
echo.

"%PY%" "%~dp0start.py"

echo.
pause
popd
endlocal
