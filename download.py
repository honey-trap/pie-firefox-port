"""Fetch the upstream CRX from Google and require the reviewed package hash."""
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
upstream = json.loads((ROOT / "upstream.json").read_text(encoding="utf-8"))
destination = ROOT / "pie-original.crx"
if destination.exists():
    data = destination.read_bytes()
    if hashlib.sha256(data).hexdigest() != upstream["sha256"]:
        raise SystemExit("Existing CRX differs from the reviewed package. It was not overwritten.")
    print("Reviewed upstream package already present.")
else:
    request = urllib.request.Request(upstream["download_url"], headers={"User-Agent": "PieFirefoxPort/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(30 * 1024 * 1024 + 1)
    if len(data) > 30 * 1024 * 1024:
        raise SystemExit("Download exceeds the expected package size limit.")
    if hashlib.sha256(data).hexdigest() != upstream["sha256"]:
        raise SystemExit(
            "Google returned a different package, possibly a newer release. "
            "Nothing was saved. Review the new release before updating upstream.json."
        )
    # Exclusive creation avoids overwriting a file created during the download.
    with destination.open("xb") as output:
        output.write(data)
    print(f"Saved and verified Pie {upstream['version']}.")
