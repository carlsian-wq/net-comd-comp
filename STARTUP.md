# net-comd-comp — Startup Guide

Project root:

`C:\Users\c_sia\OneDrive\Documents\GitHub\net-comd-comp`

**Net Command Comparator** — Arista ↔ Cisco CLI translation and semantic doc search (Streamlit + Ollama).

---

## Golden rules

1. **One instance** — port **8503** (from `config.yaml`). Launcher skips a second Streamlit if already up.
2. **First-time setup** — run `setup.ps1` and `pull_models.ps1` once per machine.
3. **Ollama shared** — same :11434 API as Log Sage; only one Ollama server needed.

---

## First-time setup (once)

```powershell
cd "C:\Users\c_sia\OneDrive\Documents\GitHub\net-comd-comp"
.\scripts\setup.ps1
.\scripts\pull_models.ps1
```

| Script | Description |
|--------|-------------|
| `setup.ps1` | Creates `venv`, installs `requirements.txt` |
| `pull_models.ps1` | Pulls Ollama models defined in config (e.g. `qwen2.5:7b`, `nomic-embed-text`) |

Install Ollama from https://ollama.com if not present.

---

## Quick start (daily)

```powershell
cd "C:\Users\c_sia\OneDrive\Documents\GitHub\net-comd-comp"
.\scripts\launch.ps1
```

Or double-click **Compass** / net-comd-comp desktop shortcut (if installed):

```powershell
.\scripts\install_desktop_compass_shortcut.ps1
```

Opens: http://localhost:8503 (LAN: `http://YOUR_IP:8503` if `server.host` is `0.0.0.0`).

**What launch does**

1. Starts Ollama API if down (`ollama serve`, hidden)
2. Starts Streamlit on configured port **only if not already running**
3. Opens Chrome/Edge app window

---

## Process map

| Friendly name | How started | Port | Config |
|---------------|-------------|------|--------|
| **Net Command Comparator** | `scripts\launch.ps1` | **8503** | `config.yaml` → `server.port` |
| **Ollama API** | Auto or tray app | **11434** | Shared |

No background workers beyond Streamlit + Ollama.

---

## `scripts\launch.ps1`

```powershell
.\scripts\launch.ps1
.\scripts\launch.ps1 -Port 8503 -Browser edge
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-Port` | from `config.yaml` (`8503`) | Streamlit port; `0` means read config |
| `-Browser` | `chrome` | `chrome` or `edge` for app-mode window |

---

## Manual start (no browser)

```powershell
cd "C:\Users\c_sia\OneDrive\Documents\GitHub\net-comd-comp"
.\venv\Scripts\streamlit.exe run app.py --server.port 8503 --server.address 0.0.0.0
```

Host/address come from `config.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8503
  public_url: http://localhost:8503
```

---

## Linux / VM (`scripts/launch.sh`)

```bash
./scripts/launch.sh                  # foreground
./scripts/launch.sh --detach         # background (servers)
./scripts/launch.sh --open-browser   # desktop Linux
./scripts/launch.sh --port 8503
```

| Flag | Description |
|------|-------------|
| `--detach` / `-d` | Run Streamlit in background |
| `--open-browser` | Open local browser |
| `--port N` | Override config port |

---

## First use inside the app

1. Sidebar → **Ingest sources from config** (downloads PDFs / URLs)
2. Sidebar → **Build semantic index**
3. Enter a Cisco or Arista command (or natural language) in the search box

---

## Other scripts

| Script | Purpose |
|--------|---------|
| `pull_models.ps1` / `pull_models.sh` | Refresh Ollama models |
| `setup.ps1` / `setup.sh` | Venv + pip install |
| `install_desktop_compass_shortcut.ps1` | Desktop shortcut |
| `diag_*.py`, `test_*.py` | Development diagnostics (not daily startup) |

---

## Stopping safely

1. Close the **PowerShell window** running Streamlit (Ctrl+C), or
2. Task Manager → end process with `net-comd-comp` and `streamlit` in command line.

Verify: http://localhost:8503 should not load.

---

## Ports (all three projects)

| Port | Project |
|------|---------|
| 8501 | hyperliquid-bot trading dashboard |
| 8502 | log-sage |
| **8503** | **net-comd-comp** (this project) |
| 11434 | Ollama (shared) |

See also: `hyperliquid-bot/STARTUP.md`, `log-sage/STARTUP.md`.