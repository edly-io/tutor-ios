iOS application plugin for `Tutor <https://docs.tutor.edly.io>`__
=================================================================

This is a plugin to easily configure and build an iOS mobile application for your
`Open edX <https://open.edx.org>`__ instance, from the official
`openedx-app-ios <https://github.com/openedx/openedx-app-ios>`__ repository.

How this differs from the Android plugin
----------------------------------------

The `tutor-android <https://github.com/overhangio/tutor-android>`__ plugin compiles the
Android app inside a Docker container and serves the resulting ``.apk`` over HTTP, so
learners can download it directly from your platform.

**That is not possible for iOS.** Building an iOS app requires Xcode, which only runs on
macOS and cannot legally or technically run in a Linux Docker container. Apple also does
not allow installing arbitrary ``.ipa`` files from a web page — apps must be distributed
through the App Store, TestFlight, or an Apple Developer Enterprise program.

Consequently, this plugin does **not** build the app for you. Instead it:

1. Generates the app's YAML configuration from your Tutor settings, so the app points at
   your platform with the correct API host, OAuth credentials and feature flags.
2. Creates the OAuth2 application in the LMS that the app authenticates against.
3. Installs that configuration into a local checkout of ``openedx-app-ios`` for you.

You then build and distribute the app from a Mac with Xcode.

Side by side:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * -
     - tutor-android
     - tutor-ios
   * - Who builds the app
     - Tutor, in a Docker container
     - You, in Xcode on a Mac
   * - What you get
     - An ``.apk`` file
     - A configured source folder
   * - Runs on your servers
     - Yes, a container serving the file
     - No, nothing runs on your infrastructure
   * - How learners install it
     - Download the ``.apk`` from your site
     - From the App Store or TestFlight
   * - Publishing
     - Not needed
     - Manual upload, plus Apple review
   * - Paid developer account
     - Not needed
     - Required to distribute

In short: this plugin hands you a **configured project**, not a finished app. Nothing is
uploaded to the App Store automatically — every release is a build you make and submit
yourself. That is a constraint Apple imposes, not a limitation of this plugin.

Requirements
------------

To **configure** the app with this plugin you only need Tutor — the configuration is
generated with Python and can be produced and verified on any platform, including Linux.

To **build and run** the app you additionally need:

- a **Mac with Apple silicon** (M1 or later). The Open edX iOS app pins Xcode 26 in its
  `fastlane setup <https://github.com/openedx/openedx-app-ios/blob/main/fastlane/Fastfile>`__
  and builds on Apple silicon CI runners. Xcode 26 does not run on Intel Macs; the last
  Intel-capable release is Xcode 16.4. An Intel Mac therefore cannot build the current
  app even on macOS Tahoe.
- a full **Xcode** installation. The Command Line Tools alone are not sufficient, as
  they do not provide ``xcodebuild`` or the iOS simulators.
- **CocoaPods** (``brew install cocoapods``), used by the app's ``pod install`` step.
- a paid **Apple Developer account**, but only to distribute the app. Building and
  running it in the simulator needs no account, because simulator builds are not
  code-signed.

If you have no Apple silicon hardware, the practical options are macOS CI runners
(GitHub Actions ``macos-latest`` is Apple silicon) or a hosted Mac.

Installation
------------

.. code-block:: bash

    pip install git+https://github.com/overhangio/tutor-ios

Usage
-----

Enable the plugin and run the initialisation, which creates the OAuth2 credentials the
app needs:

.. code-block:: bash

    tutor plugins enable ios
    tutor local launch

Then, on a Mac, clone the app with your configuration already applied:

.. code-block:: bash

    tutor ios clone ~/openedx-app-ios

You now have a configured project, ready to build in Xcode. See
`Releasing the app, end to end`_ for the rest of the path to the App Store.

If you already have a checkout of the app, configure it in place instead:

.. code-block:: bash

    tutor ios setup /path/to/openedx-app-ios

