# net-comd-comp — agent conventions

Adds to workspace root `GitHub/Agents.md`. **This file wins** on conflict inside `net-comd-comp/`.

Bot-only operational rules. Human docs: `README.md`, `STARTUP.md`.

---

## Scope

- Local **Arista ↔ Cisco CLI translator + semantic doc search** (Streamlit + Ollama).
- Ingests vendor PDFs/URLs, builds SQLite + vector index, compares commands (curated mappings override LLM when they match).
- Prefer reversible local edits. Confirm before mass-deleting `data/`, force-push, or killing shared Ollama used by other apps.
- Do not expand into unrelated repos unless asked.

---

## Environment

| Item | Convention |
|------|------------|
| OS / shell | Windows, **PowerShell 7** (`pwsh`) |
| Venv | **`venv\`** (not `.venv`) |
| Entry | `app.py` → Streamlit |
| Port | **8503** — **one instance only**; launcher skips if already up |
| Ollama | Shared API `http://localhost:11434` — chat `qwen2.5:7b`, embed `nomic-embed-text` |
| Index DB | `data/net_comd_comp.db` (runtime; do not hand-edit) |
| Vector cache | `data/semantic_commands.json` / `.npz` |
| Config | `config.yaml` — server, platforms, `command_mappings`, ollama, search, index, sources |
| Package | `net_comd_comp/` (`agent/`, `ingest/`, `embeddings/`, `index/`) |

- Work from `net-comd-comp/` for pip, scripts, and Streamlit.
- Use `venv\Scripts\python.exe` / `streamlit.exe`.
- First-time: `.\scripts\setup.ps1` then `.\scripts\pull_models.ps1`.
- Launch: `.\scripts\launch.ps1` (starts Ollama if down; opens browser). Manual:  
  `.\venv\Scripts\streamlit.exe run app.py --server.port 8503 --server.address 0.0.0.0`
- Neighbor ports: 8501 HL dashboard · 8502 log-sage · **8503 this app** · 8504 proj-sage · 11434 Ollama (shared).

---

## Sources & data

- **All curated sources live in `config.yaml` → `sources.cisco` / `sources.arista`.**
  - `urls:` remote PDFs/HTML (prefer full PDFs; Arista HTML often needs JS and ingests empty).
  - `pdfs:` local paths under `data/sources/` (e.g. hardening guide export).
- Uploads land under `data/sources/uploads/{cisco,arista}/` via the UI; cache under `data/sources/cache/`.
- **Ops-confirmed campus mappings** → `config.yaml` → `command_mappings` (bidirectional; override LLM when query matches). Never invent false Cisco↔Arista twins.
- After adding/changing sources: in-app **Ingest sources from config** → **Build semantic index**.
- **Never commit** runtime DB, vector dumps, or large cached PDFs unless the user asks. Prefer re-ingest over hand-editing SQLite.

---

## Ollama

- Semantic search, embeddings, and LLM compare need the API + models above; without them, curated mappings and keyword-ish paths still work partially.
- Launcher may start `ollama serve` if down; tray/other apps also use :11434 — **do not kill Ollama** unless the user wants a full Ollama restart.
- Models: `.\scripts\pull_models.ps1` (reads `ollama.chat_model` / `embed_model` from config).
- `ollama.num_thread` is machine-tuned; do not “optimize” without a measured reason.

---

## Restart rules

| Change | What to do |
|--------|------------|
| `config.yaml` → `command_mappings` / platforms notes | **No server restart** — `get_config()` reloads YAML each run; browser refresh is enough |
| Python under `net_comd_comp/**` (agent, ingest, index, embeddings) | Prefer **browser hard-refresh** first — `app.py` `importlib.reload`s key modules on each script run; if stale, **restart Streamlit** |
| `app.py` itself or Streamlit process state | **Server restart** required — stop the Streamlit window (Ctrl+C), then `.\scripts\launch.ps1` |
| New/updated sources or PDFs | In-app **Ingest** + **Build semantic index** (no process kill needed) |
| Already running on 8503 | **Do not** start a second Streamlit; use existing instance or stop then relaunch |
| Stop app | Ctrl+C in Streamlit PowerShell window (or end that process); leave Ollama up for other tools |

---

## Agent hygiene

- Prefer modules under `net_comd_comp/` over one-off frameworks.
- Probes: small scripts under `scripts/` or temp `_probe_*.py`; delete temps when done.
- PowerShell: here-strings / script files for anything with `$` or nested quotes (see root `Agents.md`).
- Match scope: CLI compare, mappings, ingest quality, search/index — not trading logic or other sages unless the user points there.
- After user-facing UI/config changes, note whether **browser reload**, **re-ingest**, or **server restart** is required.

After completing a coding task, always end with:

```markdown
## What you should do

- First concrete step for the user
- Second step if needed
```

Use clear action verbs (reload, restart, re-ingest, open, verify, run). If nothing is required:

```markdown
## What you should do

- No action needed — changes are live.
```
