@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================
echo             My-pills - запуск
echo ============================================
echo.
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Не удалось установить зависимости. Проверь, установлен ли Python.
    pause
    exit /b 1
)
echo.
echo Открой сайт по адресу http://127.0.0.1:5000
python app.py
echo.
echo Приложение остановлено.
pause
