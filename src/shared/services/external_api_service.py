"""
External API Services
외부 API 통합 서비스 (Dictionary, News, Text Analysis, Grammar Check)
"""
import os
import requests
from typing import Dict, List, Any, Optional
import json


class DictionaryService:
    """
    Free Dictionary API
    영어 단어 검색 서비스 (무료, API 키 불필요)
    """

    BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"

    @staticmethod
    def lookup_word(word: str) -> Dict[str, Any]:
        """
        단어 검색

        Args:
            word: 검색할 영어 단어

        Returns:
            Dict with word, phonetic, definition, example, synonyms
        """
        try:
            url = f"{DictionaryService.BASE_URL}/{word}"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                return {
                    "error": f"Word '{word}' not found",
                    "success": False
                }

            data = response.json()[0]

            # 첫 번째 정의 추출
            meaning = data.get('meanings', [{}])[0]
            definition_data = meaning.get('definitions', [{}])[0]

            return {
                "success": True,
                "word": word,
                "phonetic": data.get('phonetic', ''),
                "phonetics": [
                    {
                        "text": p.get('text', ''),
                        "audio": p.get('audio', '')
                    }
                    for p in data.get('phonetics', [])
                ],
                "part_of_speech": meaning.get('partOfSpeech', ''),
                "definition": definition_data.get('definition', ''),
                "example": definition_data.get('example', ''),
                "synonyms": definition_data.get('synonyms', [])[:5],  # 최대 5개
                "antonyms": definition_data.get('antonyms', [])[:5]
            }

        except Exception as e:
            print(f"❌ Dictionary API error: {e}")
            return {
                "error": str(e),
                "success": False
            }


class NewsService:
    """
    NewsAPI
    영어 뉴스 기사 검색 서비스
    """

    BASE_URL = "https://newsapi.org/v2/top-headlines"

    def __init__(self):
        self.api_key = os.getenv("NEWS_API_KEY")
        if not self.api_key:
            print("⚠️  NEWS_API_KEY not found in environment variables")

    def fetch_news(
        self,
        category: str = "general",
        language: str = "en",
        page_size: int = 5,
        country: str = "us"
    ) -> Dict[str, Any]:
        """
        최신 영어 뉴스 기사 가져오기

        Args:
            category: 카테고리 (general, sports, technology, health, science, entertainment)
            language: 언어 코드 (en)
            page_size: 가져올 기사 수 (1-100)
            country: 국가 코드 (us, gb, etc.)

        Returns:
            Dict with articles list
        """
        if not self.api_key:
            return {
                "error": "NEWS_API_KEY not configured",
                "success": False,
                "articles": []
            }

        try:
            params = {
                "apiKey": self.api_key,
                "category": category,
                "language": language,
                "pageSize": min(page_size, 10),  # 최대 10개
                "country": country
            }

            response = requests.get(self.BASE_URL, params=params, timeout=10)

            if response.status_code != 200:
                return {
                    "error": f"NewsAPI returned status {response.status_code}",
                    "success": False,
                    "articles": []
                }

            data = response.json()

            articles = []
            for article in data.get('articles', []):
                articles.append({
                    "title": article.get('title', ''),
                    "description": article.get('description', ''),
                    "content": article.get('content', '') or article.get('description', ''),
                    "url": article.get('url', ''),
                    "source": article.get('source', {}).get('name', ''),
                    "published_at": article.get('publishedAt', ''),
                    "image_url": article.get('urlToImage', '')
                })

            return {
                "success": True,
                "total": len(articles),
                "articles": articles
            }

        except Exception as e:
            print(f"❌ NewsAPI error: {e}")
            return {
                "error": str(e),
                "success": False,
                "articles": []
            }


