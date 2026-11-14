"""Chunks returned by a retriever, with the score that ranked them."""

from typing import Literal

from open_rag_engine.domain.base import DomainModel
from open_rag_engine.domain.chunk import Chunk

ScoreSource = Literal["dense", "bm25", "fused", "reranked"]
"""Which method produced a score. Scores are only comparable within one source."""


class ScoredChunk(DomainModel):
    chunk: Chunk
    score: float
    source: ScoreSource
