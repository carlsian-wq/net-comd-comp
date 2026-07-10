# Net Command Comparator (`net-comd-comp`)

Intelligent Arista ↔ Cisco network command comparison using **Ollama** for semantic search and translation.

**Target platforms (default):**

| Vendor | Hardware | OS |
|--------|----------|-----|
| Cisco | Catalyst 9300 Series | IOS XE 26.x.x |
| Arista | CCS-720XP | EOS 4.36.1F |

Enter a CLI command or natural-language description; the agent retrieves vendor documentation (PDFs + official URLs), then returns the equivalent command with syntax differences and caveats.

## Quick start

### Windows

```powershell
cd C:\Users\c_sia\OneDrive\Documents\GitHub\net-comd-comp
.\scripts\setup.ps1
.\scripts\pull_models.ps1
.\scripts\launch.ps1
```

### Linux (VMware / Azure / AWS)

```bash
cd /opt/net-comd-comp   # or your clone path
chmod +x scripts/*.sh
./scripts/setup.sh
./scripts/pull_models.sh
./scripts/launch.sh --detach
```

`--detach` runs Streamlit in the background (typical for servers). Use `./scripts/launch.sh` without flags for foreground/tmux. Add `--open-browser` on a desktop Linux session.

Install Ollama first (`https://ollama.com`) and enable the service when possible:

```bash
sudo systemctl enable --now ollama
```

In the sidebar: **Ingest sources from config** → **Build semantic index** (first ingest downloads the Cisco 9300 command-reference PDF).

## LAN deployment

Edit `config.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8503
  public_url: http://YOUR_SERVER_IP:8503
```

Open LAN access is enabled by default (`host: 0.0.0.0`). No login required.

## Ollama models (higher quality)

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

Or run `./scripts/pull_models.ps1` (Windows) / `./scripts/pull_models.sh` (Linux) from the project folder.

`qwen2.5:7b` fits an 8 GB GPU (e.g. RTX 5060 Laptop). For more quality on a larger GPU, try `qwen2.5:14b` in `config.yaml`.

## Curated documentation

**Cisco** — Catalyst 9300 IOS XE 26.x command reference (PDF + HTML chapters): VLAN, L2/L3, QoS, security, routing, stacking, system management.

**Arista** — EOS 4.36.1F User Manual chapters: CLI, interfaces, L2/L3, routing, security, QoS, administration.

Sources are listed in `config.yaml` under `sources.cisco` and `sources.arista`.

## Project layout

```
app.py                  Streamlit UI
config.yaml             Platforms, server, Ollama, curated sources
net_comd_comp/
  ingest/               PDF + URL loaders (incl. remote PDF cache)
  index/                SQLite chunk store
  embeddings/           Ollama embed + vector index
  agent/                Semantic search + platform-aware comparison
scripts/
  setup.ps1 / setup.sh       venv + pip install
  pull_models.ps1 / .sh      Ollama model pull helper
  launch.ps1 / launch.sh     Start Ollama + Streamlit
  lib.sh                     Shared bash helpers
```

## License

MIT