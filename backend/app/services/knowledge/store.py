"""知识库持久化：文档元数据 + 分块 + BM25 检索。"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jieba
from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.services.knowledge.aliases import expand_query
from app.services.knowledge.chunker import chunk_text
from app.services.knowledge.parser import parse_file


@dataclass
class DocumentMeta:
    id: str
    filename: str
    title: str
    competition: str = ""
    year: str = ""
    doc_type: str = "通知"
    active: bool = True
    chunk_count: int = 0
    created_at: str = ""
    source_path: str = ""


@dataclass
class ChunkRecord:
    id: str
    document_id: str
    content: str
    page: int | None = None
    index: int = 0
    filename: str = ""
    title: str = ""
    competition: str = ""
    year: str = ""
    doc_type: str = ""


@dataclass
class RetrievedChunk:
    chunk: ChunkRecord
    score: float
    rank: int


@dataclass
class KnowledgeStore:
    root: Path
    documents: dict[str, DocumentMeta] = field(default_factory=dict)
    chunks: list[ChunkRecord] = field(default_factory=list)
    _bm25: BM25Okapi | None = field(default=None, repr=False)
    _tokenized: list[list[str]] = field(default_factory=list, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    @property
    def docs_dir(self) -> Path:
        return self.root / "files"

    @property
    def meta_path(self) -> Path:
        return self.root / "documents.json"

    @property
    def chunks_path(self) -> Path:
        return self.root / "chunks.json"

    def ensure(self) -> None:
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        if not self.meta_path.exists():
            self.meta_path.write_text("[]", encoding="utf-8")
        if not self.chunks_path.exists():
            self.chunks_path.write_text("[]", encoding="utf-8")

    def load(self) -> None:
        with self._lock:
            self.ensure()
            docs = json.loads(self.meta_path.read_text(encoding="utf-8") or "[]")
            chunks = json.loads(self.chunks_path.read_text(encoding="utf-8") or "[]")
            self.documents = {d["id"]: DocumentMeta(**d) for d in docs}
            self.chunks = [ChunkRecord(**c) for c in chunks]
            self._rebuild_index()

    def save(self) -> None:
        with self._lock:
            self.meta_path.write_text(
                json.dumps([asdict(d) for d in self.documents.values()], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.chunks_path.write_text(
                json.dumps([asdict(c) for c in self.chunks], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _tokenize(self, text: str) -> list[str]:
        return [t.strip() for t in jieba.lcut(text) if t.strip() and t.strip() not in "，。！？、；：""''（）【】《》\n\t "]

    def _rebuild_index(self) -> None:
        active_ids = {d.id for d in self.documents.values() if d.active}
        active_chunks = [c for c in self.chunks if c.document_id in active_ids]
        self.chunks = active_chunks + [c for c in self.chunks if c.document_id not in active_ids]
        # BM25 只索引 active
        corpus = [c for c in self.chunks if c.document_id in active_ids]
        self._active_chunks = corpus  # type: ignore[attr-defined]
        self._tokenized = [self._tokenize(c.content) for c in corpus]
        self._bm25 = BM25Okapi(self._tokenized) if self._tokenized else None

    def list_documents(self) -> list[DocumentMeta]:
        return sorted(self.documents.values(), key=lambda d: d.created_at, reverse=True)

    def ingest_bytes(
        self,
        *,
        filename: str,
        data: bytes,
        title: str = "",
        competition: str = "",
        year: str = "",
        doc_type: str = "通知",
        defer_index: bool = False,
    ) -> DocumentMeta:
        with self._lock:
            self.ensure()
            doc_id = uuid.uuid4().hex
            safe_name = f"{doc_id}_{Path(filename).name}"
            dest = self.docs_dir / safe_name
            dest.write_bytes(data)

            text = parse_file(dest)
            pieces = chunk_text(text)
            now = datetime.now(timezone.utc).isoformat()
            meta = DocumentMeta(
                id=doc_id,
                filename=filename,
                title=title or Path(filename).stem,
                competition=competition,
                year=year,
                doc_type=doc_type,
                active=True,
                chunk_count=len(pieces),
                created_at=now,
                source_path=str(dest),
            )
            new_chunks = [
                ChunkRecord(
                    id=f"{doc_id}_{p.index}",
                    document_id=doc_id,
                    content=p.content,
                    page=p.page,
                    index=p.index,
                    filename=filename,
                    title=meta.title,
                    competition=competition,
                    year=year,
                    doc_type=doc_type,
                )
                for p in pieces
            ]
            self.documents[doc_id] = meta
            self.chunks.extend(new_chunks)
            if not defer_index:
                self._rebuild_index()
                self.save()
            return meta

    def commit(self) -> None:
        """批量入库后统一重建索引并落盘。"""
        with self._lock:
            self._rebuild_index()
            self.save()

    def set_active(self, doc_id: str, active: bool) -> DocumentMeta:
        with self._lock:
            if doc_id not in self.documents:
                raise KeyError(doc_id)
            self.documents[doc_id].active = active
            self._rebuild_index()
            self.save()
            return self.documents[doc_id]

    def delete(self, doc_id: str) -> None:
        with self._lock:
            meta = self.documents.pop(doc_id, None)
            if not meta:
                raise KeyError(doc_id)
            self.chunks = [c for c in self.chunks if c.document_id != doc_id]
            path = Path(meta.source_path)
            if path.exists():
                path.unlink(missing_ok=True)
            self._rebuild_index()
            self.save()

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        competition: str | None = None,
        year: str | None = None,
    ) -> list[RetrievedChunk]:
        with self._lock:
            if not self._bm25:
                return []
            active_ids = {d.id for d in self.documents.values() if d.active}
            corpus: list[ChunkRecord] = [
                c
                for c in self.chunks
                if c.document_id in active_ids
                and (not competition or competition in (c.competition or c.title or ""))
                and (not year or year in (c.year or ""))
            ]
            if not corpus:
                return []
            # 简称/小名扩展，例如「大挑」→「挑战杯…」
            expanded = expand_query(query)
            tokenized = [self._tokenize(c.content) for c in corpus]
            bm25 = BM25Okapi(tokenized)
            scores = bm25.get_scores(self._tokenize(expanded))
            ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[: max(top_k * 2, top_k)]
            results: list[RetrievedChunk] = []
            for rank, (i, score) in enumerate(ranked, start=1):
                if score <= 0:
                    continue
                results.append(RetrievedChunk(chunk=corpus[i], score=float(score), rank=rank))
                if len(results) >= top_k:
                    break
            return results

    def stats(self) -> dict[str, Any]:
        active_ids = {d.id for d in self.documents.values() if d.active}
        return {
            "documents": len(self.documents),
            "active_documents": len(active_ids),
            "chunks": len([c for c in self.chunks if c.document_id in active_ids]),
        }


_store: KnowledgeStore | None = None
_store_lock = threading.Lock()


def get_knowledge_store() -> KnowledgeStore:
    global _store
    with _store_lock:
        if _store is None:
            settings = get_settings()
            root = Path(settings.knowledge_dir).resolve()
            store = KnowledgeStore(root=root)
            store.load()
            _store = store
        return _store
