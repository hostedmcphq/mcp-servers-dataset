"""Monthly Zenodo version of the public dataset (28 Nov 2026): the same data/*.json files as the GitHub copy, as a new
version of record 10.5281/zenodo.24615901 (the concept DOI, which always resolves to the newest version). Runs from the
dataset repo's weekly workflow and publishes only in the first week of a month, once: a version whose `version` already
starts with this month is left alone. Usage: python3 zenodo_upload.py DATA_DIR. The token comes from ZENODO_TOKEN (the
repo secret) or ~/.config/hostedmcp/zenodo_token, is sent in a header only and never printed."""
import datetime as dt
import json
import os
import sys
import urllib.request

API = "https://zenodo.org/api"
CONCEPT_RECID = "24615901"
FILES = ["servers.json", "skills.json", "plugins.json"]


def call(method, url, token, body=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, method=method, data=data if data is not None else (json.dumps(body).encode() if body is not None else None))
    req.add_header("Authorization", f"Bearer {token}")
    if body is not None or data is not None:
        req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req, timeout=600) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def main() -> None:
    folder = sys.argv[1]
    token = os.environ.get("ZENODO_TOKEN") or open(os.path.expanduser("~/.config/hostedmcp/zenodo_token")).read().strip()
    today = dt.date.today()
    if today.day > 7 and not os.environ.get("ZENODO_FORCE"):
        print(f"zenodo: skipped, not the first week of the month ({today})")
        return
    # The concept record resolves to the newest published version.
    with urllib.request.urlopen(f"{API}/records/{CONCEPT_RECID}", timeout=60) as r:
        latest = json.loads(r.read())
    if str(latest["metadata"].get("version", "")).startswith(today.strftime("%Y-%m")):
        print(f"zenodo: skipped, {latest['metadata']['version']} is already this month's version")
        return
    draft = call("POST", f"{API}/deposit/depositions/{latest['id']}/actions/newversion", token)
    draft = call("GET", draft["links"]["latest_draft"], token)
    for f in draft.get("files", []):
        call("DELETE", f["links"]["self"], token)
    for name in FILES:
        with open(os.path.join(folder, name), "rb") as fh:
            call("PUT", f"{draft['links']['bucket']}/{name}", token, data=fh.read(), ctype="application/octet-stream")
    meta = draft["metadata"]
    meta.update({"version": today.isoformat(), "publication_date": today.isoformat()})
    meta.pop("doi", None)
    call("PUT", draft["links"]["self"], token, body={"metadata": meta})
    done = call("POST", draft["links"]["publish"], token)
    print(f"zenodo: published {done.get('doi')} (all versions: {done.get('conceptdoi')})")


if __name__ == "__main__":
    main()
