"""Check indexed docs for colleague-confirmed Cisco↔Arista mappings."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
db = ROOT / "data" / "net_comd_comp.db"
if not db.exists():
    print("no db")
    raise SystemExit(1)

conn = sqlite3.connect(db)
patterns = [
    ("cisco", "no ip redirects"),
    ("cisco", "no ip unreachables"),
    ("arista", "no ip icmp redirect"),
    ("arista", "ip icmp rate-limit-unreachable"),
    ("arista", "rate-limit-unreachable"),
    ("cisco", "spanning-tree portfast bpduguard default"),
    ("arista", "spanning-tree edge-port bpduguard default"),
]
for vendor, pat in patterns:
    n = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE vendor=? AND lower(text) LIKE ?",
        (vendor, f"%{pat.lower()}%"),
    ).fetchone()[0]
    print(f"{vendor:6} {pat!r}: {n} chunks")
    if n:
        row = conn.execute(
            "SELECT command_hint, substr(text,1,350) FROM chunks "
            "WHERE vendor=? AND lower(text) LIKE ? LIMIT 1",
            (vendor, f"%{pat.lower()}%"),
        ).fetchone()
        print(f"       hint: {row[0][:100]}")
        print(f"       text: {row[1][:280].replace(chr(10), ' | ')}")

print("\n=== broader arista icmp searches ===")
for pat in [
    "rate-limit",
    "unreachable",
    "icmp redirect",
    "edge-port bpduguard default",
    "bpduguard default",
]:
    n = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE vendor='arista' AND lower(text) LIKE ?",
        (f"%{pat.lower()}%",),
    ).fetchone()[0]
    print(f"arista {pat!r}: {n}")

print("\n=== cisco unreachables / redirects samples ===")
for pat in ["no ip redirects", "no ip unreachables", "ip unreachables"]:
    rows = conn.execute(
        "SELECT command_hint, substr(text,1,400) FROM chunks "
        "WHERE vendor='cisco' AND lower(text) LIKE ? LIMIT 2",
        (f"%{pat}%",),
    ).fetchall()
    print(f"\n{pat} ({len(rows)})")
    for h, t in rows:
        print(" ", h[:80])
        print(" ", t[:200].replace("\n", " | "))

print("\n=== arista rate-limit + unreachable ===")
rows = conn.execute(
    "SELECT command_hint, substr(text,1,500) FROM chunks "
    "WHERE vendor='arista' AND lower(text) LIKE '%rate-limit%' "
    "AND lower(text) LIKE '%unreachable%' LIMIT 5"
).fetchall()
print(f"hits: {len(rows)}")
for h, t in rows:
    print("---", h[:90])
    print(t[:450].replace("\n", " | "))

print("\n=== arista icmp rate-limit samples ===")
rows = conn.execute(
    "SELECT command_hint, substr(text,1,500) FROM chunks "
    "WHERE vendor='arista' AND lower(text) LIKE '%ip icmp rate-limit%' LIMIT 5"
).fetchall()
print(f"hits: {len(rows)}")
for h, t in rows:
    print("---", h[:90])
    print(t[:450].replace("\n", " | "))

print("\n=== arista edge-port bpduguard default excerpts ===")
rows = conn.execute(
    "SELECT substr(text,1,700) FROM chunks "
    "WHERE vendor='arista' AND lower(text) LIKE '%edge-port bpduguard default%' LIMIT 2"
).fetchall()
for (t,) in rows:
    print(t[:650].replace("\n", " | "))
    print("---")