#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphRAG 벡터 검색 정확도 테스트 (LLM 제외)
순수하게 벡터 유사도 검색과 그래프 탐색 기능만 검증
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
from api.services.graph_rag_service import get_graph_rag_service

# .env 로드
load_dotenv()


def test_student_vector_search():
    """학생 벡터 검색 테스트"""
    print("=" * 80)
    print("1️⃣  학생 벡터 유사도 검색 테스트")
    print("=" * 80)
    print()

    rag_service = get_graph_rag_service()

    # 테스트 쿼리들
    test_queries = [
        {
            "query": "문법이 약한 학생",
            "expected_weak_area": "문법",
            "description": "문법 약점 학생 검색"
        },
        {
            "query": "독해가 부족한 학생",
            "expected_weak_area": "독해",
            "description": "독해 약점 학생 검색"
        },
        {
            "query": "어휘력이 낮은 학생",
            "expected_weak_area": "어휘",
            "description": "어휘 약점 학생 검색"
        },
        {
            "query": "듣기가 약한 학생",
            "expected_weak_area": "듣기",
            "description": "듣기 약점 학생 검색"
        },
        {
            "query": "성적이 상위권인 학생",
            "expected_weak_area": None,  # 상위권 학생 찾기
            "description": "상위권 학생 검색"
        }
    ]

    total_tests = len(test_queries)
    passed_tests = 0

    for idx, test in enumerate(test_queries, 1):
        print(f"\n[테스트 {idx}/{total_tests}] {test['description']}")
        print(f"쿼리: '{test['query']}'")
        print("-" * 80)

        try:
            results = rag_service.vector_search_students(
                query_text=test['query'],
                limit=5
            )

            if results:
                print(f"✅ 검색 결과: {len(results)}명")
                print()

                for i, student in enumerate(results, 1):
                    print(f"{i}. {student.get('name', 'N/A')} (ID: {student.get('student_id', 'N/A')})")
                    print(f"   유사도: {student.get('score', 0):.4f}")
                    print(f"   약점: {student.get('weak_area', 'N/A')}")
                    print(f"   강점: {student.get('strong_area', 'N/A')}")
                    summary = student.get('summary', '')
                    if summary:
                        preview = summary[:100] + "..." if len(summary) > 100 else summary
                        print(f"   요약: {preview}")
                    print()

                # 정확도 체크
                if test['expected_weak_area']:
                    top_student = results[0]
                    weak_area = top_student.get('weak_area', '')
                    if test['expected_weak_area'] in weak_area:
                        print(f"✅ PASS: 1위 학생의 약점이 '{test['expected_weak_area']}'와 일치")
                        passed_tests += 1
                    else:
                        print(f"⚠️  PARTIAL: 1위 학생의 약점이 '{weak_area}' (예상: {test['expected_weak_area']})")
                else:
                    print(f"✅ PASS: 검색 결과 반환됨")
                    passed_tests += 1

            else:
                print("⚠️  검색 결과 없음 (유사도 0.7 미만)")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 80)
    print(f"학생 벡터 검색 정확도: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print("=" * 80)
    return passed_tests, total_tests


def test_problem_search():
    """문제 검색 테스트 (한글 필터링 확인)"""
    print("\n" + "=" * 80)
    print("2️⃣  문제 검색 테스트 (한글 필터링)")
    print("=" * 80)
    print()

    rag_service = get_graph_rag_service()

    # 테스트 케이스
    test_cases = [
        {
            "student_id": "S-01",
            "area": "독해",
            "description": "김민준 (약점: 독해)"
        },
        {
            "student_id": "S-02",
            "area": None,
            "description": "박서연 (약점 자동 감지)"
        }
    ]

    total_tests = len(test_cases)
    passed_tests = 0

    for idx, test in enumerate(test_cases, 1):
        print(f"\n[테스트 {idx}/{total_tests}] {test['description']}")
        print("-" * 80)

        try:
            problems = rag_service.search_problems_for_student(
                student_id=test['student_id'],
                area=test['area'],
                limit=5
            )

            if problems:
                print(f"✅ 문제 {len(problems)}개 검색됨")
                print()

                korean_count = 0
                english_count = 0

                for i, problem in enumerate(problems, 1):
                    stem = problem.get('stem', '')
                    has_korean = any('\u3131' <= char <= '\u314e' or '\uac00' <= char <= '\ud7a3' for char in stem)

                    if has_korean:
                        korean_count += 1
                        lang_label = "🇰🇷 한글"
                    else:
                        english_count += 1
                        lang_label = "🇬🇧 영어"

                    area_name = {'RD': 'Reading', 'GR': 'Grammar', 'WR': 'Writing',
                                 'LS': 'Listening', 'VO': 'Vocabulary'}
                    area_label = area_name.get(problem.get('area', ''), problem.get('area', 'N/A'))

                    print(f"{i}. [{area_label}] {lang_label}")
                    print(f"   ID: {problem.get('problem_id', 'N/A')}")
                    print(f"   CEFR: {problem.get('cefr', 'N/A')}")
                    print(f"   문제: {stem[:80]}...")
                    print()

                print("-" * 80)
                print(f"언어 분포: 영어 {english_count}개 / 한글 {korean_count}개")

                if korean_count == 0:
                    print("✅ PASS: 한글 문제 필터링 성공")
                    passed_tests += 1
                else:
                    print(f"❌ FAIL: 한글 문제 {korean_count}개 발견")

            else:
                print("⚠️  문제 검색 결과 없음")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 80)
    print(f"문제 검색 정확도: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print("=" * 80)
    return passed_tests, total_tests


def test_graph_traversal():
    """그래프 탐색 테스트"""
    print("\n" + "=" * 80)
    print("3️⃣  그래프 탐색 테스트")
    print("=" * 80)
    print()

    rag_service = get_graph_rag_service()

    test_students = ["S-01", "S-02", "S-03"]
    total_tests = len(test_students)
    passed_tests = 0

    for idx, student_id in enumerate(test_students, 1):
        print(f"\n[테스트 {idx}/{total_tests}] 학생 ID: {student_id}")
        print("-" * 80)

        try:
            graph_context = rag_service.get_student_graph_context(student_id)

            if graph_context.get("student"):
                student = graph_context["student"]
                print(f"✅ 학생 정보:")
                print(f"   - 이름: {student.get('name')}")
                print(f"   - 학년: {student.get('grade_label')}")
                print(f"   - 약점: {student.get('weak_area')}")
                print(f"   - 강점: {student.get('strong_area')}")

            if graph_context.get("assessment"):
                assessment = graph_context["assessment"]
                print(f"\n✅ 성적 정보:")
                print(f"   - CEFR: {assessment.get('cefr')}")
                print(f"   - 백분위: {assessment.get('percentile_rank')}위")

            if graph_context.get("class"):
                cls = graph_context["class"]
                print(f"\n✅ 반 정보:")
                print(f"   - 반: {cls.get('class_name')}")
                print(f"   - 진도: {cls.get('progress')}")

            if graph_context.get("teacher"):
                teacher = graph_context["teacher"]
                print(f"\n✅ 선생님: {teacher.get('name')}")

            if graph_context.get("peers"):
                peers = graph_context["peers"]
                print(f"\n✅ 같은 반 친구: {len(peers)}명")
                for i, peer in enumerate(peers[:3], 1):
                    print(f"   {i}. {peer.get('name')} ({peer.get('cefr')})")

            # 모든 정보가 있으면 PASS
            if all([
                graph_context.get("student"),
                graph_context.get("assessment"),
                graph_context.get("class")
            ]):
                print("\n✅ PASS: 그래프 탐색 성공")
                passed_tests += 1
            else:
                print("\n⚠️  PARTIAL: 일부 정보 누락")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 80)
    print(f"그래프 탐색 정확도: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print("=" * 80)
    return passed_tests, total_tests


def test_rag_context_generation():
    """RAG 컨텍스트 생성 테스트 (LLM 제외)"""
    print("\n" + "=" * 80)
    print("4️⃣  RAG 컨텍스트 생성 테스트 (벡터 검색 포함)")
    print("=" * 80)
    print()

    rag_service = get_graph_rag_service()

    test_cases = [
        {
            "student_id": "S-01",
            "query": "이 학생의 강점과 약점은?",
            "use_vector": True
        },
        {
            "student_id": "S-02",
            "query": "출석률은 어때?",
            "use_vector": False
        }
    ]

    total_tests = len(test_cases)
    passed_tests = 0

    for idx, test in enumerate(test_cases, 1):
        print(f"\n[테스트 {idx}/{total_tests}] 학생 {test['student_id']}")
        print(f"쿼리: '{test['query']}'")
        print(f"벡터 검색: {'사용' if test['use_vector'] else '미사용'}")
        print("-" * 80)

        try:
            rag_context = rag_service.get_rag_context(
                student_id=test['student_id'],
                query_text=test['query'],
                use_vector_search=test['use_vector']
            )

            print("생성된 RAG 컨텍스트:")
            print("-" * 80)
            print(rag_context)
            print("-" * 80)

            # 컨텍스트에 필수 정보가 포함되어 있는지 확인
            required_info = ["이름:", "CEFR", "백분위", "강점:", "약점:"]
            found_info = sum(1 for info in required_info if info in rag_context)

            print(f"\n필수 정보 포함: {found_info}/{len(required_info)}")

            if found_info >= 4:
                print("✅ PASS: RAG 컨텍스트 생성 성공")
                passed_tests += 1
            else:
                print("⚠️  PARTIAL: 일부 정보 누락")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 80)
    print(f"RAG 컨텍스트 생성 정확도: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print("=" * 80)
    return passed_tests, total_tests


def main():
    print("=" * 80)
    print("GraphRAG 벡터 검색 정확도 테스트 (LLM 제외)")
    print("=" * 80)
    print()

    all_results = []

    # 1. 학생 벡터 검색
    result1 = test_student_vector_search()
    all_results.append(("학생 벡터 검색", result1))

    # 2. 문제 검색 (한글 필터링)
    result2 = test_problem_search()
    all_results.append(("문제 검색", result2))

    # 3. 그래프 탐색
    result3 = test_graph_traversal()
    all_results.append(("그래프 탐색", result3))

    # 4. RAG 컨텍스트 생성
    result4 = test_rag_context_generation()
    all_results.append(("RAG 컨텍스트", result4))

    # 전체 결과 요약
    print("\n" + "=" * 80)
    print("📊 전체 테스트 결과 요약")
    print("=" * 80)
    print()

    total_passed = 0
    total_tests = 0

    for test_name, (passed, total) in all_results:
        accuracy = (passed / total * 100) if total > 0 else 0
        status = "✅" if accuracy >= 80 else "⚠️"
        print(f"{status} {test_name:20s}: {passed:2d}/{total:2d} ({accuracy:5.1f}%)")
        total_passed += passed
        total_tests += total

    print("-" * 80)
    overall_accuracy = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"🎯 전체 정확도: {total_passed}/{total_tests} ({overall_accuracy:.1f}%)")
    print("=" * 80)

    # 서비스 종료
    rag_service = get_graph_rag_service()
    rag_service.close()


if __name__ == "__main__":
    main()
