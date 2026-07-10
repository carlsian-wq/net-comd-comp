from __future__ import annotations

import importlib
import socket
from pathlib import Path

import streamlit as st

from net_comd_comp.config import ROOT, load_config, platform_context, resolve_path
from net_comd_comp.embeddings.ollama_embed import OllamaEmbeddings
from net_comd_comp.embeddings.vector_index import VectorIndex

# Streamlit caches imported modules; reload project code so fixes apply without restart.
import net_comd_comp.agent.keywords as _agent_keywords
import net_comd_comp.agent.compare as _agent_compare
import net_comd_comp.agent.search as _agent_search
import net_comd_comp.index.store as _index_store
import net_comd_comp.ingest.quality as _ingest_quality
import net_comd_comp.ingest.url_loader as _ingest_url_loader
import net_comd_comp.ingest.pipeline as _ingest_pipeline

importlib.reload(_agent_keywords)
importlib.reload(_index_store)
importlib.reload(_ingest_quality)
importlib.reload(_ingest_url_loader)
importlib.reload(_ingest_pipeline)
importlib.reload(_agent_search)
importlib.reload(_agent_compare)
from net_comd_comp.agent.compare import CommandComparator  # noqa: E402
from net_comd_comp.agent.search import SemanticSearcher  # noqa: E402
from net_comd_comp.index.store import CommandIndex  # noqa: E402
from net_comd_comp.ingest.pipeline import ingest_all_sources
from net_comd_comp.ollama_client import is_ollama_available, model_installed
from net_comd_comp.ollama_client import OllamaChat
from net_comd_comp.ollama_lifecycle import ensure_ollama_server

APP_BUILD = "2026-07-10-keyword-search-fix"

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
    platforms = cfg.get("platforms", {})
    cisco_p = platforms.get("cisco", {})
    arista_p = platforms.get("arista", {})
    st.caption(
        f"**Cisco:** {cisco_p.get('product', 'Catalyst')} · {cisco_p.get('os', 'IOS XE')}  \n"
        f"**Arista:** {arista_p.get('product', 'CCS')} · {arista_p.get('os', 'EOS')}  \n"
        "Semantic CLI translation powered by Ollama."
    )

    with st.sidebar:
        st.caption(f"Build: `{APP_BUILD}`")
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
        chat_model = ollama_cfg.get("chat_model", "qwen2.5:7b")
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
        cisco_chunks = index.count("cisco")
        arista_chunks = index.count("arista")
        st.metric("Cisco chunks", cisco_chunks)
        st.metric("Arista chunks", arista_chunks)
        st.metric("Embedded chunks", vector_index.count)
        if arista_chunks == 0:
            st.error("Arista docs not indexed. Ingest sources (EOS PDF) before comparing.")
        if cisco_chunks < 2000:
            st.warning(
                "Cisco PDF may not be ingested yet (only HTML pages indexed). "
                "Use **Replace existing documentation** and re-ingest."
            )
        replace_docs = st.checkbox(
            "Replace existing documentation",
            value=True,
            help="Clear old chunks before ingest. Required after fixing Arista sources "
            "(removes JavaScript error-page junk). Rebuild the semantic index afterward.",
        )
        if st.button("Ingest sources from config"):
            with st.spinner("Fetching PDFs and URLs…"):
                log_box = st.empty()

                def log(msg: str) -> None:
                    log_box.caption(msg)

                if replace_docs:
                    vector_index.clear()
                    for vendor in ("cisco", "arista"):
                        removed = index.clear_vendor(vendor)
                        log(f"Cleared {removed} {vendor} chunks")
                    log("Cleared semantic index for rebuild")
                counts = ingest_all_sources(index, cfg, on_progress=log)
            st.success(f"Ingested — Cisco: {counts['cisco']}, Arista: {counts['arista']} new chunks")
            if replace_docs:
                st.info("Run **Build semantic index** next to refresh search.")
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
            elif vector_index.count == 0:
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
                    timeout=ollama_cfg.get("chat_timeout", 180),
                )
                comparator = CommandComparator(
                    searcher,
                    chat,
                    index,
                    platform_context=platform_context(cfg),
                )
                with st.spinner("Searching documentation and comparing syntax…"):
                    result = comparator.compare(query.strip(), direction=direction)
                    hits = searcher.search_both(query.strip())
                st.session_state["last_compare"] = result
                st.session_state["last_compare_hits"] = hits

        result = st.session_state.get("last_compare")
        if result and query.strip() and result.query.strip() == query.strip():
            if result.confidence == "none":
                st.warning("Low documentation match — result may be incomplete. See caveats below.")
            elif result.confidence == "low":
                st.info(f"Retrieval confidence: **{result.confidence}** ({result.retrieval_note})")

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
                both = st.session_state.get("last_compare_hits") or {}
                for vendor, vendor_hits in both.items():
                    st.markdown(f"**{vendor.title()}**")
                    if not vendor_hits:
                        st.caption("No hits.")
                        continue
                    for hit in vendor_hits[:5]:
                        c = hit.chunk
                        st.markdown(
                            f"- `{c.command_hint[:120]}` — {c.source_name} "
                            f"(score {hit.score:.3f})"
                        )

    with tab_admin:
        st.markdown("### Curated documentation sources")
        st.markdown(
            "Default sources target **Catalyst 9300 (IOS XE 26.x)** and "
            "**CCS-720XP (EOS 4.36.1F)**. Run **Ingest sources** then "
            "**Build semantic index** in the sidebar (first run may take several minutes "
            "while the Cisco 16 MB PDF downloads)."
        )
        for vendor in ("cisco", "arista"):
            p = platforms.get(vendor, {})
            st.markdown(f"#### {p.get('product', vendor.title())}")
            st.caption(p.get("os", ""))
            for entry in cfg.get("sources", {}).get(vendor, {}).get("urls", []):
                if isinstance(entry, dict):
                    st.markdown(f"- {entry.get('name', entry.get('url', ''))}")
        st.markdown("### Add more sources")
        st.markdown(
            "Edit `config.yaml` — add local PDFs under `data/sources/` or new URLs "
            "(set `type: pdf` for remote PDFs). Re-ingest and rebuild the index."
        )
        st.info(f"Project root: `{ROOT}`")


if __name__ == "__main__":
    main()