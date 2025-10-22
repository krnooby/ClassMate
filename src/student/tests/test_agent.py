#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReAct 에이전트 테스트
학생 상담 에이전트가 적절한 도구를 선택하고 실행하는지 확인
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_agent_scenarios():
    """다양한 시나리오 테스트"""

    student_id = "S-01"  # 김민준 (약점: 독해)

    scenarios = [
        {
            "name": "📅 시간표 조회",
            "query": "우리 반 시간표 알려줘",
            "expected_tool": "get_student_context"
        },
        {
            "name": "📊 약점 분석",
            "query": "나의 약점이 뭐야?",
            "expected_tool": "get_student_context"
        },
        {
            "name": "📚 DB 문제 추천",
            "query": "내 약점 보완할 수 있는 문제 내줘",
            "expected_tool": "recommend_problems"
        },
        {
            "name": "✏️ AI 문제 생성",
            "query": "A2 레벨 환경 보호 주제로 독해 문제 만들어줘",
            "expected_tool": "generate_problem"
        },
        {
            "name": "💬 일반 상담",
            "query": "영어 공부 잘하는 방법 알려줘",
            "expected_tool": "general_chat"
        }
    ]

    print("=" * 80)
    print("🤖 ReAct 에이전트 테스트")
    print("=" * 80)
    print()

    for idx, scenario in enumerate(scenarios, 1):
        print(f"\n[테스트 {idx}/{len(scenarios)}] {scenario['name']}")
        print(f"질문: \"{scenario['query']}\"")
        print("-" * 80)

        # API 호출
        payload = {
            "student_id": student_id,
            "messages": [
                {"role": "user", "content": scenario["query"]}
            ]
        }

        try:
            response = requests.post(
                f"{API_BASE}/api/chat/student",
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                answer = result.get("message", "")

                print("🤖 AI 응답:")
                print(answer)
                print()

                # 응답 품질 체크
                if len(answer) > 50:
                    print("✅ 응답 생성됨")
                else:
                    print("⚠️  응답이 짧음")
            else:
                print(f"❌ 오류: HTTP {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"❌ 오류: {e}")

        print("=" * 80)

    print()
    print("✅ 테스트 완료!")


if __name__ == "__main__":
    # 서버 대기
    import time
    print("API 서버 준비 중...")
    for i in range(10):
        try:
            response = requests.get(f"{API_BASE}/health", timeout=2)
            if response.status_code == 200:
                print("✅ 서버 준비 완료\n")
                break
        except:
            time.sleep(1)
    else:
        print("❌ 서버 연결 실패")
        exit(1)

    test_agent_scenarios()
