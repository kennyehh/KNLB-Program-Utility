#!/bin/bash

if ! dnf -y install fastfetch; then
    echo "Error: failed to install fastfetch" >&2
    exit 1
fi

BASHRC="$HOME/.bashrc"

if grep -qF "fastfetch" "$BASHRC" 2>/dev/null; then
    echo "fastfetch already added to $BASHRC"
else
    cat >> "$BASHRC" << 'EOF'

fastfetch

EOF
    echo "Added fastfetch to $BASHRC"
fi
