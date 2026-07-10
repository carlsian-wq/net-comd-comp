from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import requests

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "nomic-embed-text"
DEFAULT_BATCH_SIZE = 32
DEFAULT_WORKERS = 2


class OllamaEmbeddings:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 180,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        workers: int = DEFAULT_WORKERS,
        num_thread: Optional[int] = None,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.batch_size = max(1, batch_size)
        self.workers = max(1, workers)
        self.num_thread = num_thread if num_thread and num_thread > 0 else None

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        payload = {"model": self.model, "input": texts}
        if self.num_thread is not None:
            payload["options"] = {"num_thread": self.num_thread}
        r = requests.post(
            f"{self.base_url}/api/embed",
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        embeddings = data.get("embeddings")
        if embeddings:
            return embeddings
        single = data.get("embedding")
        if single:
            return [single]
        return []

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        batches = [
            texts[i : i + self.batch_size]
            for i in range(0, len(texts), self.batch_size)
        ]
        if len(batches) == 1 or self.workers == 1:
            out: List[List[float]] = []
            for batch in batches:
                out.extend(self._embed_batch(batch))
            return out

        results: dict[int, List[List[float]]] = {}
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {
                pool.submit(self._embed_batch, batch): idx
                for idx, batch in enumerate(batches)
            }
            for fut in as_completed(futures):
                idx = futures[fut]
                results[idx] = fut.result()
        ordered: List[List[float]] = []
        for idx in range(len(batches)):
            ordered.extend(results[idx])
        return ordered

    def embed_one(self, text: str) -> List[float]:
        vecs = self.embed([text])
        return vecs[0] if vecs else []