@echo off
echo Deteniendo servidores en puertos 5000 y 5173...

:: Matar procesos en puerto 5000 (Backend Flask)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000') do (
    echo Matando proceso %%a en puerto 5000
    taskkill /F /PID %%a >nul 2>&1
)

:: Matar procesos en puerto 5173 (Frontend Vite)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173') do (
    echo Matando proceso %%a en puerto 5173
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Esperando 3 segundos...
timeout /t 3 /nobreak >nul

echo.
echo Iniciando Backend Flask...
cd "c:\Users\estro\Desktop\DeNuevo-ptrm\noox-id-back"
start "NooxID Backend" cmd /k "python main.py"

echo.
echo Esperando 5 segundos para que inicie el backend...
timeout /t 5 /nobreak >nul

echo.
echo Iniciando Frontend React...
cd "c:\Users\estro\Desktop\DeNuevo-ptrm\noox-id"
start "NooxID Frontend" cmd /k "npm run dev"

echo.
echo ✅ Servidores iniciando...
echo 🔧 Backend: http://localhost:5000
echo 🌐 Frontend: http://localhost:5173
echo.
pause
