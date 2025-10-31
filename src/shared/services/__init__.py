# -*- coding: utf-8 -*-
"""
Shared Services
"""
from .graph_rag_service import get_graph_rag_service
from .external_api_service import (
    get_dictionary_service,
    get_news_service,
    get_text_analysis_service,
    get_grammar_check_service,
    DictionaryService,
    NewsService,
    TextAnalysisService,
    GrammarCheckService
)

__all__ = [
    "get_graph_rag_service",
    "get_dictionary_service",
    "get_news_service",
    "get_text_analysis_service",
    "get_grammar_check_service",
    "DictionaryService",
    "NewsService",
    "TextAnalysisService",
    "GrammarCheckService"
]
