"""
Siri-like Voice Assistant: voice in -> intent -> action -> voice + screen out.
Run this for continuous voice control. Uses trained model from train.py.
"""
import pickle
import re
import sys
from pathlib import Path

# Add project root
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from intent_executor import execute_intent

MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "intent_model.pkl"
LE_PATH = MODEL_DIR / "label_encoder.pkl"


def load_model():
    if not MODEL_PATH.exists() or not LE_PATH.exists():
        raise FileNotFoundError(
            "Model not found. Run: python train.py"
        )
    with open(MODEL_PATH, "rb") as f:
        pipe = pickle.load(f)
    with open(LE_PATH, "rb") as f:
        le = pickle.load(f)
    return pipe, le


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


# Keyword-based intent override so "open notepad" -> open_notepad, etc.
# Use word boundary for short words so "word" doesn't match "password".
OPEN_WORDS = ("open", "launch", "start", "run", "bring up", "fire up", "get", "please open", "open the")
CLOSE_WORDS = ("close", "exit", "shut", "terminate", "stop", "end", "turn off", "kill")

# (keyword in user text, open_intent, close_intent) — longer/more specific first for correct priority
KEYWORD_INTENTS = [
    # VS Code (before "code" alone)
    ("visual studio code", "open_vscode", "close_vscode"),
    ("vs code", "open_vscode", "close_vscode"),
    ("vscode", "open_vscode", "close_vscode"),
    # Browsers & search
    ("google chrome", "open_chrome", "close_chrome"),
    ("chrome", "open_chrome", "close_chrome"),
    ("microsoft edge", "open_edge", "close_edge"),
    ("edge", "open_edge", "close_edge"),
    ("google drive", "open_google_drive", "close_google_drive"),
    ("google", "open_google", "close_google"),
    ("gmail", "open_gmail", "close_gmail"),
    ("youtube", "open_youtube", "close_youtube"),
    # Microsoft Office (specific before generic)
    ("microsoft word", "open_word", "close_word"),
    ("microsoft excel", "open_excel", "close_excel"),
    ("microsoft powerpoint", "open_powerpoint", "close_powerpoint"),
    ("microsoft outlook", "open_outlook", "close_outlook"),
    ("powerpoint", "open_powerpoint", "close_powerpoint"),
    ("word", "open_word", "close_word"),
    ("excel", "open_excel", "close_excel"),
    ("outlook", "open_outlook", "close_outlook"),
    # System & tools
    ("file explorer", "open_file_explorer", "close_file_explorer"),
    ("task manager", "open_task_manager", "close_task_manager"),
    ("control panel", "open_control_panel", "close_control_panel"),
    ("device manager", "open_device_manager", "close_device_manager"),
    ("registry editor", "open_registry_editor", "close_registry_editor"),
    ("snipping tool", "open_snipping_tool", "close_snipping_tool"),
    ("sticky notes", "open_sticky_notes", "close_sticky_notes"),
    ("command prompt", "open_cmd", "close_cmd"),
    ("git bash", "open_gitbash", "close_gitbash"),
    ("notepad", "open_notepad", "close_notepad"),
    ("calculator", "open_calculator", "close_calculator"),
    ("calc", "open_calculator", "close_calculator"),
    ("paint", "open_paint", "close_paint"),
    ("microsoft paint", "open_paint", "close_paint"),
    ("settings", "open_settings", "close_settings"),
    ("cmd", "open_cmd", "close_cmd"),
    ("terminal", "open_cmd", "close_cmd"),
    # Media & social
    ("spotify", "open_spotify", "close_spotify"),
    ("netflix", "open_netflix", "close_netflix"),
    ("prime video", "open_prime_video", "close_prime_video"),
    ("hotstar", "open_hotstar", "close_hotstar"),
    ("facebook", "open_facebook", "close_facebook"),
    ("twitter", "open_twitter", "close_twitter"),
    ("linkedin", "open_linkedin", "close_linkedin"),
    ("whatsapp", "open_whatsapp", "close_whatsapp"),
    ("discord", "open_discord", "close_discord"),
    ("slack", "open_slack", "close_slack"),
    ("telegram", "open_telegram", "close_telegram"),
    ("skype", "open_skype", "close_skype"),
    ("teams", "open_teams", "close_teams"),
    ("microsoft teams", "open_teams", "close_teams"),
    ("zoom", "open_zoom", "close_zoom"),
    # Dev & IDE
    ("android studio", "open_android_studio", "close_android_studio"),
    ("visual studio", "open_vscode", "close_vscode"),
    ("pycharm", "open_pycharm", "close_pycharm"),
    ("intellij", "open_intellij", "close_intellij"),
    ("eclipse", "open_eclipse", "close_eclipse"),
    ("sublime text", "open_sublime", "close_sublime"),
    ("sublime", "open_sublime", "close_sublime"),
    ("netbeans", "open_netbeans", "close_netbeans"),
    # Cloud & storage
    ("onedrive", "open_onedrive", "close_onedrive"),
    ("dropbox", "open_dropbox", "close_dropbox"),
    ("icloud", "open_icloud", "close_icloud"),
    # Other apps
    ("steam", "open_steam", "close_steam"),
    ("evernote", "open_evernote", "close_evernote"),
    ("windows defender", "open_defender", "close_defender"),
    ("defender", "open_defender", "close_defender"),
    ("antivirus", "open_antivirus", "close_antivirus"),
    ("music player", "open_music_player", "close_music_player"),
    ("groove music", "open_music_player", "close_music_player"),
    ("adobe reader", "open_adobe_reader", "close_adobe_reader"),
    ("pdf reader", "open_adobe_reader", "close_adobe_reader"),
    ("photoshop", "open_photoshop", "close_photoshop"),
    ("adobe photoshop", "open_photoshop", "close_photoshop"),
    ("vmware", "open_vmware", "close_vmware"),
    ("virtualbox", "open_virtualbox", "close_virtualbox"),
    ("maps", "open_maps", None),
    ("calendar", "open_calendar", None),
    ("downloads", "open_downloads", None),
    ("downloads folder", "open_downloads", None),
    ("desktop", "open_desktop", None),
    ("desktop folder", "open_desktop", None),
]


