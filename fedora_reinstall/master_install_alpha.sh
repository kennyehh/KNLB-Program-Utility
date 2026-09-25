#!/bin/bash

# master_install_pre-alpha.sh - Universal Linux Installer
# Based on guidelines from AGENTS.md and README.md

# Terminal colors
GREEN='\033[1;32m'
RED='\033[1;31m'
ORANGE='\033[38;5;208m'
RESET='\033[0m'

# Determine current distro and package manager
DISTRO="$(grep -Eo 'Ubuntu|Debian|Fedora|CentOS|Arch' /etc/os-release | head -n1)"
PACKAGE_MANAGER="$(command -v apt || command -v dnf || command -v pacman || echo "")"

# Scan for install scripts in the same directory
INSTALL_SCRIPTS=(install_*.sh)

# Check for potentially unsafe content in scripts
is_safe() {
    local file="$1"

    local blocked_patterns=(
        'rm -rf'
        'sudo'
        'wget'
        'curl'
        'eval'
        'source'
        'bash -c'
        'bashc'
        'wget -O'
        'curl -o'
        'echo **'
        'rm *'
        'rm -f'
        'find . -name'
    )

    for pattern in "${blocked_patterns[@]}"; do
        if grep -vE '^[[:space:]]*#' "$file" |
           grep -Fq -- "$pattern"; then
            return 1
        fi
    done

    return 0
}

# Log file option
read -p "Create log file (y/n)? " LOG

if [[ "$LOG" == "y" ]]; then
    exec > >(tee >(sed $'s/\033\\[[0-9;]*m//g' >> "master_install.log")) 2>&1

    echo
    echo "---"
    echo "Installation Log: $(date +"%Y-%m-%d %H:%M:%S")"
fi

# Display the DISTRO and PACKAGE_MANAGER information
echo "-"
echo "Current Distribution: $DISTRO"
echo "Package Manager: $PACKAGE_MANAGER"
echo "-"

# Install required package managers (flatpak, snap) as prerequisites
REQUIRED_PM_DIR="$(dirname "$0")/required_pm"
REQUIRED_PM_SCRIPTS=("$REQUIRED_PM_DIR"/install_*.sh)

for script in "${REQUIRED_PM_SCRIPTS[@]}"; do
    if [[ -f "$script" ]]; then
        echo "Executing $script..."
        if bash "$script"; then
            echo -e "${GREEN}Success!${RESET}"
        else
            echo -e "${RED}Error in $script${RESET}"
        fi
    fi
done

# Proceed with install scripts
#
# Execute safe scripts
for script in "${INSTALL_SCRIPTS[@]}"; do
    if [[ -f "$script" ]]; then
        if is_safe "$script"; then
            echo "Executing $script..."
            if bash "$script"; then
                echo -e "${GREEN}Success!${RESET}"
            else
                echo -e "${RED}Error in $script${RESET}"
            fi
        else
            echo -e "${ORANGE}Skipped $script (potentially malicious)${RESET}"
        fi
    fi
done
