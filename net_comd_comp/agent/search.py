from __future__ import annotations

from typing import Dict, List, Optional

from net_comd_comp.agent.keywords import keyword_overlap_score, query_tokens
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

    def _keyword_hits(self, query: str, *, vendor: Optional[str] = None) -> List[SearchHit]:
        chunks = self.command_index.search_keywords(query, vendor=vendor, limit=self.top_k)
        tokens = query_tokens(query)
        hits: List[SearchHit] = []
        for chunk in chunks:
            overlap = keyword_overlap_score(
                f"{chunk.command_hint}\n{chunk.text}",
                tokens,
            )
            if overlap <= 0:
                continue
            score = 0.55 + (0.45 * overlap)
            hits.append(SearchHit(chunk=chunk, score=score))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[: self.top_k]

    def _merge_hits(
        self,
        semantic: List[SearchHit],
        keyword: List[SearchHit],
    ) -> List[SearchHit]:
        merged: dict[int, SearchHit] = {}
        for hit in semantic + keyword:
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
        qvec = self.embedder.embed_one(query)
        semantic = self.vector_index.search(
            qvec,
            self.command_index,
            vendor=vendor,
            top_k=self.top_k,
            min_similarity=self.min_similarity,
        )
        keyword = self._keyword_hits(query, vendor=vendor)
        return self._merge_hits(semantic, keyword)

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
        overlap = keyword_overlap_score(
            f"{hits[0].chunk.command_hint}\n{hits[0].chunk.text}",
            tokens,
        )
        score = hits[0].score
        if score >= 0.55 and overlap >= 0.5:
            return "high"
        if score >= 0.42 and overlap >= 0.25:
            return "medium"
        if score >= 0.32 or overlap >= 0.2:
            return "low"
        return "none"