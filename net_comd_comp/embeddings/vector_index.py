from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np

from net_comd_comp.embeddings.ollama_embed import OllamaEmbeddings
from net_comd_comp.index.store import CommandIndex
from net_comd_comp.models import DocChunk, SearchHit

ProgressFn = Optional[Callable[[int, int], None]]


class VectorIndex:
    def __init__(self, data_dir: Path, model: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.path = self.data_dir / "semantic_commands.npz"
        self.meta_path = self.data_dir / "semantic_commands.json"
        self._vectors: Optional[np.ndarray] = None
        self._chunk_ids: Optional[np.ndarray] = None
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._vectors = None
            self._chunk_ids = np.array([], dtype=np.int64)
            return
        data = np.load(self.path)
        self._vectors = data["vectors"]
        self._chunk_ids = data["chunk_ids"]

    @property
    def count(self) -> int:
        return int(len(self._chunk_ids)) if self._chunk_ids is not None else 0

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
        if self.meta_path.exists():
            self.meta_path.unlink()
        self._vectors = None
        self._chunk_ids = np.array([], dtype=np.int64)

    def _save(self) -> None:
        if self._vectors is None or self._chunk_ids is None or len(self._chunk_ids) == 0:
            return
        np.savez_compressed(self.path, vectors=self._vectors, chunk_ids=self._chunk_ids)
        meta = {
            "model": self.model,
            "count": int(len(self._chunk_ids)),
            "built_at": datetime.now().isoformat(),
            "dims": int(self._vectors.shape[1]),
        }
        self.meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def build(
        self,
        command_index: CommandIndex,
        embedder: OllamaEmbeddings,
        *,
        vendor: Optional[str] = None,
        on_progress: ProgressFn = None,
    ) -> int:
        chunks = command_index.fetch_all(vendor=vendor)
        if not chunks:
            return 0
        existing = set(self._chunk_ids.tolist()) if self._chunk_ids is not None else set()
        todo = [c for c in chunks if c.id not in existing]
        if not todo:
            return 0

        texts = [f"{c.command_hint}\n{c.text}" for c in todo]
        ids = [c.id for c in todo]
        total = len(texts)
        batch_size = embedder.batch_size
        new_vectors: List[np.ndarray] = []

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            vecs = embedder.embed(texts[start:end])
            new_vectors.extend(np.asarray(v, dtype=np.float32) for v in vecs)
            if on_progress:
                on_progress(end, total)

        mat = np.vstack(new_vectors)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        mat = mat / np.maximum(norms, 1e-9)

        id_arr = np.asarray(ids, dtype=np.int64)
        if self._vectors is None or len(self._chunk_ids) == 0:
            self._vectors = mat
            self._chunk_ids = id_arr
        else:
            self._vectors = np.vstack([self._vectors, mat])
            self._chunk_ids = np.concatenate([self._chunk_ids, id_arr])
        self._save()
        return len(todo)

    def search(
        self,
        query_vec: List[float],
        command_index: CommandIndex,
        *,
        vendor: Optional[str] = None,
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> List[SearchHit]:
        if self._vectors is None or self._chunk_ids is None or len(self._chunk_ids) == 0:
            return []
        q = np.asarray(query_vec, dtype=np.float32)
        q = q / max(np.linalg.norm(q), 1e-9)
        scores = self._vectors @ q
        order = np.argsort(scores)[::-1]

        hits: List[SearchHit] = []
        chunk_cache: dict[int, DocChunk] = {}
        for idx in order:
            score = float(scores[idx])
            if score < min_similarity:
                break
            chunk_id = int(self._chunk_ids[idx])
            if chunk_id not in chunk_cache:
                rows = command_index.fetch_by_ids([chunk_id])
                if not rows:
                    continue
                chunk_cache[chunk_id] = rows[0]
            chunk = chunk_cache[chunk_id]
            if vendor and chunk.vendor != vendor:
                continue
            hits.append(SearchHit(chunk=chunk, score=score))
            if len(hits) >= top_k:
                break
        return hits