class TextAnalysisService:
    """
    Text Inspector API (또는 대안)
    텍스트 CEFR 레벨 및 가독성 분석

    Note: Text Inspector는 유료 API입니다.
    무료 대안으로 textstat 라이브러리 사용
    """

    @staticmethod
    def analyze_cefr_level(text: str) -> Dict[str, Any]:
        """
        텍스트의 CEFR 레벨 분석

        Args:
            text: 분석할 영어 텍스트

        Returns:
            Dict with cefr_level, readability_score, etc.
        """
        try:
            # textstat 라이브러리 사용 (무료)
            import textstat

            # Flesch Reading Ease (0-100, 높을수록 쉬움)
            flesch_score = textstat.flesch_reading_ease(text)

            # Flesch-Kincaid Grade Level
            fk_grade = textstat.flesch_kincaid_grade(text)

            # CEFR 레벨 추정
            # A1: 매우 쉬움 (90-100)
            # A2: 쉬움 (80-90)
            # B1: 보통 (70-80)
            # B2: 어려움 (60-70)
            # C1: 매우 어려움 (50-60)
            # C2: 전문가 (0-50)
            if flesch_score >= 90:
                cefr_level = "A1"
            elif flesch_score >= 80:
                cefr_level = "A2"
            elif flesch_score >= 70:
                cefr_level = "B1"
            elif flesch_score >= 60:
                cefr_level = "B2"
            elif flesch_score >= 50:
                cefr_level = "C1"
            else:
                cefr_level = "C2"

            # 문장/단어 통계
            sentence_count = textstat.sentence_count(text)
            word_count = textstat.lexicon_count(text, removepunct=True)
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0

            return {
                "success": True,
                "cefr_level": cefr_level,
                "flesch_reading_ease": round(flesch_score, 2),
                "flesch_kincaid_grade": round(fk_grade, 2),
                "word_count": word_count,
                "sentence_count": sentence_count,
                "avg_sentence_length": round(avg_sentence_length, 2),
                "difficulty": "Easy" if flesch_score >= 70 else "Medium" if flesch_score >= 50 else "Hard"
            }

        except ImportError:
            return {
                "error": "textstat library not installed. Run: pip install textstat",
                "success": False
            }
        except Exception as e:
            print(f"❌ Text analysis error: {e}")
            return {
                "error": str(e),
                "success": False
            }


class GrammarCheckService:
    """
    LanguageTool API
    문법 검사 서비스 (무료)
    """

    BASE_URL = "https://api.languagetool.org/v2/check"

    @staticmethod
    def check_grammar(text: str, language: str = "en-US") -> Dict[str, Any]:
        """
        문법 검사

        Args:
            text: 검사할 텍스트
            language: 언어 코드 (en-US, en-GB)

        Returns:
            Dict with errors list
        """
        try:
            data = {
                "text": text,
                "language": language
            }

            response = requests.post(
                GrammarCheckService.BASE_URL,
                data=data,
                timeout=15
            )

            if response.status_code != 200:
                return {
                    "error": f"LanguageTool returned status {response.status_code}",
                    "success": False,
                    "errors": []
                }

            result = response.json()

            errors = []
            for match in result.get('matches', []):
                errors.append({
                    "message": match.get('message', ''),
                    "short_message": match.get('shortMessage', ''),
                    "offset": match.get('offset', 0),
                    "length": match.get('length', 0),
                    "replacements": [
                        r.get('value', '')
                        for r in match.get('replacements', [])[:3]  # 최대 3개 제안
                    ],
                    "rule": match.get('rule', {}).get('id', ''),
                    "category": match.get('rule', {}).get('category', {}).get('name', '')
                })

            return {
                "success": True,
                "error_count": len(errors),
                "errors": errors
            }

        except Exception as e:
            print(f"❌ Grammar check error: {e}")
            return {
                "error": str(e),
                "success": False,
                "errors": []
            }


# Singleton instances
_dictionary_service = None
_news_service = None
_text_analysis_service = None
_grammar_check_service = None


def get_dictionary_service() -> DictionaryService:
    """Get singleton DictionaryService instance"""
    global _dictionary_service
    if _dictionary_service is None:
        _dictionary_service = DictionaryService()
    return _dictionary_service


def get_news_service() -> NewsService:
    """Get singleton NewsService instance"""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service


def get_text_analysis_service() -> TextAnalysisService:
    """Get singleton TextAnalysisService instance"""
    global _text_analysis_service
    if _text_analysis_service is None:
        _text_analysis_service = TextAnalysisService()
    return _text_analysis_service


def get_grammar_check_service() -> GrammarCheckService:
    """Get singleton GrammarCheckService instance"""
    global _grammar_check_service
    if _grammar_check_service is None:
        _grammar_check_service = GrammarCheckService()
    return _grammar_check_service
