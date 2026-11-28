# MCP servers dataset

An open dataset of **32,561 MCP servers**, **66,434 agent skills** and **5,982 Claude Code plugins**, with automated security checks, exported from [HostedMCP](https://hostedmcp.org) on 2026-11-28.

Every row links to its page on [hostedmcp.org](https://hostedmcp.org), where you find the install config for Claude Code, Cursor, VS Code, Codex and other clients, and the full checks report. Also on Hugging Face: [hostedmcp/mcp-servers-dataset](https://huggingface.co/datasets/hostedmcp/mcp-servers-dataset) (the same rows as JSON Lines, with a viewer).

| File | Rows | What |
|---|---|---|
| `data/servers.json` | 32,561 | [MCP servers](https://hostedmcp.org/servers) from the MCP Registry, GitHub, npm and PyPI |
| `data/skills.json` | 66,434 | [Agent Skills](https://hostedmcp.org/skills) (folders with a SKILL.md) from public GitHub repositories |
| `data/plugins.json` | 5,982 | [Claude Code plugins](https://hostedmcp.org/plugins) from public marketplaces |

Only listings that pass HostedMCP's quality bar are included (an indexable page: enriched, with enough content, not a duplicate). The full catalog tracks more; the monthly [State of MCP](https://hostedmcp.org/learn/state-of-mcp) report has numbers on the whole ecosystem, month by month.

## At a glance

- 776 servers are published by the vendor of the product (`official`).
- 13,049 servers are Verified: automated checks score 80 or more, at least 60 points checked, public repository, no high-severity finding. [How the checks work](https://hostedmcp.org/about/verification), and the [MCP security report](https://hostedmcp.org/reports/mcp-security).
- 10,540 servers (32%) can be used remotely over HTTP. Browse them at [hostedmcp.org/remote](https://hostedmcp.org/remote).

Servers by category:

| Category | Servers |
|---|---|
| [developer-tools](https://hostedmcp.org/categories/developer-tools) | 7,826 |
| [automation](https://hostedmcp.org/categories/automation) | 4,827 |
| [productivity](https://hostedmcp.org/categories/productivity) | 4,288 |
| [search-web](https://hostedmcp.org/categories/search-web) | 2,426 |
| [finance-data](https://hostedmcp.org/categories/finance-data) | 2,287 |
| [security](https://hostedmcp.org/categories/security) | 1,853 |
| [ai-models](https://hostedmcp.org/categories/ai-models) | 1,101 |
| [docs-knowledge](https://hostedmcp.org/categories/docs-knowledge) | 899 |
| [devops-infra](https://hostedmcp.org/categories/devops-infra) | 869 |
| [communication](https://hostedmcp.org/categories/communication) | 791 |
| [crm-marketing](https://hostedmcp.org/categories/crm-marketing) | 677 |
| [browser-automation](https://hostedmcp.org/categories/browser-automation) | 660 |

Most starred:

| Server | Stars | Category |
|---|---|---|
| [REA](https://hostedmcp.org/servers/morluto/rea) | 480,333 | developer-tools |
| [browser-use](https://hostedmcp.org/servers/browser-use/browser-use) | 122,186 | browser-automation |
| [labelhead-artist-momentum](https://hostedmcp.org/servers/paperclipai/paperclip) | 117,461 | automation |
| [gemini-cli](https://hostedmcp.org/servers/google-gemini/gemini-cli) | 109,219 | developer-tools |
| [Scrapling MCP Server](https://hostedmcp.org/servers/d4vinci/scrapling) | 106,116 | browser-automation |
| [Time](https://hostedmcp.org/servers/modelcontextprotocol/time) | 92,292 | developer-tools |
| [Git](https://hostedmcp.org/servers/modelcontextprotocol/git) | 92,292 | version-control |
| [Memory](https://hostedmcp.org/servers/modelcontextprotocol/memory) | 92,292 | vector-memory |
| [Fetch](https://hostedmcp.org/servers/modelcontextprotocol/fetch) | 92,292 | browser-automation |
| [Sequential Thinking](https://hostedmcp.org/servers/modelcontextprotocol/sequential-thinking) | 92,292 | ai-models |
| [Filesystem](https://hostedmcp.org/servers/modelcontextprotocol/filesystem) | 92,292 | filesystem |
| [Everything](https://hostedmcp.org/servers/modelcontextprotocol/everything) | 92,292 | developer-tools |
| [servers](https://hostedmcp.org/servers/modelcontextprotocol/servers) | 92,292 | developer-tools |
| [World Monitor](https://hostedmcp.org/servers/koala73/worldmonitor) | 91,243 | search-web |
| [HyperFrames by HeyGen](https://hostedmcp.org/servers/heygen-com/hyperframes) | 91,130 | automation |

## Fields

**servers**: `name`, `url` (HostedMCP page), `repo`, `registry_name` (MCP Registry), `summary`, `category`, `transport` (`stdio`, `remote`), `auth` (`none`, `api_key`, `oauth`, `mixed`, `unknown`), `languages`, `license`, `stars`, `downloads_30d` (npm and PyPI), `tools`, `official`, `verified`, `checks_score` (0–100, null before the first scan), `checks_url`, `last_commit`, `updated`.

**skills**: `name`, `url`, `repo`, `path` (folder in the repo), `summary`, `category`, `license`, `stars` (of the repository), `allowed_tools` (pre-approved tools from SKILL.md), `official`, `verified`, `checks_score`, `checks_url`, `last_commit`, `updated`.

**plugins**: `name`, `url`, `marketplace`, `marketplace_repo`, `summary`, `category`, `license`, `stars`, `version`, `updated`.

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

For live queries there is a free read-only [REST API](https://hostedmcp.org/developers) and an MCP server: `claude mcp add --transport http hostedmcp https://api.hostedmcp.org/mcp`. Maintainers can show their checks score with a [README badge](https://hostedmcp.org/badges).

## Updates

Exported every week. Stars, scores and dates are as of the export date. Spotted a wrong row? Open an issue on [GitHub](https://github.com/hostedmcphq/mcp-servers-dataset/issues), or use the claim and takedown links on the listing's page.

## License and citation

Data: MIT (see `LICENSE`). It covers what HostedMCP adds: the summaries, categories, checks scores and the compilation. Names, links, stars and other facts come from GitHub, the MCP Registry, npm and PyPI; each project keeps its own license (the `license` field), and no project code or README text is part of this dataset. A link to hostedmcp.org is welcome when you publish something built on it, but not required.

Credit line, ready to paste: `Data: HostedMCP (https://hostedmcp.org)`. Or a badge:

```markdown
[![Data: HostedMCP](https://img.shields.io/badge/data-HostedMCP-2563eb)](https://hostedmcp.org)
```

```bibtex
@misc{hostedmcp_mcp_servers_dataset,
  title  = {MCP servers dataset},
  author = {HostedMCP},
  year   = {2026},
  url    = {https://hostedmcp.org},
  note   = {Exported 2026-11-28, https://huggingface.co/datasets/hostedmcp/mcp-servers-dataset}
}
```