Re-run this command whenever you change any ``IOS_*`` setting, so the app picks up the
new values. To see where the generated configuration lives, run
``tutor ios printconfigdir``.

How the configuration is applied
--------------------------------

The Open edX iOS app reads its settings from a ``config.plist`` bundled into the app.
That file is generated during the Xcode build by ``config_script/process_config.py``,
which merges the YAML files listed in ``file_mappings.yaml`` for the current build
configuration.

``tutor ios setup`` writes:

- ``config_settings.yaml`` at the root of the checkout, pointing ``config_directory`` at
  ``./tutor_config``;
- ``tutor_config/prod/config.yaml`` and ``tutor_config/prod/file_mappings.yaml``, holding
  your rendered settings.

Your Tutor configuration is written to a dedicated ``tutor_config`` directory, so the
app's own ``default_config`` is left untouched and ``git status`` stays readable. All
three build environments (``prod``, ``stage`` and ``dev``) are mapped to the same
generated configuration, so any scheme you select in Xcode targets your platform.

Testing
-------

Static checks and unit tests run without Xcode or macOS:

.. code-block:: bash

    pip install -e ".[dev]"
    make test

That runs ruff, mypy and the unit test suite in ``tests/``, which renders the
plugin's templates and asserts the result matches what the app's Swift
configuration classes expect.

Testing the build
~~~~~~~~~~~~~~~~~

The configuration this plugin generates can be verified end to end **without
Xcode**, by running the app's own build script against it:

.. code-block:: bash

    make test-build-config

This clones ``openedx-app-ios``, installs your configuration into it, and runs
``config_script/process_config.py`` — the same script the Xcode build phase runs
— for all six build configurations. It then checks that the resulting
``config.plist`` contains the keys the app requires, and that the plugin did not
modify any file in the checkout that it does not own. This covers the whole
surface the plugin is responsible for; everything past it is stock Xcode
compiling unmodified upstream Swift.

To compile the app itself you need macOS with a full **Xcode** installation
(Command Line Tools alone are not enough) and **CocoaPods**. To check whether
your machine is ready:

.. code-block:: bash

    make test-build-xcode APP_DIR=~/openedx-app-ios

Add ``--build`` to compile the app for the simulator, which needs no Apple
Developer account because simulator builds are not code-signed:

.. code-block:: bash

    ./tests/test_build_xcode.sh ~/openedx-app-ios --build

Note that iOS App Transport Security blocks plaintext HTTP by default, so an
``http://`` ``LMS_HOST`` may fail to connect from a simulator or device even
though the app builds. Run your platform over HTTPS to test sign-in.

Making courses visible in the app
---------------------------------

By default, courses are not visible in the mobile app. To make a course available, go to
Studio → YOUR COURSE → Settings → Advanced Settings and set ``Mobile Course Available``
to ``true``.

Customising the app configuration
---------------------------------

All commonly customised fields are exposed as ``IOS_*`` Tutor settings, so you can change
them with ``tutor config save --set <KEY>=<VALUE>``. For example, to enable Firebase:

.. code-block:: bash

    tutor config save \
      --set IOS_FIREBASE_ENABLED=true \
      --set IOS_FIREBASE_PROJECT_ID=my-project \
      --set IOS_FIREBASE_API_KEY=AIzaSy... \
      --set IOS_FIREBASE_GOOGLE_APP_ID=1:1234567890:ios:abcdef \
      --set IOS_FIREBASE_GCM_SENDER_ID=1234567890

The available settings are:

- **General**: ``IOS_ENVIRONMENT_DISPLAY_NAME``, ``IOS_ORGANIZATION_CODE``,
  ``IOS_FEEDBACK_EMAIL_ADDRESS``, ``IOS_OAUTH_CLIENT_ID``, ``IOS_TOKEN_TYPE`` (``JWT`` or
  ``BEARER``), ``IOS_FAQ_URL``, ``IOS_URI_SCHEME``, ``IOS_APP_STORE_ID``.
