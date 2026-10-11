@echo off
echo ============================================
echo   Inclusitec - Instalacao de Dependencias
echo ============================================
echo.

echo Instalando dependencias Python...
pip install -r requirements.txt

echo.
echo ============================================
echo   Instalacao concluida!
echo ============================================
echo.
echo Para iniciar o servidor (backend + frontend web):
echo   python -m flask --app api.index run
echo.
echo Depois abra no navegador:
echo   http://localhost:5000
echo.
echo Versao online: https://inclusitec.com
echo.
echo Para iniciar o cliente desktop (frontend Python):
echo   python desktop\client.py
echo.
pause
