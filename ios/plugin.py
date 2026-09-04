from __future__ import annotations

import os
import re
import shutil
import subprocess
import typing as t
from glob import glob

import click
import importlib_resources
from tutor import config as tutor_config
from tutor import fmt
from tutor import hooks as tutor_hooks
from tutor.__about__ import __version_suffix__
from tutor.types import Config, get_typed

from .__about__ import __version__

# Handle version suffix in main mode, just like tutor core
if __version_suffix__:
    __version__ += "-" + __version_suffix__


config: t.Dict[str, t.Dict[str, t.Any]] = {
    "defaults": {
        "VERSION": __version__,
        "APP_REPOSITORY": "https://github.com/openedx/openedx-app-ios.git",
        "APP_VERSION": '{% if OPENEDX_COMMON_VERSION == "master" %}main{% else %}{{ OPENEDX_COMMON_VERSION }}{% endif %}',  # noqa: E501
        # config.yaml: top-level app settings
        "ENVIRONMENT_DISPLAY_NAME": "tutor",
        "ORGANIZATION_CODE": "",
        "FEEDBACK_EMAIL_ADDRESS": "{{ CONTACT_EMAIL }}",
        "OAUTH_CLIENT_ID": "ios",
        "TOKEN_TYPE": "JWT",
        "FAQ_URL": "",
        "URI_SCHEME": "",
        "APP_STORE_ID": "",
        # Single sign-on
        "SSO_URL": '{{ "https" if ENABLE_HTTPS else "http" }}://{{ LMS_HOST }}',
        "SSO_FINISHED_URL": '{{ "https" if ENABLE_HTTPS else "http" }}://{{ LMS_HOST }}',  # noqa: E501
        "SSO_BUTTON_TITLE": {"en": "Sign in with SSO"},
        # Agreement URLs (leave empty to hide the corresponding setting)
        "PRIVACY_POLICY_URL": "",
        "COOKIE_POLICY_URL": "",
        "DATA_SELL_CONSENT_URL": "",
        "TOS_URL": "",
        "EULA_URL": "",
        "SUPPORTED_LANGUAGES": [],
        # Feature flags
        "WHATS_NEW_ENABLED": False,
        "PRE_LOGIN_EXPERIENCE_ENABLED": True,
        "APP_LEVEL_DATES_ENABLED": False,
        # UI components
        "COURSE_DROPDOWN_NAVIGATION_ENABLED": False,
        "COURSE_UNIT_PROGRESS_ENABLED": False,
        "LOGIN_REGISTRATION_ENABLED": True,
        "SAML_SSO_LOGIN_ENABLED": False,
        "SAML_SSO_DEFAULT_LOGIN_BUTTON": False,
        # Theme
        "ROUNDED_CORNERS_STYLE": True,
        "BUTTON_CORNERS_RADIUS": 8,
        # Experimental features
        "APP_LEVEL_DOWNLOADS_ENABLED": False,
        # Dashboard
        "DASHBOARD_TYPE": "primary",
        # Discovery
        "DISCOVERY_TYPE": "native",
        "DISCOVERY_WEBVIEW_BASE_URL": "",
        "DISCOVERY_WEBVIEW_COURSE_DETAIL_TEMPLATE": "",
        "DISCOVERY_WEBVIEW_PROGRAM_DETAIL_TEMPLATE": "",
        # Program
        "PROGRAM_TYPE": "native",
        "PROGRAM_WEBVIEW_BASE_URL": "",
        "PROGRAM_WEBVIEW_COURSE_DETAIL_TEMPLATE": "",
        "PROGRAM_WEBVIEW_PROGRAM_DETAIL_TEMPLATE": "",
        # Firebase
        "FIREBASE_ENABLED": False,
        "FIREBASE_ANALYTICS_SOURCE": "",
        "FIREBASE_CLOUD_MESSAGING_ENABLED": False,
        "FIREBASE_API_KEY": "",
        "FIREBASE_CLIENT_ID": "",
        "FIREBASE_GOOGLE_APP_ID": "",
        "FIREBASE_GCM_SENDER_ID": "",
        "FIREBASE_PROJECT_ID": "",
        "FIREBASE_REVERSED_CLIENT_ID": "",
        # Segment.io
        "SEGMENT_IO_ENABLED": False,
        "SEGMENT_IO_WRITE_KEY": "",
        # Braze
        "BRAZE_ENABLED": False,
        "BRAZE_PUSH_NOTIFICATIONS_ENABLED": False,
        # Branch
        "BRANCH_ENABLED": False,
        "BRANCH_KEY": "",
        "BRANCH_URI_SCHEME": "",
        "BRANCH_DEEPLINK_PREFIX": "",
        # Social: Google
        "GOOGLE_ENABLED": False,
        "GOOGLE_CLIENT_ID": "",
        "GOOGLE_PLUS_KEY": "",
        # Social: Microsoft
        "MICROSOFT_ENABLED": False,
        "MICROSOFT_CLIENT_ID": "",
        # Social: Facebook
        "FACEBOOK_ENABLED": False,
        "FACEBOOK_APP_ID": "",
        "FACEBOOK_CLIENT_TOKEN": "",
        # Social: Apple
        "APPLE_SIGNIN_ENABLED": False,
        # whitelabel.yaml: app identity, applied by config_script/whitelabel.py
        "BUNDLE_ID": "org.openedx.app",
        "APP_NAME": "{{ PLATFORM_NAME }}",
        "MARKETING_VERSION": "1.0.0",
        "BUILD_NUMBER": "1",
        # Apple Developer team ID, required to archive and upload a build
        "DEV_TEAM": "",
        # Sub-projects that also need the development team applied. These are the
        # modules of the Open edX iOS app; override if your fork adds or removes any.
        "EXTRA_TARGETS": [
            "AppDates",
            "Authorization",
            "Core",
            "Course",
            "Dashboard",
            "Discovery",
            "Discussion",
            "Downloads",
            "Profile",
            "Theme",
            "WhatsNew",
        ],
        # Brand colours, as hex strings. Set both light and dark, or leave a
        # value empty to keep the app's own default for that appearance.
        "COLORS": {},
        # Images and app icon, as filenames inside IOS_IMAGES_IMPORT_DIR
        "IMAGES_IMPORT_DIR": "",
        "APP_ICON": "",
        "IMAGES": {},
        # Custom font, as paths on the build machine
        "FONT_FILE": "",
        "FONT_NAMES": {},
    },
    "unique": {
        "OAUTH2_SECRET": "{{ 24|random_string }}",
    },
}