- **Single sign-on**: ``IOS_SSO_URL``, ``IOS_SSO_FINISHED_URL``,
  ``IOS_SSO_BUTTON_TITLE`` (a mapping of language code to button label).
- **Agreement URLs**: ``IOS_PRIVACY_POLICY_URL``, ``IOS_COOKIE_POLICY_URL``,
  ``IOS_DATA_SELL_CONSENT_URL``, ``IOS_TOS_URL``, ``IOS_EULA_URL``,
  ``IOS_SUPPORTED_LANGUAGES``. Leave a URL empty to hide it in the app.
- **Feature flags**: ``IOS_WHATS_NEW_ENABLED``, ``IOS_PRE_LOGIN_EXPERIENCE_ENABLED``,
  ``IOS_APP_LEVEL_DATES_ENABLED``, ``IOS_APP_LEVEL_DOWNLOADS_ENABLED``.
- **UI components**: ``IOS_COURSE_DROPDOWN_NAVIGATION_ENABLED``,
  ``IOS_COURSE_UNIT_PROGRESS_ENABLED``, ``IOS_LOGIN_REGISTRATION_ENABLED``,
  ``IOS_SAML_SSO_LOGIN_ENABLED``, ``IOS_SAML_SSO_DEFAULT_LOGIN_BUTTON``.
- **Theme**: ``IOS_ROUNDED_CORNERS_STYLE``, ``IOS_BUTTON_CORNERS_RADIUS``.
- **Dashboard, discovery and programs**: ``IOS_DASHBOARD_TYPE`` (``primary`` or
  ``gallery``), the ``IOS_DISCOVERY_*`` group and the ``IOS_PROGRAM_*`` group.
- **Analytics and integrations**: the ``IOS_FIREBASE_*``, ``IOS_SEGMENT_IO_*``,
  ``IOS_BRAZE_*`` and ``IOS_BRANCH_*`` groups.
- **Social sign-in**: ``IOS_GOOGLE_*``, ``IOS_MICROSOFT_*``, ``IOS_FACEBOOK_*`` and
  ``IOS_APPLE_SIGNIN_ENABLED``.
- **App identity and branding**: ``IOS_BUNDLE_ID``, ``IOS_APP_NAME``,
  ``IOS_MARKETING_VERSION``, ``IOS_BUILD_NUMBER``, ``IOS_DEV_TEAM``,
  ``IOS_EXTRA_TARGETS``, ``IOS_COLORS``, ``IOS_IMAGES_IMPORT_DIR``, ``IOS_APP_ICON``,
  ``IOS_IMAGES``, ``IOS_FONT_FILE`` and ``IOS_FONT_NAMES``. See
  `Theming and white-labelling the app`_.
- **Source**: ``IOS_APP_REPOSITORY`` and ``IOS_APP_VERSION``, used by
  ``tutor ios clone``. Point these at your fork to build a customised app.

For settings that are not exposed as Tutor variables, your own Tutor plugin can append
YAML to ``config.yaml`` via the ``ios-config-yaml`` patch:

.. code-block:: python

    from tutor import hooks

    hooks.Filters.ENV_PATCHES.add_item((
        "ios-config-yaml",
        "MY_CUSTOM_KEY: my-value\n",
    ))

``process_config.py`` parses this file with PyYAML, which keeps the last value when a key
is duplicated. A top-level key written by the patch therefore **replaces** the value
emitted earlier in the file, so use ``IOS_*`` settings for partial tweaks within a group
(for example ``IOS_FIREBASE_ENABLED``) and reserve the patch for adding new keys or for
replacing an entire group.

If neither approach is sufficient, edit
``$(tutor config printroot)/env/plugins/ios/build/config/prod/config.yaml`` directly
before running ``tutor ios setup``.

Configuration checks
~~~~~~~~~~~~~~~~~~~~

