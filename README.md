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

**Arista** — EOS 4.36.1F User Manual (PDF): CLI, interfaces, L2/L3, routing, security, QoS, administration.

**Arista EOS Hardening Guide** (recommended, updated frequently) — ICMP hardening, global vs interface scope, and commands such as `ip icmp rate-limit-unreachable` that are **not** always in the User Manual PDF:

https://arista.my.site.com/AristaCommunity/s/article/arista-eos-hardening-guide

The Community article is a **JavaScript SPA**; the ingest pipeline cannot scrape it reliably. To index it:

1. Open the article in a browser (Arista Community login if required).
2. **Print → Save as PDF** (or export if Arista provides a download).
3. Save as `data/sources/arista-eos-hardening-guide.pdf`.
4. Uncomment the `pdfs` entry under `sources.arista` in `config.yaml`.
5. **Ingest sources** → **Build semantic index** (replace existing Arista docs if you want a clean merge).

Sources are listed in `config.yaml` under `sources.cisco` and `sources.arista`.

### Why some mappings are curated (not in the PDF index)

Cross-vendor equivalents often **are** documented — but not always in one place, or not with obvious wording:

| Topic | Where it usually lives |
|-------|-------------------------|
| Arista `no ip icmp redirect` | EOS User Manual (global ICMP) — **in indexed PDF** |
| Arista `ip icmp rate-limit-unreachable 0` | [Arista EOS Hardening Guide](https://arista.my.site.com/AristaCommunity/s/article/arista-eos-hardening-guide) — **not in User Manual PDF**; ingest via exported PDF or use `command_mappings` |
| Cisco `no ip redirects` / `no ip unreachables` | IOS XE interface commands — in Cisco CR, but PDF text extraction can be noisy |
| Interface (Cisco) vs global (Arista) scope | Design guides, template configs, SharePoint standards — **rarely a 1:1 “equivalent command” table** |

Ops-confirmed campus mappings live in `config.yaml` under `command_mappings`. Add sources there (or extra PDFs/URLs under `sources`) when you find authoritative vendor text, then re-ingest.

## Recommended virtual server specs

The app runs **Streamlit** (UI) + **Ollama** (LLM + embeddings) on the same host by default. Size for the chat model (`qwen2.5:7b` default), embedding model (`nomic-embed-text`), ingested PDFs, and SQLite/vector index under `data/`.

### Sizing summary

| Tier | vCPU | RAM | GPU (optional) | Disk | Use case |
|------|------|-----|----------------|------|----------|
| **Minimum** | 4 | 16 GB | — | 60 GB SSD | Lab / single user; CPU inference is slow |
| **Recommended** | 8 | 32 GB | 8 GB VRAM (e.g. T4, L4) | 100 GB SSD | Team LAN server; responsive compares |
| **Higher quality** | 8–16 | 32–64 GB | 16+ GB VRAM | 128 GB SSD | `qwen2.5:14b` or heavier concurrent use |

**Disk breakdown (approx.):** Ollama models ~5–6 GB (`qwen2.5:7b` + `nomic-embed-text`), PDF cache + index ~1–3 GB, OS + venv ~15 GB headroom.

**Network:** open TCP **8503** (Streamlit). Ollama stays on `localhost:11434` unless you split services.

**OS:** Ubuntu 22.04/24.04 LTS or RHEL 9.x for servers; Windows 11 works for dev (see Quick start).

### VMware vSphere / ESXi

| Profile | VM config | Notes |
|---------|-----------|--------|
| Recommended | 8 vCPU, 32 GB RAM, 100 GB thin disk (PVSCSI or NVMe) | 1 VM for app + Ollama |
| With GPU | Above + **NVIDIA vGPU** or passthrough (T4 16 GB, L4 24 GB, A10) | Install NVIDIA driver + CUDA in guest; Ollama uses GPU automatically when available |
| Minimum | 4 vCPU, 16 GB RAM, 60 GB disk | Set `num_thread` in `config.yaml` to vCPU count; expect 30–90 s compares |

Enable **VMware Tools**, time sync, and a snapshot before first full PDF ingest.

### Microsoft Azure

| SKU | vCPU / RAM | GPU | When to use |
|-----|------------|-----|-------------|
| **Standard_D8s_v5** | 8 / 32 GB | — | CPU-only; predictable cost |
| **Standard_D8as_v5** | 8 / 32 GB | — | AMD alternative |
| **Standard_NC4as_T4_v3** | 4 / 28 GB | 1× T4 (16 GB) | **Best default GPU VM** for `qwen2.5:7b` |
| **Standard_NV6ads_A10_v5** | 6 / 55 GB | 1× A10 | Headroom for `qwen2.5:14b` or many users |

Storage: **Premium SSD** or **Premium SSD v2**, 128 GB+. NSG: allow inbound **8503** from your LAN/VNet; restrict `0.0.0.0/0` on production.

Install Ollama in the VM, then clone the repo to `/opt/net-comd-comp` and use `launch.sh --detach`.

### Amazon Web Services (AWS)

| Instance | vCPU / RAM | GPU | When to use |
|----------|------------|-----|-------------|
| **m7i.2xlarge** | 8 / 32 GB | — | CPU-only LAN server |
| **m7i-flex.2xlarge** | 8 / 32 GB | — | Lower cost burstable option |
| **g4dn.xlarge** | 4 / 16 GB | 1× T4 (16 GB) | Works for 7b; tight on RAM — prefer **g4dn.2xlarge** (8 vCPU / 32 GB) for teams |
| **g5.xlarge** | 4 / 16 GB | 1× A10G (24 GB) | Stronger GPU; use **g5.2xlarge** if you need more RAM |

EBS: **gp3** 128 GB, 3000+ IOPS. Security group: TCP **8503** from corporate CIDR. Place in a private subnet with VPN/bastion if needed.

Use the **NVIDIA GPU AMI** (Ubuntu) for g4dn/g5, or install drivers via `ubuntu-drivers` / AWS DLAMI docs.

### Google Cloud Platform (GCP)

| Machine type | vCPU / RAM | GPU | When to use |
|--------------|------------|-----|-------------|
| **n2-standard-8** | 8 / 32 GB | — | CPU-only |
| **n2-standard-8 + NVIDIA T4** | 8 / 32 GB | 1× T4 | Attach T4 in `us-central1` / `europe-west4` zones with GPU quota |
| **g2-standard-4** | 4 / 16 GB | 1× L4 | Newer inference GPU; good for Ollama 7b |

Boot disk: 128 GB **balanced PD** or **SSD**. Firewall: tag `net-comd-comp`, allow **8503** from internal ranges.

### Other hosts (Oracle Cloud, Proxmox, Hyper-V)

Same **Recommended** row applies: **8 vCPU, 32 GB RAM, 100 GB SSD**. On OCI, **VM.Standard.E4.Flex** (8 OCPU / 32 GB) is a common CPU choice; for GPU, check regional **NVIDIA A10** bare metal or GPU shapes if available.

### Post-deploy checklist

1. `sudo systemctl enable --now ollama`
2. `./scripts/setup.sh` → `./scripts/pull_models.sh` → `./scripts/launch.sh --detach`
3. Set `server.public_url` in `config.yaml` to the VM’s LAN or private IP
4. Sidebar: **Ingest sources** → **Build semantic index** (once per environment)
5. Confirm sidebar shows **Curated mappings loaded: 3** (or your current count)

Tune `ollama.num_thread` in `config.yaml` to match vCPU count on CPU-only VMs.

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