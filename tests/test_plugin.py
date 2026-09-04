"""
Tests for the tutor-ios plugin.

These tests render the plugin's templates with a temporary Tutor root and then
assert that the result is what the Open edX iOS app actually expects. The
authoritative schema lives in the app's own source:

- ``config_script/process_config.py`` merges the YAML files listed in
  ``file_mappings.yaml`` into a ``config.plist``;
- ``Core/Core/Configuration/Config/*.swift`` reads that plist, and calls
  ``fatalError()`` when some keys are missing.
"""

from __future__ import annotations

import tempfile
import typing as t
import unittest

import yaml
from tutor import config as tutor_config
from tutor import env, hooks, plugins
from tutor.types import Config

from ios import plugin

# Keys whose absence makes Config.swift call fatalError(), crashing the app on
# launch. See Core/Core/Configuration/Config/Config.swift.
REQUIRED_KEYS = ["API_HOST_URL", "SSO_URL", "SSO_FINISHED_URL", "OAUTH_CLIENT_ID"]

# Top-level groups read by the app, mapped to the type the Swift side expects.
# A group parsed as the wrong type is silently ignored by the app, so this guards
# against subtle YAML indentation regressions.
EXPECTED_TYPES: dict[str, type] = {
    "API_HOST_URL": str,
    "OAUTH_CLIENT_ID": str,
    "TOKEN_TYPE": str,
    "PLATFORM_NAME": str,
    "WHATS_NEW_ENABLED": bool,
    "PRE_LOGIN_EXPERIENCE_ENABLED": bool,
    "APP_LEVEL_DATES_ENABLED": bool,
    "SSO_BUTTON_TITLE": dict,
    "AGREEMENT_URLS": dict,
    "UI_COMPONENTS": dict,
    "THEME": dict,
    "EXPERIMENTAL_FEATURES": dict,
    "DASHBOARD": dict,
    "DISCOVERY": dict,
    "PROGRAM": dict,
    "FIREBASE": dict,
    "SEGMENT_IO": dict,
    "BRAZE": dict,
    "BRANCH": dict,
    "GOOGLE": dict,
    "MICROSOFT": dict,
    "FACEBOOK": dict,
    "APPLE_SIGNIN": dict,
}


class PluginTestCase(unittest.TestCase):
    """
    Base test case that loads the ios plugin against a temporary Tutor root.
    """

    def setUp(self) -> None:
        super().setUp()
        hooks.Actions.CORE_READY.do()
        plugins.load_all(["ios"])
        self._root_context = tempfile.TemporaryDirectory(prefix="tutor-ios-test-")
        self.root = self._root_context.name
        self.addCleanup(self._root_context.cleanup)

    def get_config(self, **overrides: t.Any) -> Config:
        config = tutor_config.load_full(self.root)
        config.update(overrides)
        return config

    def render(self, config: Config, path: str) -> str:
        # render_file returns bytes for binary templates; ours are all text.
        rendered = env.render_file(config, *path.split("/"))
        if isinstance(rendered, bytes):
            return rendered.decode("utf-8")
        return rendered

    def render_app_config(self, **overrides: t.Any) -> t.Any:
        """
        Render config.yaml and parse it the way process_config.py does.
        """
        config = self.get_config(**overrides)
        rendered = self.render(config, "ios/build/config/prod/config.yaml")
        return yaml.safe_load(rendered)


class ConfigDefaultsTests(PluginTestCase):
    def test_settings_are_namespaced(self) -> None:
        """
        Every setting the plugin adds must be prefixed, to avoid colliding with
        Tutor core or other plugins.
        """
        defaults = dict(hooks.Filters.CONFIG_DEFAULTS.iterate())
        ios_keys = [k for k in defaults if "IOS" in k]
        self.assertTrue(ios_keys, "plugin registered no settings")
        for key in ios_keys:
            self.assertTrue(key.startswith("IOS_"), f"{key} is not namespaced")

    def test_oauth_secret_is_unique(self) -> None:
        unique = dict(hooks.Filters.CONFIG_UNIQUE.iterate())
        self.assertIn("IOS_OAUTH2_SECRET", unique)

    def test_oauth_secret_is_generated(self) -> None:
        config = self.get_config()
        secret = config["IOS_OAUTH2_SECRET"]
        self.assertIsInstance(secret, str)
        self.assertEqual(24, len(t.cast(str, secret)))


