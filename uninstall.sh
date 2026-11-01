#!/bin/bash
echo "🗑️ Uninstalling Veer Neural Voice Assistant..."
systemctl --user stop veer.service 2>/dev/null || true
systemctl --user disable veer.service 2>/dev/null || true
pkill -f "veer_engine.py" 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/veer.service"
sudo rm -f /usr/local/bin/veer /usr/local/bin/veer-toggle /usr/local/bin/hud-veer
rm -rf "$HOME/.veer" "$HOME/.cache/veer_hud_state"
echo "✅ Veer completely uninstalled."
