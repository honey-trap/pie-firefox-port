"""Smoke test using a dedicated, disposable Firefox profile."""
from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
(ROOT / "tools").mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "tools/python"))
from marionette_driver.marionette import Marionette
from marionette_driver.addons import Addons

profile = Path(tempfile.mkdtemp(prefix="firefox-test-", dir=ROOT / "tools"))
(profile / "user.js").write_text('user_pref("marionette.port", 2829);\nuser_pref("browser.shell.checkDefaultBrowser", false);\nuser_pref("browser.aboutwelcome.enabled", false);\nuser_pref("browser.startup.homepage_override.mstone", "ignore");\nuser_pref("extensions.dnr.feedback", true);\n', encoding="utf-8")
binary = Path(os.environ.get("FIREFOX_BINARY", str(ROOT / "tools/firefox/core/firefox.exe")))
if not binary.is_file():
    raise SystemExit("Set FIREFOX_BINARY to the Firefox executable before running this test.")
log = open(ROOT / "firefox-test.log", "w", encoding="utf-8")
proc = subprocess.Popen([str(binary), "-headless", "-no-remote", "-profile", str(profile), "--marionette"], env={**os.environ, "MOZ_REMOTE_ALLOW_SYSTEM_ACCESS": "1"}, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
m = None
report = {"profile": str(profile)}
try:
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError(f"Firefox exited during startup: {proc.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", 2829), timeout=0.2):
                break
        except OSError:
            time.sleep(0.2)
    else:
        raise RuntimeError("Firefox did not start Marionette within 20 seconds")
    m = Marionette(host="127.0.0.1", port=2829)
    report["session"] = m.start_session({"pageLoadStrategy":"eager"})
    m.timeout.script = 60
    m.timeout.page_load = 25
    addon_id = Addons(m).install(str(ROOT / "pie-firefox-1.33.9-unsigned.xpi"), temp=True)
    report["installed"] = addon_id
    print("Installed", flush=True)
    time.sleep(8)
    m.set_context("chrome")
    report["extension"] = m.execute_script('''
      const p = WebExtensionPolicy.getByID(arguments[0]);
      return {url: p.getURL(""), active: p.active, errors: p.extension.errors, warnings: p.extension.warnings};
    ''', script_args=[addon_id])
    print("Background active", flush=True)
    report["console"] = m.execute_script('''return Services.console.getMessageArray().map(m => m.message).filter(s => /moz-extension:/.test(s)).slice(-30);''')
    m.set_context("content")
    m.navigate(report["extension"]["url"] + "popover.html")
    print("Popup loaded", flush=True)
    time.sleep(3)
    report["page"] = m.execute_script('return {url:location.href,title: document.title, text: document.body.innerText.slice(0,3000), api: typeof browser, chrome: typeof chrome};', sandbox=None)
    report["api"] = m.execute_async_script('''
      const done = arguments[arguments.length-1];
      Promise.all([browser.declarativeNetRequest.getEnabledRulesets(), browser.scripting.getRegisteredContentScripts(), browser.storage.local.get(null)]).then(([rules,scripts,storage]) => done({rules,scripts,storageKeys:Object.keys(storage)})).catch(e => done({error:String(e)}));
    ''', sandbox=None)
    rules = json.loads((ROOT / "firefox/adblock-rulesets/chrome-only/default-oisd-big.json").read_text())
    domains = [r["condition"]["requestDomains"][-1] for r in rules]
    report["blocking"] = m.execute_async_script('''
      const domains = arguments[0], done = arguments[arguments.length-1];
      (async () => {
        const samples = [];
        for (const domain of domains) {
          const result = await browser.declarativeNetRequest.testMatchOutcome({url:"https://"+domain+"/test.js", type:"script", initiator:"https://example.org"});
          samples.push({domain, blocked:result.matchedRules.some(r => r.rulesetId === "default")});
        }
        const control = await browser.declarativeNetRequest.testMatchOutcome({url:"https://example.org/clean.js",type:"script",initiator:"https://example.org"});
        const subdomain = await browser.declarativeNetRequest.testMatchOutcome({url:"https://sub."+domains.at(-1)+"/test.js",type:"script",initiator:"https://example.org"});
        const suffix = await browser.declarativeNetRequest.testMatchOutcome({url:"https://"+domains.at(-1)+".example.org/test.js",type:"script",initiator:"https://example.org"});
        return {samplesTested:samples.length, failures:samples.filter(s=>!s.blocked), control, subdomain, suffix, availableRules:await browser.declarativeNetRequest.getAvailableStaticRuleCount()};
      })().then(done).catch(e=>done({error:String(e)}));
    ''', script_args=[domains], sandbox=None)
    print("Rule matching checked", flush=True)
    print("Checking offscreen messaging", flush=True)
    report["offscreen"] = m.execute_async_script('''
      const done = arguments[arguments.length-1];
      (async () => {
        const bg = await browser.runtime.getBackgroundPage();
        await bg.chrome.offscreen.createDocument({url:browser.runtime.getURL("offscreen.html")});
        const result = await browser.runtime.sendMessage({target:"offscreen",name:"offscreen:tag",payload:{url:"about:blank"}});
        return {contexts:await bg.chrome.runtime.getContexts({contextTypes:["OFFSCREEN_DOCUMENT"]}), replied:result===null};
      })().then(done).catch(e=>done({error:String(e)}));
    ''', sandbox=None)
    report["settings"] = m.execute_async_script('''
      const done = arguments[arguments.length-1];
      browser.runtime.sendMessage({name:"adblock:action:getSettings",payload:{}}).then(s=>done({received:!!s, keys:Object.keys(s||{})})).catch(e=>done({error:String(e)}));
    ''', sandbox=None)
    assert len(report["api"]["rules"]) == 7, report["api"]
    assert "error" not in report["blocking"], report["blocking"]
    assert not report["blocking"]["failures"], report["blocking"]
    assert not report["blocking"]["control"]["matchedRules"], report["blocking"]
    assert not report["blocking"]["suffix"]["matchedRules"], report["blocking"]
    assert any(r["rulesetId"] == "default" for r in report["blocking"]["subdomain"]["matchedRules"])
    assert report["offscreen"].get("replied"), report["offscreen"]
    assert report["settings"].get("received"), report["settings"]
    report["passed"] = True
finally:
    (ROOT / "firefox-test-report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ["console", "session"]}, indent=2, default=str))
    if m:
        try: m.quit()
        except Exception: pass
    if proc.poll() is None:
        proc.terminate()
    log.close()