class AppConfigTests(PluginTestCase):
    """
    Tests for the rendered config.yaml, which becomes the app's config.plist.
    """

    def test_renders_valid_yaml(self) -> None:
        self.assertIsInstance(self.render_app_config(), dict)

    def test_required_keys_are_populated(self) -> None:
        """
        Config.swift calls fatalError() when these are missing or empty, which
        crashes the app at launch.
        """
        parsed = self.render_app_config()
        for key in REQUIRED_KEYS:
            self.assertIn(key, parsed)
            self.assertTrue(parsed[key], f"{key} must not be empty")

    def test_key_types_match_the_app(self) -> None:
        parsed = self.render_app_config()
        for key, expected in EXPECTED_TYPES.items():
            self.assertIn(key, parsed)
            self.assertIsInstance(
                parsed[key], expected, f"{key} has the wrong YAML type"
            )

    def test_api_host_follows_lms_host(self) -> None:
        parsed = self.render_app_config(LMS_HOST="courses.example.com")
        self.assertEqual("http://courses.example.com", parsed["API_HOST_URL"])

    def test_api_host_uses_https_when_enabled(self) -> None:
        parsed = self.render_app_config(LMS_HOST="courses.example.com")
        self.assertTrue(parsed["API_HOST_URL"].startswith("http://"))
        parsed = self.render_app_config(
            LMS_HOST="courses.example.com", ENABLE_HTTPS=True
        )
        self.assertEqual("https://courses.example.com", parsed["API_HOST_URL"])

    def test_nested_groups_are_nested(self) -> None:
        """
        The app reads these as nested dictionaries; flattening them would break
        it silently.
        """
        parsed = self.render_app_config()
        self.assertIn("ENABLED", parsed["EXPERIMENTAL_FEATURES"]["APP_LEVEL_DOWNLOADS"])
        self.assertIn("BASE_URL", parsed["DISCOVERY"]["WEBVIEW"])
        self.assertIn("SUPPORTED_LANGUAGES", parsed["AGREEMENT_URLS"])

    def test_booleans_render_as_yaml_booleans(self) -> None:
        """
        Python's True/False must survive as YAML booleans, not strings.
        """
        parsed = self.render_app_config(IOS_FIREBASE_ENABLED=True)
        self.assertIs(True, parsed["FIREBASE"]["ENABLED"])
        parsed = self.render_app_config(IOS_FIREBASE_ENABLED=False)
        self.assertIs(False, parsed["FIREBASE"]["ENABLED"])

    def test_settings_reach_the_app_config(self) -> None:
        parsed = self.render_app_config(
            IOS_OAUTH_CLIENT_ID="my-client",
            IOS_TOKEN_TYPE="BEARER",
            IOS_FAQ_URL="https://example.com/faq",
            IOS_BUTTON_CORNERS_RADIUS=12,
        )
        self.assertEqual("my-client", parsed["OAUTH_CLIENT_ID"])
        self.assertEqual("BEARER", parsed["TOKEN_TYPE"])
        self.assertEqual("https://example.com/faq", parsed["FAQ_URL"])
        self.assertEqual(12, parsed["THEME"]["BUTTON_CORNERS_RADIUS"])

    def test_supported_languages_renders_as_list(self) -> None:
        parsed = self.render_app_config(IOS_SUPPORTED_LANGUAGES=["en", "ar"])
        self.assertEqual(["en", "ar"], parsed["AGREEMENT_URLS"]["SUPPORTED_LANGUAGES"])

    def test_sso_button_title_renders_as_mapping(self) -> None:
        parsed = self.render_app_config(
            IOS_SSO_BUTTON_TITLE={"en": "Sign in", "ar": "تسجيل الدخول"}
        )
        self.assertEqual(
            {"en": "Sign in", "ar": "تسجيل الدخول"}, parsed["SSO_BUTTON_TITLE"]
        )

    def test_patch_can_add_keys(self) -> None:
        hooks.Filters.ENV_PATCHES.add_item(("ios-config-yaml", "MY_CUSTOM_KEY: hello"))
        parsed = self.render_app_config()
        self.assertEqual("hello", parsed["MY_CUSTOM_KEY"])

    def test_patch_can_override_keys(self) -> None:
        """
        PyYAML keeps the last value for a duplicated key, which is the documented
        way to override a whole group.
        """
        hooks.Filters.ENV_PATCHES.add_item(
            ("ios-config-yaml", 'API_HOST_URL: "https://override.example.com"')
        )
        parsed = self.render_app_config()
        self.assertEqual("https://override.example.com", parsed["API_HOST_URL"])


