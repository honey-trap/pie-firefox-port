"""Reproducibly adapt the downloaded Chrome package for local Firefox testing."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import re
import struct
import zipfile

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", type=Path, default=ROOT, help="Directory for the unpacked extension, XPI, and build report")
OUTPUT = parser.parse_args().output_dir.resolve()
OUTPUT.mkdir(parents=True, exist_ok=True)
upstream = json.loads((ROOT / "upstream.json").read_text(encoding="utf-8"))
data = (ROOT / "pie-original.crx").read_bytes()
if hashlib.sha256(data).hexdigest() != upstream["sha256"]:
    raise SystemExit("CRX hash mismatch. Review the upstream release before building.")
assert data[:4] == b"Cr24", "Not a CRX package"
version = struct.unpack_from("<I", data, 4)[0]
assert version == 3, f"Unsupported CRX version: {version}"
offset = 12 + struct.unpack_from("<I", data, 8)[0]
source = zipfile.ZipFile(io.BytesIO(data[offset:]))
out = OUTPUT / "firefox"
out.mkdir(exist_ok=True)
files = {}
for entry in source.infolist():
    if entry.is_dir() or entry.filename.startswith("_metadata/"):
        continue
    assert (out / entry.filename).resolve().is_relative_to(out.resolve())
    files[entry.filename] = source.read(entry)

manifest = json.loads(files["manifest.json"])
assert manifest["version"] == "1.33.9", "Review compatibility patches for new Pie releases"
for key in ("key", "update_url", "externally_connectable"):
    manifest.pop(key, None)
manifest["name"] = "Pie Adblock (unofficial Firefox port)"
manifest["background"] = {"scripts": ["firefox-compat.js", "background.js"]}
manifest["permissions"].remove("offscreen")
manifest["browser_specific_settings"] = {
    "gecko": {"id": "pie-adblock-local-port@local.invalid", "strict_min_version": "140.0"}
}
for resource in manifest["web_accessible_resources"]:
    resource.pop("use_dynamic_url", None)
    resource["resources"] = [name.lstrip("/") for name in resource["resources"]]
files["manifest.json"] = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
files["firefox-compat.js"] = (ROOT / "firefox-compat.js").read_bytes()

# Firefox's localization keys are case-insensitive. Keep the first spelling.
locale_duplicates = []
for name in list(files):
    if name.startswith("_locales/") and name.endswith("/messages.json"):
        messages = json.loads(files[name])
        seen = set()
        clean = {}
        for key, value in messages.items():
            if key.lower() in seen:
                locale_duplicates.append({"file": name, "key": key})
                continue
            seen.add(key.lower())
            clean[key] = value
        files[name] = json.dumps(clean, ensure_ascii=False).encode("utf-8")

# Use Firefox's promise-based API for the offscreen message replies.
offscreen = files["offscreen.js"].decode("utf-8")
assert offscreen.count("const n=chrome||browser;") == 1
files["offscreen.js"] = offscreen.replace("const n=chrome||browser;", "const n=browser;").encode("utf-8")

omitted = []
for resource in manifest["declarative_net_request"]["rule_resources"]:
    path = resource["path"]
    rules = json.loads(files[path])
    supported = []
    for rule in rules:
        if "responseHeaders" in rule["condition"]:
            omitted.append({"file": path, "rule": rule, "reason": "Firefox does not support DNR response-header conditions"})
        else:
            supported.append(rule)
    if len(supported) != len(rules):
        files[path] = json.dumps(supported, separators=(",", ":")).encode("utf-8")

# The OISD list contains only domain blocks. Group equivalent domains into
# requestDomains arrays to fit Firefox's static-rule budget without truncation.
primary = manifest["declarative_net_request"]["rule_resources"][0]
rules = json.loads(files[primary["path"]])
domains = []
for rule in rules:
    assert rule["action"] == {"type": "block"} and rule["priority"] == 1
    assert set(rule["condition"]) == {"urlFilter", "isUrlFilterCaseSensitive"}
    assert rule["condition"]["isUrlFilterCaseSensitive"] is False
    match = re.fullmatch(r"\|\|([a-z0-9_.-]+)\^", rule["condition"]["urlFilter"])
    assert match, "New OISD syntax needs review"
    domains.append(match.group(1))
grouped = [{"id": index + 1, "priority": 1, "action": {"type": "block"},
            "condition": {"requestDomains": domains[start:start + 1000]}}
           for index, start in enumerate(range(0, len(domains), 1000))]
files[primary["path"]] = json.dumps(grouped, separators=(",", ":")).encode("utf-8")
files["manifest.json"] = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")

# A URL helper in the Chrome bundle mistakes about:blank for a bare hostname.
background = files["background.js"].decode("utf-8")
needle = 'if(o){const e=o.includes("://")?o:`https://${o}`'
assert background.count(needle) == 1
background = background.replace(needle, 'if(o&&!/^(?:about|moz-extension|chrome|resource|file|data):/.test(o)){const e=o.includes("://")?o:`https://${o}`')
files["background.js"] = background.encode("utf-8")

for name, content in files.items():
    path = out / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

archive = OUTPUT / "pie-firefox-1.33.9-unsigned.xpi"
temporary_archive = archive.with_suffix(".xpi.tmp")
with zipfile.ZipFile(temporary_archive, "w", zipfile.ZIP_DEFLATED) as package:
    for name, content in sorted(files.items()):
        entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        entry.create_system = 3
        entry.external_attr = 0o100644 << 16
        entry.compress_type = zipfile.ZIP_DEFLATED
        package.writestr(entry, content, compresslevel=9)
try:
    temporary_archive.replace(archive)
except OSError as error:
    raise SystemExit("Could not replace the XPI. If it is loaded in a browser, use --output-dir with a different folder.") from error
report = {
    "upstream_version": manifest["version"],
    "crx_sha256": hashlib.sha256(data).hexdigest(),
    "xpi_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "omitted_rules": omitted,
    "locale_duplicates_removed": locale_duplicates,
    "oisd_domains_preserved": len(domains),
    "oisd_grouped_rules": len(grouped),
    "file_count": len(files),
}
(OUTPUT / "build-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Built {archive.name}: {len(files)} files; omitted {len(omitted)} unsupported rule(s)")
