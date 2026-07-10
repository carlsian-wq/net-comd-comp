from net_comd_comp.config import load_config, resolve_path
from net_comd_comp.index.store import CommandIndex
from net_comd_comp.ingest.pipeline import ingest_vendor
import sqlite3

cfg = load_config()
db = resolve_path(cfg, cfg["index"]["db_path"])
idx = CommandIndex(db)

def log(msg: str) -> None:
    print(msg)

idx.clear_vendor("cisco")
added = ingest_vendor(idx, "cisco", cfg, on_progress=log, replace=False)
print("added", added, "total", idx.count("cisco"))
conn = sqlite3.connect(db)
rows = conn.execute(
    "SELECT source_type, source_name, COUNT(c.id) FROM chunks c "
    "WHERE vendor='cisco' GROUP BY source_type, source_name ORDER BY COUNT(c.id) DESC"
).fetchall()
for row in rows:
    print(row)