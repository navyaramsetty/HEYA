"""
wake_assistant.py  —  Waku Voice Assistant
Continuous-loop assistant powered by intents.json
Run: python wake_assistant.py
Say "quit" / "exit" / "bye" to stop.
"""

import json
import os
import sys
import time
import random
import datetime
import webbrowser
import subprocess
import platform
import threading

import speech_recognition as sr
import pyttsx3

# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────
INTENTS_FILE = os.path.join(os.path.dirname(__file__), "intents.json")
ASSISTANT_NAME = "Waku"
WAKE_WORDS = ["hey waku", "ok waku", "waku", "hello waku"]
USE_WAKE_WORD = False   # Set True to require wake-word before each command

# ──────────────────────────────────────────────────────────────
# TTS ENGINE
# ──────────────────────────────────────────────────────────────
engine = pyttsx3.init()
engine.setProperty("rate", 165)
engine.setProperty("volume", 1.0)
# Try to pick a natural-sounding voice
voices = engine.getProperty("voices")
for v in voices:
    if "zira" in v.name.lower() or "samantha" in v.name.lower() or "female" in v.name.lower():
        engine.setProperty("voice", v.id)
        break


def speak(text: str, animate=True) -> None:
    """Speak text and print it."""
    print(f"\n  🔊  {ASSISTANT_NAME}: {text}\n")
    engine.say(text)
    engine.runAndWait()


# ──────────────────────────────────────────────────────────────
# RECOGNIZER
# ──────────────────────────────────────────────────────────────
recognizer = sr.Recognizer()
recognizer.pause_threshold = 0.8
recognizer.energy_threshold = 300


def listen(timeout: int = 6, phrase_limit: int = 12) -> str:
    """Record from microphone and return recognised text (lower-cased)."""
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        print("  🎤  Listening...", end="", flush=True)
        try:
            audio = recognizer.listen(source, timeout=timeout,
                                      phrase_time_limit=phrase_limit)
            print()
        except sr.WaitTimeoutError:
            print(" (no input)")
            return ""

    try:
        text = recognizer.recognize_google(audio)
        print(f"  👤  You: {text}")
        return text.lower().strip()
    except sr.UnknownValueError:
        print(" (unclear)")
        return ""
    except sr.RequestError as e:
        print(f"\n  ⚠️  Speech API error: {e}")
        return ""


