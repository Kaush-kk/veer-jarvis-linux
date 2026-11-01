#!/bin/bash
set -e
echo "⚡ Installing Veer (Offline Neural Voice Assistant & Braille HUD)..."

if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3.12 alsa-utils pulseaudio-utils curl unzip libnotify mpv micro
elif command -v apt >/dev/null 2>&1; then
    sudo apt update && sudo apt install -y python3-venv python3-pip alsa-utils pulseaudio-utils curl unzip libnotify-bin mpv micro
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm python alsa-utils libpulse curl unzip libnotify mpv micro
fi

mkdir -p "$HOME/.veer/voice_cache" "$HOME/Vault/Music"
PY_BIN=$(command -v python3.12 || command -v python3)
[ ! -d "$HOME/.veer/venv" ] && "$PY_BIN" -m venv "$HOME/.veer/venv"

"$HOME/.veer/venv/bin/python" -m pip install --upgrade pip
"$HOME/.veer/venv/bin/python" -m pip install vosk edge-tts numpy

if [ ! -d "$HOME/.veer/model" ]; then
    echo "⬇️ Downloading offline Vosk speech model (36MB)..."
    cd "$HOME/.veer"
    curl -LO https://alphacephei.com/vosk/models/vosk-model-small-en-in-0.4.zip
    unzip -q vosk-model-small-en-in-0.4.zip
    mv vosk-model-small-en-in-0.4 model
    rm -f vosk-model-small-en-in-0.4.zip
    cd - >/dev/null
fi

cp veer_engine.py "$HOME/.veer/veer_engine.py"
[ ! -f "$HOME/Vault/veer_commands.json" ] && cp veer_commands.json "$HOME/Vault/veer_commands.json"

sudo cp veer veer-toggle hud-veer /usr/local/bin/
sudo chmod +x /usr/local/bin/veer /usr/local/bin/veer-toggle /usr/local/bin/hud-veer

echo "✅ Veer installed! Run 'veer add' to create custom voice commands, or 'veer test' to start."
echo "💡 Optional: Install Air-Sense hand tracking -> git clone https://github.com/Kaush-kk/air-sense.git"
