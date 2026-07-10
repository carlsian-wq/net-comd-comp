import sqlite3
from pathlib import Path
from net_comd_comp.config import load_config, resolve_path
from net_comd_comp.ingest.url_loader import fetch_pdf_text_cached
import re

cfg = load_config()
db = resolve_path(cfg, cfg["index"]["db_path"])
conn = sqlite3.connect(db)

for q in [
    "no ip unreachables",
    "ip unreachables",
    "no ip redirects",
    "no ip icmp redirect",
]:
    total = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE lower(text) LIKE ?",
        (f"%{q}%",),
    ).fetchone()[0]
    arista = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE vendor='arista' AND lower(text) LIKE ?",
        (f"%{q}%",),
    ).fetchone()[0]
    print(f"{q}: total={total} arista={arista}")

print("\n=== Arista no ip unreachables chunks ===")
rows = conn.execute(
    "SELECT command_hint, substr(text, 1, 600) FROM chunks "
    "WHERE vendor='arista' AND lower(text) LIKE '%no ip unreachables%'"
).fetchall()
for hint, text in rows[:4]:
    print("HINT:", hint[:120])
    print(text[:500])
    print("---")

print("\n=== Cisco no ip redirects chunks ===")
rows = conn.execute(
    "SELECT command_hint, substr(text, 1, 600) FROM chunks "
    "WHERE vendor='cisco' AND lower(text) LIKE '%no ip redirects%'"
).fetchall()
for hint, text in rows[:3]:
    print("HINT:", hint[:120])
    print(text[:500])
    print("---")

cache = Path("data/sources/cache")
arista_pdf = fetch_pdf_text_cached(
    "https://www.arista.com/assets/data/pdf/user-manual/EOS-User-Manual.pdf",
    cache,
)
for pat in ["no ip unreachables", "no ip icmp redirect", "no ip redirects"]:
    print(f"\nPDF mentions '{pat}':", len(re.findall(pat, arista_pdf, re.I)))
    m = re.search(rf".{{0,80}}{re.escape(pat)}.{{0,120}}", arista_pdf, re.I)
    if m:
        print(" sample:", m.group().replace("\n", " ")[:200])