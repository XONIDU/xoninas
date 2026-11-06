@echo off
setlocal EnableExtensions
title XONINAS 2026 - NAS Local con Carpetas Protegidas
color 0A

rem ============================================================
rem  USO
rem    INICIAR_XONINAS.bat                 menu (inicia solo a los 10 s)
rem    INICIAR_XONINAS.bat /auto on        activa el inicio automatico
rem    INICIAR_XONINAS.bat /auto off       lo desactiva
rem    INICIAR_XONINAS.bat /auto status    muestra el estado
rem ============================================================

set "APPDIR=%~dp0"
set "TASK=XONINAS"
set "HIDDEN=%~dp0xoninas_oculto.vbs"
set "STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\xoninas.vbs"
pushd "%APPDIR%"

rem ============================================================
rem  PERMISOS DE ADMINISTRADOR
rem  Al elevar, Windows inicia en System32, por eso se le pasa la
rem  carpeta de trabajo. Se conservan los argumentos (%*).
rem ============================================================
net session >nul 2>&1
if %errorlevel% neq 0 goto :elevar
goto :admin_ok

:elevar
echo Solicitando permisos de administrador...
echo.
set "UACVBS=%temp%\getadmin_xoninas.vbs"
> "%UACVBS%" echo Set UAC = CreateObject^("Shell.Application"^)
>> "%UACVBS%" echo UAC.ShellExecute "cmd.exe", "/c """"%~f0"" %*""", "%APPDIR%", "runas", 1
cscript //nologo "%UACVBS%"
del "%UACVBS%" >nul 2>&1
exit /B

:admin_ok
cd /d "%~dp0"

rem ============================================================
rem  VERIFICAR QUE start.py EXISTE
rem ============================================================
if not exist "%~dp0start.py" goto :sin_start

rem ============================================================
rem  ELEGIR PYTHON (venv del proyecto > launcher py > python del PATH)
rem  Siempre queda la ruta completa, la tarea programada la necesita.
rem ============================================================
set "PY="
if exist "%~dp0venv\Scripts\python.exe" set "PY=%~dp0venv\Scripts\python.exe"
if not defined PY if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY for /f "delims=" %%i in ('where py 2^>nul') do if not defined PY set "PY=%%i"
if not defined PY for /f "delims=" %%i in ('where python 2^>nul ^| findstr /v /i /c:"WindowsApps"') do if not defined PY set "PY=%%i"
if not defined PY goto :sin_python

rem ============================================================
rem  QUE HACER: argumentos o menu
rem ============================================================
set "OPC=1"
if /i "%~1"=="/auto" goto :arg_auto
if "%~1"=="" goto :menu
goto :dispatch

:arg_auto
set "OPC=4"
if /i "%~2"=="on" set "OPC=2"
if /i "%~2"=="off" set "OPC=3"
if /i "%~2"=="status" set "OPC=4"
goto :dispatch

:menu
cls
echo ============================================================
echo           XONINAS 2026 - NAS Local
echo ============================================================
echo.
echo   [1] Iniciar XONINAS ahora
echo   [2] Activar inicio automatico (al iniciar sesion en Windows)
echo   [3] Desactivar inicio automatico
echo   [4] Ver estado del inicio automatico
echo.
echo   Si no eliges nada, se inicia en 10 segundos.
echo.
choice /c 1234 /n /t 10 /d 1 /m "Elige una opcion: "
set "OPC=%errorlevel%"

:dispatch
if "%OPC%"=="2" goto :auto_on
if "%OPC%"=="3" goto :auto_off
if "%OPC%"=="4" goto :auto_status
goto :ejecutar

rem ============================================================
rem  ACTIVAR INICIO AUTOMATICO
rem  Crea una tarea programada que arranca XONINAS al iniciar sesion,
rem  con privilegios elevados y SIN aviso de UAC, sin ventana visible.
rem ============================================================
:auto_on
echo.
echo [INFO] Activando el inicio automatico...

