# MCP servers dataset

An open dataset of **28,475 MCP servers**, **31,415 agent skills** and **4,048 Claude Code plugins**, with automated security checks, exported from [HostedMCP](https://hostedmcp.org) on 2026-11-15.

Every row links to its page on hostedmcp.org, where you find the install config for Claude Code, Cursor, VS Code, Codex and other clients, and the full checks report.

| File | Rows | What |
|---|---|---|
| [`data/servers.json`](data/servers.json) | 28,475 | MCP servers from the MCP Registry, GitHub, npm and PyPI |
| [`data/skills.json`](data/skills.json) | 31,415 | Agent Skills (folders with a SKILL.md) from public GitHub repositories |
| [`data/plugins.json`](data/plugins.json) | 4,048 | Claude Code plugins from public marketplaces |

Only listings that pass HostedMCP's quality bar are included (an indexable page: enriched, with enough content, not a duplicate). The full catalog tracks more; see [the State of MCP report](https://hostedmcp.org/learn/state-of-mcp-november-2026) for numbers on the whole ecosystem.

## At a glance

- 651 servers are published by the vendor of the product (`official`).
- 12,305 servers are Verified: automated checks score 80 or more, at least 60 points checked, public repository, no high-severity finding. [How the checks work](https://hostedmcp.org/about/verification).
- 8,935 servers (31%) can be used remotely over HTTP.

Servers by category:

| Category | Servers |
|---|---|
| [developer-tools](https://hostedmcp.org/categories/developer-tools) | 7,067 |
| [automation](https://hostedmcp.org/categories/automation) | 4,352 |
| [productivity](https://hostedmcp.org/categories/productivity) | 3,835 |
| [search-web](https://hostedmcp.org/categories/search-web) | 2,027 |
| [finance-data](https://hostedmcp.org/categories/finance-data) | 1,918 |
| [security](https://hostedmcp.org/categories/security) | 1,621 |
| [ai-models](https://hostedmcp.org/categories/ai-models) | 941 |
| [devops-infra](https://hostedmcp.org/categories/devops-infra) | 795 |
| [docs-knowledge](https://hostedmcp.org/categories/docs-knowledge) | 748 |
| [communication](https://hostedmcp.org/categories/communication) | 685 |
| [crm-marketing](https://hostedmcp.org/categories/crm-marketing) | 579 |
| [browser-automation](https://hostedmcp.org/categories/browser-automation) | 559 |

Most starred:

| Server | Stars | Category |
|---|---|---|
| [REA](https://hostedmcp.org/servers/morluto/rea) | 458,434 | developer-tools |
| [browser-use](https://hostedmcp.org/servers/browser-use/browser-use) | 121,037 | browser-automation |
| [labelhead-artist-momentum](https://hostedmcp.org/servers/paperclipai/paperclip) | 113,790 | automation |
| [gemini-cli](https://hostedmcp.org/servers/google-gemini/gemini-cli) | 108,832 | developer-tools |
| [Scrapling MCP Server](https://hostedmcp.org/servers/d4vinci/scrapling) | 102,447 | browser-automation |
| [servers](https://hostedmcp.org/servers/modelcontextprotocol/servers) | 91,976 | developer-tools |
| [World Monitor](https://hostedmcp.org/servers/koala73/worldmonitor) | 90,647 | search-web |
| [claude-flow](https://hostedmcp.org/servers/ruvnet/claude-flow) | 81,672 | developer-tools |
| [Ruflo](https://hostedmcp.org/servers/ruvnet/ruflo-f29fbc) | 81,672 | developer-tools |
| [ruflo](https://hostedmcp.org/servers/ruvnet/ruflo) | 81,672 | ai-models |
| [Netdata](https://hostedmcp.org/servers/netdata/mcp-server) | 81,408 | monitoring |
| [headroom](https://hostedmcp.org/servers/headroomlabs-ai/headroom) | 79,660 | developer-tools |
| [Context7](https://hostedmcp.org/servers/upstash/context7) | 64,810 | docs-knowledge |
| [TrendRadar](https://hostedmcp.org/servers/sansan0/trendradar) | 63,636 | search-web |
| [Chrome DevTools MCP](https://hostedmcp.org/servers/chromedevtools/chrome-devtools-mcp-432e39) | 55,795 | browser-automation |

## Fields

**servers.json**: `name`, `url` (HostedMCP page), `repo`, `registry_name` (MCP Registry), `summary`, `category`, `transport` (`stdio`, `remote`), `auth` (`none`, `api_key`, `oauth`, `unknown`), `languages`, `license`, `stars`, `downloads_30d` (npm and PyPI), `tools`, `official`, `verified`, `checks_score` (0–100, null before the first scan), `checks_url`, `last_commit`, `updated`.

**skills.json**: `name`, `url`, `repo`, `path` (folder in the repo), `summary`, `category`, `license`, `stars` (of the repository), `allowed_tools` (pre-approved tools from SKILL.md), `official`, `verified`, `checks_score`, `checks_url`, `last_commit`, `updated`.

**plugins.json**: `name`, `url`, `marketplace`, `marketplace_repo`, `summary`, `category`, `license`, `stars`, `version`, `updated`.

Summaries are written by HostedMCP. READMEs and SKILL.md files are not included: they belong to their authors, so follow `repo` for them. Dates are UTC.

## Use it

```python
import json, urllib.request
url = "https://raw.githubusercontent.com/hostedmcphq/mcp-servers-dataset/main/data/servers.json"
servers = json.load(urllib.request.urlopen(url))
remote_oauth = [s for s in servers if "remote" in s["transport"] and s["auth"] == "oauth"]
```

```bash
jq '[.[] | select(.verified and .category == "databases")] | length' data/servers.json
```

For live queries, HostedMCP also runs a read-only MCP server: `claude mcp add --transport http hostedmcp https://api.hostedmcp.org/mcp`.

## Updates

Exported weekly. Stars, scores and dates are as of the export date. Spotted a wrong row? Open an issue here, or use the claim and takedown links on the listing's page.

## License

Data: [CC BY 4.0](LICENSE). Credit "HostedMCP (hostedmcp.org)" with a link when you publish anything built on it.
