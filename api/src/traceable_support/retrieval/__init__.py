"""Model-aware hybrid retrieval."""

from .hybrid import (
    BusinessRetrievalRequest as RetrievalRequest,
    BusinessRetrievalResult as EvidenceBundle,
    ModelAwareRrfPipeline,
)

Retriever = ModelAwareRrfPipeline

__all__ = ["EvidenceBundle", "ModelAwareRrfPipeline", "RetrievalRequest", "Retriever"]
