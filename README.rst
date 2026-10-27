iOS application plugin for `Tutor <https://docs.tutor.edly.io>`__
=================================================================

This plugin configures the official `Open edX iOS app
<https://github.com/openedx/openedx-app-ios>`__ for your Tutor platform. It:

- creates the OAuth2 application the app signs in with;
- generates the app's configuration (API host, OAuth client, feature flags, branding)
  from ``IOS_*`` Tutor settings;
- applies that configuration to a checkout of the app.

It does not build or publish the app. You do that in Xcode on a Mac.

How this differs from the Android plugin
----------------------------------------

`tutor-android <https://github.com/overhangio/tutor-android>`__ builds the app in a
Docker container and serves the ``.apk`` from your platform. That isn't possible for
iOS: Xcode only runs on macOS, and Apple only allows installing apps from the App Store,
TestFlight or an Enterprise program.

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
     - No, only the OAuth2 application is created
   * - How learners install it
     - Download the ``.apk`` from your site
     - From the App Store or TestFlight
   * - Paid developer account
     - Not needed
     - Required to publish

Requirements
------------

Generating the configuration only needs Tutor, on any OS. Building the app needs:

- a Mac with **Apple silicon** and **Xcode 26**, the version the app is built with (see
  its `Fastfile <https://github.com/openedx/openedx-app-ios/blob/main/fastlane/Fastfile>`__).
  Xcode 26 doesn't run on Intel Macs. Without one, use a macOS CI runner such as GitHub
  Actions ``macos-latest``, or a hosted Mac;
- the full Xcode, not just the Command Line Tools, which have no simulators;
- `CocoaPods <https://cocoapods.org>`__: ``brew install cocoapods``;
- a platform served over **HTTPS**. The app blocks plain HTTP, so you can't sign in to a
  local ``http://local.openedx.io``;
- a paid Apple Developer account, only to publish. The simulator needs none.

Compatibility
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Plugin branch
     - Tutor
     - App version cloned
     - Tested with
   * - ``release``
     - 22.x
     - the Open edX release tag, e.g. ``release/verawood.1``
     - Xcode 26
   * - ``main``
     - nightly
     - ``main``
     - Xcode 26

The app version follows ``OPENEDX_COMMON_VERSION``. To build another one, set
``IOS_APP_VERSION`` to any branch or tag of the app.

Installation
------------

.. code-block:: bash

    pip install "git+https://github.com/overhangio/tutor-ios@release"
    tutor plugins enable ios

Use the branch that matches your Tutor version, see `Compatibility`_.

Usage
-----

Generate the configuration and create the OAuth2 application:

.. code-block:: bash

    tutor config save
    tutor local do init --limit=ios       # or: tutor k8s do init --limit=ios

Check that the application exists: open ``https://<LMS_HOST>/admin/oauth2_provider/application/``
and look for the client ID ``ios``.

To change a setting, add ``--set``, for example ``tutor config save --set
IOS_APP_NAME="My App"``. See `Settings`_.

If Tutor runs on your Mac
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    tutor ios clone ~/openedx-app-ios     # clone the app and apply the configuration
    tutor ios setup ~/openedx-app-ios     # or apply it to an existing checkout

If Tutor runs on a server
~~~~~~~~~~~~~~~~~~~~~~~~~

The configuration is generated in a ``build`` folder, which contains no secrets. On the
server, package it and note the app version:

.. code-block:: bash

    cd "$(tutor config printroot)/env/plugins/ios"
    tar czf ~/ios-build.tgz build
    tutor config printvalue IOS_APP_VERSION

On the Mac, fetch it, clone the app and apply the configuration. The app's branding
script needs a few Python packages, so install them in a virtualenv (Homebrew's Python
refuses a global ``pip install``):

.. code-block:: bash

    scp user@server:ios-build.tgz . && tar xzf ios-build.tgz
    git clone --branch <IOS_APP_VERSION> https://github.com/openedx/openedx-app-ios
    python3 -m venv ios-venv
    ios-venv/bin/pip install pyyaml pillow coloredlogs
    TUTOR_IOS_PYTHON=ios-venv/bin/python bash build/setup.sh openedx-app-ios

