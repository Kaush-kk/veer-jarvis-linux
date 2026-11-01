# ⚡ Veer — Offline Neural Voice Assistant & Braille HUD for Linux

A zero-lag, offline Linux voice assistant powered by **Vosk Speech Recognition**, **RyanNeural Edge-TTS**, and a real-time **Unicode Braille Gyroscopic Neural Core (`hud-veer`)**.

---

## 1. One-Command Installation

    git clone https://github.com/Kaush-kk/veer-jarvis-linux.git
    cd veer-jarvis-linux && ./install.sh

### Optional Companion Module: Air-Sense (Webcam Hand Gestures)
To enable Veer's touchless hand-gesture commands (`"start air sense"`, `"air sense hud"`, `"stop air sense"`), install the companion **[air-sense](https://github.com/Kaush-kk/air-sense)** repository:

    git clone https://github.com/Kaush-kk/air-sense.git
    cd air-sense && ./install.sh

*(If Air-Sense is not installed, Veer operates normally and alerts you if you invoke an Air-Sense voice command).*

---

## 2. Complete Usage & Custom Command Guide

### Master CLI Controls
* **`veer start`** — Starts Veer silently in the background (`Super + V` toggles Veer ON/OFF).
* **`veer stop`** — Stops Veer and releases your microphone.
* **`veer test`** — Runs Veer live in the terminal showing real-time microphone levels and recognized words.
* **`hud-veer`** — Launches the live animated **Braille Gyroscopic Neural Core** visualizer in your terminal.

### Adding & Customizing Your Own Voice Commands (Zero Coding Required)
* **Interactive Command Wizard (`veer add`):**
  Run `veer add` in your terminal and answer the 4 prompts:
  1. Unique command ID (e.g., `favourite_song`)
  2. Voice phrases to trigger it (e.g., `favourite song, play favourite`)
  3. Spoken reply (e.g., `Playing your favourite song from Metrolist`)
  4. Linux command to execute (e.g., `metrolist --play "laboon ko"`)
* **List all configured commands:** `veer list`
* **Remove a command:** `veer remove <command_name>`
* **Edit raw JSON config:** `veer edit` (`~/Vault/veer_commands.json`)

---

## 3. One-Command Complete Removal (Uninstall & Delete Cloned Repo)

To completely stop Veer, remove all binaries, models, and virtual environments, and delete the cloned GitHub folder:

    ~/veer-jarvis-linux/uninstall.sh && rm -rf ~/veer-jarvis-linux