class WhitelabelTests(PluginTestCase):
    """
    Tests for whitelabel.yaml, consumed by the app's config_script/whitelabel.py.
    """

    def render_whitelabel(self, **overrides: t.Any) -> t.Any:
        config = self.get_config(**overrides)
        return yaml.safe_load(self.render(config, "ios/build/config/whitelabel.yaml"))

    def test_renders_valid_yaml(self) -> None:
        self.assertIsInstance(self.render_whitelabel(), dict)

    def test_app_name_defaults_to_platform_name(self) -> None:
        """
        IOS_APP_NAME defaults to the '{{ PLATFORM_NAME }}' template, so the app
        follows the platform name unless it is set explicitly.

        Note that the default is resolved by tutor when the configuration is
        loaded, so this asserts on the loaded value rather than overriding
        PLATFORM_NAME here: an override applied after load_full() would not
        re-render the template, which is an artefact of the test setup and not
        how `tutor config save` behaves.
        """
        config = self.get_config()
        self.assertEqual(config["PLATFORM_NAME"], config["IOS_APP_NAME"])

    def test_app_name_is_overridable(self) -> None:
        parsed = self.render_whitelabel(IOS_APP_NAME="Example Learn")
        configurations = parsed["project_config"]["configurations"]
        self.assertEqual("Example Learn", configurations["ReleaseProd"]["product_name"])

    def test_every_build_configuration_is_covered(self) -> None:
        """
        Whichever scheme is selected in Xcode must get the same identity.
        """
        parsed = self.render_whitelabel(IOS_BUNDLE_ID="org.example.mobile")
        configurations = parsed["project_config"]["configurations"]
        self.assertEqual(
            {
                "DebugDev",
                "ReleaseDev",
                "DebugStage",
                "ReleaseStage",
                "DebugProd",
                "ReleaseProd",
            },
            set(configurations),
        )
        for name, values in configurations.items():
            self.assertEqual("org.example.mobile", values["app_bundle_id"], name)

    def test_versions_render_as_strings(self) -> None:
        """
        A YAML float (1.0) would corrupt the Xcode project file.
        """
        parsed = self.render_whitelabel(
            IOS_MARKETING_VERSION="2.5.1", IOS_BUILD_NUMBER="42"
        )
        project = parsed["project_config"]
        self.assertIsInstance(project["marketing_version"], str)
        self.assertIsInstance(project["current_project_version"], str)
        self.assertEqual("2.5.1", project["marketing_version"])

    def test_dev_team_is_omitted_when_unset(self) -> None:
        """
        whitelabel.py logs an error for an empty dev_team, so omit the key.
        """
        parsed = self.render_whitelabel(IOS_DEV_TEAM="")
        self.assertNotIn("dev_team", parsed["project_config"])
        self.assertNotIn("project_extra_targets", parsed["project_config"])

    def test_dev_team_brings_extra_targets(self) -> None:
        """
        Setting dev_team without project_extra_targets makes whitelabel.py error.
        """
        parsed = self.render_whitelabel(IOS_DEV_TEAM="ABCDE12345")
        project = parsed["project_config"]
        self.assertEqual("ABCDE12345", project["dev_team"])
        self.assertIn("Core", project["project_extra_targets"])

    def test_colors_accept_a_plain_hex_string(self) -> None:
        parsed = self.render_whitelabel(IOS_COLORS={"Primary": "#0A3055"})
        colors = parsed["assets"]["Theme"]["colors"]
        self.assertEqual({"light": "#0A3055", "dark": "#0A3055"}, colors["Primary"])

    def test_colors_accept_light_and_dark(self) -> None:
        parsed = self.render_whitelabel(
            IOS_COLORS={"Accent": {"light": "#FF0000", "dark": "#880000"}}
        )
        colors = parsed["assets"]["Theme"]["colors"]
        self.assertEqual({"light": "#FF0000", "dark": "#880000"}, colors["Accent"])

    def test_assets_omitted_when_no_branding_is_set(self) -> None:
        parsed = self.render_whitelabel()
        self.assertNotIn("assets", parsed)
        self.assertNotIn("font", parsed)

    def test_app_icon_and_images(self) -> None:
        parsed = self.render_whitelabel(
            IOS_IMAGES_IMPORT_DIR="/brand",
            IOS_APP_ICON="icon.png",
            IOS_IMAGES={"appLogo": "logo.svg"},
        )
        theme = parsed["assets"]["Theme"]
        self.assertEqual("/brand", parsed["images_import_dir"])
        self.assertEqual("icon.png", theme["icon"]["AppIcon"]["image_name"])
        self.assertEqual("logo.svg", theme["images"]["appLogo"]["image_name"])

    def test_patch_can_extend_whitelabel(self) -> None:
        hooks.Filters.ENV_PATCHES.add_item(
            ("ios-whitelabel-yaml", "files:\n  extra:\n    import_file_path: /x")
        )
        parsed = self.render_whitelabel()
        self.assertIn("extra", parsed["files"])


