import os, sys, time, glob, json, hashlib, subprocess, threading, difflib
from collections import deque
import numpy as np
from vosk import Model, KaldiRecognizer, SetLogLevel

SetLogLevel(-1)

CONFIG_PATH = os.path.expanduser("~/Vault/veer_commands.json")
MUSIC_DIR   = os.path.expanduser("~/Vault/Music")
MODEL_PATH  = os.path.expanduser("~/.veer/model")
CACHE_DIR   = os.path.expanduser("~/.veer/voice_cache")

VOICE_MODEL = "en-GB-RyanNeural"

# Phonetic error corrections for common speech-to-text mismatches
PHONETIC_FIXES = {
    "since": "sense", "sent": "sense", "cents": "sense", "essence": "air sense",
    "bolt": "vault", "volt": "vault", "fault": "vault", "world": "vault",
    "here": "veer", "fear": "veer", "dear": "veer", "beer": "veer",
    "proses": "protocol", "practical": "protocol"
}

os.makedirs(CACHE_DIR, exist_ok=True)
track_idx = -1
is_speaking = False
audio_queue = deque(maxlen=15)

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
    time.sleep(0.2)
    audio_queue.clear()
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
    track = files[track_idx]
    subprocess.run(["pkill", "-f", "mpv.*--no-video"], stderr=subprocess.DEVNULL)
    subprocess.Popen(["mpv", "--no-video", "--loop-playlist=inf", track],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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

def normalize_text(text):
    words = text.lower().replace("[unk]", "").split()
    fixed = [PHONETIC_FIXES.get(w, w) for w in words]
    return " ".join(fixed)

def matches_any(text, phrase_list):
    for p in phrase_list:
        p_clean = p.lower().strip()
        if p_clean in text:
            return True
        # Fuzzy match check for natural pronunciation variance
        p_words = p_clean.split()
        if len(p_words) >= 2 and all(pw in text for pw in p_words):
            return True
        if difflib.SequenceMatcher(None, text, p_clean).ratio() >= 0.78:
            return True
    return False

def mic_reader_worker():
    try:
        proc = subprocess.Popen(
            ["parec", "--rate=16000", "--format=s16le", "--channels=1", "--raw", "--latency-msec=30"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        proc = subprocess.Popen(
            ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw", "-q", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )

    while True:
        data = proc.stdout.read(1600)
        if not data:
            break
        if not is_speaking:
            audio_queue.append(data)

def main():
    cfg = load_config()
    print("✦ Pre-caching Veer neural voice lines...")
    pre_cache_voice_lines(cfg)

    model = Model(MODEL_PATH)
    # Using full dictionary vocabulary (no grammar restriction) prevents multi-word clipping
    rec = KaldiRecognizer(model, 16000)

    reader = threading.Thread(target=mic_reader_worker, daemon=True)
    reader.start()

    awake = True
    speak(cfg.get("wake_reply", "Veer online."))
    print("🟢 VEER FULL-DICTIONARY MODE ACTIVE (Speak naturally)")

    try:
        while True:
            if not audio_queue:
                time.sleep(0.01)
                continue

            raw_data = audio_queue.popleft()
            samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
            peak = int(np.max(np.abs(samples))) if len(samples) else 0

            # Dynamic leveling
            if 300 < peak < 16000:
                gain = min(2.2, 14000.0 / peak)
                samples = np.clip(samples * gain, -32768, 32767).astype(np.int16)
                pcm_data = samples.tobytes()
            else:
                pcm_data = raw_data

            is_final = rec.AcceptWaveform(pcm_data)
            if is_final:
                raw_text = json.loads(rec.Result()).get("text", "")
            else:
                raw_text = json.loads(rec.PartialResult()).get("partial", "")

            text = normalize_text(raw_text)

            if sys.stdout.isatty() and text:
                bars = min(10, peak // 1500)
                meter = "█" * bars + "░" * (10 - bars)
                sys.stdout.write(f"\r🎙️ Mic [{meter}] Heard: {text:<42}")
                sys.stdout.flush()

            if not text:
                continue

            # 1. Sleep Triggers
            if matches_any(text, cfg.get("sleep_phrases", [])):
                if awake:
                    awake = False
                    speak(cfg.get("sleep_reply", "Standing by."))
                rec.Reset()
                audio_queue.clear()
                continue

            # 2. Wake Triggers
            if matches_any(text, cfg.get("wake_phrases", [])) and not awake:
                awake = True
                speak(cfg.get("wake_reply", "Veer online."))
                rec.Reset()
                audio_queue.clear()
                continue

            if not awake and "veer" not in text:
                if is_final:
                    rec.Reset()
                continue

            # 3. Match Commands
            for cmd in cfg.get("commands", []):
                if matches_any(text, cmd.get("triggers", [])):
                    speak(cmd.get("reply", ""))
                    action = cmd.get("action", "")
                    if action == "INTERNAL:PLAY_NEXT":
                        play_next_track()
                    elif action == "INTERNAL:DIAGNOSTICS":
                        run_diagnostics()
                    elif action:
                        subprocess.Popen(action, shell=True,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    rec.Reset()
                    audio_queue.clear()
                    break

            if is_final:
                rec.Reset()

    except KeyboardInterrupt:
        print("\n🔇 Veer shutting down.")

if __name__ == "__main__":
    main()
