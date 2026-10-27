# Upstream code and attribution

This repository contains conversion tooling for a separately obtained Pie
Adblock package. It is not affiliated with Pie or Mozilla.

The Chrome CRX, extracted upstream files, generated Firefox files, XPI packages,
browser runtimes, profiles, and dependency installations are excluded from Git.
The build preserves upstream license notices inside the local output. Its
original code is not relicensed by this project's MIT license.

Pie identifies only portions of its product as open source. Its public
`pie-adblock-rules` repository covers rules and the scriptlet reader; it is not
the source tree for the entire Chrome extension. We have not established
permission to redistribute the entire modified Pie product. Confirm the
applicable upstream permissions before attaching built packages to a public
release or submitting the full product for signing.

Pie's published terms, section 3.2, restrict modification and distribution unless
written permission or an applicable legal exception permits them.

Sources checked on October 27, 2026:

- [Pie: open-source status](https://www.pie.org/about)
- [Pie rules and scriptlet reader](https://github.com/piedotorg/pie-adblock-rules)
- [Original Chrome listing](https://chromewebstore.google.com/detail/jpkfgepcmmchgfbjblnodjhldacghenp)
- [Pie terms](https://www.pie.org/terms)

The package hash and upstream version reviewed for these patches are pinned in
`upstream.json`. A newer Chrome package requires a fresh compatibility review.