class ValidationTests(PluginTestCase):
    """
    Tests for the CONFIG_LOADED validation warnings.
    """

    def collect_warnings(self, **overrides: t.Any) -> str:
        from unittest import mock

        config = self.get_config(**overrides)
        with mock.patch("ios.plugin.fmt.echo_alert") as echo_alert:
            plugin._validate_ios_config(config)
        if not echo_alert.call_args:
            return ""
        return str(echo_alert.call_args[0][0])

    def test_valid_defaults_produce_no_warnings(self) -> None:
        self.assertEqual("", self.collect_warnings())

    def test_rejects_unknown_token_type(self) -> None:
        self.assertIn("IOS_TOKEN_TYPE", self.collect_warnings(IOS_TOKEN_TYPE="jwt"))

    def test_rejects_unknown_dashboard_type(self) -> None:
        self.assertIn(
            "IOS_DASHBOARD_TYPE", self.collect_warnings(IOS_DASHBOARD_TYPE="fancy")
        )

    def test_rejects_url_without_scheme(self) -> None:
        self.assertIn(
            "IOS_FAQ_URL", self.collect_warnings(IOS_FAQ_URL="example.com/faq")
        )

    def test_accepts_empty_optional_url(self) -> None:
        self.assertEqual("", self.collect_warnings(IOS_FAQ_URL=""))

    def test_rejects_invalid_bundle_id(self) -> None:
        self.assertIn(
            "IOS_BUNDLE_ID", self.collect_warnings(IOS_BUNDLE_ID="not a bundle")
        )

    def test_accepts_valid_bundle_id(self) -> None:
        self.assertEqual("", self.collect_warnings(IOS_BUNDLE_ID="org.example.mobile"))

    def test_rejects_non_numeric_version(self) -> None:
        self.assertIn(
            "IOS_MARKETING_VERSION", self.collect_warnings(IOS_MARKETING_VERSION="v1")
        )

    def test_webview_mode_requires_a_base_url(self) -> None:
        warnings = self.collect_warnings(
            IOS_DISCOVERY_TYPE="webview", IOS_DISCOVERY_WEBVIEW_BASE_URL=""
        )
        self.assertIn("IOS_DISCOVERY_WEBVIEW_BASE_URL", warnings)

    def test_webview_mode_with_base_url_is_fine(self) -> None:
        self.assertEqual(
            "",
            self.collect_warnings(
                IOS_DISCOVERY_TYPE="webview",
                IOS_DISCOVERY_WEBVIEW_BASE_URL="https://example.com",
            ),
        )


