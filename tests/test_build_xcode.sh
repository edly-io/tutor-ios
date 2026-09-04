#!/usr/bin/env bash
#
# Preflight and optional compile of the Open edX iOS app.
#
# Building an iOS app requires macOS with a full Xcode installation. This script
# reports exactly what is missing, and compiles the app for the simulator if
# everything is present.
#
# Usage: ./tests/test_build_xcode.sh /path/to/openedx-app-ios [--build]
set -uo pipefail

APP_DIR="${1:-}"
DO_BUILD="${2:-}"

ok()   { printf '  \033[1;32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[1;31m✗\033[0m %s\n' "$1"; }
info() { printf '  \033[1;33m•\033[0m %s\n' "$1"; }
log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$1"; }

MISSING=0

log "Checking build prerequisites"

if [ "$(uname -s)" = "Darwin" ]; then
    ok "macOS $(sw_vers -productVersion)"
else
    bad "not macOS — iOS apps cannot be built on $(uname -s), and not in Docker"
    exit 1
fi

DEVELOPER_DIR="$(xcode-select -p 2>/dev/null || true)"
if [ -z "$DEVELOPER_DIR" ]; then
    bad "no developer directory selected"
    MISSING=1
elif [ "${DEVELOPER_DIR%%/CommandLineTools}" != "$DEVELOPER_DIR" ]; then
    bad "only Command Line Tools are installed, at $DEVELOPER_DIR"
    info "Xcode itself is required. Install it from the App Store, then run:"
    info "  sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer"
    MISSING=1
elif xcodebuild -version >/dev/null 2>&1; then
    ok "$(xcodebuild -version | head -1) at $DEVELOPER_DIR"
else
    bad "xcodebuild is not usable at $DEVELOPER_DIR"
    MISSING=1
fi

if command -v pod >/dev/null 2>&1; then
    ok "CocoaPods $(pod --version)"
else
    bad "CocoaPods is not installed"
    info "Install it with: brew install cocoapods"
    MISSING=1
fi

if [ -z "$APP_DIR" ]; then
    bad "no app directory given"
    info "Usage: $(basename "$0") /path/to/openedx-app-ios [--build]"
    MISSING=1
elif [ ! -e "$APP_DIR/OpenEdX.xcworkspace" ]; then
    bad "$APP_DIR is not an openedx-app-ios checkout"
    info "Create one with: tutor ios clone $APP_DIR"
    MISSING=1
else
    ok "app checkout at $APP_DIR"
    if [ -f "$APP_DIR/tutor_config/prod/config.yaml" ]; then
        ok "Tutor configuration is installed"
        HOST="$(grep '^API_HOST_URL:' "$APP_DIR/tutor_config/prod/config.yaml" | cut -d'"' -f2)"
        info "the app will point at $HOST"
        case "$HOST" in
            http://*)
                info "note: iOS App Transport Security blocks plaintext HTTP by default,"
                info "so an http:// host may fail to connect from a simulator or device."
                ;;
        esac
    else
        bad "Tutor configuration is not installed in this checkout"
        info "Install it with: tutor ios setup $APP_DIR"
        MISSING=1
    fi
fi

if [ "$MISSING" -ne 0 ]; then
    log "Prerequisites are missing — cannot build"
    echo
    echo "The configuration this plugin generates can still be verified without"
    echo "Xcode, by running: ./tests/test_build_config.sh"
    echo
    exit 1
fi

log "All prerequisites satisfied"

if [ "$DO_BUILD" != "--build" ]; then
    cat <<EOF

Re-run with --build to compile the app for the simulator, or build manually:

    cd $APP_DIR
    pod install
    open OpenEdX.xcworkspace

EOF
    exit 0
fi

log "Installing pods (this takes several minutes)"
(cd "$APP_DIR" && pod install) || { bad "pod install failed"; exit 1; }

log "Building the OpenEdXProd scheme for the simulator"
# A simulator build needs no code-signing identity, so this works without an
# Apple Developer account.
(
    cd "$APP_DIR"
    xcodebuild \
        -workspace OpenEdX.xcworkspace \
        -scheme OpenEdXProd \
        -configuration DebugProd \
        -destination 'generic/platform=iOS Simulator' \
        -skipPackagePluginValidation \
        -skipMacroValidation \
        CODE_SIGNING_ALLOWED=NO \
        build
) || { bad "xcodebuild failed"; exit 1; }

log "PASS — the app compiled with your Tutor configuration"
