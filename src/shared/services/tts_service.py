"""
TTS Service - OpenAI TTS API를 사용한 고품질 음성 생성 및 효과음 믹싱
"""
import os
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from datetime import datetime

# pydub는 효과음 믹싱에만 사용 (선택적)
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️  pydub not available - audio mixing disabled")


class TTSService:
    """OpenAI TTS를 사용한 듣기 문제 음성 생성"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.audio_dir = Path('/home/sh/projects/ClassMate/static/audio')
        self.effects_dir = Path('/home/sh/projects/ClassMate/static/effects')

        # 음성 매핑 (OpenAI TTS 음성)
        self.voice_map = {
            'Samantha': 'nova',      # Female - warm
            'Karen': 'shimmer',      # Female - gentle
            'Victoria': 'alloy',     # Female - neutral
            'David': 'onyx',         # Male - deep
            'Daniel': 'echo',        # Male - clear
            'Mark': 'fable',         # Male - expressive
        }

        # 효과음 파일 매핑 (카테고리별로 구성)
        self.effects = {
            # 기존 효과음 (호환성 유지)
            'phone_ring': 'phone_ring.mp3',
            'cafe_ambient': 'cafe_ambient.mp3',
            'office_ambient': 'office_ambient.mp3',
            'outdoor_ambient': 'outdoor_ambient.mp3',

            # 전화·메시지
            'smartphone_ring': 'smartphone_ring.mp3',
            'text_notification': 'text_notification.mp3',
            'call_connect': 'call_connect.mp3',

            # 문·출입
            'doorbell': 'doorbell.mp3',
            'door_knock': 'door_knock.mp3',
            'door_open_close': 'door_open_close.mp3',

            # 학교·사무
            'school_bell': 'school_bell.mp3',
            'keyboard_typing': 'keyboard_typing.mp3',
            'paper_shuffle': 'paper_shuffle.mp3',

            # 상점·카페
            'cash_register': 'cash_register.mp3',
            'coffee_machine': 'coffee_machine.mp3',

            # 교통·안내
            'subway_announcement': 'subway_announcement.mp3',
            'airport_boarding': 'airport_boarding.mp3',

            # 자연·야외
            'rain': 'rain.mp3',
            'birds_chirping': 'birds_chirping.mp3',

            # 병원
            'hospital_ambient': 'hospital_ambient.mp3',

            # 시험 전용
            'test_start_tone': 'test_start_tone.mp3',
            'test_end_tone': 'test_end_tone.mp3',
        }

    def parse_listening_problem(self, content: str) -> Tuple[List[Dict], Optional[str], Optional[str]]:
        """
        듣기 문제에서 [SPEAKERS]와 [AUDIO] 파싱

        Returns:
            (speakers, audio_text, effect_type)
        """
        speakers = []
        audio_text = None
        effect_type = None

        # [SPEAKERS]: 파싱
        speakers_match = re.search(r'\[SPEAKERS\]:\s*(.+?)(?:\n|$)', content)
        if speakers_match:
            try:
                speakers_json = json.loads(speakers_match.group(1).strip())
                speakers = speakers_json.get('speakers', [])
            except json.JSONDecodeError as e:
                print(f"⚠️ Failed to parse [SPEAKERS]: {e}")

        # [AUDIO]: 파싱 (대화 텍스트)
        # Extract from [AUDIO]: until question starts (What/Where/When/etc or a)/b)/c)
        audio_match = re.search(
            r'\[AUDIO\]:(.*?)(?=\n(?:What|Where|When|Who|Why|How) |\n[a-e]\)|\[Question\]|$)',
            content,
            re.DOTALL
        )
        if audio_match:
            audio_text = audio_match.group(1).strip()

        # [EFFECT]: 파싱 (효과음 타입)
        effect_match = re.search(r'\[EFFECT\]:\s*(\w+)', content)
        if effect_match:
            effect_type = effect_match.group(1).strip()

        return speakers, audio_text, effect_type

    def parse_dialogue_lines(self, audio_text: str) -> List[Dict]:
        """
        대화 텍스트를 개별 발화로 분리

        Example input:
            Emma: Hi, are you coming to the party?
            John: Yes, I'll be there at 7 PM.

        Returns:
            [{'speaker': 'Emma', 'text': 'Hi, are you coming to the party?'}, ...]
        """
        lines = []
        for line in audio_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            # "Speaker: text" 형식 파싱
            match = re.match(r'^([A-Za-z\s]+):\s*(.+)$', line)
            if match:
                speaker = match.group(1).strip()
                text = match.group(2).strip()
                lines.append({'speaker': speaker, 'text': text})

        return lines

    def get_openai_voice(self, speaker_name: str, speakers: List[Dict]) -> str:
        """
        화자의 OpenAI TTS 음성 결정

        Args:
            speaker_name: 화자 이름 (예: 'Emma')
            speakers: [SPEAKERS] 정보

        Returns:
            OpenAI voice name (nova, onyx, etc.)
        """
        # speakers에서 해당 화자 찾기
        speaker_info = next((s for s in speakers if s['name'] == speaker_name), None)

        if speaker_info and 'voice' in speaker_info:
            # 매핑된 음성 사용
            original_voice = speaker_info['voice']
            openai_voice = self.voice_map.get(original_voice, 'alloy')
            return openai_voice

        # 기본값: 성별로 결정
        if speaker_info and speaker_info.get('gender') == 'male':
            return 'onyx'
        else:
            return 'nova'

    def generate_tts_segment(self, text: str, voice: str, speed: float = 1.0) -> bytes:
        """
        OpenAI TTS로 음성 생성

        Args:
            text: 발화 텍스트
            voice: OpenAI voice (nova, onyx, etc.)
            speed: 속도 (0.25 ~ 4.0)

        Returns:
            MP3 audio bytes
        """
        try:
            print(f"🎤 Generating TTS: voice={voice}, text='{text[:50]}...'")

            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
                speed=speed
            )

            # Return audio bytes directly
            return response.content

        except Exception as e:
            print(f"❌ TTS generation failed: {e}")
            return b''  # Empty bytes on error

    def create_listening_audio(
        self,
        content: str,
        speed: float = 0.9
    ) -> Optional[str]:
        """
        듣기 문제 전체 오디오 생성 (화자별 음성 + 효과음 믹싱)

        Args:
            content: 문제 전체 텍스트 ([SPEAKERS], [AUDIO] 포함)
            speed: TTS 속도 (0.9 = 조금 느리게, 듣기에 적합)

        Returns:
            생성된 오디오 파일 경로 (예: '/static/audio/problem_abc123.mp3')
            실패 시 None
        """
        # 1. 파싱
        speakers, audio_text, effect_type = self.parse_listening_problem(content)

        if not audio_text:
            print("⚠️ No [AUDIO] content found")
            return None

        if not speakers:
            print("⚠️ No [SPEAKERS] info found")
            return None

        dialogue_lines = self.parse_dialogue_lines(audio_text)

        if not dialogue_lines:
            print("⚠️ No dialogue lines parsed")
            return None

        print(f"📝 Generating TTS for {len(dialogue_lines)} lines from {len(speakers)} speakers")

        # Check if pydub is available for multi-speaker support
        if not PYDUB_AVAILABLE:
            print("⚠️ pydub not available - using single voice fallback")
            # Fallback to simple version
            voice = 'alloy'
            if speakers and len(speakers) > 0:
                speaker_voice = speakers[0].get('voice', 'Samantha')
                voice = self.voice_map.get(speaker_voice, 'alloy')

            audio_bytes = self.generate_tts_segment(audio_text, voice, speed)
            if not audio_bytes:
                return None

            content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
            filename = f"listening_{content_hash}.mp3"
            output_path = self.audio_dir / filename

            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            print(f"✅ Audio saved (single voice): {output_path}")
            return f"/static/audio/{filename}"

        # 2. 각 발화를 개별 TTS로 생성 (화자별 다른 음성)
        combined_audio = AudioSegment.silent(duration=500)  # 0.5초 무음으로 시작

        for i, line in enumerate(dialogue_lines):
            speaker_name = line['speaker']
            text = line['text']

            # 음성 선택 (화자별)
            voice = self.get_openai_voice(speaker_name, speakers)

            print(f"  [{i+1}/{len(dialogue_lines)}] {speaker_name}: {text[:30]}... (voice={voice})")

            # TTS 생성
            audio_bytes = self.generate_tts_segment(text, voice, speed)

            if not audio_bytes:
                print(f"    ⚠️ TTS failed for line {i+1}, skipping")
                continue

            # bytes를 AudioSegment로 변환
            try:
                from io import BytesIO
                segment = AudioSegment.from_mp3(BytesIO(audio_bytes))

                # 결합 (발화 사이 0.3초 간격)
                combined_audio += segment
                combined_audio += AudioSegment.silent(duration=300)

            except Exception as e:
                print(f"    ⚠️ Failed to convert audio segment: {e}")
                continue

        # 3. 효과음 추가 (있으면)
        if effect_type and effect_type in self.effects:
            effect_file = self.effects_dir / self.effects[effect_type]
            if effect_file.exists():
                try:
                    effect = AudioSegment.from_mp3(str(effect_file))
                    # 효과음을 배경에 깔기 (볼륨 -20dB)
                    effect = effect - 20
                    # 효과음 길이를 대화 길이에 맞춤
                    if len(effect) < len(combined_audio):
                        effect = effect * (len(combined_audio) // len(effect) + 1)
                    effect = effect[:len(combined_audio)]

                    combined_audio = combined_audio.overlay(effect)
                    print(f"✅ Added sound effect: {effect_type}")
                except Exception as e:
                    print(f"⚠️ Failed to add effect: {e}")

        # 4. 파일 저장 (해시 기반 파일명)
        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        filename = f"listening_{content_hash}.mp3"
        output_path = self.audio_dir / filename

        try:
            combined_audio.export(str(output_path), format="mp3", bitrate="128k")
            print(f"✅ Audio saved: {output_path} ({len(combined_audio)}ms, {len(dialogue_lines)} segments)")

            # 웹에서 접근 가능한 경로 반환
            return f"/static/audio/{filename}"

        except Exception as e:
            print(f"❌ Failed to save audio: {e}")
            return None

    def get_or_create_audio(self, content: str, force_regenerate: bool = False) -> Optional[str]:
        """
        캐시된 오디오 파일이 있으면 반환, 없으면 생성

        Args:
            content: 문제 내용
            force_regenerate: True면 기존 파일 무시하고 재생성

        Returns:
            오디오 파일 URL
        """
        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        filename = f"listening_{content_hash}.mp3"
        file_path = self.audio_dir / filename

        # 캐시 확인
        if not force_regenerate and file_path.exists():
            print(f"✅ Using cached audio: {filename}")
            return f"/static/audio/{filename}"

        # 새로 생성
        return self.create_listening_audio(content)


# 싱글톤 인스턴스
_tts_service = None

def get_tts_service() -> TTSService:
    """TTS 서비스 싱글톤 getter"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
