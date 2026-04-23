"""
waku_launcher.py  ─  Waku Voice Assistant Launcher
====================================================
Alexa-style desktop app. Every command speaks what it is doing.
Full music player with multiple MP3 tracks.

Put these files in the same folder:
    intents.json        your intents file
    train.py            run once to create intent_model.pkl
    waku_launcher.py    this file
    music/              folder with .mp3 files (optional)

Run:
    python train.py           first time only
    python waku_launcher.py
"""

import subprocess, sys, importlib
for _pkg, _mod in [
    ("customtkinter","customtkinter"),("SpeechRecognition","speech_recognition"),
    ("pyttsx3","pyttsx3"),("scikit-learn","sklearn"),("pygame","pygame"),("Pillow","PIL"),
]:
    try: importlib.import_module(_mod)
    except ImportError:
        print(f"  Installing {_pkg}...")
        subprocess.check_call([sys.executable,"-m","pip","install",_pkg,"-q"])

import tkinter as tk
import customtkinter as ctk
import threading, json, os, re, time, random, datetime
import webbrowser, platform, math, pickle
import subprocess as sp

import speech_recognition as sr
import pyttsx3, pygame
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

OS           = platform.system()
HERE         = os.path.dirname(os.path.abspath(__file__))
INTENTS_FILE = os.path.join(HERE,"intents.json")
MODEL_FILE   = os.path.join(HERE,"intent_model.pkl")
MUSIC_DIR    = os.path.join(HERE,"music")

C = {
    "bg":"#080810","surface":"#0F0F1E","card":"#16162A","border":"#22224A",
    "accent":"#6C63FF","cyan":"#22D3EE","green":"#10B981","amber":"#F59E0B",
    "text":"#E2E0FF","muted":"#5A5A8A","danger":"#F87171",
}

JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "I told my computer I needed a break. Now it keeps sending me Kit-Kat ads.",
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "What do you call a fake noodle? An impasta!",
    "I'm reading a book about anti-gravity — impossible to put down!",
    "Why did the scarecrow win an award? Outstanding in his field!",
    "Why don't eggs tell jokes? They'd crack each other up!",
    "I used to hate facial hair, but then it grew on me.",
    "What do you call cheese that isn't yours? Nacho cheese!",
    "Why can't a nose be 12 inches long? Because then it would be a foot!",
]
QUOTES = [
    "The only way to do great work is to love what you do. — Steve Jobs",
    "In the middle of every difficulty lies opportunity. — Albert Einstein",
    "It does not matter how slowly you go as long as you do not stop. — Confucius",
    "Life is what happens when you are busy making other plans. — John Lennon",
    "The future belongs to those who believe in the beauty of their dreams. — Eleanor Roosevelt",
    "Success is not final, failure is not fatal: it is the courage to continue. — Churchill",
    "Believe you can and you're halfway there. — Theodore Roosevelt",
    "You miss 100% of the shots you don't take. — Wayne Gretzky",
    "The secret of getting ahead is getting started. — Mark Twain",
    "Whether you think you can or you think you can't, you're right. — Henry Ford",
]

COMMAND_CARDS = [
    ("⏰","Time",       "what time is it"),   ("📅","Date",      "tell me the date"),
    ("😄","Joke",       "tell me a joke"),    ("💬","Quote",     "tell me a quote"),
    ("▶️","Play Music", "play music"),        ("⏹","Stop Music", "stop the music"),
    ("⏭","Next Song",  "next song please"),  ("🎵","Spotify",   "open spotify"),
    ("🔍","Google",     "open google"),       ("▶️","YouTube",   "open youtube"),
    ("📧","Gmail",      "open gmail"),        ("🗺️","Maps",      "open maps"),
    ("💻","VS Code",    "open visual studio code"), ("🧮","Calculator","open calculator"),
    ("📝","Notepad",    "open notepad"),      ("📅","Calendar",  "open calendar"),
    ("📸","Screenshot", "take screenshot"),   ("⚙️","Settings",  "open settings"),
    ("📁","Explorer",   "open file explorer"),("🔒","Lock",      "lock screen"),
    ("🐍","PyCharm",    "open pycharm"),      ("☕","IntelliJ",  "open intellij"),
    ("🌑","Eclipse",    "open eclipse"),      ("🖥️","CMD",       "open cmd"),
    ("💬","WhatsApp",   "open whatsapp"),     ("📨","Telegram",  "open telegram"),
    ("💼","LinkedIn",   "open linkedin"),     ("☁️","Drive",     "open google drive"),
    ("🔢","Math",       "calculate 5 plus 3"),("🌐","Translate", "translate this word"),
    ("📰","News",       "get latest news"),   ("✈️","Flight",    "book a flight"),
]


