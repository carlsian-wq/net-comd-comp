from __future__ import annotations

import socket
from pathlib import Path

import streamlit as st

from net_comd_comp.agent.compare import CommandComparator
from net_comd_comp.agent.search import SemanticSearcher
from net_comd_comp.config import ROOT, load_config, resolve_path
from net_comd_comp.embeddings.ollama_embed import OllamaEmbeddings
from net_comd_comp.embeddings.vector_index import VectorIndex
from net_comd_comp.index.store import CommandIndex
from net_comd_comp.ingest.pipeline import ingest_all_sources
from net_comd_comp.ollama_client import is_ollama_available, model_installed
from net_comd_comp.ollama_client import OllamaChat
from net_comd_comp.ollama_lifecycle import ensure_ollama_server

st.set_page_config(
    page_title="Net Command Comparator",
    page_icon="🔀",
    layout="wide",
)


@st.cache_resource
def get_config():
    return load_config()


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _init_state(cfg: dict) -> None:
    if "ollama_checked" not in st.session_state:
        base = cfg["ollama"]["base_url"]
        if not is_ollama_available(base):
            ensure_ollama_server(base)
        st.session_state.ollama_checked = True


def _paths(cfg: dict) -> tuple[Path, Path]:
    db = resolve_path(cfg, cfg["index"]["db_path"])
    data_dir = resolve_path(cfg, cfg["index"]["data_dir"])
    return db, data_dir


