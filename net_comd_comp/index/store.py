from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from net_comd_comp.models import DocChunk

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    text TEXT NOT NULL,
    command_hint TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_vendor ON chunks(vendor);
CREATE UNIQUE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(vendor, content_hash);
"""


class CommandIndex:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def upsert_chunks(
        self,
        vendor: str,
        source_name: str,
        source_type: str,
        source_ref: str,
        chunks: Iterable[Tuple[str, str]],
    ) -> int:
        now = datetime.now().isoformat()
        added = 0
        with self._connect() as conn:
            for text, hint in chunks:
                h = self._hash(text)
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO chunks
                    (vendor, source_name, source_type, source_ref, text, command_hint, content_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (vendor, source_name, source_type, source_ref, text, hint, h, now),
                )
                added += cur.rowcount
            conn.commit()
        return added

    def count(self, vendor: Optional[str] = None) -> int:
        with self._connect() as conn:
            if vendor:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM chunks WHERE vendor = ?",
                    (vendor,),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()
        return int(row["c"])

    def list_sources(self) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT vendor, source_name, source_type, source_ref, COUNT(*) AS chunks
                FROM chunks
                GROUP BY vendor, source_name, source_type, source_ref
                ORDER BY vendor, source_name
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def fetch_all(self, vendor: Optional[str] = None, limit: int = 50000) -> List[DocChunk]:
        sql = "SELECT * FROM chunks"
        params: tuple = ()
        if vendor:
            sql += " WHERE vendor = ?"
            params = (vendor,)
        sql += " ORDER BY id DESC LIMIT ?"
        params = (*params, limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_chunk(r) for r in rows]

    def fetch_by_ids(self, ids: List[int]) -> List[DocChunk]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM chunks WHERE id IN ({placeholders})",
                ids,
            ).fetchall()
        by_id = {int(r["id"]): self._row_to_chunk(r) for r in rows}
        return [by_id[i] for i in ids if i in by_id]

    @staticmethod
    def _row_to_chunk(row: sqlite3.Row) -> DocChunk:
        return DocChunk(
            id=int(row["id"]),
            vendor=row["vendor"],
            source_name=row["source_name"],
            source_type=row["source_type"],
            source_ref=row["source_ref"],
            text=row["text"],
            command_hint=row["command_hint"] or "",
        )

    def clear_vendor(self, vendor: str) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM chunks WHERE vendor = ?", (vendor,))
            conn.commit()
            return cur.rowcount

    def search_phrases(
        self,
        phrases: Iterable[str],
        *,
        vendor: Optional[str] = None,
        limit: int = 12,
    ) -> List[tuple[DocChunk, float]]:
        """Return chunks ranked by longest matching phrase (best for CLI lookups)."""
        ranked: dict[int, tuple[DocChunk, float]] = {}
        for phrase in phrases:
            p = phrase.strip().lower()
            if len(p) < 3:
                continue
            sql = "SELECT * FROM chunks WHERE (lower(text) LIKE ? OR lower(command_hint) LIKE ?)"
            params: list = [f"%{p}%", f"%{p}%"]
            if vendor:
                sql += " AND vendor = ?"
                params.append(vendor)
            sql += " ORDER BY length(text) ASC LIMIT ?"
            params.append(limit)
            with self._connect() as conn:
                rows = conn.execute(sql, params).fetchall()
            phrase_score = min(0.98, 0.72 + (len(p.split()) * 0.06))
            for row in rows:
                chunk = self._row_to_chunk(row)
                if chunk.id not in ranked or ranked[chunk.id][1] < phrase_score:
                    ranked[chunk.id] = (chunk, phrase_score)
        return sorted(ranked.values(), key=lambda x: x[1], reverse=True)[:limit]