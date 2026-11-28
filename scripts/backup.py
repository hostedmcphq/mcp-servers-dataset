#!/usr/bin/env python3
"""Full SQL dump of D1 without locking it (docs/04 §15, docs/02 §6).

  python3 tool/backup.py staging|production OUT.sql.gz

`wrangler d1 export` holds D1 in "Currently processing a long-running export" for the whole run (about 11 minutes for
production on 18 Nov 2026): page renders, RPC calls and jobs failed with that error meanwhile. This reads every table
with ordinary paged queries over the D1 REST API instead (1,000 rows a page, by rowid), so D1 keeps serving
everything else. The dump is not a snapshot: rows written while it runs may or may not be in it. D1 Time Travel
(30 days) is the exact point-in-time restore; this file is the copy outside D1.

Writes schema (CREATE TABLE), then the rows as INSERT statements, then indexes and triggers, gzipped. Left out:
SQLite and Cloudflare internal tables and the FTS index `listings_fts*` (rebuilt after a restore, docs/07 §9). The rows
of `revalidations` (Next's tag cache) are left out too; the table itself is created, empty. Restore into SQLite: `(echo 'BEGIN;'; gunzip -c OUT.sql.gz; echo 'COMMIT;') | sqlite3 restored.db` (one
transaction, or 5 million single inserts take hours). Into D1: `wrangler d1 execute <db> --remote --file OUT.sql`.

Reads the account id from ~/.config/hostedmcp/cf_ids and the token from ~/.config/hostedmcp/cf_analytics_token
(it has D1 read access). Never prints the token.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

CONFIG = os.path.expanduser("~/.config/hostedmcp")
# Production: the main database since ADR-49 (the locale databases are in the weekly D1SnapshotWorkflow copy).
DATABASES = {"staging": "hostedmcp-db-staging", "production": "hostedmcp-main"}
PAGE = 1000
SKIP_PREFIXES = ("sqlite_", "_cf_", "listings_fts")
# Tables whose rows are a cache: the table is created on restore, empty.
SCHEMA_ONLY = {"revalidations"}
# One request a second (owner, 19 Nov 2026: "backup kadang membuat web down"). D1 runs one query at a time per database,
# so a backup reading back to back leaves pages less room; at most ~3 a second is also the API's limit (1,200 per 5
# minutes per user). Slower is fine: it runs Sunday 10:30 WIB, the quietest hours (~3% of daily traffic).
MIN_INTERVAL_S = 1.0
FIRST_ROWID = -(2**63)
# A dump with fewer rows than this share of the last good one is refused, so it never replaces that backup.
MIN_SHARE_OF_LAST = 0.5
STATE = os.path.join(CONFIG, "backup-last-{env}.json")


def read_config() -> tuple[str, str]:
    token = open(os.path.join(CONFIG, "cf_analytics_token")).read().strip()
    ids = dict(line.strip().split("=", 1) for line in open(os.path.join(CONFIG, "cf_ids")) if "=" in line)
    return token, ids["ACCOUNT_ID"]


class D1:
    def __init__(self, token: str, account: str, name: str):
        self.token, self.account = token, account
        self._last = 0.0
        dbs = self._call("GET", f"/accounts/{account}/d1/database?name={name}")
        match = [d for d in dbs if d.get("name") == name]
        if not match:
            raise SystemExit(f"no D1 database named {name}")
        self.id = match[0]["uuid"]

    def _call(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4{path}",
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        for attempt in range(6):
            wait = self._last + MIN_INTERVAL_S - time.time()
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.load(r)["result"]
            except urllib.error.HTTPError as e:
                text = e.read().decode(errors="replace")
                # Busy D1 (overloaded, queued) and rate limits pass; anything else is a real error.
                if attempt < 5 and e.code == 429:
                    time.sleep(60 * (attempt + 1))
                    continue
                if attempt < 5 and (e.code in (500, 502, 503) or "overloaded" in text or "queued" in text):
                    time.sleep(6 * (attempt + 1))
                    continue
                raise SystemExit(f"D1 API {e.code}: {text[:300]}")
            except (urllib.error.URLError, TimeoutError):
                if attempt < 5:
                    time.sleep(6 * (attempt + 1))
                    continue
                raise

    def query(self, sql: str, params: list | None = None) -> list[dict]:
        result = self._call("POST", f"/accounts/{self.account}/d1/database/{self.id}/query", {"sql": sql, "params": params or []})
        return result[0]["results"]


def literal(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, list):  # a BLOB comes back as a list of byte values
        return "X'" + bytes(v).hex() + "'"
    text = str(v)
    if "\x00" in text:  # sqlite3's reader stops a string at NUL; write it as bytes cast back to text
        return "CAST(X'" + text.encode("utf-8").hex() + "' AS TEXT)"
    return "'" + text.replace("'", "''") + "'"


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def dump(db: D1, out_path: str) -> dict[str, int]:
    objects = db.query("select type, name, tbl_name, sql from sqlite_master where sql is not null order by type = 'table' desc, name")
    tables = [o for o in objects if o["type"] == "table" and not o["name"].startswith(SKIP_PREFIXES)]
    later = [o for o in objects if o["type"] in ("index", "trigger") and not o["tbl_name"].startswith(SKIP_PREFIXES)]
    counts: dict[str, int] = {}
    with gzip.open(out_path, "wt", encoding="utf-8", compresslevel=6) as f:
        # No BEGIN/COMMIT: D1 refuses them in an imported file. defer_foreign_keys lets a child table come before its
        # parent, as in `wrangler d1 export`. With sqlite3, wrap the file in BEGIN/COMMIT for speed (see the docstring).
        f.write("PRAGMA defer_foreign_keys=TRUE;\n")
        for t in tables:
            f.write(f"{t['sql']};\n")
        for t in tables:
            if t["name"] in SCHEMA_ONLY:
                continue
            name, after, n = t["name"], FIRST_ROWID, 0
            # A WITHOUT ROWID table (endpoint_uptime_daily, 19 Nov 2026) has no rowid: page it by its primary key.
            pk = [] if "without rowid" not in t["sql"].lower() else [r["name"] for r in db.query(f"select name from pragma_table_info('{name}') where pk > 0 order by pk")]
            last: list = []
            while True:
                if pk:
                    keys = ", ".join(quote(c) for c in pk)
                    where = f"where ({keys}) > ({', '.join('?' for _ in pk)}) " if last else ""
                    rows = db.query(f"select * from {quote(name)} {where}order by {keys} limit {PAGE}", last)
                else:
                    rows = db.query(f"select rowid as __rowid__, * from {quote(name)} where rowid > ?1 order by rowid limit {PAGE}", [after])
                if not rows:
                    break
                cols = [c for c in rows[0] if c != "__rowid__"]
                head = f"INSERT INTO {quote(name)} ({', '.join(quote(c) for c in cols)}) VALUES "
                for r in rows:
                    f.write(head + "(" + ", ".join(literal(r[c]) for c in cols) + ");\n")
                n += len(rows)
                if pk:
                    last = [rows[-1][c] for c in pk]
                else:
                    after = rows[-1]["__rowid__"]
                if len(rows) < PAGE:
                    break
            counts[name] = n
            print(f"{name}: {n} rows", flush=True)
        for o in later:
            f.write(f"{o['sql']};\n")
    return counts


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in DATABASES:
        raise SystemExit("usage: tool/backup.py staging|production OUT.sql.gz")
    env = sys.argv[1]
    token, account = read_config()
    started = time.time()
    counts = dump(D1(token, account, DATABASES[env]), sys.argv[2])
    rows = sum(counts.values())
    summary = {"tables": len(counts), "rows": rows, "seconds": round(time.time() - started), "bytes": os.path.getsize(sys.argv[2]), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print(json.dumps(summary))
    # Refuse a dump that cannot be right (no tables, or far fewer rows than last time): it would replace the only
    # copy outside D1 (review, 18 Nov 2026). Exiting non-zero stops backup.sh before the upload.
    state = STATE.format(env=env)
    last = json.load(open(state)) if os.path.exists(state) else None
    if not counts or rows == 0:
        raise SystemExit("refusing the dump: no tables or no rows")
    if last and rows < last["rows"] * MIN_SHARE_OF_LAST:
        raise SystemExit(f"refusing the dump: {rows} rows, less than half of the last good dump ({last['rows']} on {last['at']})")
    with open(state, "w") as f:
        json.dump(summary, f)


if __name__ == "__main__":
    main()