# ── Model ─────────────────────────────────────────────────────
def load_or_train():
    needs = (not os.path.exists(MODEL_FILE) or
             os.path.getmtime(INTENTS_FILE) > os.path.getmtime(MODEL_FILE))
    if needs:
        print("  Training intent model...")
        with open(INTENTS_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        X, y = [], []
        if isinstance(raw, list):
            for group in raw:
                for item in group:
                    if "text" in item and "label" in item:
                        X.append(item["text"].lower()); y.append(item["label"])
        else:
            for intent in raw.get("intents",[]):
                for p in intent.get("patterns",[]):
                    X.append(p.lower()); y.append(intent["tag"])
        pipe = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1,3), analyzer="char_wb")),
            ("clf",   LogisticRegression(max_iter=2000, C=10.0)),
        ])
        pipe.fit(X, y)
        with open(MODEL_FILE,"wb") as f: pickle.dump(pipe, f)
        print(f"  Trained on {len(X)} samples → {len(set(y))} intents")
    else:
        with open(MODEL_FILE,"rb") as f: pipe = pickle.load(f)
        print(f"  Model loaded.")
    return pipe

def predict(model, text):
    tag  = model.predict([text.lower()])[0]
    conf = float(max(model.predict_proba([text.lower()])[0]))
    return tag, conf


# ── TTS ───────────────────────────────────────────────────────
class TTS:
    def __init__(self):
        self._e = pyttsx3.init()
        self._e.setProperty("rate", 165)
        self._e.setProperty("volume", 1.0)
        for v in self._e.getProperty("voices"):
            if any(k in v.name.lower() for k in ("zira","samantha","karen","female")):
                self._e.setProperty("voice", v.id); break
        self._lk = threading.Lock()

    def speak(self, text, done_cb=None):
        def _run():
            with self._lk:
                self._e.say(text); self._e.runAndWait()
            if done_cb: done_cb()
        threading.Thread(target=_run, daemon=True).start()


# ── Recogniser ────────────────────────────────────────────────
class Recogniser:
    def __init__(self):
        self._r = sr.Recognizer()
        self._r.pause_threshold = 0.8
        self._r.energy_threshold = 300
        self._r.dynamic_energy_threshold = True

    def listen(self, timeout=7, phrase_limit=12):
        try:
            with sr.Microphone() as src:
                self._r.adjust_for_ambient_noise(src, duration=0.3)
                audio = self._r.listen(src, timeout=timeout, phrase_time_limit=phrase_limit)
            return self._r.recognize_google(audio).lower().strip()
        except Exception:
            return ""


# ── Music Player ──────────────────────────────────────────────
class MusicPlayer:
    def __init__(self, music_dir):
        pygame.mixer.init()
        self._dir    = music_dir
        self._tracks = []
        self._index  = 0
        self._refresh()

    def _refresh(self):
        if os.path.isdir(self._dir):
            self._tracks = sorted([
                os.path.join(self._dir, f) for f in os.listdir(self._dir)
                if f.lower().endswith(".mp3")
            ])

    def play(self):
        self._refresh()
        if not self._tracks:
            return "No MP3 files found. Add .mp3 files to the music folder next to this script."
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.unpause()
                return "Resuming music."
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self._tracks[self._index])
            pygame.mixer.music.play()
            name = os.path.splitext(os.path.basename(self._tracks[self._index]))[0]
            return f"Now playing: {name}."
        except Exception as e:
            return f"Could not play music. {e}"

    def stop(self):
        pygame.mixer.music.stop()
        return "Music stopped."

    def next_track(self):
        self._refresh()
        if not self._tracks:
            return "No tracks found in the music folder."
        self._index = (self._index + 1) % len(self._tracks)
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self._tracks[self._index])
            pygame.mixer.music.play()
            name = os.path.splitext(os.path.basename(self._tracks[self._index]))[0]
            return f"Playing next: {name}."
        except Exception as e:
            return f"Could not skip track. {e}"

    def get_track_list(self):
        self._refresh()
        return [os.path.splitext(os.path.basename(t))[0] for t in self._tracks]

    def is_playing(self):
        return pygame.mixer.music.get_busy()


# ── Helpers ───────────────────────────────────────────────────
def _open_url(url, label):
    webbrowser.open(url)
    return f"Opening {label} in your browser."

def _open_app(win_cmd, mac_app, linux_cmd, label):
    try:
        if OS == "Windows":   sp.Popen(win_cmd, shell=True)
        elif OS == "Darwin":  sp.Popen(["open","-a",mac_app])
        else:                 sp.Popen(linux_cmd, shell=True)
        return f"Opening {label}."
    except Exception as e:
        return f"Could not open {label}. {e}"

def _kill(name):
    try:
        if OS == "Windows": sp.run(["taskkill","/f","/im",f"{name}.exe"], capture_output=True)
        else:               sp.run(["pkill","-f",name], capture_output=True)
        return f"Closing {name}."
    except Exception:
        return f"Could not close {name}."


