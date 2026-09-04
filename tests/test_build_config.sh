#!/usr/bin/env bash
#
# End-to-end check of the configuration this plugin generates.
#
# This clones the Open edX iOS app and runs the app's OWN build script
# (config_script/process_config.py) against the Tutor-generated configuration,
# exactly as the Xcode build phase does. It then verifies the resulting
# config.plist contains what Config.swift needs.
#
# This requires neither Xcode nor macOS: it validates the entire surface this
# plugin is responsible for. Compiling the app itself needs Xcode; see
# ./test_build_xcode.sh for a preflight check of that.
#
# Usage: ./tests/test_build_config.sh [work_directory]
set -euo pipefail

WORK_DIR="${1:-$(mktemp -d -t tutor-ios-build)}"
APP_DIR="$WORK_DIR/openedx-app-ios"
FAKE_BUILD="$WORK_DIR/build"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$1"; }
fail() { printf '\033[1;31mFAIL: %s\033[0m\n' "$1" >&2; exit 1; }

command -v git >/dev/null || fail "git is required"
command -v tutor >/dev/null || fail "tutor is required (is your virtualenv active?)"

log "Rendering the Tutor environment"
tutor config save >/dev/null
CONFIG_DIR="$(tutor ios printconfigdir)"
[ -d "$CONFIG_DIR" ] || fail "$CONFIG_DIR was not generated"
echo "Configuration generated at $CONFIG_DIR"

if [ ! -d "$APP_DIR" ]; then
    log "Cloning the Open edX iOS app (shallow)"
    REPO="$(tutor config printvalue IOS_APP_REPOSITORY)"
    VERSION="$(tutor config printvalue IOS_APP_VERSION)"
    git clone --quiet --depth 1 --branch "$VERSION" "$REPO" "$APP_DIR"
fi

log "Installing the generated configuration into the checkout"
tutor ios setup "$APP_DIR" >/dev/null
[ -f "$APP_DIR/config_settings.yaml" ] || fail "config_settings.yaml was not installed"
[ -f "$APP_DIR/tutor_config/prod/config.yaml" ] || fail "config.yaml was not installed"

# The app must be left untouched apart from the files we own, so that a user's
# checkout stays clean and upgradable.
log "Checking the app checkout is otherwise unmodified"
UNEXPECTED="$(cd "$APP_DIR" && git status --porcelain | grep -v 'config_settings.yaml' | grep -v 'tutor_config' || true)"
if [ -n "$UNEXPECTED" ]; then
    fail "the plugin modified files it does not own:"$'\n'"$UNEXPECTED"
fi
echo "Only config_settings.yaml and tutor_config/ were touched."

# Run the app's own config script the way the Xcode build phase does, for every
# scheme, so a broken config_mapping is caught.
for CONFIGURATION in ReleaseProd DebugProd ReleaseStage DebugStage ReleaseDev DebugDev; do
    log "Running the app's process_config.py for $CONFIGURATION"
    rm -rf "$FAKE_BUILD"
    mkdir -p "$FAKE_BUILD/OpenEdX.app"
    cat > "$FAKE_BUILD/OpenEdX.app/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict/></plist>
PLIST

    (
        cd "$APP_DIR"
        BUILT_PRODUCTS_DIR="$FAKE_BUILD" \
        WRAPPER_NAME="OpenEdX.app" \
        INFOPLIST_PATH="OpenEdX.app/Info.plist" \
        PRODUCT_NAME="OpenEdX" \
        PRODUCT_BUNDLE_IDENTIFIER="org.openedx.app" \
        python3 config_script/process_config.py "$CONFIGURATION" \
            '{"prod":["ReleaseProd","DebugProd"],"stage":["ReleaseStage","DebugStage"],"dev":["ReleaseDev","DebugDev"]}'
    ) || fail "process_config.py failed for $CONFIGURATION"

    python3 - "$FAKE_BUILD/OpenEdX.app/config.plist" <<'PY'
import plistlib, sys
plist = plistlib.load(open(sys.argv[1], "rb"))
# Config.swift calls fatalError() when any of these is missing or empty.
required = ["API_HOST_URL", "SSO_URL", "SSO_FINISHED_URL", "OAUTH_CLIENT_ID"]
missing = [k for k in required if not plist.get(k)]
if missing:
    sys.exit(f"FAIL: config.plist is missing required keys: {missing}")
for key, kind in [("AGREEMENT_URLS", dict), ("UI_COMPONENTS", dict), ("FIREBASE", dict)]:
    if not isinstance(plist.get(key), kind):
        sys.exit(f"FAIL: {key} is {type(plist.get(key)).__name__}, expected {kind.__name__}")
print(f"  config.plist OK: {len(plist)} keys, API_HOST_URL={plist['API_HOST_URL']}")
PY
done

log "PASS"
cat <<EOF

The configuration this plugin generates is consumed correctly by the app's own
build script for all six build configurations.

Checkout: $APP_DIR

To compile the app, on a Mac with Xcode:

    cd $APP_DIR
    pod install
    open OpenEdX.xcworkspace

EOF
