"""
Intent executor: maps predicted intents to actions and responses.
Executes the command and returns a message to display and speak.
"""
import os
import platform
import random
import re
import subprocess
import webbrowser
from datetime import datetime

# Jokes for tell_joke intent
JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "Why did the scarecrow win an award? He was outstanding in his field!",
    "Why don't eggs tell jokes? They'd crack each other up!",
    "What do you call a bear with no teeth? A gummy bear!",
    "Why can't you give a balloon a lecture? Because it goes over your head!",
    "What do you call a fake noodle? An impasta!",
    "Why did the math book look sad? Because it had too many problems!",
    "What do you call a can opener that doesn't work? A can't opener!",
    "Why did the coffee file a police report? It got mugged!",
    "What do you call a fish without eyes? A fsh!",
]

# Quotes for tell_quote intent
QUOTES = [
    "The only way to do great work is to love what you do. — Steve Jobs",
    "Innovation distinguishes between a leader and a follower. — Steve Jobs",
    "Life is what happens when you're busy making other plans. — John Lennon",
    "The future belongs to those who believe in the beauty of their dreams. — Eleanor Roosevelt",
    "It is during our darkest moments that we must focus to see the light. — Aristotle",
    "The only impossible journey is the one you never begin. — Tony Robbins",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. — Winston Churchill",
    "Believe you can and you're halfway there. — Theodore Roosevelt",
]

# Windows app names / commands
WIN_APPS = {
    "open_notepad": ("notepad", []),
    "open_calculator": ("calc", []),
    "open_vscode": ("code", []),
    "open_cmd": ("cmd", ["/k"]),
    "open_file_explorer": ("explorer", []),
    "open_task_manager": ("taskmgr", []),
    "open_control_panel": ("control", []),
    "open_settings": ("ms-settings:", []),  # URI
    "open_snipping_tool": ("snippingtool", []),
    "open_paint": ("mspaint", []),
    "open_sticky_notes": ("sticky notes", []),  # Win 10/11
    "open_registry_editor": ("regedit", []),
    "open_maps": ("ms-maps:", []),
    "open_calendar": ("outlookcal:", []),
    "open_spotify": ("spotify", []),
    "open_google": ("https://www.google.com", "url"),
    "open_gmail": ("https://mail.google.com", "url"),
    "open_youtube": ("https://www.youtube.com", "url"),
    "open_facebook": ("https://www.facebook.com", "url"),
    "open_twitter": ("https://twitter.com", "url"),
    "open_linkedin": ("https://www.linkedin.com", "url"),
    "open_whatsapp": ("https://web.whatsapp.com", "url"),
    "open_netflix": ("https://www.netflix.com", "url"),
    "open_prime_video": ("https://www.primevideo.com", "url"),
    "open_hotstar": ("https://www.hotstar.com", "url"),
    "open_google_drive": ("https://drive.google.com", "url"),
    "open_icloud": ("https://www.icloud.com", "url"),
    "open_chrome": ("chrome", []),
    "open_edge": ("msedge", []),
    "open_powerpoint": ("powerpnt", []),
    "open_excel": ("excel", []),
    "open_word": ("winword", []),
    "open_outlook": ("outlook", []),
    "open_teams": ("ms-teams", []),
    "open_zoom": ("zoom", []),
    "open_onedrive": ("onedrive", []),
    "open_dropbox": ("dropbox", []),
    "open_steam": ("steam", []),
    "open_skype": ("skype", []),
    "open_discord": ("discord", []),
    "open_slack": ("slack", []),
    "open_telegram": ("telegram", []),
    "open_vmware": ("vmware", []),
    "open_virtualbox": ("VirtualBox", []),
    "open_pycharm": ("pycharm64", []),
    "open_intellij": ("idea64", []),
    "open_eclipse": ("eclipse", []),
    "open_android_studio": ("studio64", []),
    "open_sublime": ("sublime_text", []),
    "open_netbeans": ("netbeans", []),
    "open_evernote": ("evernote", []),
    "open_defender": ("windowsdefender:", []),
    "open_antivirus": ("windowsdefender:", []),
    "open_music_player": ("wmplayer", []),
    "open_adobe_reader": ("AcroRd32", []),
    "open_photoshop": ("photoshop", []),
    "open_gitbash": ("git-bash", []),
    "open_device_manager": ("devmgmt.msc", []),
    "open_downloads": (os.path.expanduser("~\\Downloads"), "path"),
    "open_desktop": (os.path.expanduser("~\\Desktop"), "path"),
}

