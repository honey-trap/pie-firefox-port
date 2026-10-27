# Pie for Firefox-based browsers

An unofficial port of Pie Adblock 1.33.9 for Firefox-based desktop browsers, maintained by
[honey-trap](https://github.com/honey-trap) and
[AlixSalba](https://github.com/AlixSalba).

The popup and core blocking features work in our Firefox tests. Testing in Zen Browser
has also shown working Twitch playback with no ads observed. This is still an
experimental build, and it is not affiliated with Pie or Mozilla.

## Before you install

Download the `.xpi` file from the latest GitHub release under **Assets**. Use it
for either installation method below. You do not need Python or any build tools
to install the extension.

Choose the `.xpi` file, not GitHub's **Source code (zip)** download, which is for
people working on the project.

Use a Firefox-based desktop browser with Firefox 140 or a compatible newer
engine. Testing has covered Firefox and Zen; other browsers have not been
verified.

## Install permanently (without having to reload it each time you open your browser)

This method requires a browser build that allows unsigned extensions. Firefox
Developer Edition, Nightly, and ESR support this setting; support in other
Firefox-based browsers depends on the build. Standard Firefox releases do not
allow this permanent unsigned installation. Use the temporary method below if
your browser does not support it.

**This turns off signature enforcement for all extensions in your browser profile,
not just Pie.** Only install extension files from sources you trust. Each person
using this method must change the setting in their own browser profile.

1. Open `about:config` in your browser and accept the warning.
2. Search for `xpinstall.signatures.required` and change it to **false**.
3. Open `about:addons`, click the gear, and choose **Install Add-on From File**.
4. Select `pie-firefox-1.33.9-unsigned.xpi` (or the XPI for the release you
   downloaded) and approve the installation permissions.
5. Fully close and reopen your browser. Check that Pie is still listed and enabled in
   `about:addons`, then check its site access on a normal website.

Use **Install Add-on From File** for this installation. **Load Temporary Add-on**
only lasts until the browser closes. If you already loaded Pie temporarily,
install the XPI through the Add-ons Manager and verify it after restarting.

If your browser still rejects the unsigned file, its build may not honor the
setting. Check its documentation or use the temporary method below.

Turning `xpinstall.signatures.required` back to **true** can disable the unsigned
extension.

## Load temporarily

Use this option to try the extension for one browser session. You do not need to
change signature checking for a temporary installation. Use the same `.xpi` file
described above.

1. Open `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on** and select `pie-firefox-1.33.9-unsigned.xpi`
   (or the XPI for your version).
3. Open the extension on a normal website and allow site access if prompted.

The extension is removed when the browser closes. Repeat these steps next time
you open your browser if you want to use it again.

Open Pie from your browser's extensions menu. The menu location and toolbar
pinning options vary by browser.

<br><br><br>

----------------------------------------------------------------------------------------------------

<br><br><br>

## Known limits

Pie website/account features and integration with Pie Shopping are not fully
tested. Firefox does not support Chrome's webpage `externally_connectable`
messaging, and this port does not add a replacement bridge. Video-ad behavior
can change with the sites, so the current viewing results are not a guarantee.
Long-session background suspension and every remote-update path still need tests.

The build retains Pie's backend calls, analytics, onboarding, and remote filters.
It is not a privacy audit. The extension package itself does not auto-update
from the Chrome store.

## License

The original porting tools and documentation use the [MIT license](LICENSE).
Pie and its dependencies retain their own terms. The local build preserves their
bundled notices. See [upstream code and attribution](THIRD_PARTY.md).

<br><br><br>

----------------------------------------------------------------------------------------------------

<br><br><br>

## For contributors

The instructions below are for contributors who want to build, modify, or test
the extension themselves. To install and use it, follow the download and
installation instructions at the top of this page.

### Build

This repository contains the porting tools. You download Pie's Chrome package
separately; the original package and built extension are not checked into Git.

You need Python 3.10 or newer. The build uses Python's standard library.

```sh
python download.py
python build.py
```

The downloader accepts only the package hash in `upstream.json`. If Google serves
a newer release, it stops without saving it. Each new release needs a review of
the patches. An existing copy of the reviewed CRX can be placed at
`pie-original.crx` instead.

The output is `firefox/` and `pie-firefox-1.33.9-unsigned.xpi`.
`build-report.json` records the input/output hashes and rule changes.
If the XPI is currently loaded in a browser, build into another folder with
`python build.py --output-dir review-artifacts/rebuild`.

To try the unpacked build, follow the temporary installation steps above and
select `firefox/manifest.json` instead of the XPI.

### What the port changes

The background script runs in Firefox's extension page instead of a Chrome
service worker. A hidden extension iframe handles Pie's offscreen messages.

Firefox's rule budget is smaller than Pie's list. The build groups all 195,198
OISD domain entries into 196 equivalent domain rules, so the list fits without
truncation. The other six rulesets stay intact apart from one unsupported rule
that depends on response-header matching. The build report identifies it.

The port also fixes duplicate translation keys, removes Chrome-specific manifest
fields, and handles Firefox's internal page URLs. Toolbar pin detection reports
unpinned because Firefox has no equivalent API.

### Testing

The runtime tests pass on Firefox 159.0: startup, popup rendering, all seven
rulesets, 196 domain samples, clean-domain controls, offscreen messaging, and
settings retrieval. [Test details](docs/VALIDATION.md).

For the extension validator, install Node.js 22 or newer and run:

```sh
npm ci
npm run check
npm run lint:extension
```

Run `python verify_build.py` to check repeatable package bytes, domain-list
preservation, rule IDs, and the bundled license notices.

The recorded validator result is 0 errors and 111 warnings. The warnings include
bundled-code findings and missing Firefox data declarations and still need review.

The Windows browser test needs `marionette_driver==3.7.1` and a Firefox binary.
Set `FIREFOX_BINARY` to its path, then run `python test_firefox.py`. It uses a
separate profile and makes network requests through Pie's original onboarding.
