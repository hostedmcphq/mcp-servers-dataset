#!/usr/bin/env python3
"""Public dataset export (docs/06 §1, ADR-41 sibling): indexable servers, skills and plugins of production D1, each row
with its hostedmcp.org page, MIT (owner 21 Nov 2026: the rows come from public projects, so the most permissive
license; it covers HostedMCP's own work, each project keeps its own license). Writes two copies of the same rows:

  --github DIR   the GitHub repo (github.com/hostedmcphq/mcp-servers-dataset): data/*.json (a JSON array, one row a line, so
                 weekly diffs stay readable) and README.md
  --hf DIR       the Hugging Face dataset (huggingface.co/datasets/hostedmcp/mcp-servers-dataset): data/*.jsonl and a
                 README.md with the dataset card metadata, so the viewer shows three configs

    python3 tool/dataset/export.py --github ~/Documents/mcp-servers-dataset --hf /tmp/hf-dataset

Reads D1 over the REST API with tool/backup.py's client (1,000 rows a page by rowid, one request a second), not with
wrangler, so it runs from launchd without access to ~/Documents and keeps D1 free for pages. Only facts and HostedMCP's
own summaries; README and SKILL.md text belongs to its authors and is never included. Never prints the token.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from backup import D1, read_config  # noqa: E402  (tool/backup.py; copied next to this file in the dataset repo)

SITE = "https://hostedmcp.org"
HF_REPO = "hostedmcp/mcp-servers-dataset"
GITHUB_REPO = "hostedmcphq/mcp-servers-dataset"
PAGE = 1000


def primary(kind: str, alias: str) -> str:
    return (
        f"(select c.slug from listing_categories lc join categories c on c.id = lc.category_id "
        f"where lc.listing_type = '{kind}' and lc.listing_id = {alias}.id order by lc.is_primary desc, lc.confidence desc limit 1)"
    )


def paged(db: D1, select: str, table: str, where: str) -> list[dict]:
    """Every matching row, by rowid: no OFFSET scans, one page a second. Callers write `+x.status` and `+x.indexable`
    (unary plus): otherwise SQLite walks the *_quality index and sorts every matching row for each page (EXPLAIN,
    28 Nov 2026), instead of reading the table once along the rowid."""
    rows: list[dict] = []
    after = -(2**63)
    while True:
        page = db.query(f"select x.rowid r, {select} from {table} x where x.rowid > ?1 and {where} order by x.rowid limit {PAGE}", [after])
        rows += page
        if len(page) < PAGE:
            return rows
        after = page[-1]["r"]


def day(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d") if ms else None


def loads(s, fallback):
    try:
        return json.loads(s) if s else fallback
    except ValueError:
        return fallback


def by_quality(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (-r["quality_score"], -r["stars"], r["id"]))


def export(db: D1) -> tuple[list[dict], list[dict], list[dict]]:
    servers = by_quality(paged(db, f"""x.id, x.slug_owner o, x.slug_name n, x.display_name, x.registry_name, x.repo_url, x.summary_en, {primary("server", "x")} category,
        x.transport_local, x.transport_remote, x.auth_type, x.languages, x.license, x.stars, x.downloads_30d, x.tools_count, x.is_official,
        x.is_verified, x.scan_score, x.last_commit_at, x.updated_at, x.quality_score""", "servers", "+x.indexable = 1 and +x.status = 'active' and x.canonical_id is null"))
    skills = by_quality(paged(db, f"""x.id, x.slug_owner o, x.slug_name n, x.name, x.repo_url, x.path, x.summary_en, {primary("skill", "x")} category, x.license,
        x.stars, x.allowed_tools, x.is_official, x.is_verified, x.scan_score, x.last_commit_at, x.updated_at, x.quality_score""",
        "skills", "+x.indexable = 1 and +x.status = 'active' and x.canonical_id is null"))
    plugins = by_quality(paged(db, """x.id, x.slug_owner o, x.slug_name n, x.name, x.marketplace_repo, x.marketplace_name, x.summary_en, x.category, x.license,
        x.stars, x.version, x.updated_at, x.quality_score""", "plugins", "+x.indexable = 1 and +x.status = 'active'"))

    def checks_url(kind, r):
        return None if r["scan_score"] is None else f"{SITE}/{kind}/{r['o']}/{r['n']}/checks"

    s_out = [{
        "name": r["display_name"], "url": f"{SITE}/servers/{r['o']}/{r['n']}", "repo": r["repo_url"], "registry_name": r["registry_name"],
        "summary": r["summary_en"], "category": r["category"],
        "transport": [t for t, on in (("stdio", r["transport_local"]), ("remote", r["transport_remote"])) if on],
        "auth": r["auth_type"], "languages": loads(r["languages"], []), "license": r["license"], "stars": r["stars"],
        "downloads_30d": r["downloads_30d"], "tools": r["tools_count"], "official": r["is_official"] == 1, "verified": r["is_verified"] == 1,
        "checks_score": r["scan_score"], "checks_url": checks_url("servers", r), "last_commit": day(r["last_commit_at"]), "updated": day(r["updated_at"]),
    } for r in servers]
    k_out = [{
        "name": r["name"], "url": f"{SITE}/skills/{r['o']}/{r['n']}", "repo": r["repo_url"], "path": r["path"], "summary": r["summary_en"],
        "category": r["category"], "license": r["license"], "stars": r["stars"], "allowed_tools": loads(r["allowed_tools"], None),
        "official": r["is_official"] == 1, "verified": r["is_verified"] == 1, "checks_score": r["scan_score"], "checks_url": checks_url("skills", r),
        "last_commit": day(r["last_commit_at"]), "updated": day(r["updated_at"]),
    } for r in skills]
    p_out = [{
        "name": r["name"], "url": f"{SITE}/plugins/{r['o']}/{r['n']}", "marketplace": r["marketplace_name"],
        "marketplace_repo": f"https://github.com/{r['marketplace_repo']}", "summary": r["summary_en"], "category": r["category"],
        "license": r["license"], "stars": r["stars"], "version": r["version"], "updated": day(r["updated_at"]),
    } for r in plugins]
    return s_out, k_out, p_out


def n(x: int) -> str:
    return f"{x:,}"


def card(servers, skills, plugins, today: str, hf: bool) -> str:
    """README for both copies; every number is counted from the rows written next to it (ADR-11)."""
    ext = "jsonl" if hf else "json"
    remote = sum(1 for s in servers if "remote" in s["transport"])
    verified = sum(1 for s in servers if s["verified"])
    official = sum(1 for s in servers if s["official"])
    cats = Counter(s["category"] for s in servers if s["category"]).most_common(12)
    starred = sorted(servers, key=lambda s: -s["stars"])[:15]
    cell = lambda t: t.replace("|", "\\|")  # noqa: E731
    other = (f"Also on GitHub: [{GITHUB_REPO}](https://github.com/{GITHUB_REPO}) (the same rows as JSON arrays)." if hf
             else f"Also on Hugging Face: [{HF_REPO}](https://huggingface.co/datasets/{HF_REPO}) (the same rows as JSON Lines, with a viewer).")
    load = (f"""```python
from datasets import load_dataset
servers = load_dataset("{HF_REPO}", "servers", split="train")
remote_oauth = servers.filter(lambda s: "remote" in s["transport"] and s["auth"] == "oauth")
```""" if hf else f"""```python
import json, urllib.request
url = "https://raw.githubusercontent.com/{GITHUB_REPO}/main/data/servers.json"
servers = json.load(urllib.request.urlopen(url))
remote_oauth = [s for s in servers if "remote" in s["transport"] and s["auth"] == "oauth"]
```

