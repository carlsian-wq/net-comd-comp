import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location(
    "cli_skeleton", ROOT / "net_comd_comp/agent/cli_skeleton.py"
)
cli_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli_mod)

spec2 = importlib.util.spec_from_file_location("config", ROOT / "net_comd_comp/config.py")
config_mod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(config_mod)

# Load store without pulling agent __init__
spec3 = importlib.util.spec_from_file_location("store", ROOT / "net_comd_comp/index/store.py")
store_mod = importlib.util.module_from_spec(spec3)
sys.modules["net_comd_comp.agent.cli_skeleton"] = cli_mod
spec3.loader.exec_module(store_mod)

cli_skeleton = cli_mod.cli_skeleton
skeleton_search_phrases = cli_mod.skeleton_search_phrases
best_line_skeleton = cli_mod.best_line_skeleton
load_config = config_mod.load_config
resolve_path = config_mod.resolve_path
CommandIndex = store_mod.CommandIndex

cfg = load_config()
db = resolve_path(cfg, cfg["index"]["db_path"])
index = CommandIndex(db)

query = "user <user> <usergroup> v3 auth sha <removed> priv aes256 <removed>"
print("skeleton:", cli_skeleton(query))
print("phrases:", skeleton_search_phrases(query)[:8])

row = index._connect().execute(
    "SELECT text FROM chunks WHERE vendor='arista' AND text LIKE '%snmp-server user tech-1%'"
).fetchone()
if row:
    text = row[0]
    line = best_line_skeleton(text)
    qt = cli_mod.structural_tokens(query)
    ht = cli_mod.structural_tokens(line)
    print("\narista example line:", line)
    print("overlap", len(set(qt) & set(ht)) / len(qt))
    print("subseq", cli_mod.token_subsequence_score(qt, ht))

cisco_row = index._connect().execute(
    "SELECT text FROM chunks WHERE vendor='cisco' AND text LIKE '%snmp-server user%' LIMIT 1"
).fetchone()
if cisco_row:
    print("\ncisco line:", best_line_skeleton(cisco_row[0])[:120])

for q2 in ("snmp-server user", "snmp-server group v3"):
    n = index._connect().execute(
        "SELECT COUNT(*) FROM chunks WHERE lower(text) LIKE ? AND vendor='cisco'",
        (f"%{q2}%",),
    ).fetchone()[0]
    print(f"cisco chunks like {q2!r}: {n}")

for vendor in ("cisco", "arista"):
    hits = index.search_skeleton(query, vendor=vendor, limit=5)
    print(f"\n=== {vendor} skeleton hits ({len(hits)}) ===")
    for chunk, score in hits:
        line = best_line_skeleton(f"{chunk.command_hint}\n{chunk.text}")
        print(f"{score:.3f} line={line[:90]}")