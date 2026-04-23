@echo off
cd /d "%~dp0"
if not exist "models\intent_model.pkl" (
    echo Training model first...
    python train.py
    echo.
)
echo Starting Voice Assistant...
python assistant.py %*
