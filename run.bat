@echo off

REM Crear entorno virtual
python -m venv ocr_env

REM Activar entorno virtual
call ocr_env\Scripts\activate

REM Instalar dependencias
pip install -r requirements.txt

REM Ejecutar la aplicación
python main.py

pause