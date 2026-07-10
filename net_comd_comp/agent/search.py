from __future__ import annotations

from typing import Dict, List, Optional

from net_comd_comp.embeddings.ollama_embed import OllamaEmbeddings
from net_comd_comp.embeddings.vector_index import VectorIndex
from net_comd_comp.index.store import CommandIndex
from net_comd_comp.models import SearchHit


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

    def search(
        self,
        query: str,
        *,
        vendor: Optional[str] = None,
    ) -> List[SearchHit]:
        qvec = self.embedder.embed_one(query)
        return self.vector_index.search(
            qvec,
            self.command_index,
            vendor=vendor,
            top_k=self.top_k,
            min_similarity=self.min_similarity,
        )

    def search_both(self, query: str) -> Dict[str, List[SearchHit]]:
        return {
            "cisco": self.search(query, vendor="cisco"),
            "arista": self.search(query, vendor="arista"),
        }