# Net Command Comparator (`net-comd-comp`)

Intelligent Arista ↔ Cisco network command comparison using **Ollama** for semantic search and translation.

**Target platforms (default):**

| Vendor | Hardware | OS |
|--------|----------|-----|
| Cisco | Catalyst 9300 Series | IOS XE 26.x.x |
| Arista | CCS-720XP | EOS 4.36.1F |

Enter a CLI command or natural-language description; the agent retrieves vendor documentation (PDFs + official URLs), then returns the equivalent command with syntax differences and caveats.

## Quick start

```powershell
cd C:\Users\c_sia\OneDrive\Documents\GitHub\net-comd-comp
.\scripts\setup.ps1
.\scripts\pull_models.ps1
.\scripts\launch.ps1
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

```powershell
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

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
  setup.ps1             venv + pip install
  pull_models.ps1       Ollama model pull helper
  launch.ps1            Start Ollama + Streamlit
```

## License

MIT