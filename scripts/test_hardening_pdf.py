"""Quick check: hardening PDF text and key ICMP commands."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from net_comd_comp.ingest.pdf_loader import extract_pdf_text
from net_comd_comp.ingest.chunker import chunk_text, dedupe_chunks
from net_comd_comp.ingest.quality import filter_chunks

pdf = ROOT / "data/sources/arista-eos-hardening-guide.pdf"
text = extract_pdf_text(pdf)
print(f"chars: {len(text)}")
patterns = [
    "rate-limit-unreachable",
    "no ip icmp redirect",
    "ip icmp redirect",
    "icmp rate-limit",
]
for p in patterns:
    print(f"  {p!r}: {p.lower() in text.lower()}")

chunks = filter_chunks(dedupe_chunks(chunk_text(text)))
print(f"usable chunks: {len(chunks)}")
if chunks:
    print("sample hint:", chunks[0][1][:100])