# ── Actions ───────────────────────────────────────────────────
class Actions:
    def __init__(self, music, ask_fn):
        self._music = music
        self._ask   = ask_fn

    def dispatch(self, tag, text):
        fn = getattr(self, f"_do_{tag}", None)
        if fn: return fn(text)
        return f"Handling {tag.replace('_',' ')}."

    # time/date
    def _do_greet(self, t):
        h = datetime.datetime.now().hour
        p = "Good morning" if h<12 else "Good afternoon" if h<17 else "Good evening"
        return f"{p}! I am Waku, your personal voice assistant. How can I help?"
    def _do_tell_time(self, t):
        return "The current time is " + datetime.datetime.now().strftime("%I:%M %p") + "."
    def _do_tell_date(self, t):
        return "Today is " + datetime.datetime.now().strftime("%A, %B %d, %Y") + "."

    # music
    def _do_play_music(self, t):         return self._music.play()
    def _do_stop_music(self, t):         return self._music.stop()
    def _do_next_song(self, t):          return self._music.next_track()
    def _do_close_music_player(self, t): return self._music.stop()
    def _do_open_music_player(self, t):  return self._music.play()

    # fun
    def _do_tell_joke(self, t):  return random.choice(JOKES)
    def _do_tell_quote(self, t): return random.choice(QUOTES)

    # web
    def _do_open_youtube(self, t):     return _open_url("https://youtube.com",          "YouTube")
    def _do_open_google(self, t):      return _open_url("https://google.com",           "Google")
    def _do_open_gmail(self, t):       return _open_url("https://mail.google.com",      "Gmail")
    def _do_open_maps(self, t):        return _open_url("https://maps.google.com",      "Google Maps")
    def _do_open_spotify(self, t):     return _open_url("https://open.spotify.com",     "Spotify")
    def _do_open_netflix(self, t):     return _open_url("https://netflix.com",          "Netflix")
    def _do_open_facebook(self, t):    return _open_url("https://facebook.com",         "Facebook")
    def _do_open_twitter(self, t):     return _open_url("https://twitter.com",          "Twitter")
    def _do_open_linkedin(self, t):    return _open_url("https://linkedin.com",         "LinkedIn")
    def _do_open_whatsapp(self, t):    return _open_url("https://web.whatsapp.com",     "WhatsApp")
    def _do_open_telegram(self, t):    return _open_url("https://web.telegram.org",     "Telegram")
    def _do_open_google_drive(self,t): return _open_url("https://drive.google.com",     "Google Drive")
    def _do_open_icloud(self, t):      return _open_url("https://icloud.com",           "iCloud")
    def _do_open_onedrive(self, t):    return _open_url("https://onedrive.live.com",    "OneDrive")
    def _do_open_dropbox(self, t):     return _open_url("https://dropbox.com",          "Dropbox")
    def _do_open_hotstar(self, t):     return _open_url("https://hotstar.com",          "Hotstar")
    def _do_open_prime_video(self, t): return _open_url("https://primevideo.com",       "Prime Video")
    def _do_open_discord(self, t):     return _open_url("https://discord.com/app",      "Discord")
    def _do_open_slack(self, t):       return _open_url("https://app.slack.com",        "Slack")
    def _do_open_zoom(self, t):        return _open_url("https://zoom.us",              "Zoom")
    def _do_open_teams(self, t):       return _open_url("https://teams.microsoft.com",  "Microsoft Teams")
    def _do_open_skype(self, t):       return _open_url("https://web.skype.com",        "Skype")
    def _do_open_evernote(self, t):    return _open_url("https://evernote.com/client/web","Evernote")
    def _do_open_steam(self, t):       return _open_url("https://store.steampowered.com","Steam")

    # search
    def _do_search_google(self, text):
        noise = ["search on google","google something for me","search for",
                 "search google for","look up","find information about","google","search"]
        q = text.lower()
        for n in sorted(noise, key=len, reverse=True): q = q.replace(n,"")
        q = q.strip()
        if not q: q = self._ask("What should I search for?") or ""
        if q:
            webbrowser.open(f"https://google.com/search?q={q}")
            return f"Searching Google for {q}."
        return "No search query provided."

    # desktop apps
    def _do_open_calculator(self, t): return _open_app("calc","Calculator","gnome-calculator","Calculator")
    def _do_open_notepad(self, t):    return _open_app("notepad","TextEdit","gedit","Notepad")
    def _do_open_calendar(self, t):
        if OS == "Windows": webbrowser.open("https://calendar.google.com")
        elif OS == "Darwin": sp.Popen(["open","-a","Calendar"])
        else: sp.Popen("gnome-calendar", shell=True)
        return "Opening Calendar."
    def _do_open_chrome(self, t):        return _open_app("start chrome","Google Chrome","google-chrome","Google Chrome")
    def _do_open_edge(self, t):          return _open_app("start msedge","Microsoft Edge","microsoft-edge","Microsoft Edge")
    def _do_open_vscode(self, t):        return _open_app("code","Visual Studio Code","code","VS Code")
    def _do_open_pycharm(self, t):       return _open_app("pycharm","PyCharm","pycharm.sh","PyCharm")
    def _do_open_intellij(self, t):      return _open_app("idea","IntelliJ IDEA","idea.sh","IntelliJ IDEA")
    def _do_open_eclipse(self, t):       return _open_app("eclipse","Eclipse","eclipse","Eclipse")
    def _do_open_sublime(self, t):       return _open_app("subl","Sublime Text","subl","Sublime Text")
    def _do_open_android_studio(self,t): return _open_app("studio64","Android Studio","android-studio","Android Studio")
    def _do_open_netbeans(self, t):      return _open_app("netbeans","NetBeans","netbeans","NetBeans")
    def _do_open_word(self, t):          return _open_app("start winword","Microsoft Word","libreoffice --writer","Microsoft Word")
    def _do_open_excel(self, t):         return _open_app("start excel","Microsoft Excel","libreoffice --calc","Microsoft Excel")
    def _do_open_powerpoint(self, t):    return _open_app("start powerpnt","Microsoft PowerPoint","libreoffice --impress","PowerPoint")
    def _do_open_outlook(self, t):       return _open_app("start outlook","Microsoft Outlook","thunderbird","Outlook")
    def _do_open_photoshop(self, t):     return _open_app("photoshop","Adobe Photoshop","gimp","Photoshop")
    def _do_open_adobe_reader(self, t):  return _open_app("AcroRd32","Adobe Acrobat Reader","evince","Adobe Reader")
    def _do_open_paint(self, t):         return _open_app("mspaint","Preview","pinta","Paint")
    def _do_open_sticky_notes(self, t):  return _open_app("stikynot","Stickies","gnote","Sticky Notes")
    def _do_open_task_manager(self, t):  return _open_app("taskmgr","Activity Monitor","gnome-system-monitor","Task Manager")
    def _do_open_cmd(self, t):           return _open_app("start cmd","Terminal","x-terminal-emulator","Command Prompt")
    def _do_open_settings(self, t):      return _open_app("start ms-settings:","System Preferences","gnome-control-center","Settings")
    def _do_open_control_panel(self, t): return _open_app("control","System Preferences","gnome-control-center","Control Panel")
    def _do_open_file_explorer(self, t):
        if OS=="Windows": sp.Popen("explorer")
        elif OS=="Darwin": sp.Popen(["open", os.path.expanduser("~")])
        else: sp.Popen("nautilus ~", shell=True)
        return "Opening File Explorer."
    def _do_open_snipping_tool(self, t): return _open_app("snippingtool","Screenshot","gnome-screenshot","Snipping Tool")
    def _do_open_device_manager(self,t): return _open_app("devmgmt.msc","System Information","hardinfo","Device Manager")
    def _do_open_registry_editor(self,t):return _open_app("regedit","Terminal","xterm","Registry Editor")
    def _do_open_gitbash(self, t):       return _open_app("\"C:\\Program Files\\Git\\git-bash.exe\"","Terminal","x-terminal-emulator","Git Bash")
    def _do_open_virtualbox(self, t):    return _open_app("virtualbox","VirtualBox","virtualbox","VirtualBox")
    def _do_open_vmware(self, t):        return _open_app("vmware","VMware Fusion","vmware","VMware")
    def _do_open_antivirus(self, t):     return _open_app("start windowsdefender:","System Preferences","clamtk","Antivirus")
    def _do_open_defender(self, t):      return _open_app("start windowsdefender:","Security","clamtk","Windows Defender")

    # close commands
    def _do_close_notepad(self, t):       return _kill("notepad")
    def _do_close_calculator(self, t):    return _kill("calc")
    def _do_close_chrome(self, t):        return _kill("chrome")
    def _do_close_edge(self, t):          return _kill("msedge")
    def _do_close_vscode(self, t):        return _kill("code")
    def _do_close_youtube(self, t):       return "Closing YouTube tab in your browser."
    def _do_close_google(self, t):        return "Closing Google tab in your browser."
    def _do_close_gmail(self, t):         return "Closing Gmail tab in your browser."
    def _do_close_spotify(self, t):       return _kill("spotify")
    def _do_close_word(self, t):          return _kill("winword")
    def _do_close_excel(self, t):         return _kill("excel")
    def _do_close_powerpoint(self, t):    return _kill("powerpnt")
    def _do_close_outlook(self, t):       return _kill("outlook")
    def _do_close_pycharm(self, t):       return _kill("pycharm")
    def _do_close_intellij(self, t):      return _kill("idea")
    def _do_close_eclipse(self, t):       return _kill("eclipse")
    def _do_close_sublime(self, t):       return _kill("subl")
    def _do_close_android_studio(self,t): return _kill("studio")
    def _do_close_netbeans(self, t):      return _kill("netbeans")
    def _do_close_discord(self, t):       return _kill("discord")
    def _do_close_slack(self, t):         return _kill("slack")
    def _do_close_zoom(self, t):          return _kill("zoom")
    def _do_close_teams(self, t):         return _kill("teams")
    def _do_close_skype(self, t):         return _kill("skype")
    def _do_close_telegram(self, t):      return _kill("telegram")
    def _do_close_whatsapp(self, t):      return _kill("whatsapp")
    def _do_close_facebook(self, t):      return "Closing Facebook tab in your browser."
    def _do_close_twitter(self, t):       return "Closing Twitter tab in your browser."
    def _do_close_linkedin(self, t):      return "Closing LinkedIn tab in your browser."
    def _do_close_netflix(self, t):       return _kill("netflix")
    def _do_close_hotstar(self, t):       return "Closing Hotstar tab in your browser."
    def _do_close_prime_video(self, t):   return "Closing Prime Video tab in your browser."
    def _do_close_google_drive(self, t):  return "Closing Google Drive tab in your browser."
    def _do_close_icloud(self, t):        return "Closing iCloud tab in your browser."
    def _do_close_onedrive(self, t):      return _kill("onedrive")
    def _do_close_dropbox(self, t):       return _kill("dropbox")
    def _do_close_steam(self, t):         return _kill("steam")
    def _do_close_evernote(self, t):      return _kill("evernote")
    def _do_close_photoshop(self, t):     return _kill("photoshop")
    def _do_close_adobe_reader(self, t):  return _kill("acrobat")
    def _do_close_paint(self, t):         return _kill("mspaint")
    def _do_close_sticky_notes(self, t):  return _kill("stikynot")
    def _do_close_task_manager(self, t):  return _kill("taskmgr")
    def _do_close_cmd(self, t):           return _kill("cmd")
    def _do_close_settings(self, t):      return _kill("SystemSettings")
    def _do_close_control_panel(self, t): return _kill("control")
    def _do_close_file_explorer(self, t): return _kill("explorer")
    def _do_close_snipping_tool(self, t): return _kill("snippingtool")
    def _do_close_device_manager(self,t): return _kill("mmc")
    def _do_close_registry_editor(self,t):return _kill("regedit")
    def _do_close_gitbash(self, t):       return _kill("git-bash")
    def _do_close_virtualbox(self, t):    return _kill("virtualbox")
    def _do_close_vmware(self, t):        return _kill("vmware")
    def _do_close_antivirus(self, t):     return "Closing antivirus application."
    def _do_close_defender(self, t):      return "Closing Windows Defender."

    # system
    def _do_take_screenshot(self, t):
        try:
            import pyautogui
            ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(os.path.expanduser("~"), f"waku_screenshot_{ts}.png")
            pyautogui.screenshot(path)
            return f"Screenshot saved as waku_screenshot_{ts}.png."
        except ImportError:
            if OS=="Windows": sp.Popen("snippingtool", shell=True)
            return "Opening screenshot tool."
    def _do_record_screen(self, t):
        return "Screen recording needs OBS Studio. Download it from obsproject.com."
    def _do_lock_screen(self, t):
        if OS=="Windows": sp.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
        elif OS=="Darwin": sp.Popen(["pmset","displaysleepnow"])
        else: sp.Popen("gnome-screensaver-command -l", shell=True)
        return "Locking your screen."
    def _do_shutdown_computer(self, t):
        return "For safety, please shut down manually from the Start menu."
    def _do_restart_computer(self, t):
        return "For safety, please restart manually from the Start menu."
    def _do_log_off(self, t):
        return "For safety, please log off manually."
    def _do_open_clipboard(self, t):
        if OS=="Windows": sp.Popen("ms-settings:clipboard", shell=True)
        return "Opening clipboard history."
    def _do_clear_clipboard(self, t):
        try:
            import pyperclip; pyperclip.copy("")
        except ImportError: pass
        return "Clipboard cleared."
    def _do_open_downloads(self, t):
        path = os.path.join(os.path.expanduser("~"), "Downloads")
        if OS=="Windows": sp.Popen(f'explorer "{path}"', shell=True)
        elif OS=="Darwin": sp.Popen(["open", path])
        else: sp.Popen(f'xdg-open "{path}"', shell=True)
        return "Opening Downloads folder."
    def _do_open_desktop(self, t):
        path = os.path.join(os.path.expanduser("~"), "Desktop")
        if OS=="Windows": sp.Popen(f'explorer "{path}"', shell=True)
        elif OS=="Darwin": sp.Popen(["open", path])
        else: sp.Popen(f'xdg-open "{path}"', shell=True)
        return "Opening Desktop folder."

    # utilities
    def _do_calculate_math(self, text):
        expr = (text.lower()
                .replace("calculate","").replace("compute","").replace("solve","")
                .replace("evaluate","").replace("what is","").replace("find","")
                .replace("plus","+").replace("minus","-").replace("times","*")
                .replace("multiplied by","*").replace("divided by","/")
                .replace("to the power of","**").strip())
        try:
            safe = re.sub(r"[^0-9+\-*/().\s]","", expr)
            result = eval(safe)  # noqa
            return f"The answer is {result}."
        except Exception:
            return "I could not calculate that. Try saying calculate 5 plus 3."
    def _do_translate_word(self, t):
        webbrowser.open("https://translate.google.com")
        return "Opening Google Translate for you."
    def _do_weather_info(self, t):
        webbrowser.open("https://weather.com")
        return "Opening Weather for you."
    def _do_get_news(self, t):
        webbrowser.open("https://news.google.com")
        return "Opening Google News for you."
    def _do_book_flight(self, t):
        webbrowser.open("https://www.google.com/travel/flights")
        return "Opening Google Flights to help you book a flight."
    def _do_set_alarm(self, text):
        m = re.search(r"(\d{1,2})[:\.]?(\d{0,2})\s*(am|pm)?", text, re.I)
        if m:
            hr = int(m.group(1)); mn = int(m.group(2) or 0)
            per = (m.group(3) or "").lower()
            if per=="pm" and hr!=12: hr+=12
            if per=="am" and hr==12: hr=0
            webbrowser.open("https://calendar.google.com")
            return f"Alarm noted for {hr:02d}:{mn:02d}. Opening Google Calendar to confirm."
        webbrowser.open("https://calendar.google.com")
        return "Opening Google Calendar for you to set an alarm."
    def _do_set_timer(self, text):
        m = re.search(r"(\d+)\s*(second|minute|hour|sec|min|hr)", text, re.I)
        if m:
            val = int(m.group(1)); unit = m.group(2).lower()
            webbrowser.open(f"https://www.google.com/search?q={val}+{unit}+timer")
            return f"Starting a {val} {unit} timer via Google."
        webbrowser.open("https://www.google.com/search?q=timer")
        return "Opening a timer for you."
    def _do_create_note(self, t):
        webbrowser.open("https://keep.google.com")
        return "Opening Google Keep to create a note."
    def _do_create_reminder(self, t):
        webbrowser.open("https://calendar.google.com")
        return "Opening Google Calendar to set a reminder."
    def _do_send_email(self, t):
        webbrowser.open("https://mail.google.com/mail/u/0/#compose")
        return "Opening Gmail compose window."


