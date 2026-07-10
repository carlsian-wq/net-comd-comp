# Net Command Comparator (`net-comd-comp`)

Intelligent Arista ↔ Cisco network command comparison using **Ollama** for semantic search and translation.

Enter a CLI command or a natural-language description of what you want to configure; the agent retrieves relevant documentation (PDFs and vendor URLs), then returns the equivalent command on the other platform with syntax differences and caveats.

## Features

- **Bidirectional translation**: Cisco → Arista, Arista → Cisco, or auto-detect
- **Documentation ingestion**: PDF files and live vendor documentation URLs
- **Semantic search**: Ollama embeddings (`nomic-embed-text`) over ingested CLI excerpts
- **Comparison agent**: Ollama chat model explains equivalents and differences
- **Portable deployment**: `config.yaml` controls bind address, port, and public URL for multi-user access

## Quick start

```powershell
cd C:\Users\c_sia\OneDrive\Documents\GitHub\net-comd-comp
.\scripts\setup.ps1
.\scripts\launch.ps1
```

Open the URL shown in the sidebar. For LAN users, set in `config.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8503
  public_url: http://YOUR_SERVER_IP:8503
```

## Ollama models

```powershell
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

## Adding documentation

1. Copy PDFs into `data/sources/` (or reference any path).
2. Edit `config.yaml` under `sources.cisco` and `sources.arista`.
3. In the app sidebar: **Ingest sources from config** → **Build semantic index**.

## Project layout

```
app.py                  Streamlit UI
config.yaml             Server, Ollama, sources, search settings
net_comd_comp/
  ingest/               PDF + URL loaders, chunking
  index/                SQLite chunk store
  embeddings/           Ollama embed + vector index
  agent/                Semantic search + comparison
scripts/
  setup.ps1             venv + pip install
  launch.ps1            Start Ollama + Streamlit
```

## License

MIT