# Windows: executables that are in system PATH (no need for start or full path)
WIN_IN_PATH = frozenset({
    "notepad", "calc", "mspaint", "cmd", "explorer", "taskmgr", "control", "regedit",
    "snippingtool", "taskmgr", "devmgmt.msc",
})

# Windows: optional full paths for apps that often aren't in PATH (try these first, then fallback to start)
def _win_app_paths():
    pf = os.environ.get("ProgramFiles", "C:\\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    appdata = os.environ.get("APPDATA", "")
    local = os.environ.get("LOCALAPPDATA", "")
    return {
        "wmplayer": os.path.join(pf86, "Windows Media Player", "wmplayer.exe"),
        "Windows Media Player": os.path.join(pf86, "Windows Media Player", "wmplayer.exe"),
        "Spotify": os.path.join(appdata, "Spotify", "Spotify.exe"),
        "chrome": os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
        "msedge": os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
        "Code": os.path.join(pf, "Microsoft VS Code", "Code.exe"),
        "code": os.path.join(pf, "Microsoft VS Code", "Code.exe"),
        "Discord": os.path.join(local, "Discord", "app.exe"),
        "discord": os.path.join(local, "Discord", "app.exe"),
        "Slack": os.path.join(local, "slack", "slack.exe"),
        "slack": os.path.join(local, "slack", "slack.exe"),
        "Telegram": os.path.join(pf, "Telegram Desktop", "Telegram.exe"),
        "telegram": os.path.join(pf, "Telegram Desktop", "Telegram.exe"),
        "Zoom": os.path.join(pf86, "Zoom", "bin", "Zoom.exe"),
        "zoom": os.path.join(pf86, "Zoom", "bin", "Zoom.exe"),
        "Steam": os.path.join(pf86, "Steam", "steam.exe"),
        "steam": os.path.join(pf86, "Steam", "steam.exe"),
    }

# Hide console window when launching apps on Windows (avoids "not recognized" popup)
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

# Process names to kill for close_* (Windows)
WIN_CLOSE = {
    "close_notepad": "notepad.exe",
    "close_calculator": "Calculator.exe",
    "close_vscode": "Code.exe",
    "close_spotify": "Spotify.exe",
    "close_chrome": "chrome.exe",
    "close_edge": "msedge.exe",
    "close_excel": "EXCEL.EXE",
    "close_word": "WINWORD.EXE",
    "close_powerpoint": "POWERPNT.EXE",
    "close_outlook": "OUTLOOK.EXE",
    "close_teams": "ms-teams.exe",
    "close_zoom": "Zoom.exe",
    "close_cmd": "cmd.exe",
    "close_file_explorer": "explorer.exe",  # use with care
    "close_task_manager": "Taskmgr.exe",
    "close_paint": "mspaint.exe",
    "close_snipping_tool": "SnippingTool.exe",
    "close_music_player": "wmplayer.exe",
    "close_skype": "skype.exe",
    "close_discord": "Discord.exe",
    "close_slack": "Slack.exe",
    "close_telegram": "Telegram.exe",
    "close_onedrive": "OneDrive.exe",
    "close_dropbox": "Dropbox.exe",
    "close_steam": "steam.exe",
    "close_adobe_reader": "AcroRd32.exe",
    "close_photoshop": "photoshop.exe",
    "close_defender": "SecurityHealthSystray.exe",
    "close_antivirus": "SecurityHealthSystray.exe",
    "close_google": "chrome.exe",  # or msedge
    "close_gmail": "chrome.exe",
    "close_youtube": "chrome.exe",
    "close_facebook": "chrome.exe",
    "close_twitter": "chrome.exe",
    "close_linkedin": "chrome.exe",
    "close_whatsapp": "chrome.exe",
    "close_netflix": "chrome.exe",
    "close_prime_video": "chrome.exe",
    "close_hotstar": "chrome.exe",
    "close_google_drive": "chrome.exe",
    "close_icloud": "chrome.exe",
    "close_vscode": "Code.exe",
    "close_sticky_notes": "StickyNotes.exe",
    "close_registry_editor": "regedit.exe",
    "close_device_manager": "mmc.exe",
    "close_gitbash": "bash.exe",
    "close_evernote": "evernote.exe",
    "close_pycharm": "pycharm64.exe",
    "close_intellij": "idea64.exe",
    "close_eclipse": "eclipse.exe",
    "close_android_studio": "studio64.exe",
    "close_sublime": "sublime_text.exe",
    "close_netbeans": "netbeans.exe",
    "close_vmware": "vmware.exe",
    "close_virtualbox": "VirtualBox.exe",
    "close_control_panel": "control.exe",
    "close_settings": "SystemSettings.exe",
    "close_file_explorer": "explorer.exe",
}


def _run_cmd(cmd: list | str, use_shell: bool = False) -> bool:
    try:
        if isinstance(cmd, str):
            if cmd.startswith("ms-") or cmd.startswith("outlook") or cmd.startswith("windowsdefender"):
                os.startfile(cmd)
            else:
                subprocess.Popen(cmd, shell=use_shell)
        else:
            subprocess.Popen(cmd, shell=use_shell)
        return True
    except Exception:
        return False


def _open_app(key: str) -> tuple[bool, str]:
    entry = WIN_APPS.get(key)
    if not entry:
        return False, f"Unknown app for intent: {key}"
    target, rest = entry[0], entry[1] if len(entry) > 1 else []
    if rest == "url":
        try:
            webbrowser.open(target)
            return True, f"Opened {key.replace('open_', '').replace('_', ' ')}."
        except Exception:
            return False, "Could not open browser."
    if rest == "path":
        try:
            os.startfile(target)
            return True, f"Opened {key.replace('open_', '').replace('_', ' ')}."
        except Exception:
            return False, "Could not open folder."
    # Normalize target for path/URI checks
    target_str = str(target).strip()
    if isinstance(rest, list) and not rest:
        try:
            if target_str.endswith(".msc") or target_str in ("control", "regedit", "taskmgr", "devmgmt.msc"):
                os.startfile(target_str)
                return True, f"Opened {key.replace('open_', '').replace('_', ' ')}."
            if ":" in target_str:
                os.startfile(target_str)
                return True, f"Opened {key.replace('open_', '').replace('_', ' ')}."
            # Windows: use start so apps not in PATH are found via Start Menu / App Paths
            if platform.system() == "Windows":
                extra = (rest if isinstance(rest, list) else [])
                if extra:
                    subprocess.Popen([target_str] + list(extra), shell=True)
                elif target_str in WIN_IN_PATH:
                    os.startfile(target_str)
                else:
                    # Try known full path first, then start (so Windows resolves via Start Menu / App Paths)
                    paths = _win_app_paths()
                    exe_path = paths.get(target_str)
                    if exe_path and os.path.isfile(exe_path):
                        os.startfile(exe_path)
                    elif key == "open_music_player":
                        # Fallback: try wmplayer path, then Windows Music app URI
                        wmp = paths.get("wmplayer")
                        if wmp and os.path.isfile(wmp):
                            os.startfile(wmp)
                        else:
                            try:
                                os.startfile("mswindowsmusic:")
                            except Exception:
                                subprocess.Popen('start "" "Windows Media Player"', shell=True, creationflags=_CREATE_NO_WINDOW)
                    else:
                        # start "" "AppName" lets Windows resolve the app; hide console to avoid error popup
                        subprocess.Popen(f'start "" "{target_str}"', shell=True, creationflags=_CREATE_NO_WINDOW)
                return True, f"Opened {key.replace('open_', '').replace('_', ' ')}."
            # Non-Windows: direct run
            subprocess.Popen([target_str] + (rest if isinstance(rest, list) else []), shell=True)
            return True, f"Opened {key.replace('open_', '').replace('_', ' ')}."
        except Exception as e:
            return False, f"Could not open: {e}"
    try:
        subprocess.Popen([target_str] + (rest if isinstance(rest, list) else []), shell=True)
        return True, f"Opened {key.replace('open_', '').replace('_', ' ')}."
    except Exception as e:
        return False, str(e)


def _close_app(key: str) -> tuple[bool, str]:
    proc = WIN_CLOSE.get(key)
    if not proc:
        return False, f"Unknown close action: {key}"
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/IM", proc, "/F"], capture_output=True)
            return True, f"Closed {key.replace('close_', '').replace('_', ' ')}."
        return False, "Close command is supported only on Windows."
    except Exception as e:
        return False, str(e)


# Safe math: only allow numbers and + - * / ( ) . and **
def _safe_calculate(expr: str) -> tuple[bool, str]:
    expr = expr.strip().replace(" ", "")
    allowed = set("0123456789+-*/().")
    if not all(c in allowed for c in expr):
        return False, "Only numbers and + - * / ( ) are allowed."
    try:
        result = eval(expr)
        return True, str(round(result, 4) if isinstance(result, float) else result)
    except Exception:
        return False, "Could not calculate that expression."


def execute_intent(intent: str, raw_text: str = "") -> str:
    """
    Execute the action for the given intent and return a message to speak/display.
    """
    raw_text = (raw_text or "").strip().lower()

    # Greet
    if intent == "greet":
        return random.choice([
            "Hello! How can I help you?",
            "Hi there! What can I do for you?",
            "Hey! I'm here. What do you need?",
        ])

    # Time & date
    if intent == "tell_time":
        now = datetime.now()
        return f"The time is {now.strftime('%I:%M %p')}."

    if intent == "tell_date":
        now = datetime.now()
        return f"Today is {now.strftime('%A, %B %d, %Y')}."

    # Joke & quote
    if intent == "tell_joke":
        joke = random.choice(JOKES)
        return joke

    if intent == "tell_quote":
        return random.choice(QUOTES)

    # Math (extract numbers and operators from raw_text if possible)
    if intent == "calculate_math":
        raw = raw_text.lower()
        raw = re.sub(r"\s+", " ", raw)
        raw = re.sub(r"to the power of", "**", raw)
        raw = re.sub(r"times", "*", raw)
        raw = re.sub(r"divided by", "/", raw)
        raw = re.sub(r"plus", "+", raw)
        raw = re.sub(r"minus", "-", raw)
        expr = re.sub(r"[^\d+\-*/().\s]", "", raw)
        expr = re.sub(r"\s+", "", expr)
        if not expr:
            expr = "2+2"
        ok, msg = _safe_calculate(expr)
        return msg if ok else f"Calculation failed. {msg}"

    # Open apps / URLs
    if intent in WIN_APPS:
        ok, msg = _open_app(intent)
        return msg

    # Close apps
    if intent in WIN_CLOSE:
        ok, msg = _close_app(intent)
        return msg

    # System actions (Windows)
    if intent == "restart_computer":
        try:
            os.system("shutdown /r /t 5")
            return "Computer will restart in 5 seconds."
        except Exception:
            return "Could not trigger restart."

    if intent == "shutdown_computer":
        try:
            os.system("shutdown /s /t 5")
            return "Computer will shut down in 5 seconds."
        except Exception:
            return "Could not trigger shutdown."

    if intent == "lock_screen":
        try:
            if platform.system() == "Windows":
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
                return "Screen locked."
        except Exception:
            pass
        return "Could not lock screen."

    if intent == "log_off":
        try:
            os.system("shutdown /l")
            return "Logging off."
        except Exception:
            return "Could not log off."

    # Screenshot / clipboard / etc.
    if intent == "take_screenshot":
        try:
            subprocess.Popen(["snippingtool", "/clip"], shell=True)
            return "Opening Snipping Tool to take a screenshot."
        except Exception:
            return "Could not open Snipping Tool."

    if intent == "open_clipboard":
        try:
            subprocess.Popen("clip", shell=True)
            return "Clipboard is in use; paste to see contents."
        except Exception:
            return "Could not access clipboard."

    if intent == "clear_clipboard":
        try:
            subprocess.run("echo off | clip", shell=True)
            return "Clipboard cleared."
        except Exception:
            return "Could not clear clipboard."

    # Placeholder intents (no external API)
    placeholders = {
        "set_alarm": "Alarm set. (Use your system clock or phone for real alarms.)",
        "set_timer": "Timer started. (Use your phone or a timer app for accuracy.)",
        "create_note": "Opening Notepad for your note.",
        "play_music": "Use your music app or say 'open Spotify' to play music.",
        "stop_music": "Stopping is handled by your music player.",
        "next_song": "Use your music player to skip to the next track.",
        "translate_word": "Say the word and the language you want to translate to.",
        "weather_info": "I don't have weather access yet. You can ask your browser.",
        "get_news": "Opening news in browser.",
        "book_flight": "I can't book flights. Please use a travel website.",
        "send_email": "Opening your email client.",
        "create_reminder": "Use Calendar or a reminder app for reminders.",
        "search_google": "Opening Google for you.",
        "record_screen": "Use Windows Game Bar (Win+G) or a screen recorder app.",
    }
    if intent in placeholders:
        msg = placeholders[intent]
        if intent == "create_note":
            _run_cmd("notepad", use_shell=True)
        elif intent == "get_news":
            webbrowser.open("https://news.google.com")
        elif intent == "search_google":
            webbrowser.open("https://www.google.com")
        return msg

    return f"I understood the command as: {intent}. No action is configured for it yet."