def main() -> None:
    cfg = get_config()
    _init_state(cfg)
    db_path, data_dir = _paths(cfg)

    ui = cfg.get("ui", {})
    server = cfg.get("server", {})
    ollama_cfg = cfg.get("ollama", {})
    search_cfg = cfg.get("search", {})

    st.title(ui.get("page_title", "Net Command Comparator"))
    st.caption(
        "Semantic Arista ↔ Cisco CLI translation powered by Ollama. "
        "Sources: PDFs and vendor documentation URLs in `config.yaml`."
    )

    with st.sidebar:
        st.subheader("Server")
        public_url = server.get("public_url", "http://localhost:8503")
        lan_ip = _local_ip()
        port = server.get("port", 8503)
        st.markdown(f"**Configured URL:** `{public_url}`")
        st.markdown(f"**LAN access:** `http://{lan_ip}:{port}`")
        st.caption("Edit `server.public_url` in config.yaml for your deployment.")

        st.divider()
        st.subheader("Ollama")
        base_url = ollama_cfg.get("base_url", "http://localhost:11434")
        online = is_ollama_available(base_url)
        st.markdown("Status: **online**" if online else "Status: **offline**")
        chat_model = ollama_cfg.get("chat_model", "qwen2.5:3b")
        embed_model = ollama_cfg.get("embed_model", "nomic-embed-text")
        if online:
            st.caption(f"Chat: `{chat_model}` · Embed: `{embed_model}`")
            if not model_installed(chat_model, base_url):
                st.warning(f"Pull chat model: `ollama pull {chat_model}`")
            if not model_installed(embed_model, base_url):
                st.warning(f"Pull embed model: `ollama pull {embed_model}`")
        else:
            if st.button("Start Ollama server"):
                if ensure_ollama_server(base_url):
                    st.success("Ollama API is up.")
                    st.rerun()
                else:
                    st.error("Could not start Ollama on :11434.")

        st.divider()
        st.subheader("Index")
        index = CommandIndex(db_path)
        vector_index = VectorIndex(data_dir, embed_model)
        st.metric("Document chunks", index.count())
        st.metric("Embedded chunks", vector_index.count())
        if st.button("Ingest sources from config"):
            with st.spinner("Fetching PDFs and URLs…"):
                log_box = st.empty()

                def log(msg: str) -> None:
                    log_box.caption(msg)

                counts = ingest_all_sources(index, cfg, on_progress=log)
            st.success(f"Ingested — Cisco: {counts['cisco']}, Arista: {counts['arista']} new chunks")
            st.rerun()

        if st.button("Build semantic index"):
            if not online or not model_installed(embed_model, base_url):
                st.error("Ollama embed model required.")
            else:
                embedder = OllamaEmbeddings(
                    model=embed_model,
                    base_url=base_url,
                    num_thread=ollama_cfg.get("num_thread"),
                )
                prog = st.progress(0, text="Embedding…")

                def on_progress(done: int, total: int) -> None:
                    prog.progress(done / max(total, 1), text=f"Embedding {done}/{total}")

                added = vector_index.build(index, embedder, on_progress=on_progress)
                prog.empty()
                st.success(f"Added {added} embeddings.")
                st.rerun()

        with st.expander("Indexed sources"):
            for row in index.list_sources():
                st.text(
                    f"{row['vendor']}: {row['source_name']} ({row['chunks']} chunks, {row['source_type']})"
                )

    tab_search, tab_admin = st.tabs(["Compare commands", "Documentation sources"])

    with tab_search:
        direction = st.selectbox(
            "Translation direction",
            options=[
                ("auto", "Auto-detect"),
                ("cisco_to_arista", "Cisco → Arista"),
                ("arista_to_cisco", "Arista → Cisco"),
            ],
            format_func=lambda x: x[1],
            index=0,
        )[0]
        query = st.text_area(
            "Enter a CLI command or describe what you want to configure",
            placeholder="e.g. configure a trunk port with VLAN 10 and 20 allowed",
            height=120,
        )
        run = st.button("Find equivalent command", type="primary", disabled=not query.strip())

        if run:
            if not online:
                st.error("Ollama is offline. Start the server from the sidebar.")
            elif vector_index.count() == 0:
                st.warning("Semantic index is empty. Ingest sources and build the index first.")
            elif not model_installed(chat_model, base_url) or not model_installed(embed_model, base_url):
                st.error("Required Ollama models are missing.")
            else:
                embedder = OllamaEmbeddings(
                    model=embed_model,
                    base_url=base_url,
                    num_thread=ollama_cfg.get("num_thread"),
                )
                searcher = SemanticSearcher(
                    index,
                    vector_index,
                    embedder,
                    top_k=search_cfg.get("top_k", 10),
                    min_similarity=search_cfg.get("min_similarity", 0.32),
                )
                chat = OllamaChat(
                    model=chat_model,
                    base_url=base_url,
                    num_thread=ollama_cfg.get("num_thread"),
                )
                comparator = CommandComparator(searcher, chat)
                with st.spinner("Searching documentation and comparing syntax…"):
                    result = comparator.compare(query.strip(), direction=direction)

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(f"Source ({result.source_vendor})")
                    st.code(result.source_command or "(not identified)", language="bash")
                with col2:
                    st.subheader(f"Target ({result.target_vendor})")
                    st.code(result.target_command or "(no equivalent found)", language="bash")

                st.markdown("### Explanation")
                st.write(result.explanation or "No explanation returned.")

                if result.differences:
                    st.markdown("### Syntax / behavior differences")
                    for item in result.differences:
                        st.markdown(f"- {item}")
                if result.caveats:
                    st.markdown("### Caveats")
                    for item in result.caveats:
                        st.markdown(f"- {item}")
                if result.citations:
                    st.markdown("### Sources cited")
                    for item in result.citations:
                        st.markdown(f"- {item}")

                with st.expander("Retrieved documentation excerpts"):
                    both = searcher.search_both(query.strip())
                    for vendor, hits in both.items():
                        st.markdown(f"**{vendor.title()}**")
                        if not hits:
                            st.caption("No hits.")
                            continue
                        for hit in hits[:5]:
                            c = hit.chunk
                            st.markdown(
                                f"- `{c.command_hint[:120]}` — {c.source_name} "
                                f"(score {hit.score:.3f})"
                            )

    with tab_admin:
        st.markdown("### Add documentation")
        st.markdown(
            "1. Place PDF files under `data/sources/` (or any path).\n"
            "2. Add PDF paths and vendor doc URLs to `config.yaml` under `sources.cisco` / `sources.arista`.\n"
            "3. Use **Ingest sources** then **Build semantic index** in the sidebar.\n"
            "4. Set `server.public_url` to your web server's address so users know where to connect."
        )
        st.code(
            f"""# Example config.yaml entries
sources:
  cisco:
    pdfs:
      - data/sources/cisco/ios-xe-guide.pdf
    urls:
      - name: IOS XE reference
        url: https://www.cisco.com/...
  arista:
    pdfs:
      - data/sources/arista/eos-cli.pdf
    urls:
      - name: EOS command reference
        url: https://www.arista.com/...""",
            language="yaml",
        )
        st.info(f"Project root: `{ROOT}`")


if __name__ == "__main__":
    main()