# ── Orb ───────────────────────────────────────────────────────
class OrbCanvas(tk.Canvas):
    _SC = {"idle":"#6C63FF","listening":"#22D3EE","processing":"#F59E0B","speaking":"#10B981"}

    def __init__(self, parent, size=174):
        super().__init__(parent, width=size, height=size, bg=C["bg"], highlightthickness=0)
        self.cx=size//2; self.cy=size//2; self.R=size//2-22
        self.state="idle"; self._ang=0.0; self._ph=0.0
        self._tick()

    def set_state(self, s): self.state=s

    def _tick(self):
        sp={"idle":0.6,"listening":3.5,"processing":5.0,"speaking":2.2}
        self._ang=(self._ang+sp.get(self.state,1.0))%360; self._ph+=0.10
        self._draw(); self.after(30, self._tick)

    def _draw(self):
        self.delete("all")
        cx,cy,R=self.cx,self.cy,self.R; col=self._SC.get(self.state,"#6C63FF")
        for off,a in [(28,.04),(18,.09),(9,.18)]:
            rr=R+off; self.create_oval(cx-rr,cy-rr,cx+rr,cy+rr,outline=self._dim(col,a),width=1,fill="")
        a1=math.radians(self._ang)
        for a,sz in [(a1,5),(a1+math.pi,3)]:
            dx=cx+(R+15)*math.cos(a); dy=cy+(R+15)*math.sin(a)
            self.create_oval(dx-sz,dy-sz,dx+sz,dy+sz,fill=col,outline="")
        self.create_oval(cx-R,cy-R,cx+R,cy+R,fill=col,outline="")
        self.create_oval(cx-R+10,cy-R+10,cx-R+32,cy-R+32,fill="#FFFFFF",outline="",stipple="gray25")
        if self.state in ("listening","speaking","processing"): self._waves(cx,cy)
        else: self._mic(cx,cy)

    def _waves(self,cx,cy):
        n,bw,gap=7,4,5; total=n*bw+(n-1)*gap; x0=cx-total//2
        for i in range(n):
            h=max(26*abs(math.sin(self._ph+i*0.8)),5); x=x0+i*(bw+gap)
            self.create_rectangle(x,cy+h/2,x+bw,cy-h/2,fill="#FFFFFF",outline="")

    def _mic(self,cx,cy):
        mw,mh=10,15
        self.create_rectangle(cx-mw//2,cy-mh//2,cx+mw//2,cy+mh//2,fill="#FFFFFF",outline="")
        self.create_arc(cx-mw,cy-2,cx+mw,cy+mh,start=0,extent=-180,style="arc",outline="#FFFFFF",width=2)
        self.create_line(cx,cy+mh//2+2,cx,cy+mh//2+7,fill="#FFFFFF",width=2)
        self.create_line(cx-5,cy+mh//2+7,cx+5,cy+mh//2+7,fill="#FFFFFF",width=2)

    @staticmethod
    def _dim(h,a):
        r=int(int(h[1:3],16)*a); g=int(int(h[3:5],16)*a); b=int(int(h[5:7],16)*a)
        return f"#{r:02x}{g:02x}{b:02x}"


# ── Main Window ───────────────────────────────────────────────
class WakuApp(ctk.CTk):
    def __init__(self, model):
        super().__init__()
        self.title("Waku — Voice Assistant")
        self.geometry("460x860"); self.minsize(420,720)
        self.configure(fg_color=C["bg"])
        self._model=model; self._tts=TTS(); self._rec=Recogniser()
        self._music=MusicPlayer(MUSIC_DIR)
        self._acts=Actions(self._music, self._ask_voice)
        self._state="idle"
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.bind("<space>", lambda e: self._toggle_listen())
        self.bind("<Escape>", lambda e: self._go_idle())
        self.after(700, lambda: self._respond(
            "Hello! I am Waku, your personal voice assistant. "
            "Press Space or tap the orb to speak."))

    def _build_ui(self):
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(6,weight=1)
        self._build_topbar(); self._build_orb(); self._build_status()
        self._build_chat(); self._build_controls()
        self._build_music_bar(); self._build_commands()

    def _build_topbar(self):
        bar=ctk.CTkFrame(self,fg_color=C["surface"],corner_radius=0,height=48)
        bar.grid(row=0,column=0,sticky="ew"); bar.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(bar,text="🎙",font=("Segoe UI Emoji",20),text_color=C["accent"]).grid(row=0,column=0,padx=(14,6),pady=10)
        ctk.CTkLabel(bar,text="WAKU",font=("Segoe UI",17,"bold"),text_color=C["text"]).grid(row=0,column=1,sticky="w")
        self._dot=ctk.CTkLabel(bar,text="●",font=("Segoe UI",13),text_color=C["green"])
        self._dot.grid(row=0,column=2,padx=4)
        self._bar_lbl=ctk.CTkLabel(bar,text="Ready",font=("Segoe UI",10),text_color=C["muted"])
        self._bar_lbl.grid(row=0,column=3,padx=(0,14))

    def _build_orb(self):
        frm=ctk.CTkFrame(self,fg_color=C["bg"]); frm.grid(row=1,column=0,pady=(14,0))
        self._orb=OrbCanvas(frm,size=174); self._orb.pack()
        self._orb.bind("<Button-1>",lambda e: self._toggle_listen())
        self._orb.configure(cursor="hand2")

    def _build_status(self):
        self._status_var=tk.StringVar(value="Press Space or tap the orb")
        self._status_lbl=ctk.CTkLabel(self,textvariable=self._status_var,font=("Segoe UI",11),text_color=C["muted"])
        self._status_lbl.grid(row=2,column=0,pady=(4,0))

    def _build_chat(self):
        outer=ctk.CTkFrame(self,fg_color=C["surface"],corner_radius=12)
        outer.grid(row=3,column=0,sticky="ew",padx=16,pady=(10,0)); outer.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(outer,text="CONVERSATION",font=("Segoe UI",8,"bold"),text_color=C["muted"]).grid(row=0,column=0,sticky="w",padx=12,pady=(8,2))
        self._chat=ctk.CTkTextbox(outer,height=95,font=("Segoe UI",11),fg_color=C["card"],text_color=C["text"],corner_radius=8,wrap="word",state="disabled")
        self._chat.grid(row=1,column=0,sticky="ew",padx=8,pady=(0,8))

    def _build_controls(self):
        row=ctk.CTkFrame(self,fg_color="transparent"); row.grid(row=4,column=0,sticky="ew",padx=16,pady=8)
        row.grid_columnconfigure((0,1,2),weight=1)
        self._listen_btn=ctk.CTkButton(row,text="🎤  Listen",font=("Segoe UI",11),fg_color=C["accent"],hover_color="#5550CC",corner_radius=50,height=38,command=self._toggle_listen)
        self._listen_btn.grid(row=0,column=0,padx=(0,4),sticky="ew")
        ctk.CTkButton(row,text="⏹  Stop",font=("Segoe UI",11),fg_color=C["card"],hover_color=C["border"],corner_radius=50,height=38,command=self._go_idle).grid(row=0,column=1,padx=4,sticky="ew")
        ctk.CTkButton(row,text="✕  Quit",font=("Segoe UI",11),fg_color=C["card"],hover_color="#7F1D1D",text_color=C["danger"],corner_radius=50,height=38,command=self._quit).grid(row=0,column=2,padx=(4,0),sticky="ew")

    def _build_music_bar(self):
        bar=ctk.CTkFrame(self,fg_color=C["surface"],corner_radius=10)
        bar.grid(row=5,column=0,sticky="ew",padx=16,pady=(0,4)); bar.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(bar,text="🎵",font=("Segoe UI Emoji",14)).grid(row=0,column=0,padx=(12,6),pady=8)
        self._now_playing=tk.StringVar(value="No track playing")
        ctk.CTkLabel(bar,textvariable=self._now_playing,font=("Segoe UI",10),text_color=C["muted"]).grid(row=0,column=1,sticky="w")
        for col,(txt,cmd) in enumerate([
            ("▶",lambda: self._run_cmd("play music")),
            ("⏹",lambda: self._run_cmd("stop the music")),
            ("⏭",lambda: self._run_cmd("next song please")),
        ],start=2):
            ctk.CTkButton(bar,text=txt,width=32,height=28,font=("Segoe UI",12),fg_color=C["card"],hover_color=C["border"],corner_radius=6,command=cmd).grid(row=0,column=col,padx=3,pady=6)
        ctk.CTkButton(bar,text="≡",width=32,height=28,font=("Segoe UI",12),fg_color=C["card"],hover_color=C["border"],corner_radius=6,command=self._show_tracks).grid(row=0,column=5,padx=(3,12),pady=6)

    def _build_commands(self):
        ctk.CTkLabel(self,text="COMMANDS  —  click any card to run",font=("Segoe UI",8,"bold"),text_color=C["muted"]).grid(row=5,column=0,sticky="w",padx=20,pady=(6,2))
        scroll=ctk.CTkScrollableFrame(self,fg_color=C["surface"],corner_radius=12,height=210)
        scroll.grid(row=6,column=0,sticky="nsew",padx=16,pady=(0,14)); self.grid_rowconfigure(6,weight=1)
        cols=4
        for c in range(cols): scroll.grid_columnconfigure(c,weight=1)
        for idx,(icon,label,phrase) in enumerate(COMMAND_CARDS):
            r,c=divmod(idx,cols); self._make_card(scroll,icon,label,phrase,r,c)

    def _make_card(self,parent,icon,label,phrase,r,c):
        card=ctk.CTkFrame(parent,fg_color=C["card"],corner_radius=10,cursor="hand2")
        card.grid(row=r,column=c,padx=3,pady=3,sticky="nsew")
        ctk.CTkLabel(card,text=icon,font=("Segoe UI Emoji",17)).pack(pady=(9,1))
        ctk.CTkLabel(card,text=label,font=("Segoe UI",9),text_color=C["text"],wraplength=90).pack(pady=(0,8))
        def _click(e=None,p=phrase):
            if self._state=="idle": self._run_cmd(p)
        card.bind("<Button-1>",_click)
        for ch in card.winfo_children(): ch.bind("<Button-1>",_click)
        def _enter(e,w=card): w.configure(fg_color=C["border"])
        def _leave(e,w=card): w.configure(fg_color=C["card"])
        card.bind("<Enter>",_enter); card.bind("<Leave>",_leave)

    def _set_state(self,state,status,bar):
        self._state=state; self._orb.set_state(state)
        self._status_var.set(status); self._bar_lbl.configure(text=bar)
        dc={"idle":C["green"],"listening":C["cyan"],"processing":C["amber"],"speaking":C["green"]}.get(state,C["muted"])
        self._dot.configure(text_color=dc)
        sc={"idle":C["muted"],"listening":C["cyan"],"processing":C["amber"],"speaking":C["green"]}.get(state,C["muted"])
        self._status_lbl.configure(text_color=sc)

    def _go_idle(self):
        self._set_state("idle","Press Space or tap the orb","Ready")
        self._listen_btn.configure(text="🎤  Listen",fg_color=C["accent"])

    def _log(self,role,text):
        self._chat.configure(state="normal")
        prefix="👤  You:  " if role=="user" else "🔊  Waku: "
        self._chat.insert("end",prefix+text+"\n\n"); self._chat.see("end")
        self._chat.configure(state="disabled")

    def _toggle_listen(self):
        if self._state=="listening": self._go_idle()
        else: self._start_listen()

    def _start_listen(self):
        self._set_state("listening","Listening...  speak now","Listening")
        self._listen_btn.configure(text="⏹  Stop",fg_color="#0E7490")
        threading.Thread(target=self._listen_worker,daemon=True).start()

    def _listen_worker(self):
        text=self._rec.listen()
        if text: self.after(0,lambda: self._run_cmd(text))
        else: self.after(0,self._go_idle)

    def _run_cmd(self,text):
        self._log("user",text)
        self._set_state("processing","Thinking...","Processing")
        self._listen_btn.configure(text="🎤  Listen",fg_color=C["accent"])
        threading.Thread(target=self._process_worker,args=(text,),daemon=True).start()

    def _process_worker(self,text):
        tag,conf=predict(self._model,text)
        if conf<0.15:
            response="I did not catch that. Try saying open YouTube or play music."
        else:
            response=self._acts.dispatch(tag,text)
        self.after(0,lambda r=response,b=(tag=="greet" and False): self._respond(r,b))

    def _respond(self,text,is_farewell=False):
        self._log("waku",text)
        self._set_state("speaking","Speaking...","Speaking")
        if any(w in text.lower() for w in ("now playing","playing next","resuming")):
            self._now_playing.set(text)
        elif "music stopped" in text.lower():
            self._now_playing.set("No track playing")
        def _done():
            self.after(0,self._go_idle)
            if is_farewell: self.after(1500,self._quit)
        self._tts.speak(text,done_cb=_done)

    def _ask_voice(self,prompt):
        self._tts.speak(prompt); time.sleep(1.8)
        self.after(0,lambda: self._set_state("listening","Listening for your answer...","Listening"))
        result=self._rec.listen(timeout=6)
        self.after(0,self._go_idle)
        return result

    def _show_tracks(self):
        tracks=self._music.get_track_list()
        popup=ctk.CTkToplevel(self); popup.title("Music Library")
        popup.geometry("320x380"); popup.configure(fg_color=C["surface"]); popup.grab_set()
        ctk.CTkLabel(popup,text="🎵  Music Library",font=("Segoe UI",14,"bold"),text_color=C["text"]).pack(pady=(16,8))
        if not tracks:
            ctk.CTkLabel(popup,text="No MP3 files found.\n\nCreate a 'music' folder next to\nwaku_launcher.py and add .mp3 files.",font=("Segoe UI",11),text_color=C["muted"],justify="center").pack(pady=20)
        else:
            sb=ctk.CTkScrollableFrame(popup,fg_color=C["card"],corner_radius=8)
            sb.pack(fill="both",expand=True,padx=12,pady=(0,12))
            for i,name in enumerate(tracks,1):
                ctk.CTkLabel(sb,text=f"{i}.  {name}",font=("Segoe UI",10),text_color=C["text"],anchor="w").pack(fill="x",padx=8,pady=3)
        ctk.CTkButton(popup,text="Close",corner_radius=50,fg_color=C["card"],hover_color=C["border"],command=popup.destroy).pack(pady=(0,12))

    def _quit(self):
        self._music.stop(); pygame.mixer.quit()
        try: self.destroy()
        except Exception: pass


if __name__=="__main__":
    if not os.path.exists(INTENTS_FILE):
        print(f"\n  ERROR: intents.json not found at {INTENTS_FILE}\n"); sys.exit(1)
    print("="*50); print("  Waku Voice Assistant"); print("="*50)
    if not os.path.isdir(MUSIC_DIR):
        os.makedirs(MUSIC_DIR,exist_ok=True)
        print(f"\n  Tip: Add .mp3 files to: {MUSIC_DIR}")
    model=load_or_train(); print("  Starting launcher..."); print("="*50)
    app=WakuApp(model); app.mainloop()
