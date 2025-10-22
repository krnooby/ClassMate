#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
문제 추천 기능 테스트
학생이 "독해 문제 내줘" 했을 때 실제 DB 문제가 나오는지 확인
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_problem_recommendation():
    """문제 추천 기능 테스트"""
    print("=" * 80)
    print("문제 추천 기능 테스트")
    print("=" * 80)
    print()

    student_id = "S-01"  # 김민준 (약점: 독해)

    # 테스트 시나리오
    scenarios = [
        {
            "name": "1. 약점 확인",
            "message": "제 약점이 뭔가요?"
        },
        {
            "name": "2. 독해 문제 요청",
            "message": "독해 문제 내줘"
        },
        {
            "name": "3. 문법 문제 요청",
            "message": "문법 문제도 풀고 싶어요"
        }
    ]

    messages = []

    for scenario in scenarios:
        print(f"\n{'='*80}")
        print(f"📝 {scenario['name']}")
        print(f"{'='*80}\n")

        # 사용자 메시지 추가
        messages.append({
            "role": "user",
            "content": scenario["message"]
        })

        print(f"👤 학생: {scenario['message']}")
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
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                assistant_message = result.get("message", "")

                print("🤖 AI 코치:")
                print("-" * 80)
                print(assistant_message)
                print("-" * 80)

                # AI 응답 추가
                messages.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                # 영어 문제가 포함되어 있는지 체크
                has_english = any(ord(c) < 128 and c.isalpha() for c in assistant_message)
                has_korean_problem = "답:" in assistant_message or "정답:" in assistant_message

                print()
                print("📊 검증:")
                if "문제" in scenario["message"]:
                    if has_english and "Choose" in assistant_message or "True or False" in assistant_message:
                        print("  ✅ 영어 문제가 포함되어 있습니다")
                    elif has_korean_problem:
                        print("  ⚠️  한국어 문제가 포함되어 있을 수 있습니다")
                    else:
                        print("  ℹ️  문제 형식이 명확하지 않습니다")

            else:
                print(f"❌ 오류: {response.status_code}")
                print(response.text)
                break

        except Exception as e:
            print(f"❌ 오류: {e}")
            break

    print()
    print("=" * 80)
    print("✅ 테스트 완료!")
    print("=" * 80)

if __name__ == "__main__":
    # 서버 대기
    import time
    print("API 서버 준비 중...")
    for i in range(10):
        try:
            response = requests.get(f"{API_BASE}/health", timeout=2)
            if response.status_code == 200:
                print("✅ 서버 준비 완료")
                break
        except:
            time.sleep(1)
    else:
        print("❌ 서버 연결 실패")
        exit(1)

    test_problem_recommendation()
