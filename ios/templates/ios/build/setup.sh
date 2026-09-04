#!/usr/bin/env bash
#
# Configure a local openedx-app-ios checkout to point at this Tutor platform.
#
# iOS applications can only be compiled with Xcode, which requires macOS, so
# unlike the Android app this build cannot run inside a Docker container. This
# script instead copies the Tutor-rendered configuration into your checkout of
# the app, after which you build the app from Xcode on a Mac.
#
# Usage: ./setup.sh /path/to/openedx-app-ios
set -euo pipefail

CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/config"

if [ "$#" -ne 1 ]; then
    echo "Usage: $(basename "$0") /path/to/openedx-app-ios" >&2
    exit 1
fi

APP_DIR="$1"

if [ ! -d "$APP_DIR" ]; then
    echo "Error: '$APP_DIR' is not a directory." >&2
    echo "Clone the app first: git clone {{ IOS_APP_REPOSITORY }}" >&2
    exit 1
fi

if [ ! -e "$APP_DIR/config_script/process_config.py" ]; then
    echo "Error: '$APP_DIR' does not look like an openedx-app-ios checkout" >&2
    echo "(config_script/process_config.py is missing)." >&2
    exit 1
fi

# The app resolves `config_directory` relative to the repository root, so the
# rendered environment configuration is copied to a dedicated directory there
# instead of overwriting the upstream `default_config`.
echo "Installing Tutor configuration into $APP_DIR ..."
rm -rf "$APP_DIR/tutor_config"
mkdir -p "$APP_DIR/tutor_config"
cp -R "$CONFIG_DIR/prod" "$APP_DIR/tutor_config/prod"
cp "$CONFIG_DIR/config_settings.yaml" "$APP_DIR/config_settings.yaml"

# Apply app identity (bundle ID, name, version, colours) via the app's own
# white-labelling script, which rewrites the Xcode project in place.
cp "$CONFIG_DIR/whitelabel.yaml" "$APP_DIR/whitelabel.yaml"
if command -v python3 >/dev/null 2>&1; then
    echo "Applying app identity with the app's whitelabel script ..."
    if ! (cd "$APP_DIR" && python3 config_script/whitelabel.py --config-file whitelabel.yaml); then
        echo
        echo "Warning: whitelabel.py failed. The app configuration is installed and" >&2
        echo "usable, but the bundle ID, app name and colours were not applied." >&2
        echo "It needs PyYAML, Pillow and coloredlogs; install them with:" >&2
        echo "  pip install pyyaml pillow coloredlogs" >&2
        echo "Then re-run: cd $APP_DIR && python3 config_script/whitelabel.py --config-file whitelabel.yaml" >&2
    fi
else
    echo "Warning: python3 not found, skipping the whitelabel step." >&2
fi

echo
echo "Done. The app is now configured for {{ LMS_HOST }}."
echo
echo "Next steps, on a macOS machine with Xcode installed:"
echo
echo "  cd $APP_DIR"
echo "  pod install"
echo "  open OpenEdX.xcworkspace"
echo
echo "Then select the 'OpenEdXProd' scheme and press Run."