The plugin validates your ``IOS_*`` settings whenever the configuration is loaded, and
warns about values that would produce a broken or silently misconfigured app: a
``TOKEN_TYPE`` outside ``JWT``/``BEARER``, a URL without an ``http(s)://`` scheme, a
bundle identifier that is not reverse-DNS, a non-numeric version, or a webview
discovery mode with no base URL. These are warnings rather than errors, so an
intentionally unusual value will not block ``tutor config save`` — but most of them
would otherwise only surface as odd behaviour once the app is running on a device.

Theming and white-labelling the app
-----------------------------------

App identity — the bundle identifier, display name, version, colours, icon and font —
is applied by the app's own ``config_script/whitelabel.py``, which rewrites the Xcode
project and asset catalogue in place. This plugin generates its configuration too, and
``tutor ios setup`` runs it for you, so these are ordinary Tutor settings:

.. code-block:: bash

    tutor config save \
      --set IOS_BUNDLE_ID=org.example.mobile \
      --set IOS_APP_NAME="Example Learn" \
      --set IOS_MARKETING_VERSION=1.2.0 \
      --set IOS_BUILD_NUMBER=7

- ``IOS_BUNDLE_ID`` — reverse-DNS identifier, unique to your app on the App Store.
- ``IOS_APP_NAME`` — the name under the icon. Defaults to ``PLATFORM_NAME``.
- ``IOS_MARKETING_VERSION`` and ``IOS_BUILD_NUMBER`` — the version learners see and the
  internal build counter. Every upload to Apple needs a higher build number than the
  last, so bump ``IOS_BUILD_NUMBER`` for each submission.
- ``IOS_DEV_TEAM`` — your Apple Developer team ID, needed to archive and upload. When
  set, it is also applied to each sub-project listed in ``IOS_EXTRA_TARGETS``.

Colours are set per asset name, either as one hex value or as separate light and dark
values. Because these are YAML values, use a configuration file rather than ``--set``:

.. code-block:: yaml

    IOS_COLORS:
      Primary: "#0A3055"
      AccentColor:
        light: "#FF0000"
        dark: "#880000"

The asset names must match those in the app's ``Theme/Theme/Assets.xcassets/Colors``
catalogue. An empty ``IOS_COLORS`` leaves the app's own palette untouched.

Images, the app icon and a custom font need files on the build machine. Point
``IOS_IMAGES_IMPORT_DIR`` at a directory and reference filenames inside it:

.. code-block:: yaml

    IOS_IMAGES_IMPORT_DIR: /path/to/brand-assets
    IOS_APP_ICON: app-icon.png
    IOS_IMAGES:
      appLogo: logo.svg
    IOS_FONT_FILE: /path/to/brand-assets/Brand.ttf
    IOS_FONT_NAMES:
      regular: Brand-Regular
      bold: Brand-Bold

The white-labelling step needs a few Python packages that the app's script imports
(``pyyaml``, ``pillow``, ``coloredlogs``). If they are missing, ``tutor ios setup``
warns and skips this step: your app configuration is still installed and usable, only
the identity and branding are left at the app's defaults.

Unlike ``config.yaml``, these changes are written into the checkout itself rather than
read at build time. Re-running ``tutor ios setup`` is safe and idempotent. For settings
this plugin does not expose, append to the generated file via the
``ios-whitelabel-yaml`` patch, or see the app's `configuration documentation
<https://github.com/openedx/openedx-app-ios/blob/main/Documentation/CONFIGURATION_MANAGEMENT.md>`__.

Using this plugin in production
-------------------------------

It is worth being explicit about how the pieces fit together in production, because it
differs from every other Tutor plugin: **nothing from this plugin runs on your server.**

The plugin has two production responsibilities:

1. **The OAuth2 client.** ``tutor local launch`` (or ``tutor k8s launch``) runs the
   plugin's init task in the LMS, creating the public OAuth2 application the app
   authenticates against. This is the only part that touches your running platform, and
   it is required for the app to work at all.
2. **The app configuration.** ``tutor ios setup`` bakes your settings into the app
   binary at build time. There is no iOS container, no image to push, and no service
   added to your deployment.

