#!/bin/bash

# We use Alacritty's default Linux config directory as our storage location here.
THEME_DIR="$HOME/.config/alacritty/themes"
mkdir -p "$THEME_DIR"
git clone https://github.com/alacritty/alacritty-theme "$THEME_DIR"

CONFIG_DIR="$HOME/.config/alacritty"
mkdir -p "$CONFIG_DIR"

cat > "$CONFIG_DIR/alacritty.toml" << 'EOF'
[window]
dimensions = { columns = 109, lines = 30 }
title = "Alacritty"
#decorations = "none"
opacity = 0.9
dynamic_padding = true
padding.x = 2
padding.y = 2

[scrolling]
history = 10000
multiplier = 5

[cursor.style]
shape = "Beam"
blinking = "Never"

[colors]
#transparent_background_colors = true
draw_bold_text_with_bright_colors = true

[env]
TERM = "xterm-256color"

[font]
#glyph_offset = { x = 1, y = 0}
normal.family = "MesloLGS Nerd Font Mono"
normal.style = "Regular"
size = 12.0

[font.bold]
family = "MesloLGS Nerd Font Mono"
style = "Bold"

[font.italic]
family = "MesloLGS Nerd Font Mono"
style = "Italic"

[keyboard]
bindings = [
 # Clipboard
 { key = "V", mods = "Control | Shift", action = "Paste" },
 { key = "C", mods = "Control | Shift", action = "Copy" },
 # Increase/decrease font size without restarting
 { key = "Equals",    mods = "Control",       action = "IncreaseFontSize" },
 { key = "Minus",     mods = "Control",       action = "DecreaseFontSize" },
 { key = "Key0",      mods = "Control",       action = "ResetFontSize"    },
 { key = "N",         mods = "Super",         action = "CreateNewWindow" }
 ]

[general]
live_config_reload = true
import = ["~/.config/alacritty/themes/tokyo-night.toml",]
#import = ["~/.config/alacritty/themes/tokyo_night_enhanced",]

[mouse]
hide_when_typing = true
EOF

echo "Alacritty config written to: $CONFIG_DIR/alacritty.toml"
