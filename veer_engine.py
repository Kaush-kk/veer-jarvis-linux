#!/usr/bin/env python3
import os, sys, time, glob, json, hashlib, shutil, threading, subprocess
from collections import deque
import numpy as np
from vosk import Model, KaldiRecognizer, SetLogLevel

SetLogLevel(-1)

CONFIG_PATH = os.path.expanduser("~/Vault/veer_commands.json")
MUSIC_DIR   = os.path.expanduser("~/Vault/Music")
MODEL_PATH  = os.path.expanduser("~/.veer/model")
CACHE_DIR   = os.path.expanduser("~/.veer/voice_cache")
VOICE_MODEL = "en-GB-RyanNeural"

os.makedirs(CACHE_DIR, exist_ok=True)
track_idx = -1
audio_queue = deque(maxlen=25)
is_speaking = False
running = True

PHONETIC_MAP = {
    "since": "sense", "sent": "sense", "cents": "sense", "sins": "sense",
    "airlines": "air sense", "essence": "air sense",
    "bolt": "vault", "volt": "vault", "fault": "vault", "bald": "vault",
    "we": "veer", "here": "veer", "fear": "veer", "dear": "veer", "peer": "veer"
}

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def get_audio_cache_path(text):
    h = hashlib.md5(f"{VOICE_MODEL}:{text}".encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.mp3")

def synthesize_to_cache(text, out_file):
    try:
        subprocess.run(
            [sys.executable, "-m", "edge_tts", "--voice", VOICE_MODEL, "--rate=+5%", "--text", text, "--write-media", out_file],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
        )
    except Exception:
        pass

def pre_cache_voice_lines(cfg):
    lines = [cfg.get("wake_reply", ""), cfg.get("sleep_reply", "")]
    for cmd in cfg.get("commands", []):
        if cmd.get("reply"):
            lines.append(cmd["reply"])
    for text in set(filter(None, lines)):
        out_file = get_audio_cache_path(text)
        if not os.path.exists(out_file):
            synthesize_to_cache(text, out_file)

def speak(text):
    global is_speaking
    if not text:
        return
    is_speaking = True
    audio_queue.clear()
    print(f"\n🗣️ VEER: {text}")
    subprocess.Popen(["notify-send", "-u", "normal", "-t", "2500", "✦ VEER", text],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out_file = get_audio_cache_path(text)
    if not os.path.exists(out_file):
        synthesize_to_cache(text, out_file)
    if os.path.exists(out_file):
        subprocess.run(["mpv", "--no-video", "--really-quiet", out_file],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(["espeak-ng", "-v", "en-us", "-s", "160", text],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    audio_queue.clear()
    time.sleep(0.15)
    is_speaking = False

def play_next_track():
    global track_idx
    exts = ("*.opus", "*.mp3", "*.m4a", "*.wav", "*.flac")
    files = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(MUSIC_DIR, ext)))
    files = sorted(files)
    if not files:
        speak("No music files found in your Vault directory.")
        return
    track_idx = (track_idx + 1) % len(files)
    subprocess.run(["pkill", "-f", "mpv.*--no-video"], stderr=subprocess.DEVNULL)
    subprocess.Popen(["mpv", "--no-video", "--loop-playlist=inf", files[track_idx]],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

def run_diagnostics():
    load = os.getloadavg()[0]
    with open("/proc/meminfo") as f:
        lines = f.readlines()
    total = int(lines[0].split()[1]) / (1024 * 1024)
    avail = int(lines[2].split()[1]) / (1024 * 1024)
    ram_pct = int(((total - avail) / total) * 100)
    bat_path = "/sys/class/power_supply/BAT0/capacity"
    bat = f"{open(bat_path).read().strip()} percent" if os.path.exists(bat_path) else "AC power"
    speak(f"All systems nominal. CPU load is {load:.1f}. Memory usage is at {ram_pct} percent. Power is at {bat}.")

def execute_action(action, reply_text=""):
    if action.startswith("INTERNAL:AIRSENSE_") or "air-sense" in action:
        if not shutil.which("air-sense") and not os.path.exists("/usr/local/bin/air-sense"):
            speak("Air Sense module not found on this system. Please install the Air Sense companion repository from GitHub.")
            subprocess.Popen([
                "notify-send", "-u", "critical", "-t", "5000",
                "✦ Air-Sense Companion Missing",
                "Install: git clone https://github.com/Kaush-kk/air-sense.git"
            ])
            return
        if reply_text:
            speak(reply_text)
        sub = "hud" if ("HUD" in action or "hud" in action) else ("stop" if "STOP" in action or "stop" in action else "start")
        subprocess.Popen(["/usr/local/bin/air-sense", sub],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return

    if reply_text:
        speak(reply_text)

    if action == "INTERNAL:PLAY_NEXT":
        play_next_track()
    elif action == "INTERNAL:DIAGNOSTICS":
        run_diagnostics()
    elif action:
        subprocess.Popen(action, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

def normalize_phonetics(text):
    words = text.lower().strip().split()
    mapped = [PHONETIC_MAP.get(w, w) for w in words]
    return " ".join(mapped)

def match_trigger(heard, triggers):
    h_norm = normalize_phonetics(heard)
    h_words = set(h_norm.split())
    for trig in triggers:
        t_clean = trig.lower().strip()
        if t_clean in h_norm:
            return True
        t_words = set(t_clean.split())
        if len(t_words) >= 2 and t_words.issubset(h_words):
            return True
    return False

def mic_reader_thread():
    proc = None
    try:
        proc = subprocess.Popen(
            ["parec", "--rate=16000", "--format=s16le", "--channels=1", "--raw", "--latency-msec=30"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        proc = subprocess.Popen(
            ["arecord", "-D", "pipewire", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw", "-q", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
    while running:
        data = proc.stdout.read(1600)
        if not data:
            break
        if not is_speaking:
            audio_queue.append(data)
    proc.terminate()

def main():
    global running
    subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "0"], stderr=subprocess.DEVNULL)
    subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SOURCE@", "1.00"], stderr=subprocess.DEVNULL)

    cfg = load_config()
    print("✦ Pre-caching Veer neural voice lines...")
    pre_cache_voice_lines(cfg)

    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, 16000)

    threading.Thread(target=mic_reader_thread, daemon=True).start()
    awake = True
    speak(cfg.get("wake_reply", "Veer online."))
    print("🟢 VEER LIVE (Zero-Lag Stream Active — Speak naturally)")

    try:
        while True:
            if not audio_queue:
                time.sleep(0.015)
                continue
            chunk = audio_queue.popleft()
            samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
            peak = np.max(np.abs(samples)) if len(samples) else 0
            if peak > 300:
                gain = min(1.8, 18000.0 / max(peak, 1.0))
                chunk = np.clip(samples * gain, -32768, 32767).astype(np.int16).tobytes()

            is_final = rec.AcceptWaveform(chunk)
            text = json.loads(rec.Result()).get("text", "").strip() if is_final else json.loads(rec.PartialResult()).get("partial", "").strip()
            if not text:
                continue

            norm_text = normalize_phonetics(text)
            sys.stdout.write(f"\r🎙️ Hearing: {norm_text:<48}")
            sys.stdout.flush()

            if match_trigger(norm_text, cfg.get("sleep_phrases", [])):
                if awake:
                    awake = False
                    speak(cfg.get("sleep_reply", "Standing by."))
                rec.Reset()
                audio_queue.clear()
                continue

            if match_trigger(norm_text, cfg.get("wake_phrases", [])) and not awake:
                awake = True
                speak(cfg.get("wake_reply", "Veer online."))
                rec.Reset()
                audio_queue.clear()
                continue

            if not awake and "veer" not in norm_text:
                if is_final:
                    rec.Reset()
                continue

            for cmd in cfg.get("commands", []):
                if match_trigger(norm_text, cmd.get("triggers", [])):
                    execute_action(cmd.get("action", ""), cmd.get("reply", ""))
                    rec.Reset()
                    audio_queue.clear()
                    break
    except KeyboardInterrupt:
        running = False
        print("\n🔇 Veer shutting down.")

if __name__ == "__main__":
    main()