def _keyword_matches(t: str, keyword: str) -> bool:
    """True if keyword appears in t as a whole word (or as whole phrase)."""
    if " " in keyword:
        return keyword in t
    # Word boundary: "word" matches " open word " or "word " or " word" but not "password"
    pattern = r"(^|[\s])" + re.escape(keyword) + r"([\s]|$)"
    return bool(re.search(pattern, t))


def _intent_from_keywords(text: str) -> tuple[str | None, float]:
    """If user text clearly contains an app name + open/close, return that intent (conf 1.0)."""
    t = normalize(text)
    if not t:
        return None, 0.0
    for keyword, open_intent, close_intent in KEYWORD_INTENTS:
        if not _keyword_matches(t, keyword):
            continue
        # Prefer close if close words appear
        for w in CLOSE_WORDS:
            if w in t and close_intent is not None:
                return close_intent, 1.0
        # Open: explicit open words or default to open when keyword is an app name
        for w in OPEN_WORDS:
            if w in t:
                return open_intent, 1.0
        if "open" in t or "launch" in t or "start" in t or "run" in t:
            return open_intent, 1.0
    return None, 0.0


def predict_intent(pipe, le, text: str):
    text_norm = normalize(text)
    if not text_norm:
        return None, 0.0
    # Keyword override first so "open notepad" -> open_notepad
    intent, conf = _intent_from_keywords(text)
    if intent is not None:
        return intent, conf
    # Else use model
    proba = pipe.predict_proba([text_norm])[0]
    idx = proba.argmax()
    label = le.inverse_transform([idx])[0]
    return label, float(proba[idx])


def speak(text: str) -> None:
    """Text-to-speech using pyttsx3 (offline) or fallback print."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        print("[Voice: not available — install pyttsx3]")
        print(f"[Would say: {text}]")


def listen_once() -> str | None:
    """Listen for one voice command. Returns recognized text or None."""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("\nListening... (speak now)")
            r.adjust_for_ambient_noise(source, duration=0.3)
            audio = r.listen(source, timeout=8, phrase_time_limit=10)
        print("Processing...")
        text = r.recognize_google(audio, language="en-US")
        return text.strip()
    except Exception as e:
        print(f"Listening error: {e}")
        return None


def run_voice_loop(pipe, le, use_voice_input: bool = True):
    """Main loop: listen -> predict -> execute -> speak + print."""
    print("=" * 50)
    print("  Voice Assistant (Siri-like)")
    print("  Say a command or type it. Say 'exit' or 'quit' to stop.")
    print("=" * 50)

    while True:
        if use_voice_input:
            user_input = listen_once()
            if user_input is None:
                continue
            # Allow "exit" from voice
            if user_input.strip().lower() in ("exit", "quit", "stop", "goodbye"):
                print("Goodbye!")
                speak("Goodbye!")
                break
        else:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break

        intent, conf = predict_intent(pipe, le, user_input)
        if intent is None:
            print("Assistant: I didn't catch that.")
            speak("I didn't catch that.")
            continue

        if conf < 0.5:
            print(f"Assistant: I'm not sure I understood. (confidence: {conf:.2f})")
            speak("I'm not sure I understood. Please try again.")
            continue

        # Execute and get response
        response = execute_intent(intent, user_input)

        # On screen
        print(f"Command: {intent}")
        print(f"Assistant: {response}")

        # Voice
        speak(response)


def main():
    use_voice = "--text" not in sys.argv
    pipe, le = load_model()
    run_voice_loop(pipe, le, use_voice_input=use_voice)


if __name__ == "__main__":
    main()
