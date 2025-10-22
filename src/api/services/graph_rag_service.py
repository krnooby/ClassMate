# -*- coding: utf-8 -*-
"""
GraphRAG Service (Proxy)
⚠️ DEPRECATED: This module has moved to shared.services.graph_rag_service

이 파일은 하위 호환성을 위해 유지되며, shared.services로 리다이렉트합니다.
새로운 코드에서는 `from shared.services import get_graph_rag_service`를 사용하세요.
"""
import warnings

# Deprecation warning
warnings.warn(
    "api.services.graph_rag_service is deprecated. "
    "Use 'from shared.services import get_graph_rag_service' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from shared.services.graph_rag_service import (
    GraphRAGService,
    get_graph_rag_service
)

__all__ = ["GraphRAGService", "get_graph_rag_service"]
