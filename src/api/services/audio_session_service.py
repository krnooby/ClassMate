# -*- coding: utf-8 -*-
"""
Audio Session Service
세션별 오디오 파일 추적 및 정리
"""
from __future__ import annotations
from typing import Dict, List, Set
from pathlib import Path
import json
import os

class AudioSessionService:
    """세션별 오디오 파일 관리"""

    _instance = None

    def __init__(self):
        self.session_audio_map: Dict[str, Set[str]] = {}
        self.tracking_file = Path("data/audio_sessions.json")
        self._load_tracking_data()

    @classmethod
    def get_instance(cls):
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = AudioSessionService()
        return cls._instance

    def _load_tracking_data(self):
        """저장된 추적 데이터 로드"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    data = json.load(f)
                    # JSON에서 list를 set으로 변환
                    self.session_audio_map = {
                        k: set(v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"Warning: Failed to load audio tracking data: {e}")
                self.session_audio_map = {}

    def _save_tracking_data(self):
        """추적 데이터 저장"""
        try:
            self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
            # set을 list로 변환하여 JSON 저장
            data = {k: list(v) for k, v in self.session_audio_map.items()}
            with open(self.tracking_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save audio tracking data: {e}")

    def track_audio(self, session_id: str, audio_path: str):
        """세션에 오디오 파일 연결"""
        if session_id not in self.session_audio_map:
            self.session_audio_map[session_id] = set()

        self.session_audio_map[session_id].add(audio_path)
        self._save_tracking_data()
        print(f"📎 Tracked: {audio_path} → session {session_id}")

    def get_session_audio(self, session_id: str) -> List[str]:
        """세션의 모든 오디오 파일 반환"""
        return list(self.session_audio_map.get(session_id, set()))

    def cleanup_session(self, session_id: str) -> int:
        """세션의 모든 오디오 파일 삭제"""
        if session_id not in self.session_audio_map:
            return 0

        audio_files = self.session_audio_map[session_id]
        deleted_count = 0

        for audio_path in audio_files:
            file_path = Path(audio_path)
            if file_path.exists():
                try:
                    file_path.unlink()
                    deleted_count += 1
                    print(f"🗑️  Deleted: {audio_path}")
                except Exception as e:
                    print(f"Warning: Failed to delete {audio_path}: {e}")

        # 세션 정보 제거
        del self.session_audio_map[session_id]
        self._save_tracking_data()

        print(f"✅ Cleaned up {deleted_count} audio files for session {session_id}")
        return deleted_count

    def cleanup_all_orphaned(self) -> int:
        """추적되지 않는 오디오 파일 모두 삭제"""
        audio_dir = Path("static/audio")
        if not audio_dir.exists():
            return 0

        # 모든 추적 중인 파일 목록
        tracked_files = set()
        for files in self.session_audio_map.values():
            tracked_files.update(files)

        deleted_count = 0
        for mp3_file in audio_dir.glob("*.mp3"):
            file_str = str(mp3_file)
            if file_str not in tracked_files:
                try:
                    mp3_file.unlink()
                    deleted_count += 1
                    print(f"🗑️  Deleted orphaned: {mp3_file.name}")
                except Exception as e:
                    print(f"Warning: Failed to delete {mp3_file}: {e}")

        print(f"✅ Cleaned up {deleted_count} orphaned audio files")
        return deleted_count
