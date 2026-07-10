import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "data" / "net_comd_comp.db"
if not db.exists():
    print("no db")
    raise SystemExit(1)

conn = sqlite3.connect(db)
queries = [
    "snmp-server user",
    "user v3 auth sha",
    "snmp user v3",
    "user <user> <usergroup> v3 auth sha",
    "v3 auth sha",
    "priv aes",
]
for q in queries:
    rows = conn.execute(
        "SELECT vendor, command_hint FROM chunks WHERE lower(text) LIKE ? LIMIT 4",
        (f"%{q.lower()}%",),
    ).fetchall()
    print(f"=== {q!r} ({len(rows)})")
    for vendor, hint in rows:
        print(f"  {vendor}: {hint[:120]}")

print("\n=== arista snmp-server user text samples ===")
for vendor, text in conn.execute(
    """
    SELECT vendor, substr(text, 1, 500) FROM chunks
    WHERE vendor='arista' AND lower(text) LIKE '%snmp-server user%'
    LIMIT 5
    """
).fetchall():
    print(text[:480].replace("\n", " | "), "\n---")

query = "user <user> <usergroup> v3 auth sha <removed> priv aes256 <removed>"
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "cli_skeleton", ROOT / "net_comd_comp/agent/cli_skeleton.py"
)
cli_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli_mod)
print("\nquery skeleton:", cli_mod.cli_skeleton(query))
row = conn.execute(
    "SELECT command_hint, substr(text,1,800) FROM chunks WHERE lower(text) LIKE '%snmp-server user%' AND vendor='arista' LIMIT 1"
).fetchone()
if row:
    print("arista hint skeleton:", cli_mod.cli_skeleton(row[0]))
    print("arista text skeleton sample:", cli_mod.cli_skeleton(row[1][:400]))

print("\n=== cisco snmp user samples ===")
for vendor, text in conn.execute(
    """
    SELECT vendor, substr(text, 1, 400) FROM chunks
    WHERE vendor='cisco' AND lower(text) LIKE '%snmp%' AND lower(text) LIKE '%user%'
    LIMIT 5
    """
).fetchall():
    print(vendor, text[:350].replace("\n", " | "), "\n---")