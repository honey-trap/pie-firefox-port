"""Check repeatable packaging and preservation of the upstream domain list."""
from pathlib import Path
import hashlib
import io
import json
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
upstream = json.loads((ROOT / "upstream.json").read_text(encoding="utf-8"))
output = ROOT / "review-artifacts" / "verification"
archive = output / f"pie-firefox-{upstream['version']}-unsigned.xpi"

for attempt in range(2):
    subprocess.run([sys.executable, str(ROOT / "build.py"), "--output-dir", str(output)], check=True)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if attempt == 0:
        first_digest = digest
    elif digest != first_digest:
        raise SystemExit("Repeated builds produced different package bytes.")

crx = (ROOT / "pie-original.crx").read_bytes()
offset = 12 + struct.unpack_from("<I", crx, 8)[0]
with zipfile.ZipFile(io.BytesIO(crx[offset:])) as original, zipfile.ZipFile(archive) as built:
    rule_path = "adblock-rulesets/chrome-only/default-oisd-big.json"
    original_rules = json.loads(original.read(rule_path))
    grouped_rules = json.loads(built.read(rule_path))
    original_domains = [rule["condition"]["urlFilter"][2:-1] for rule in original_rules]
    built_domains = [domain for rule in grouped_rules for domain in rule["condition"]["requestDomains"]]
    if original_domains != built_domains:
        raise SystemExit("The output domain list differs from the upstream list.")

    manifest = json.loads(built.read("manifest.json"))
    count = 0
    for entry in manifest["declarative_net_request"]["rule_resources"]:
        rules = json.loads(built.read(entry["path"]))
        count += len(rules)
        if len({rule["id"] for rule in rules}) != len(rules):
            raise SystemExit(f"Duplicate rule IDs in {entry['path']}")
        if any("responseHeaders" in rule["condition"] for rule in rules):
            raise SystemExit("An unsupported response-header condition remains.")
    if count > 30000:
        raise SystemExit(f"Static rules exceed the verified Firefox budget: {count}")

    # Keep bundled attribution intact while changing the surrounding extension.
    notices = [name for name in original.namelist() if name.endswith(".LICENSE.txt")]
    for name in notices:
        if original.read(name) != built.read(name):
            raise SystemExit(f"Upstream license notice changed: {name}")

print(f"Verified: deterministic XPI; {len(built_domains):,} domains; {count:,} static rules; {len(notices)} unchanged notices.")
print(f"SHA-256: {digest}")