Because the configuration is compiled into the binary, **changing an** ``IOS_*``
**setting has no effect on already-installed apps.** Your production release cycle is
therefore:

.. code-block:: bash

    # 1. Change configuration
    tutor config save --set IOS_FEEDBACK_EMAIL_ADDRESS=help@example.com

    # 2. Re-apply it to your app checkout, on a Mac
    tutor ios setup ~/openedx-app-ios

    # 3. Rebuild, then ship a new version through TestFlight or the App Store

Point ``API_HOST_URL`` at your production LMS by setting ``LMS_HOST`` and enabling
``ENABLE_HTTPS``, which this plugin follows automatically. Serving your platform over
HTTPS is mandatory in production, for the App Transport Security reason noted under
`Testing the build`_.

Set ``IOS_APP_STORE_ID`` once you have an App Store listing, so the app's
"rate this app" and upgrade prompts link to the right place.

Releasing the app, end to end
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The full path from a Tutor setting to a learner's phone. Steps 1–2 happen anywhere;
steps 3 onwards need an Apple silicon Mac (see `Requirements`_).

**1. Configure and create the OAuth client**

.. code-block:: bash

    tutor config save --set LMS_HOST=courses.example.com --set ENABLE_HTTPS=true
    tutor local launch          # or: tutor k8s launch

**2. Verify the configuration is correct**

Run ``make test-build-config`` (see `Testing the build`_) to catch configuration
mistakes before involving Xcode at all.

**3. Get a configured checkout of the app**

.. code-block:: bash

    tutor ios clone ~/openedx-app-ios

**4. Build and test in the simulator**

.. code-block:: bash

    cd ~/openedx-app-ios
    pod install
    open OpenEdX.xcworkspace

Select the ``OpenEdXProd`` scheme and press Run. Sign in with a real account on your
platform and confirm your courses appear. This step needs no Apple Developer account.

**5. Check your app identity**

The bundle identifier, name, version and branding were already applied in step 3 from
your ``IOS_*`` settings — see `Theming and white-labelling the app`_. Confirm them in
Xcode, and remember that every upload needs a higher ``IOS_BUILD_NUMBER`` than the last.
Set ``IOS_DEV_TEAM`` before archiving.

**6. Archive and upload**

Select **Any iOS Device** as the destination, then **Product → Archive**. When the
Organizer opens, choose **Distribute App → App Store Connect**. This requires your
paid Apple Developer account and a distribution certificate. Alternatively, run
``fastlane`` from the app repository to script the same thing in CI.

**7. Submit for review**

In `App Store Connect <https://appstoreconnect.apple.com>`__, attach the uploaded build
to a version, complete the metadata, screenshots and privacy answers, then submit.
Review typically takes a day or two, but budget longer for a first submission.

**8. Learners install it**

Once approved, learners install from the App Store. Apple offers three distribution
channels, all requiring the paid developer account:

- **TestFlight**, for beta testing with up to 10,000 users, skipping full review;
- the **App Store**, for public release;
- the **Apple Developer Enterprise Program**, for in-house distribution.

A common production arrangement is to run ``tutor ios setup`` and the Xcode build
together on a macOS CI runner, so releases are reproducible and no developer machine
holds the signing identity.

**Repeat for each change.** Because configuration is compiled into the binary, any
``IOS_*`` change means redoing steps 1 and 3–7 and shipping a new version. Installed
apps do not pick up configuration changes from your server.

Keep stage and production separate: build stage against your stage ``LMS_HOST`` and
ship it to TestFlight; build production against your production host for the App Store.
A binary cannot be repointed after it is built.

Troubleshooting
---------------

Community support is available from the official `Open edX forum
<https://discuss.openedx.org>`__. Do you need help with this plugin? See the
`troubleshooting <https://docs.tutor.edly.io/troubleshooting.html>`__ section from the
Tutor documentation.

License
-------

This work is licensed under the terms of the `GNU Affero General Public License (AGPL)
<https://www.gnu.org/licenses/agpl-3.0.en.html>`_.
