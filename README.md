# Voice Assistant (Siri-like)

A local voice assistant that takes **voice commands**, predicts **intent** from `intents.json`, **executes** the action, and responds **on screen and by voice**.

## Setup

1. **Create a virtual environment (recommended)**

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   On Windows, if `PyAudio` fails, try:

   ```bash
   pip install pipwin
   pipwin install pyaudio
   ```

3. **Train the model** (uses `intents.json`)

   ```bash
   python train.py
   ```

   This creates `models/intent_model.pkl` and `models/label_encoder.pkl`.

## Run the assistant (Siri-like voice control)

- **Wake word mode** (like Siri/Alexa — say a wake phrase, then your command):

  ```bash
  python waku_launcher.py
  ```
   
  A window opens with an animated orb. Say **"Hey waku"**, **"Alexa"**, or **"Open Assistant"** (or **"Hey Assistant"**, **"Hey Voice"**) to activate. The orb animates and listens for your command, then runs it and speaks the response.

- **Voice mode** (always listening, no wake word):

  ```bash
  python assistant.py
  ```

- **Text-only mode** (type commands, no mic):

  ```bash
  python assistant.py --text
  ```

Say or type commands like:

- “Can you tell me a joke?” → tells a joke and says it out loud  
- “What time is it?” → says the current time  
- “Open notepad” / “Open Chrome” → opens the app  
- “Hello” → greeting  
- “Exit” or “Quit” → stops the assistant  

Output is shown **on screen** and **spoken** (when voice output is available).

## Test without microphone

Run the test script with **text commands** only:

```bash
python test_voice_assistant.py
```

This runs a set of sample commands and then lets you type more. To test with **real voice**:

```bash
python test_voice_assistant.py --voice
```

## Quick run (Windows)

Run `run_assistant.bat` to train (if needed) and start the assistant in voice mode.

## Project layout

| File | Purpose |
|------|--------|
| `intents.json` | Training data: phrases and labels |
| `train.py` | Trains intent classifier from intents.json, saves model |
| `intent_executor.py` | Maps intents to actions (open app, tell time, joke, etc.) |
| `assistant.py` | Main loop: voice/text in → intent → action → voice + screen out |
| `test_voice_assistant.py` | Test script for text and optional voice |
| `wake_assistant.py` | Wake-word mode: Siri-like UI, say "Hey Siri" / "Alexa" / "Open Assistant" then command |
| `run_assistant.bat` | Windows: train (if needed) and start assistant |
| `run_wake_assistant.bat` | Windows: train (if needed) and start wake-word assistant |

## Flow

1. **Input**: Voice (microphone) or text.  
2. **Intent**: Trained model predicts intent from `intents.json` labels.  
3. **Execute**: `intent_executor` runs the action (e.g. open app, tell time, tell joke).  
4. **Output**: Response is **printed** and **spoken** (e.g. “Can you tell me a joke?” → joke on screen + voice).
