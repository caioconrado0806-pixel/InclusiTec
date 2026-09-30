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
echo Para iniciar o servidor, execute:
echo   python app.py
echo.
echo Depois abra no navegador:
echo   http://localhost:5000
echo.
pause
