#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
벡터 검색 (코사인 유사도) 테스트
다양한 질문으로 벡터 검색의 정확도를 평가합니다.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from api.services.graph_rag_service import get_graph_rag_service

load_dotenv()

# 테스트 쿼리 (코사인 유사도 검증용)
TEST_QUERIES = [
    {
        "name": "테스트 1: 특정 약점 찾기 (독해)",
        "query": "독해가 약한 학생을 찾아주세요",
        "expected": "약점이 '독해'인 학생들이 상위에 나와야 함",
        "student_ids": ["S-01", "S-04"]  # 실제 독해가 약점인 학생들
    },
    {
        "name": "테스트 2: 특정 약점 찾기 (문법)",
        "query": "문법이 부족한 학생",
        "expected": "약점이 '문법'인 학생들이 상위에 나와야 함",
        "student_ids": ["S-02"]  # 문법이 약점
    },
    {
        "name": "테스트 3: 특정 강점 찾기 (어휘)",
        "query": "단어를 잘 외우는 학생",
        "expected": "강점이 '어휘'인 학생들이 상위에 나와야 함",
        "student_ids": ["S-02"]  # 어휘가 강점
    },
    {
        "name": "테스트 4: 특정 강점 찾기 (쓰기)",
        "query": "글쓰기를 잘하는 학생",
        "expected": "강점이 '쓰기'인 학생들이 상위에 나와야 함",
        "student_ids": ["S-01"]  # 쓰기가 강점
    },
    {
        "name": "테스트 5: 복합 조건 (출석)",
        "query": "결석이 많은 학생",
        "expected": "출석률이 낮은 학생들이 상위에 나와야 함",
        "student_ids": []  # 출석률 낮은 학생
    },
    {
        "name": "테스트 6: 복합 조건 (숙제)",
        "query": "숙제를 잘 안 내는 학생",
        "expected": "숙제 제출률이 낮은 학생들이 상위에 나와야 함",
        "student_ids": ["S-03"]  # 76.9% 완료율
    },
    {
        "name": "테스트 7: 긍정적 특징 (성실함)",
        "query": "성실하고 출석률이 높은 학생",
        "expected": "출석률 100%인 학생들이 상위에 나와야 함",
        "student_ids": ["S-04", "S-05"]  # 출석률 100%
    },
    {
        "name": "테스트 8: 학년 기반",
        "query": "초등학교 저학년 학생",
        "expected": "초등학교 1-3학년 학생들이 나와야 함",
        "student_ids": ["S-01", "S-04"]  # E3, E2
    },
    {
        "name": "테스트 9: CEFR 레벨",
        "query": "영어 실력이 초급인 학생",
        "expected": "CEFR A1-A2 학생들이 나와야 함",
        "student_ids": []  # A1-A2 학생들
    },
    {
        "name": "테스트 10: 종합 실력",
        "query": "전반적으로 영어를 잘하는 학생",
        "expected": "CEFR 높고 백분위 높은 학생들이 나와야 함",
        "student_ids": []  # 고득점 학생들
    }
]

def main():
    print("=" * 80)
    print("벡터 검색 (코사인 유사도) 정확도 테스트")
    print("=" * 80)
    print()

    rag_service = get_graph_rag_service()

    all_results = []

    for test in TEST_QUERIES:
        print("=" * 80)
        print(f"🔍 {test['name']}")
        print("=" * 80)
        print(f"쿼리: \"{test['query']}\"")
        print(f"기대: {test['expected']}")
        print()

        try:
            # 벡터 검색 실행
            results = rag_service.vector_search_students(
                query_text=test['query'],
                limit=5
            )

            if results:
                print(f"✅ 검색 결과: {len(results)}명")
                print()

                for i, result in enumerate(results, 1):
                    student_id = result.get('student_id')
                    name = result.get('name')
                    score = result.get('score', 0)
                    strong = result.get('strong_area', 'N/A')
                    weak = result.get('weak_area', 'N/A')

                    # 기대 학생 ID에 포함되는지 체크
                    is_expected = "✓" if student_id in test['student_ids'] else " "

                    print(f"  [{is_expected}] {i}. {name} ({student_id})")
                    print(f"      유사도: {score:.4f}")
                    print(f"      강점: {strong} / 약점: {weak}")

                    # 요약 일부 표시
                    summary = result.get('summary', '')
                    if summary:
                        preview = summary[:80] + "..." if len(summary) > 80 else summary
                        print(f"      요약: {preview}")
                    print()

                # 정확도 평가
                if test['student_ids']:
                    found_ids = [r['student_id'] for r in results]
                    correct = len(set(test['student_ids']) & set(found_ids))
                    total = len(test['student_ids'])
                    accuracy = (correct / total * 100) if total > 0 else 0

                    print(f"📊 정확도: {correct}/{total} ({accuracy:.1f}%)")
                    all_results.append({
                        'name': test['name'],
                        'accuracy': accuracy,
                        'found': correct,
                        'total': total
                    })

            else:
                print("⚠️  검색 결과 없음 (유사도 0.7 미만)")

        except Exception as e:
            print(f"❌ 오류: {e}")
            import traceback
            traceback.print_exc()

        print()

    # 전체 결과 요약
    if all_results:
        print("=" * 80)
        print("📊 전체 테스트 결과 요약")
        print("=" * 80)
        print()

        total_accuracy = sum(r['accuracy'] for r in all_results) / len(all_results)
        total_found = sum(r['found'] for r in all_results)
        total_expected = sum(r['total'] for r in all_results)

        for r in all_results:
            status = "✅" if r['accuracy'] >= 50 else "⚠️"
            print(f"{status} {r['name']}: {r['accuracy']:.1f}% ({r['found']}/{r['total']})")

        print()
        print(f"평균 정확도: {total_accuracy:.1f}%")
        print(f"전체: {total_found}/{total_expected} 학생 검색 성공")

    rag_service.close()

if __name__ == "__main__":
    main()
