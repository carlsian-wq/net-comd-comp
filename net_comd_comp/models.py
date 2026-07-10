from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DocChunk:
    id: int
    vendor: str
    source_name: str
    source_type: str
    source_ref: str
    text: str
    command_hint: str = ""


@dataclass
class SearchHit:
    chunk: DocChunk
    score: float


@dataclass
class CompareResult:
    query: str
    direction: str
    source_vendor: str
    target_vendor: str
    source_command: str
    target_command: str
    explanation: str
    differences: List[str]
    caveats: List[str]
    citations: List[str]
    raw_response: str = ""
    confidence: str = "low"
    retrieval_note: str = ""