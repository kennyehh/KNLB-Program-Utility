#!/bin/bash

if ! dnf -y install snapd; then
    echo "Error: failed to install snapd" >&2
    exit 1
fi

systemctl enable --now snapd.socket

if [[ ! -e /snap ]]; then
    ln -s /var/lib/snapd/snap /snap
fi