########################################
# INITIALIZATION TASKS
########################################

with open(
    os.path.join(
        str(importlib_resources.files("ios") / "templates"),
        "ios",
        "tasks",
        "lms",
        "init",
    ),
    encoding="utf8",
) as fi:
    tutor_hooks.Filters.CLI_DO_INIT_TASKS.add_item(("lms", fi.read()))


########################################
# TEMPLATE RENDERING
########################################

# Add the "templates" folder as a template root
tutor_hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    str(importlib_resources.files("ios") / "templates")
)
# Render the "build" folder
tutor_hooks.Filters.ENV_TEMPLATE_TARGETS.add_items(
    [
        ("ios/build", "plugins"),
    ],
)

########################################
# PATCH LOADING
########################################

for path in glob(str(importlib_resources.files("ios") / "patches" / "*")):
    with open(path, encoding="utf-8") as patch_file:
        tutor_hooks.Filters.ENV_PATCHES.add_item(
            (os.path.basename(path), patch_file.read())
        )


########################################
# CONFIGURATION
########################################

tutor_hooks.Filters.CONFIG_DEFAULTS.add_items(
    [(f"IOS_{key}", value) for key, value in config.get("defaults", {}).items()]
)
tutor_hooks.Filters.CONFIG_UNIQUE.add_items(
    [(f"IOS_{key}", value) for key, value in config.get("unique", {}).items()]
)
tutor_hooks.Filters.CONFIG_OVERRIDES.add_items(
    list(config.get("overrides", {}).items())
)


########################################
# CONFIGURATION VALIDATION
########################################

# Values the Open edX iOS app only accepts from a fixed set. A wrong value here
# does not fail the build: the app falls back to a default or silently ignores
# the setting, so the mistake only surfaces as odd behaviour at runtime.
CHOICES: dict[str, tuple[str, ...]] = {
    "IOS_TOKEN_TYPE": ("JWT", "BEARER"),
    "IOS_DISCOVERY_TYPE": ("native", "webview", "none"),
    "IOS_PROGRAM_TYPE": ("native", "webview", "none"),
    "IOS_DASHBOARD_TYPE": ("primary", "gallery"),
    "IOS_FIREBASE_ANALYTICS_SOURCE": ("", "segment", "firebase", "none"),
}

# Settings that must be a URL when set, so a missing scheme is caught early.
# Config.swift discards a value that URL(string:) cannot parse.
URL_SETTINGS = (
    "IOS_SSO_URL",
    "IOS_SSO_FINISHED_URL",
    "IOS_FAQ_URL",
    "IOS_PRIVACY_POLICY_URL",
    "IOS_COOKIE_POLICY_URL",
    "IOS_DATA_SELL_CONSENT_URL",
    "IOS_TOS_URL",
    "IOS_EULA_URL",
    "IOS_DISCOVERY_WEBVIEW_BASE_URL",
    "IOS_PROGRAM_WEBVIEW_BASE_URL",
)

