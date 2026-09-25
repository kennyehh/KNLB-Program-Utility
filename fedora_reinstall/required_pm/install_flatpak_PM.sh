#!/bin/bash

if ! dnf -y install flatpak; then
    echo "Error: failed to install flatpak" >&2
    exit 1
fi

flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
