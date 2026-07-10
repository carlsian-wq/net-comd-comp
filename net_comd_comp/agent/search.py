from __future__ import annotations

from typing import Dict, List, Optional

from net_comd_comp.agent.keywords import (
    keyword_overlap_score,
    query_tokens,
    search_phrases,
)
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
    ):
        self.command_index = command_index
        self.vector_index = vector_index
        self.embedder = embedder
        self.top_k = top_k
        self.min_similarity = min_similarity

    def _phrase_hits(
        self,
        query: str,
        *,
        vendor: Optional[str] = None,
    ) -> List[SearchHit]:
        phrases = search_phrases(query, target_vendor=vendor)
        ranked = self.command_index.search_phrases(phrases, vendor=vendor, limit=self.top_k)
        return [SearchHit(chunk=chunk, score=score) for chunk, score in ranked]

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
        qvec = self.embedder.embed_one(query)
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
        overlap = keyword_overlap_score(
            f"{top.chunk.command_hint}\n{top.chunk.text}",
            tokens,
        )
        score = top.score
        text_lower = f"{top.chunk.command_hint}\n{top.chunk.text}".lower()
        phrase_match = any(
            p in text_lower
            for p in search_phrases(query)
            if len(p.split()) >= 2
        )
        if phrase_match and score >= 0.7:
            return "high"
        if score >= 0.55 and (overlap >= 0.34 or phrase_match):
            return "high"
        if score >= 0.42 and (overlap >= 0.25 or phrase_match):
            return "medium"
        if score >= 0.32 or overlap >= 0.2 or phrase_match:
            return "low"
        return "none"