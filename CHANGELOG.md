# Changelog

This file includes a history of past releases. Changes that were not yet added to a release are in the [changelog.d/](./changelog.d) folder.

<!--
⚠️ DO NOT ADD YOUR CHANGES TO THIS FILE! (unless you want to modify existing changelog entries in this file)
Changelog entries are managed by scriv. After you have made some changes to this plugin, create a changelog entry with:

    scriv create

Edit and commit the newly-created file in changelog.d.

If you need to create a new release, create a separate commit just for that. It is important to respect these
instructions, because git commits are used to generate release notes:
  - Modify the version number in `__about__.py`.
  - Collect changelog entries with `scriv collect`
  - The title of the commit should be the same as the new version: "vX.Y.Z".
-->

<!-- scriv-insert-here -->

<a id='changelog-22.0.0'></a>
## v22.0.0 (2026-09-04)

- [Feature] Add iOS mobile app plugin for Tutor, targeting Verawood. Generates the Open edX iOS app configuration from Tutor settings and creates the OAuth2 application in the LMS the app authenticates against. Unlike the Android app, iOS apps cannot be built in Docker because Xcode requires macOS, so this plugin configures a local `openedx-app-ios` checkout rather than producing a downloadable binary. (by @Faraz32123)

- [Feature] Generate the app's `whitelabel.yaml` from Tutor settings and apply it during `tutor ios setup`, so the bundle identifier, app name, version, development team, colours, app icon and font are configured with `IOS_*` settings instead of by hand. (by @Faraz32123)

- [Improvement] Validate `IOS_*` settings when the configuration is loaded, warning about values the app would reject or silently ignore, such as an unknown `TOKEN_TYPE`, a URL with no scheme, or an invalid bundle identifier. (by @Faraz32123)

- [Improvement] Support Python 3.10 through 3.14, matching tutor-android. Drop Python 3.9 (end-of-life). (by @Faraz32123)
