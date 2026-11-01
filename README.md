# ⚡ Veer — Offline Neural Voice Assistant & Braille HUD for Linux

A zero-lag, offline Linux voice assistant powered by **Vosk STT**, **RyanNeural Edge-TTS**, and a real-time **Unicode Braille Gyroscopic Neural Core (`hud-veer`)**.

## Easy Custom Command Builder (Zero Coding Required)
Create and manage your own voice triggers, custom spoken replies, and Linux actions directly from the terminal:
* **Add a command interactively:** `veer add`
* **List all voice commands:** `veer list`
* **Remove a command:** `veer remove <command_name>`
* **Edit raw JSON registry:** `veer edit` (`~/Vault/veer_commands.json`)

## Official Companion Module: Air-Sense (Optional)
Veer includes built-in voice hooks (`"start air sense"`, `"air sense hud"`, `"stop air sense"`) for **[Air-Sense](https://github.com/Kaush-kk/air-sense)**—our 1-hand and 2-hand webcam spatial telepathy engine.
* If Air-Sense is not installed, Veer operates normally and notifies you if you invoke an Air-Sense voice trigger.
* To enable touchless hand gestures alongside Veer, install the companion repository:

    git clone https://github.com/Kaush-kk/air-sense.git
    cd air-sense && ./install.sh

## One-Command Install (Veer Core)

    git clone https://github.com/Kaush-kk/veer-jarvis-linux.git
    cd veer-jarvis-linux && ./install.sh
