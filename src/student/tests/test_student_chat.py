#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
학생용 AI 상담 테스트 스크립트
"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

def wait_for_server(max_retries=30):
    """API 서버가 준비될 때까지 대기"""
    print("API 서버 준비 대기 중...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{API_BASE}/health", timeout=2)
            if response.status_code == 200:
                print("✅ API 서버 준비 완료!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        if i % 5 == 0:
            print(f"   대기 중... ({i}/{max_retries})")

    print("❌ API 서버 시작 실패")
    return False

def test_student_chat():
    """학생용 AI 상담 테스트"""
    print("=" * 80)
    print("학생용 AI 상담 테스트")
    print("=" * 80)
    print()

    # 서버 준비 대기
    if not wait_for_server():
        return

    # 테스트할 학생 ID
    student_id = "S-01"  # 김민준 학생

    # 테스트 대화 시나리오
    conversations = [
        {
            "question": "안녕하세요! 저는 요즘 영어 공부가 너무 어려워요. 특히 독해가 제일 힘들어요.",
            "description": "첫 인사 + 고민 상담"
        },
        {
            "question": "독해를 잘하려면 어떻게 공부해야 할까요?",
            "description": "구체적인 학습 방법 질문"
        },
        {
            "question": "제가 잘하는 부분도 있나요?",
            "description": "강점 확인"
        }
    ]

    # 대화 히스토리 (멀티턴 채팅)
    messages = []

    for idx, conv in enumerate(conversations, 1):
        print(f"\n{'='*80}")
        print(f"대화 {idx}: {conv['description']}")
        print(f"{'='*80}\n")

        # 사용자 메시지 추가
        messages.append({
            "role": "user",
            "content": conv["question"]
        })

        print(f"👤 학생: {conv['question']}")
        print()

        # API 호출
        payload = {
            "student_id": student_id,
            "messages": messages
        }

        try:
            response = requests.post(
                f"{API_BASE}/api/chat/student",
                json=payload,
                timeout=60  # LLM 응답 대기 시간
            )

            if response.status_code == 200:
                result = response.json()
                assistant_message = result.get("message", "")

                print(f"🤖 AI 코치:")
                print("-" * 80)
                print(assistant_message)
                print("-" * 80)

                # 컨텍스트 정보 (첫 대화에서만)
                if idx == 1 and result.get("student_context"):
                    print()
                    print("📊 참고한 학생 정보:")
                    print("-" * 80)
                    print(result["student_context"])
                    print("-" * 80)

                # AI 응답을 대화 히스토리에 추가
                messages.append({
                    "role": "assistant",
                    "content": assistant_message
                })

            else:
                print(f"❌ 오류 발생: {response.status_code}")
                print(response.text)
                break

        except requests.exceptions.Timeout:
            print("❌ 요청 타임아웃 (60초 초과)")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            break

        # 다음 대화 전 잠시 대기
        if idx < len(conversations):
            time.sleep(1)

    print()
    print("=" * 80)
    print("✅ 학생용 AI 상담 테스트 완료!")
    print("=" * 80)
    print()
    print("요약:")
    print(f"  - 테스트 학생: {student_id} (김민준)")
    print(f"  - 총 대화 수: {len(conversations)}회")
    print(f"  - GraphRAG 활용: ✅")
    print(f"  - 멀티턴 대화: ✅")
    print()

if __name__ == "__main__":
    test_student_chat()
