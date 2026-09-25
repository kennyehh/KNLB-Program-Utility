#!/bin/bash

while true; do
    # Prompt user for font URL
    read -p "Enter the font file URL: " FONT_URL

    # Extract font name from URL (remove .zip extension)
    FONT_NAME=$(basename "$FONT_URL" | sed 's/\.zip$//')

    # Create directory for font
    FONT_DIR="$HOME/.local/share/fonts/$FONT_NAME"
    mkdir -p "$FONT_DIR"

    # Download font
    if ! wget -O "${FONT_DIR}/font.zip" "$FONT_URL"; then
        echo "Error: failed to download $FONT_URL" >&2
        rm -rf "$FONT_DIR"
    else
        # Unzip font
        if ! unzip "${FONT_DIR}/font.zip" -d "$FONT_DIR"; then
            echo "Error: failed to unzip downloaded font" >&2
            rm -rf "$FONT_DIR"
        else
            # Clean up
            rm "${FONT_DIR}/font.zip"
            fc-cache -f "$FONT_DIR" >/dev/null
            echo "Font installed to: $FONT_DIR"
        fi
    fi

    # Ask if there are more fonts
    while true; do
        read -p "Are there more fonts? (Y/N) " response
        response=${response:-n}  # Default to 'n' if empty input

        if [[ $response == "N" || $response == "n" ]]; then
            exit 0
        elif [[ $response == "Y" || $response == "y" ]]; then
            break
        else
            echo "Invalid input. Please enter Y or N."
        fi
    done
done
