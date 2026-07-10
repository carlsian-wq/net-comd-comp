import sqlite3
from net_comd_comp.config import load_config, resolve_path

cfg = load_config()
db = resolve_path(cfg, cfg["index"]["db_path"])
conn = sqlite3.connect(db)

for q in ["no ip redirects", "no ip icmp redirect", "ip icmp redirect", "icmp redirect"]:
    c = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE lower(text) LIKE ?",
        (f"%{q}%",),
    ).fetchone()[0]
    print(q, c)

rows = conn.execute(
    "SELECT vendor, command_hint, substr(text, 1, 200) FROM chunks "
    "WHERE lower(text) LIKE '%icmp redirect%' LIMIT 8"
).fetchall()
for vendor, hint, text in rows:
    print("---", vendor, hint[:80])
    print(text[:180])

print("\n=== arista ip icmp redirect full ===")
rows = conn.execute(
    "SELECT command_hint, substr(text, 1, 500) FROM chunks "
    "WHERE vendor='arista' AND lower(text) LIKE '%ip icmp redirect%'"
).fetchall()
for hint, text in rows:
    print("HINT", hint[:120])
    print(text[:400])
    print("---")