```bash
jq '[.[] | select(.verified and .category == "databases")] | length' data/servers.json
```""")
    meta = f"""---
license: mit
pretty_name: MCP servers, agent skills and Claude Code plugins
language:
- en
tags:
- mcp
- model-context-protocol
- agent-skills
- claude-code
- ai-agents
- llm-tools
size_categories:
- 10K<n<100K
configs:
- config_name: servers
  data_files: data/servers.jsonl
  default: true
- config_name: skills
  data_files: data/skills.jsonl
- config_name: plugins
  data_files: data/plugins.jsonl
---

""" if hf else ""
    return f"""{meta}# MCP servers dataset

An open dataset of **{n(len(servers))} MCP servers**, **{n(len(skills))} agent skills** and **{n(len(plugins))} Claude Code plugins**, with automated security checks, exported from [HostedMCP]({SITE}) on {today}.

Every row links to its page on [hostedmcp.org]({SITE}), where you find the install config for Claude Code, Cursor, VS Code, Codex and other clients, and the full checks report. {other}

| File | Rows | What |
|---|---|---|
| `data/servers.{ext}` | {n(len(servers))} | [MCP servers]({SITE}/servers) from the MCP Registry, GitHub, npm and PyPI |
| `data/skills.{ext}` | {n(len(skills))} | [Agent Skills]({SITE}/skills) (folders with a SKILL.md) from public GitHub repositories |
| `data/plugins.{ext}` | {n(len(plugins))} | [Claude Code plugins]({SITE}/plugins) from public marketplaces |

Only listings that pass HostedMCP's quality bar are included (an indexable page: enriched, with enough content, not a duplicate). The full catalog tracks more; the monthly [State of MCP]({SITE}/learn/state-of-mcp) report has numbers on the whole ecosystem, month by month.

## At a glance

- {n(official)} servers are published by the vendor of the product (`official`).
- {n(verified)} servers are Verified: automated checks score 80 or more, at least 60 points checked, public repository, no high-severity finding. [How the checks work]({SITE}/about/verification), and the [MCP security report]({SITE}/reports/mcp-security).
- {n(remote)} servers ({round(100 * remote / max(1, len(servers)))}%) can be used remotely over HTTP. Browse them at [hostedmcp.org/remote]({SITE}/remote).