rem Lanzador oculto: fija la carpeta de trabajo y no muestra ventana
> "%HIDDEN%" echo Set sh = CreateObject("WScript.Shell")
>> "%HIDDEN%" echo sh.CurrentDirectory = "%~dp0"
>> "%HIDDEN%" echo sh.Run """%PY%"" ""%~dp0start.py"" --service", 0, False

rem Evita un segundo lanzador: quita el inicio automatico hecho desde /admin
del "%STARTUP_VBS%" >nul 2>&1

schtasks /create /tn "%TASK%" /tr "wscript.exe //B \"%HIDDEN%\"" /sc onlogon /delay 0000:20 /rl highest /f >nul
if errorlevel 1 goto :auto_fallo

rem Ajustes pensados para una laptop: sin limite de 3 dias, sin detenerse con bateria
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(Get-ScheduledTask -TaskName '%TASK%').Settings; $s.DisallowStartIfOnBatteries=$false; $s.StopIfGoingOnBatteries=$false; $s.ExecutionTimeLimit='PT0S'; $s.StartWhenAvailable=$true; $s.RestartCount=3; $s.RestartInterval='PT1M'; Set-ScheduledTask -TaskName '%TASK%' -Settings $s | Out-Null" >nul 2>&1
if errorlevel 1 echo [AVISO] No se pudieron ajustar las opciones de bateria de la tarea.

echo.
echo [OK] Inicio automatico ACTIVADO.
echo      XONINAS arrancara solo 20 segundos despues de iniciar sesion,
echo      con permisos de administrador y sin pedir confirmacion.
echo.
choice /c SN /n /m "Quieres iniciarlo ahora mismo en segundo plano? [S/N] "
if errorlevel 2 goto :fin
schtasks /run /tn "%TASK%" >nul 2>&1
echo [OK] Iniciando en segundo plano. Abre http://localhost:5000
goto :fin

:auto_fallo
echo.
echo [ERROR] No se pudo crear la tarea programada.
del "%HIDDEN%" >nul 2>&1
goto :fin

rem ============================================================
rem  DESACTIVAR INICIO AUTOMATICO
rem ============================================================
:auto_off
echo.
schtasks /delete /tn "%TASK%" /f >nul 2>&1
del "%HIDDEN%" >nul 2>&1
del "%STARTUP_VBS%" >nul 2>&1
echo [OK] Inicio automatico DESACTIVADO.
echo      Si XONINAS esta corriendo ahora, sigue activo hasta que lo cierres.
goto :fin

rem ============================================================
rem  ESTADO
rem ============================================================
:auto_status
echo.
schtasks /query /tn "%TASK%" >nul 2>&1
if errorlevel 1 goto :status_off
echo [OK] Inicio automatico: ACTIVADO (tarea programada %TASK%)
goto :status_extra
:status_off
echo [INFO] Inicio automatico: DESACTIVADO
:status_extra
if exist "%STARTUP_VBS%" echo [AVISO] Existe tambien un inicio automatico creado desde /admin. Conviene dejar solo uno.
goto :fin

rem ============================================================
rem  EJECUTAR start.py CON PERMISOS DE ADMINISTRADOR (modo manual)
rem ============================================================
:ejecutar
set "IP=<TU-IP>"
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "IP=%%a"
    goto :ipok
)
:ipok
set "IP=%IP: =%"

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
echo [INFO] Inicio automatico: INICIAR_XONINAS.bat /auto on
echo.
echo Presiona Ctrl+C para detener el servidor
echo ============================================================
echo.

"%PY%" "%~dp0start.py"
goto :fin

rem ============================================================
rem  ERRORES
rem ============================================================
:sin_start
echo [ERROR] No se encuentra start.py en esta carpeta
echo.
echo Ruta actual: %~dp0
echo.
echo Asegurate de que start.py esta en la misma carpeta que este .bat
echo.
pause
exit /B 1

:sin_python
echo [ERROR] No se encontro Python. Instalalo y marca "Add Python to PATH".
echo.
pause
exit /B 1

:fin
echo.
pause
popd
endlocal