Run the app
~~~~~~~~~~~

.. code-block:: bash

    cd openedx-app-ios
    pod install
    open -a Xcode OpenEdX.xcworkspace

In Xcode, select the ``OpenEdXProd`` scheme and an iPhone simulator, then press Run.

Courses are hidden from the app by default. To show one, open the course in Studio, go
to **Settings → Advanced Settings** and set **Mobile Course Available** to ``true``.

The configuration is compiled into the app. After changing any ``IOS_*`` setting, run
``tutor config save``, apply the configuration again (``tutor ios setup``, or copy the
``build`` folder and rerun ``setup.sh``) and rebuild.

Settings
--------

The most common settings and their defaults:

.. list-table::
   :header-rows: 1

   * - Setting
     - Default
   * - ``IOS_API_HOST_URL``
     - your LMS URL
   * - ``IOS_APP_NAME``
     - ``PLATFORM_NAME``
   * - ``IOS_BUNDLE_ID``
     - ``org.openedx.app``
   * - ``IOS_OAUTH_CLIENT_ID``
     - ``ios``
   * - ``IOS_FEEDBACK_EMAIL_ADDRESS``
     - ``CONTACT_EMAIL``
   * - ``IOS_DISCOVERY_TYPE``, ``IOS_PROGRAM_TYPE``
     - ``native`` (or ``webview``, ``none``)
   * - ``IOS_DASHBOARD_TYPE``
     - ``primary`` (or ``gallery``)
   * - ``IOS_APP_REPOSITORY``, ``IOS_APP_VERSION``
     - the official app, see `Compatibility`_

All settings, by group:

- **General**: ``IOS_ENVIRONMENT_DISPLAY_NAME``, ``IOS_ORGANIZATION_CODE``,
  ``IOS_TOKEN_TYPE`` (``JWT`` or ``BEARER``), ``IOS_FAQ_URL``, ``IOS_URI_SCHEME``,
  ``IOS_APP_STORE_ID``.
- **Single sign-on**: ``IOS_SSO_URL``, ``IOS_SSO_FINISHED_URL``,
  ``IOS_SSO_BUTTON_TITLE``.
- **Agreement URLs**: ``IOS_PRIVACY_POLICY_URL``, ``IOS_COOKIE_POLICY_URL``,
  ``IOS_DATA_SELL_CONSENT_URL``, ``IOS_TOS_URL``, ``IOS_EULA_URL``,
  ``IOS_SUPPORTED_LANGUAGES``. An empty URL is hidden in the app.
- **Feature flags**: ``IOS_WHATS_NEW_ENABLED``, ``IOS_PRE_LOGIN_EXPERIENCE_ENABLED``,
  ``IOS_APP_LEVEL_DATES_ENABLED``, ``IOS_APP_LEVEL_DOWNLOADS_ENABLED``.
- **UI components**: ``IOS_COURSE_DROPDOWN_NAVIGATION_ENABLED``,
  ``IOS_COURSE_UNIT_PROGRESS_ENABLED``, ``IOS_LOGIN_REGISTRATION_ENABLED``,
  ``IOS_SAML_SSO_LOGIN_ENABLED``, ``IOS_SAML_SSO_DEFAULT_LOGIN_BUTTON``.
- **Theme**: ``IOS_ROUNDED_CORNERS_STYLE``, ``IOS_BUTTON_CORNERS_RADIUS``.
- **Discovery and programs**: ``IOS_DISCOVERY_WEBVIEW_*``, ``IOS_PROGRAM_WEBVIEW_*``.
- **Analytics**: ``IOS_FIREBASE_*``, ``IOS_SEGMENT_IO_*``, ``IOS_BRAZE_*``,
  ``IOS_BRANCH_*``.
- **Social sign-in**: ``IOS_GOOGLE_*``, ``IOS_MICROSOFT_*``, ``IOS_FACEBOOK_*``,
  ``IOS_APPLE_SIGNIN_ENABLED``.
- **Branding**: see `Branding`_.

``tutor config save`` warns about values that would break the app, such as an invalid
``IOS_TOKEN_TYPE``, a URL without ``http(s)://`` or a malformed bundle ID.

