from __future__ import annotations

from typing import Any, Dict, List, Optional

from net_comd_comp.agent.cli_skeleton import cli_skeleton, structural_tokens
from net_comd_comp.agent.keywords import (
    keyword_overlap_score,
    query_tokens,
    search_phrases,
)
from net_comd_comp.agent.mappings import curated_search_phrases
from net_comd_comp.embeddings.ollama_embed import OllamaEmbeddings
from net_comd_comp.embeddings.vector_index import VectorIndex
from net_comd_comp.index.store import CommandIndex
from net_comd_comp.models import DocChunk, SearchHit


class SemanticSearcher:
    def __init__(
        self,
        command_index: CommandIndex,
        vector_index: VectorIndex,
        embedder: OllamaEmbeddings,
        *,
        top_k: int = 10,
        min_similarity: float = 0.32,
        cfg: Dict[str, Any] | None = None,
    ):
        self.command_index = command_index
        self.vector_index = vector_index
        self.embedder = embedder
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.cfg = cfg or {}

    def _phrase_hits(
        self,
        query: str,
        *,
        vendor: Optional[str] = None,
    ) -> List[SearchHit]:
        phrases = search_phrases(query, target_vendor=vendor)
        phrases.extend(curated_search_phrases(self.cfg, query))
        phrases = list(dict.fromkeys(phrases))
        ranked = self.command_index.search_phrases(phrases, vendor=vendor, limit=self.top_k)
        skeleton_ranked = self.command_index.search_skeleton(
            query, vendor=vendor, limit=self.top_k
        )
        hits: dict[int, SearchHit] = {}
        for chunk, score in ranked + skeleton_ranked:
            if chunk.id not in hits or hits[chunk.id].score < score:
                hits[chunk.id] = SearchHit(chunk=chunk, score=score)
        merged = sorted(hits.values(), key=lambda h: h.score, reverse=True)
        return merged[: self.top_k]

    def _merge_hits(
        self,
        semantic: List[SearchHit],
        phrase: List[SearchHit],
    ) -> List[SearchHit]:
        merged: dict[int, SearchHit] = {}
        for hit in phrase + semantic:
            cid = hit.chunk.id
            if cid not in merged or hit.score > merged[cid].score:
                merged[cid] = hit
        return sorted(merged.values(), key=lambda h: h.score, reverse=True)[: self.top_k]

    def search(
        self,
        query: str,
        *,
        vendor: Optional[str] = None,
    ) -> List[SearchHit]:
        phrase = self._phrase_hits(query, vendor=vendor)
        embed_text = cli_skeleton(query) or query
        qvec = self.embedder.embed_one(embed_text)
        semantic = self.vector_index.search(
            qvec,
            self.command_index,
            vendor=vendor,
            top_k=self.top_k,
            min_similarity=self.min_similarity,
        )
        return self._merge_hits(semantic, phrase)

    def search_both(self, query: str) -> Dict[str, List[SearchHit]]:
        return {
            "cisco": self.search(query, vendor="cisco"),
            "arista": self.search(query, vendor="arista"),
        }

    @staticmethod
    def best_score(hits: List[SearchHit]) -> float:
        return hits[0].score if hits else 0.0

    @staticmethod
    def retrieval_confidence(query: str, hits: List[SearchHit]) -> str:
        if not hits:
            return "none"
        tokens = query_tokens(query)
        top = hits[0]
        excerpt = f"{top.chunk.command_hint}\n{top.chunk.text}"
        overlap = keyword_overlap_score(excerpt, tokens)
        hay_tokens = set(structural_tokens(excerpt))
        skeleton_overlap = (
            len(set(tokens) & hay_tokens) / len(tokens) if tokens else 0.0
        )
        overlap = max(overlap, skeleton_overlap)
        score = top.score
        text_lower = excerpt.lower()
        skeleton = cli_skeleton(query)
        phrase_match = any(
            p in text_lower
            for p in search_phrases(query)
            if len(p.split()) >= 2
        ) or (skeleton and skeleton in cli_skeleton(excerpt))
        if phrase_match and score >= 0.7:
            return "high"
        if score >= 0.55 and (overlap >= 0.34 or phrase_match):
            return "high"
        if score >= 0.42 and (overlap >= 0.25 or phrase_match):
            return "medium"
        if score >= 0.32 or overlap >= 0.2 or phrase_match:
            return "low"
        return "none"