# A bundle identifier is a reverse-DNS string; Xcode rejects anything else.
BUNDLE_ID_RE = re.compile(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")


@tutor_hooks.Actions.CONFIG_LOADED.add()
def _validate_ios_config(config: Config) -> None:
    """
    Warn about IOS_* values that would produce a broken or misconfigured app.

    These are warnings rather than errors: a value may be intentionally unusual,
    and refusing to render the environment would be worse than flagging it.
    """
    errors: list[str] = []

    for setting, allowed in CHOICES.items():
        value = config.get(setting)
        if isinstance(value, str) and value not in allowed:
            options = ", ".join(repr(choice) for choice in allowed)
            errors.append(f"{setting}: {value!r} is not one of {options}")

    for setting in URL_SETTINGS:
        value = config.get(setting)
        if isinstance(value, str) and value and not re.match(r"^https?://", value):
            errors.append(
                f"{setting}: {value!r} is not an http(s) URL, so the app will ignore it"
            )

    bundle_id = config.get("IOS_BUNDLE_ID")
    if isinstance(bundle_id, str) and not BUNDLE_ID_RE.match(bundle_id):
        errors.append(
            f"IOS_BUNDLE_ID: {bundle_id!r} is not a valid reverse-DNS "
            "identifier, such as 'org.example.mobile'"
        )

    for setting in ("IOS_MARKETING_VERSION", "IOS_BUILD_NUMBER"):
        value = config.get(setting)
        # Xcode requires these to be dot-separated numbers. YAML would parse an
        # unquoted 1.0 as a float, which also breaks the project file.
        if value is not None and not re.match(r"^[0-9]+(\.[0-9]+)*$", str(value)):
            errors.append(f"{setting}: {value!r} must be a dot-separated number")

    # The app reads the discovery/program webview URLs only in webview mode, but
    # an empty base URL there yields a blank screen rather than an error.
    for prefix in ("DISCOVERY", "PROGRAM"):
        if config.get(f"IOS_{prefix}_TYPE") == "webview" and not config.get(
            f"IOS_{prefix}_WEBVIEW_BASE_URL"
        ):
            errors.append(
                f"IOS_{prefix}_TYPE is 'webview' but "
                f"IOS_{prefix}_WEBVIEW_BASE_URL is empty"
            )

    if errors:
        message = "\n".join(f"  - {error}" for error in errors)
        fmt.echo_alert(f"tutor-ios configuration issues:\n{message}")


########################################
# CUSTOM CLI COMMANDS
########################################


def _build_dir(context: t.Any) -> str:
    """
    Return the path to the rendered "ios/build" directory in the Tutor environment.
    """
    return os.path.join(context.root, "env", "plugins", "ios", "build")


@click.group(name="ios", help="Configure and build the Open edX iOS application")
def ios_command() -> None:
    pass


@ios_command.command(name="printconfigdir")
@click.pass_obj
def print_config_dir(context: t.Any) -> None:
    """
    Print the path to the generated iOS app configuration.
    """
    click.echo(os.path.join(_build_dir(context), "config"))


@ios_command.command(name="setup")
@click.argument(
    "app_directory",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
@click.pass_obj
def setup(context: t.Any, app_directory: str) -> None:
    """
    Install the generated configuration in a local openedx-app-ios checkout.

    APP_DIRECTORY is the path to your clone of the Open edX iOS app repository.
    """
    script = os.path.join(_build_dir(context), "setup.sh")
    if not os.path.exists(script):
        raise click.ClickException(
            f"{script} does not exist. Run 'tutor config save' first."
        )
    subprocess.run(["bash", script, app_directory], check=True)


@ios_command.command(name="clone")
@click.argument(
    "app_directory",
    type=click.Path(file_okay=False, resolve_path=True),
    default="openedx-app-ios",
)
@click.pass_obj
def clone(context: t.Any, app_directory: str) -> None:
    """
    Clone the Open edX iOS app repository and configure it for this platform.

    APP_DIRECTORY defaults to "openedx-app-ios" in the current directory.
    """
    if not shutil.which("git"):
        raise click.ClickException("git is required but was not found in $PATH.")

    user_config = tutor_config.load(context.root)
    repository = get_typed(user_config, "IOS_APP_REPOSITORY", str)
    version = get_typed(user_config, "IOS_APP_VERSION", str)

    if os.path.exists(app_directory):
        raise click.ClickException(
            f"{app_directory} already exists. Delete it, or run "
            f"'tutor ios setup {app_directory}' to configure it in place."
        )

    click.echo(f"Cloning {repository} (branch {version}) into {app_directory} ...")
    subprocess.run(
        [
            "git",
            "clone",
            "--branch",
            version,
            "--depth",
            "1",
            repository,
            app_directory,
        ],
        check=True,
    )
    subprocess.run(
        ["bash", os.path.join(_build_dir(context), "setup.sh"), app_directory],
        check=True,
    )


tutor_hooks.Filters.CLI_COMMANDS.add_item(ios_command)
