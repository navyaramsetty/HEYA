@echo off
cd /d "%~dp0"
if not exist "models\intent_model.pkl" (
    echo Training model first...
    python train.py
    echo.
)
echo Starting Voice Assistant with Wake Word...
echo Say "Hey Siri", "Alexa", or "Open Assistant" to activate.
python wake_assistant.py %*