class ConfigSettingsTests(PluginTestCase):
    """
    Tests for the files process_config.py uses to locate the configuration.
    """

    def test_config_settings_points_at_tutor_config(self) -> None:
        parsed = yaml.safe_load(
            self.render(self.get_config(), "ios/build/config/config_settings.yaml")
        )
        # Must not point at the app's own default_config, which we leave alone.
        self.assertEqual("./tutor_config", parsed["config_directory"])

    def test_every_environment_maps_to_generated_config(self) -> None:
        """
        Whichever Xcode scheme the user selects must resolve to our config.
        """
        parsed = yaml.safe_load(
            self.render(self.get_config(), "ios/build/config/config_settings.yaml")
        )
        self.assertEqual({"prod", "stage", "dev"}, set(parsed["config_mapping"]))
        for environment in ("prod", "stage", "dev"):
            self.assertEqual("prod", parsed["config_mapping"][environment])

    def test_file_mappings_lists_the_config_file(self) -> None:
        parsed = yaml.safe_load(
            self.render(self.get_config(), "ios/build/config/prod/file_mappings.yaml")
        )
        self.assertEqual(["config.yaml"], parsed["ios"]["files"])


class InitTaskTests(PluginTestCase):
    def test_oauth_application_is_created_in_the_lms(self) -> None:
        tasks = list(hooks.Filters.CLI_DO_INIT_TASKS.iterate())
        ios_tasks = [(s, t) for s, t in tasks if "iOS application" in t]
        self.assertEqual(1, len(ios_tasks), "expected exactly one iOS init task")
        service, task = ios_tasks[0]
        self.assertEqual("lms", service)

        config = self.get_config(IOS_OAUTH_CLIENT_ID="ios")
        rendered = env.render_str(config, task)
        self.assertIn("create_dot_application", rendered)
        self.assertIn("--client-id ios", rendered)
        # The secret must be interpolated, not left as a template variable.
        self.assertNotIn("{{", rendered)
        self.assertIn(t.cast(str, config["IOS_OAUTH2_SECRET"]), rendered)

    def test_oauth_client_id_is_configurable(self) -> None:
        tasks = [t for _, t in hooks.Filters.CLI_DO_INIT_TASKS.iterate()]
        task = next(t for t in tasks if "iOS application" in t)
        rendered = env.render_str(self.get_config(IOS_OAUTH_CLIENT_ID="custom"), task)
        self.assertIn("--client-id custom", rendered)


class SetupScriptTests(PluginTestCase):
    def test_script_refuses_a_non_app_directory(self) -> None:
        """
        The script must not silently write config into an unrelated directory.
        """
        rendered = self.render(self.get_config(), "ios/build/setup.sh")
        self.assertIn("config_script/process_config.py", rendered)
        self.assertIn("set -euo pipefail", rendered)

    def test_script_targets_tutor_config_directory(self) -> None:
        rendered = self.render(self.get_config(), "ios/build/setup.sh")
        self.assertIn("tutor_config", rendered)
        # default_config belongs to the app; we must not overwrite it.
        self.assertNotIn('rm -rf "$APP_DIR/default_config"', rendered)


if __name__ == "__main__":
    unittest.main()
