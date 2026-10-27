# Validation record

Date: October 27, 2026. Upstream: Pie 1.33.9.

## Automated runtime checks

The existing test run used an isolated Windows Firefox 159.0 profile:

- Temporary installation and background startup succeeded; the extension reported
  no manifest errors or warnings.
- All seven static rulesets activated. All 195,198 original OISD domain entries
  were preserved in 196 grouped rules.
- Browser rule matching passed for one domain from each of the 196 groups.
  A subdomain matched; a clean domain and a misleading suffix domain did not.
- The original popup rendered, the offscreen iframe replied to a message, and
  internal settings retrieval returned data.

`web-ext` 10.8.0 reported 0 errors, 0 notices, and 111 warnings. These warnings
include upstream bundled-code findings and the missing Firefox data disclosure.
They have not been represented as resolved or approved by Mozilla.

## Manual testing in Zen Browser

During manual testing, Pie was enabled on YouTube and Twitch, no ads appeared,
and Twitch playback continued normally. This was a browsing check rather than a
controlled video-ad test. The installed Zen version was not recorded.

## Not yet verified

Signed installation/restart persistence; long-session background suspension;
remote-filter update behavior under every configuration; Pie website/account and
Shopping-extension integration; formal data-consent behavior; all warning paths.

Machine-local logs, screenshots, and test profiles remain outside the tracked
repository. They can contain local paths, generated device IDs, and URLs.

## Repository build checks

Two consecutive builds produced the same XPI bytes. At that point, every runtime
file matched the previously tested package; only ZIP metadata/compression changed. The
verification script also checked all 195,198 domain entries, the 4,431-rule static
budget, unique rule IDs, and all 10 bundled license notices. Python and JavaScript
syntax checks passed.

A later build changes the displayed name to
`Pie Adblock (unofficial Firefox port)`. Package comparison confirmed that only
the manifest name changed; all other manifest fields and packaged files match
the earlier package. The renamed build's installation and restart behavior in
Zen Browser have not yet been confirmed.