Settings that take a list or a mapping are easier to write in
``$(tutor config printroot)/config.yml``. Run ``tutor config save`` after editing it.

For a key with no ``IOS_*`` setting, add it to the app's ``config.yaml`` with the
``ios-config-yaml`` patch:

.. code-block:: python

    from tutor import hooks

    hooks.Filters.ENV_PATCHES.add_item(("ios-config-yaml", "MY_CUSTOM_KEY: my-value\n"))

A key in the patch replaces the whole key of the same name, so use ``IOS_*`` settings to
change part of a group.

Branding
~~~~~~~~

The bundle ID, app name, version, colours, icon and font are applied by the app's
``config_script/whitelabel.py``, which ``tutor ios setup`` and ``setup.sh`` run for you.

- ``IOS_BUNDLE_ID``: reverse-DNS ID, unique on the App Store.
- ``IOS_MARKETING_VERSION`` and ``IOS_BUILD_NUMBER``: every upload to Apple needs a
  higher build number.
- ``IOS_DEV_TEAM``: your Apple team ID, needed to publish. Until it is set, setup prints
  ``ERROR 'dev_team' is empty in config``, which you can ignore.

Colours, images and fonts go in ``config.yml``:

.. code-block:: yaml

    IOS_COLORS:
      Primary: "#0A3055"
      AccentColor:
        light: "#FF0000"
        dark: "#880000"
    IOS_IMAGES_IMPORT_DIR: /Users/me/brand-assets
    IOS_APP_ICON: app-icon.png
    IOS_IMAGES:
      appLogo: logo.svg
    IOS_FONT_FILE: /Users/me/brand-assets/Brand.ttf
    IOS_FONT_NAMES:
      regular: Brand-Regular
      bold: Brand-Bold

Colour names must match the app's ``Theme/Theme/Assets.xcassets/Colors``. Image and font
paths are read when ``setup.sh`` runs, so they must be paths **on the Mac**, even when
Tutor runs on a server. For other keys, use the ``ios-whitelabel-yaml`` patch.

Publishing the app
------------------

1. Point Tutor at your production platform (``LMS_HOST`` with ``ENABLE_HTTPS=true``) and
   run the init step from `Usage`_.
2. Set ``IOS_BUNDLE_ID``, ``IOS_DEV_TEAM``, a higher ``IOS_BUILD_NUMBER``, and
   ``IOS_APP_STORE_ID`` once you have a listing. Apply the configuration.
3. In Xcode, select **Any iOS Device**, then **Product → Archive → Distribute App → App
   Store Connect**.
4. Submit the build in `App Store Connect <https://appstoreconnect.apple.com>`__, or
   share it through TestFlight.

Installed apps don't pick up configuration changes, so every change needs a new build.

Testing
-------

.. code-block:: bash

    pip install -e ".[dev]"
    make test                                         # lint, types and unit tests
    make test-build-config                            # run the app's config script on the output
    make test-build-xcode APP_DIR=~/openedx-app-ios   # check the Mac is ready to build

``test-build-config`` needs no Xcode. It clones the app, applies the configuration, runs
the app's ``process_config.py`` for every build configuration and checks the result.

Troubleshooting
---------------

- **"No such command 'ios'"**: the plugin isn't enabled. Run ``tutor plugins enable ios``.
- **"No module named ..." from whitelabel.py**: the branding packages are missing from
  the Python that ran it. See `If Tutor runs on a server`_.
- **Plugin "SwiftLintBuildToolPlugin" must be enabled**: click the error in Xcode,
  choose **Trust & Enable** and run again.
- **Build errors in Pods or Swift files with a newer Xcode** (for example a Pods
  deployment target error, or "used before being initialized"): use Xcode 26.
- **The app shows "offline", or sign-in fails**: the platform must be served over HTTPS,
  and the OAuth2 application must exist (see `Usage`_).
- **No courses on the dashboard**: set **Mobile Course Available** on the course, see
  `Run the app`_.

For anything else, ask on the `Open edX forum <https://discuss.openedx.org>`__.

License
-------

This work is licensed under the terms of the `GNU Affero General Public License (AGPL)
<https://www.gnu.org/licenses/agpl-3.0.en.html>`_.