Servers by category:

| Category | Servers |
|---|---|
""" + "\n".join(f"| [{c}]({SITE}/categories/{c}) | {n(k)} |" for c, k in cats) + """

Most starred:

| Server | Stars | Category |
|---|---|---|
""" + "\n".join(f"| [{cell(s['name'])}]({s['url']}) | {n(s['stars'])} | {s['category'] or ''} |" for s in starred) + f"""

## Fields

**servers**: `name`, `url` (HostedMCP page), `repo`, `registry_name` (MCP Registry), `summary`, `category`, `transport` (`stdio`, `remote`), `auth` (`none`, `api_key`, `oauth`, `mixed`, `unknown`), `languages`, `license`, `stars`, `downloads_30d` (npm and PyPI), `tools`, `official`, `verified`, `checks_score` (0–100, null before the first scan), `checks_url`, `last_commit`, `updated`.

**skills**: `name`, `url`, `repo`, `path` (folder in the repo), `summary`, `category`, `license`, `stars` (of the repository), `allowed_tools` (pre-approved tools from SKILL.md), `official`, `verified`, `checks_score`, `checks_url`, `last_commit`, `updated`.

**plugins**: `name`, `url`, `marketplace`, `marketplace_repo`, `summary`, `category`, `license`, `stars`, `version`, `updated`.

Summaries are written by HostedMCP. READMEs and SKILL.md files are not included: they belong to their authors, so follow `repo` for them. Dates are UTC.

## Use it

{load}

For live queries there is a free read-only [REST API]({SITE}/developers) and an MCP server: `claude mcp add --transport http hostedmcp https://api.hostedmcp.org/mcp`. Maintainers can show their checks score with a [README badge]({SITE}/badges).

## Updates

Exported every week. Stars, scores and dates are as of the export date. Spotted a wrong row? Open an issue on [GitHub](https://github.com/{GITHUB_REPO}/issues), or use the claim and takedown links on the listing's page.

## License and citation

Data: MIT (see `LICENSE`). It covers what HostedMCP adds: the summaries, categories, checks scores and the compilation. Names, links, stars and other facts come from GitHub, the MCP Registry, npm and PyPI; each project keeps its own license (the `license` field), and no project code or README text is part of this dataset. A link to hostedmcp.org is welcome when you publish something built on it, but not required.

Credit line, ready to paste: `Data: HostedMCP (https://hostedmcp.org)`. Or a badge:

```markdown
[![Data: HostedMCP](https://img.shields.io/badge/data-HostedMCP-2563eb)](https://hostedmcp.org)
```

```bibtex
@misc{{hostedmcp_mcp_servers_dataset,
  title  = {{MCP servers dataset}},
  author = {{HostedMCP}},
  year   = {{{today[:4]}}},
  url    = {{{SITE}}},
  note   = {{Exported {today}, https://huggingface.co/datasets/{HF_REPO}}}
}}
```
"""

MIT = """MIT License

Copyright (c) 2026 HostedMCP (hostedmcp.org)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--github")
    ap.add_argument("--hf")
    ap.add_argument("--env", default="production", choices=["production", "staging"])
    a = ap.parse_args()
    if not (a.github or a.hf):
        ap.error("give --github DIR and/or --hf DIR")
    # GitHub Actions (the dataset repo's weekly workflow) passes the read-only token as secrets; the Mac reads its files.
    if os.environ.get("CF_API_TOKEN"):
        token, account = os.environ["CF_API_TOKEN"], os.environ["CF_ACCOUNT_ID"]
    else:
        token, account = read_config()
    db = D1(token, account, {"production": "hostedmcp-main", "staging": "hostedmcp-db-staging"}[a.env])
    servers, skills, plugins = export(db)
    # A broken export (a failed query read as empty) must never replace the published files.
    if len(servers) < 1000 or len(skills) < 1000:
        raise SystemExit(f"refusing to write: only {len(servers)} servers and {len(skills)} skills")
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    for root, hf in ((a.github, False), (a.hf, True)):
        if not root:
            continue
        os.makedirs(os.path.join(root, "data"), exist_ok=True)
        for name, rows in (("servers", servers), ("skills", skills), ("plugins", plugins)):
            if hf:
                body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
                path = os.path.join(root, "data", f"{name}.jsonl")
            else:
                body = "[\n" + ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows) + "\n]\n"
                path = os.path.join(root, "data", f"{name}.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
        with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
            f.write(card(servers, skills, plugins, today, hf))
        with open(os.path.join(root, "LICENSE"), "w", encoding="utf-8") as f:
            f.write(MIT)
    print(json.dumps({"servers": len(servers), "skills": len(skills), "plugins": len(plugins), "date": today}))


if __name__ == "__main__":
    main()