# ──────────────────────────────────────────────────────────────
# INTENT LOADER
# ──────────────────────────────────────────────────────────────
def load_intents(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("intents", [])
    except FileNotFoundError:
        print(f"  ⚠️  intents.json not found at {path}")
        return []


def match_intent(user_text: str, intents: list) -> dict | None:
    """Simple keyword-matching intent classifier."""
    user_words = set(user_text.lower().split())
    best_score = 0
    best_intent = None

    for intent in intents:
        for pattern in intent["patterns"]:
            pattern_words = set(pattern.lower().split())
            # Full phrase match = highest priority
            if pattern.lower() in user_text:
                return intent
            # Word-overlap score
            overlap = len(user_words & pattern_words)
            if overlap > best_score:
                best_score = overlap
                best_intent = intent

    return best_intent if best_score >= 1 else None


# ──────────────────────────────────────────────────────────────
# ACTION HANDLERS
# ──────────────────────────────────────────────────────────────
OS = platform.system()   # "Windows" | "Darwin" | "Linux"


def open_url(url: str, label: str) -> str:
    webbrowser.open(url)
    return f"Opening {label} for you."


def run_app(cmd_win, cmd_mac, cmd_linux) -> str:
    try:
        if OS == "Windows":
            os.system(f'start {cmd_win}')
        elif OS == "Darwin":
            os.system(f'open -a "{cmd_mac}"')
        else:
            subprocess.Popen(cmd_linux, shell=True)
        return "Done!"
    except Exception as e:
        return f"Sorry, I couldn't open that. {e}"


def get_system_info() -> str:
    import psutil
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    info = f"CPU usage is {cpu}%. RAM: {ram.percent}% used out of {round(ram.total/1e9,1)} GB."
    try:
        battery = psutil.sensors_battery()
        if battery:
            info += f" Battery at {int(battery.percent)}%."
    except Exception:
        pass
    return info


def take_screenshot() -> str:
    try:
        import pyautogui
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(os.path.expanduser("~"), f"screenshot_{ts}.png")
        pyautogui.screenshot(path)
        return f"Screenshot saved to your home folder as screenshot_{ts}.png"
    except ImportError:
        return "pyautogui is not installed. Run: pip install pyautogui"


def media_key(key: str) -> None:
    """Send a media key press (best-effort, platform-specific)."""
    try:
        import pyautogui
        pyautogui.press(key)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────
# ACTION DISPATCHER
# ──────────────────────────────────────────────────────────────
def dispatch_action(action_token: str, user_text: str) -> str:
    """Map __ACTION:xxx__ tokens to real behaviour."""
    a = action_token.strip("_").replace("ACTION:", "")

    # ── Time / Date ──────────────────────────────────────────
    if a == "get_time":
        return "The current time is " + datetime.datetime.now().strftime("%I:%M %p") + "."

    if a == "get_date":
        return "Today is " + datetime.datetime.now().strftime("%A, %B %d, %Y") + "."

    if a == "get_day":
        return "Today is " + datetime.datetime.now().strftime("%A") + "."

    # ── Websites ─────────────────────────────────────────────
    if a == "open_youtube":    return open_url("https://youtube.com",        "YouTube")
    if a == "open_google":     return open_url("https://google.com",         "Google")
    if a == "open_gmail":      return open_url("https://mail.google.com",    "Gmail")
    if a == "open_github":     return open_url("https://github.com",         "GitHub")
    if a == "open_wikipedia":  return open_url("https://wikipedia.org",      "Wikipedia")
    if a == "open_maps":       return open_url("https://maps.google.com",    "Google Maps")
    if a == "open_spotify":    return open_url("https://open.spotify.com",   "Spotify")
    if a == "open_netflix":    return open_url("https://netflix.com",        "Netflix")
    if a == "open_weather":    return open_url("https://weather.com",        "Weather")

    # ── Search ───────────────────────────────────────────────
    if a == "search_google":
        query = (user_text.lower()
                 .replace("search for", "")
                 .replace("google search", "")
                 .replace("search google for", "")
                 .replace("look up", "")
                 .replace("find information about", "")
                 .replace("search", "")
                 .strip())
        if not query:
            speak("What would you like me to search?")
            query = listen(timeout=6)
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return f"Searching Google for '{query}'."
        return "No search query provided."

    if a == "search_youtube":
        query = (user_text.lower()
                 .replace("search youtube for", "")
                 .replace("find on youtube", "")
                 .replace("youtube search for", "")
                 .replace("play on youtube", "")
                 .strip())
        if not query:
            speak("What should I search on YouTube?")
            query = listen(timeout=6)
        if query:
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            return f"Searching YouTube for '{query}'."
        return "No search query provided."

    # ── System apps ──────────────────────────────────────────
    if a == "open_calculator":
        if OS == "Windows":   os.system("start calc")
        elif OS == "Darwin":  os.system("open -a Calculator")
        else:                 subprocess.Popen("gnome-calculator", shell=True)
        return "Opening calculator."

    if a == "open_notepad":
        if OS == "Windows":   os.system("notepad")
        elif OS == "Darwin":  os.system("open -a TextEdit")
        else:                 subprocess.Popen("gedit", shell=True)
        return "Opening text editor."

    if a == "open_camera":
        if OS == "Windows":   os.system("start microsoft.windows.camera:")
        elif OS == "Darwin":  os.system("open -a FaceTime")
        else:                 subprocess.Popen("cheese", shell=True)
        return "Opening camera."

    # ── Volume ───────────────────────────────────────────────
    if a == "volume_up":
        if OS == "Windows":
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                vol = min(volume.GetMasterVolumeLevelScalar() + 0.1, 1.0)
                volume.SetMasterVolumeLevelScalar(vol, None)
            except Exception:
                media_key("volumeup")
        else:
            media_key("volumeup")
        return "Volume increased."

    if a == "volume_down":
        media_key("volumedown")
        return "Volume decreased."

    if a == "mute":
        media_key("volumemute")
        return "Muted."

    # ── Media ────────────────────────────────────────────────
    if a == "pause_music":
        media_key("playpause")
        return "Toggled play/pause."

    if a == "next_song":
        media_key("nexttrack")
        return "Skipping to next track."

    # ── Fun ──────────────────────────────────────────────────
    if a == "flip_coin":
        result = random.choice(["Heads! 🪙", "Tails! 🪙"])
        return f"I flipped a coin... it's {result}"

    if a == "roll_dice":
        result = random.randint(1, 6)
        return f"I rolled a dice... you got {result}!"

    # ── Screenshot ───────────────────────────────────────────
    if a == "screenshot":
        return take_screenshot()

    # ── System info ──────────────────────────────────────────
    if a == "system_info":
        try:
            return get_system_info()
        except ImportError:
            return "Install psutil for system info: pip install psutil"

    # ── Alarm / reminder (basic) ──────────────────────────────
    if a in ("set_alarm", "set_reminder"):
        return ("I can't set alarms directly yet, but you can open your system Clock app. "
                "Say 'open google' and use Google Calendar for reminders!")

    # ── Capabilities ─────────────────────────────────────────
    if a == "show_capabilities":
        return (
            "Here's what I can do: tell the time and date, open websites like YouTube, "
            "Google, Gmail, GitHub, Netflix and Spotify, search Google or YouTube, "
            "tell jokes and fun facts, open apps like calculator, notepad and camera, "
            "control your volume, take screenshots, flip a coin, roll a dice, "
            "and show system info. Just ask!"
        )

    return "I'm not sure how to do that yet."


# ──────────────────────────────────────────────────────────────
# COMMAND PROCESSOR
# ──────────────────────────────────────────────────────────────
def process_command(user_text: str, intents: list) -> bool:
    """
    Process one command. Returns False if assistant should quit.
    """
    if not user_text:
        return True

    intent = match_intent(user_text, intents)

    if intent is None:
        speak("I'm not sure I understood that. Could you try again?")
        return True

    # Farewell → quit
    if intent["tag"] == "farewell":
        speak(random.choice(intent["responses"]))
        return False

    # Pick a response
    response = random.choice(intent["responses"])

    # Handle action tokens
    if response.startswith("__ACTION:"):
        response = dispatch_action(response, user_text)

    speak(response)
    return True


# ──────────────────────────────────────────────────────────────
# STARTUP BANNER
# ──────────────────────────────────────────────────────────────
BANNER = r"""
  ╔══════════════════════════════════════════════════════╗
  ║                                                      ║
  ║    ██╗    ██╗ █████╗ ██╗  ██╗██╗   ██╗              ║
  ║    ██║    ██║██╔══██╗██║ ██╔╝██║   ██║              ║
  ║    ██║ █╗ ██║███████║█████╔╝ ██║   ██║              ║
  ║    ██║███╗██║██╔══██║██╔═██╗ ██║   ██║              ║
  ║    ╚███╔███╔╝██║  ██║██║  ██╗╚██████╔╝              ║
  ║     ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝               ║
  ║                                                      ║
  ║         Your Personal Voice Assistant                ║
  ║                                                      ║
  ╠══════════════════════════════════════════════════════╣
  ║  Say "hey waku" or just speak a command              ║
  ║  Say "what can you do" to list commands              ║
  ║  Say "quit" or "bye" to exit                         ║
  ╚══════════════════════════════════════════════════════╝
"""


# ──────────────────────────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────────────────────────
def main():
    print(BANNER)
    intents = load_intents(INTENTS_FILE)
    if not intents:
        print("  ⚠️  No intents loaded — check intents.json path.")
        sys.exit(1)

    print(f"  ✅  Loaded {len(intents)} intents.\n")
    speak(f"Hello! I'm {ASSISTANT_NAME}, your personal voice assistant. How can I help you today?")

    while True:
        try:
            # ── Wake-word mode (optional) ──────────────────
            if USE_WAKE_WORD:
                print(f"\n  💤  Waiting for wake word ({', '.join(WAKE_WORDS)})...")
                trigger = listen(timeout=10, phrase_limit=5)
                if not any(w in trigger for w in WAKE_WORDS):
                    continue
                speak("Yes? I'm listening.")

            # ── Listen for command ─────────────────────────
            command = listen(timeout=7, phrase_limit=12)

            keep_running = process_command(command, intents)

            if not keep_running:
                break

        except KeyboardInterrupt:
            speak("Keyboard interrupt detected. Goodbye!")
            break
        except Exception as e:
            print(f"\n  ⚠️  Unexpected error: {e}")
            time.sleep(1)
            continue

    print("\n  👋  Waku has shut down. Goodbye!\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
