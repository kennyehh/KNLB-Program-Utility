#!/bin/bash

dnf -y install alacritty

bash "$(dirname "$0")/configs/config_alacritty.sh"
