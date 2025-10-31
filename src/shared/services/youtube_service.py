# -*- coding: utf-8 -*-
"""
YouTube Service
YouTube Data API v3를 사용하여 교육용 영상 검색
"""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv()


class YouTubeService:
    """YouTube Data API v3 서비스"""

    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.base_url = "https://www.googleapis.com/youtube/v3"

    def search_videos(
        self,
        query: str,
        max_results: int = 5,
        video_duration: str = "any",  # any, short, medium, long
        order: str = "relevance"  # relevance, rating, viewCount, date
    ) -> List[Dict[str, Any]]:
        """
        YouTube 영상 검색

        Args:
            query: 검색 쿼리 (예: "English listening A1 level for kids")
            max_results: 반환할 최대 결과 수 (기본: 5)
            video_duration: 영상 길이 필터 (any, short(<4분), medium(4-20분), long(>20분))
            order: 정렬 방식

        Returns:
            검색 결과 리스트 (제목, 채널명, 링크, 썸네일, 조회수 등)
        """
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY not found in environment variables")

        # API 요청 파라미터
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "videoDuration": video_duration,
            "order": order,
            "relevanceLanguage": "en",  # 영어 콘텐츠 우선
            "safeSearch": "strict",  # 안전 검색 활성화 (교육용)
            "key": self.api_key
        }

        try:
            # YouTube Search API 호출
            response = requests.get(f"{self.base_url}/search", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 결과 파싱
            videos = []
            for item in data.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]

                videos.append({
                    "title": snippet["title"],
                    "channel": snippet["channelTitle"],
                    "description": snippet["description"],
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": snippet["thumbnails"]["medium"]["url"],
                    "published_at": snippet["publishedAt"]
                })

            return videos

        except requests.exceptions.RequestException as e:
            print(f"❌ YouTube API Error: {str(e)}")
            return []

    def search_channels(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        YouTube 채널 검색

        Args:
            query: 검색 쿼리 (예: "English learning channel for kids")
            max_results: 반환할 최대 결과 수

        Returns:
            검색 결과 리스트 (채널명, 링크, 설명, 구독자 수 등)
        """
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY not found in environment variables")

        params = {
            "part": "snippet",
            "q": query,
            "type": "channel",
            "maxResults": max_results,
            "relevanceLanguage": "en",
            "key": self.api_key
        }

        try:
            response = requests.get(f"{self.base_url}/search", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            channels = []
            for item in data.get("items", []):
                channel_id = item["id"]["channelId"]
                snippet = item["snippet"]

                channels.append({
                    "title": snippet["channelTitle"],
                    "description": snippet["description"],
                    "channel_id": channel_id,
                    "url": f"https://www.youtube.com/channel/{channel_id}",
                    "thumbnail": snippet["thumbnails"]["medium"]["url"]
                })

            return channels

        except requests.exceptions.RequestException as e:
            print(f"❌ YouTube API Error: {str(e)}")
            return []

    def get_video_statistics(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        영상 통계 조회 (조회수, 좋아요, 댓글 수 등)

        Args:
            video_id: YouTube 영상 ID

        Returns:
            통계 정보 딕셔너리
        """
        if not self.api_key:
            return None

        params = {
            "part": "statistics",
            "id": video_id,
            "key": self.api_key
        }

        try:
            response = requests.get(f"{self.base_url}/videos", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("items"):
                stats = data["items"][0]["statistics"]
                return {
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0))
                }

            return None

        except requests.exceptions.RequestException as e:
            print(f"❌ YouTube API Error: {str(e)}")
            return None


# 싱글톤 인스턴스
_youtube_service_instance: Optional[YouTubeService] = None


def get_youtube_service() -> YouTubeService:
    """YouTube Service 싱글톤 인스턴스 반환"""
    global _youtube_service_instance
    if _youtube_service_instance is None:
        _youtube_service_instance = YouTubeService()
    return _youtube_service_instance
