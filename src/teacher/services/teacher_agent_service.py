# -*- coding: utf-8 -*-
"""
Teacher Agent Service
OpenAI Function Calling 기반 선생님 업무 지원 시스템
"""
from __future__ import annotations
import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from shared.services import (
    get_graph_rag_service,
    get_dictionary_service,
    get_news_service,
    get_text_analysis_service,
    get_grammar_check_service
)
from shared.prompts import PromptManager


# ANSI 색상 코드
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # 색상
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # 배경색
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'


def print_box(title: str, content: str, color: str = Colors.CYAN):
    """박스 형태로 로그 출력"""
    width = 80
    print(f"\n{color}{'='*width}{Colors.RESET}")
    print(f"{color}{Colors.BOLD}{title.center(width)}{Colors.RESET}")
    print(f"{color}{'='*width}{Colors.RESET}")
    for line in content.split('\n'):
        if line.strip():
            print(f"{color}  {line}{Colors.RESET}")
    print(f"{color}{'='*width}{Colors.RESET}\n")


def print_section(emoji: str, title: str, content: str, color: str = Colors.BLUE):
    """섹션 형태로 로그 출력"""
    print(f"\n{color}{Colors.BOLD}{emoji} {title}{Colors.RESET}")
    print(f"{color}{'-'*60}{Colors.RESET}")
    for line in content.split('\n'):
        if line.strip():
            print(f"{color}  {line}{Colors.RESET}")
    print()


class TeacherAgentService:
    """선생님 맞춤 Function Calling 에이전트"""

    def __init__(self):
        """초기화"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key)
        self.graph_rag_service = get_graph_rag_service()

        # Function definitions
        self.functions = self._create_functions()

    def _route_query(self, message: str, teacher_id: str) -> str:
        """
        질문 의도를 분석하여 적절한 모델 선택
        Returns: "intelligence" (gpt-4.1-mini) or "reasoning" (o4-mini/o3)
        """
        routing_prompt = f'''Analyze this teacher's question and choose the appropriate model:

**intelligence** (gpt-4.1-mini) - Fast, cost-effective for:
- Simple student data lookup (성적 조회, 출석 확인, 학생 목록)
- Direct questions with single answer (누가 1등?, 평균 몇 점?)
- Greetings and small talk (안녕하세요, 수고하세요)
- Basic statistics (학급 평균, 출석률)
- Function calls only (DB 조회만 필요)
Examples: "학생 목록 보여줘", "김민준 성적은?", "학급 평균 점수는?", "안녕하세요", "오늘 출석률은?"

**reasoning** (o4-mini) - Deep thinking for:
- Comparative analysis (학생 간 비교, 트렌드 분석)
- Class performance insights (학급 전체 패턴 파악)
- Teaching strategy recommendations (수업 개선 방안)
- Intervention planning (부진 학생 지도 계획)
- Multi-student synthesis (여러 학생 종합 분석)
Examples: "김민준과 이서윤의 학습 패턴을 비교해줘", "학급 전체의 약점을 분석하고 수업 계획 세워줘", "성적이 떨어지는 학생들을 위한 전략은?", "상위권과 하위권의 차이는 무엇이고 어떻게 좁힐까?", "다음 달 커리큘럼 추천해줘"

Question: "{message}"

Respond with ONLY "intelligence" or "reasoning".'''

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cheap, fast router
                messages=[{"role": "user", "content": routing_prompt}],
                max_tokens=10,
                temperature=0
            )
            decision = response.choices[0].message.content.strip().lower()

            # 시각적 로깅
            if decision == "intelligence":
                print_section(
                    "🧠",
                    "ROUTING DECISION",
                    f"Query: {message[:50]}...\n"
                    f"Model: INTELLIGENCE (gpt-4.1-mini)\n"
                    f"Reason: Fast function calling for simple tasks",
                    Colors.CYAN
                )
            else:
                print_section(
                    "🧠",
                    "ROUTING DECISION",
                    f"Query: {message[:50]}...\n"
                    f"Model: REASONING (o4-mini)\n"
                    f"Reason: Deep thinking required for complex analysis",
                    Colors.MAGENTA
                )

            return decision if decision in ["intelligence", "reasoning"] else "intelligence"
        except Exception as e:
            print(f"{Colors.RED}⚠️  Routing failed: {e}, defaulting to intelligence{Colors.RESET}")
            return "intelligence"  # Default fallback

    def _needs_react(self, message: str) -> bool:
        """
        ReAct 모드가 필요한 복잡한 질문인지 판단

        복잡한 질문 패턴:
        1. 연결어가 있는 다단계 작업: "~하고 ~해줘", "~찾아서 ~해줘"
        2. 순차적 지시: "먼저 ~ 그다음 ~"
        3. 동사 3개 이상 (여러 작업)
        """
        import re

        # 패턴 1: 연결어 ("하고", "찾아서", "확인하고" 등)
        multi_task_keywords = ['하고', '그리고', '찾아서', '확인하고', '조회하고', '알려주고', '분석하고', '추천해']
        for keyword in multi_task_keywords:
            if keyword in message and ('해줘' in message or '주세요' in message or '줘' in message):
                return True

        # 패턴 2: "먼저...그다음" 또는 "먼저...그리고"
        if '먼저' in message and ('그다음' in message or '그리고' in message):
            return True

        # 패턴 3: 동사 3개 이상
        action_verbs = ['찾', '분석', '추천', '확인', '조회', '검색', '비교', '생성', '설명', '알려', '보여', '세워']
        verb_count = sum(1 for verb in action_verbs if verb in message)
        if verb_count >= 3:
            return True

        return False

    def _react_chat(
        self,
        teacher_id: str,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_steps: int = 5
    ) -> Dict[str, Any]:
        """
        ReAct (Reasoning + Acting) 모드로 복잡한 다단계 작업 처리

        Args:
            teacher_id: 선생님 ID
            message: 선생님의 메시지
            chat_history: 이전 대화 기록
            max_steps: 최대 반복 횟수

        Returns:
            Dict with 'message' and 'model_info'
        """
        print(f"\n{'='*60}")
        print(f"🔄 ReAct Mode Activated (Teacher)")
        print(f"Query: {message}")
        print(f"{'='*60}\n")

        # System prompt
        system_prompt = PromptManager.get_system_prompt(
            role="teacher_agent",
            model="o4-mini",
            context={"teacher_id": teacher_id}
        )

        # 메시지 구성
        messages = [{"role": "system", "content": system_prompt}]

        if chat_history:
            messages.extend(chat_history)

        messages.append({"role": "user", "content": message})

        used_models = ["gpt-4o-mini (router)", "o4-mini (ReAct)"]

        # ReAct 루프
        for step in range(1, max_steps + 1):
            print(f"\n--- ReAct Step {step}/{max_steps} ---")

            # LLM 호출
            response = self.client.chat.completions.create(
                model="o4-mini",
                messages=messages,
                tools=self.functions,
                tool_choice="auto",
                max_completion_tokens=10000
            )

            assistant_message = response.choices[0].message

            # Thought 출력 (LLM의 사고 과정)
            if assistant_message.content:
                print(f"💭 Thought: {assistant_message.content[:200]}...")

            # Function 호출이 있으면 실행
            if assistant_message.tool_calls:
                messages.append(assistant_message)

                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    print(f"🔧 Action: {function_name}({arguments})")

                    # Function 실행
                    result = self._execute_function(function_name, arguments)

                    print(f"📊 Observation: {result[:200]}...")

                    # UI 트리거 체크
                    ui_trigger = self._parse_ui_trigger(result)
                    if ui_trigger:
                        return {
                            "message": ui_trigger["data"].get("message", ""),
                            "ui_panel": ui_trigger["ui_panel"],
                            "ui_data": ui_trigger["data"],
                            "model_info": {
                                "primary": "o4-mini (ReAct)",
                                "all_used": used_models
                            }
                        }

                    # Observation을 메시지에 추가
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
            else:
                # Final answer (Function 호출 없음)
                print(f"✅ Final Answer Reached")

                content = assistant_message.content or "답변을 생성할 수 없습니다."

                return {
                    "message": content,
                    "model_info": {
                        "primary": "o4-mini (ReAct)",
                        "all_used": used_models
                    }
                }

        # 최대 반복 횟수 초과
        print(f"⚠️  Max steps ({max_steps}) reached")

        # 마지막 응답 생성
        final_response = self.client.chat.completions.create(
            model="o4-mini",
            messages=messages,
            max_completion_tokens=10000
        )

        return {
            "message": final_response.choices[0].message.content or "최대 반복 횟수를 초과했습니다. 질문을 더 구체적으로 해주세요.",
            "model_info": {
                "primary": "o4-mini (ReAct)",
                "all_used": used_models
            }
        }

    def _check_response_quality(self, response_text: str) -> bool:
        """
        Check if o4-mini response quality is acceptable
        Returns: True if good, False if needs o3 fallback
        """
        # Bad indicators: too short, generic, error patterns
        if len(response_text) < 50:
            return False
        if "죄송합니다" in response_text and "오류" in response_text:
            return False
        if response_text.count("...") > 3:  # Too many ellipses = incomplete
            return False
        return True

    def _create_functions(self) -> List[Dict[str, Any]]:
        """OpenAI Function Calling용 function 정의"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_my_class_students",
                    "description": "자기반 학생들의 목록과 정보를 조회합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "teacher_id": {
                                "type": "string",
                                "description": "선생님 ID (예: T-01)"
                            },
                            "include_details": {
                                "type": "boolean",
                                "description": "상세 정보 포함 여부 (CEFR 레벨, 강약점 등)",
                                "default": False
                            }
                        },
                        "required": ["teacher_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_students_by_score",
                    "description": "학원 전체 또는 특정 반에서 특정 영역 점수가 기준 미만인 학생들을 검색합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "area": {
                                "type": "string",
                                "description": "영역: '독해'(RD), '문법'(GR), '어휘'(VO), '듣기'(LS), '쓰기'(WR)",
                                "enum": ["독해", "문법", "어휘", "듣기", "쓰기", "RD", "GR", "VO", "LS", "WR"]
                            },
                            "threshold": {
                                "type": "integer",
                                "description": "기준 점수 (예: 70점 미만 → 70)"
                            },
                            "class_id": {
                                "type": "string",
                                "description": "반 ID (생략 시 학원 전체 검색)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "최대 학생 수 (기본 20명)",
                                "default": 20
                            }
                        },
                        "required": ["area", "threshold"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_students_by_behavior",
                    "description": "수업 태도가 좋지 않은 학생들을 검색합니다 (출석률 낮음, 숙제 미제출 등)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "criteria": {
                                "type": "string",
                                "description": "검색 기준: 'attendance'(출석률), 'homework'(숙제 완료율), 'both'(둘 다)",
                                "enum": ["attendance", "homework", "both"]
                            },
                            "threshold": {
                                "type": "integer",
                                "description": "기준 비율 (예: 70% 미만 → 70)"
                            },
                            "class_id": {
                                "type": "string",
                                "description": "반 ID (생략 시 학원 전체 검색)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "최대 학생 수",
                                "default": 20
                            }
                        },
                        "required": ["criteria", "threshold"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "trigger_exam_upload_ui",
                    "description": "시험지 업로드 UI를 우측 패널에 표시합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "exam_type": {
                                "type": "string",
                                "description": "시험 유형 (중간고사, 기말고사, 모의고사 등)",
                                "default": "일반"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "trigger_daily_input_ui",
                    "description": "학생 기록부(Daily Input) 작성 UI를 우측 패널에 표시합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "teacher_id": {
                                "type": "string",
                                "description": "선생님 ID (자기반 학생 불러오기)"
                            }
                        },
                        "required": ["teacher_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_student_details",
                    "description": "특정 학생의 상세 정보를 조회합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "학생 ID"
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "lookup_word",
                    "description": "영어 단어를 검색하여 발음, 정의, 예문, 동의어를 제공합니다 (수업 자료 준비용)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "word": {
                                "type": "string",
                                "description": "검색할 영어 단어"
                            }
                        },
                        "required": ["word"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_news",
                    "description": "학생들에게 추천할 영어 뉴스 기사를 검색합니다 (읽기 자료 준비용)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "뉴스 카테고리",
                                "enum": ["general", "sports", "technology", "health", "science", "entertainment"],
                                "default": "general"
                            },
                            "page_size": {
                                "type": "integer",
                                "description": "가져올 기사 수 (1-10)",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_text_difficulty",
                    "description": "텍스트의 난이도(CEFR 레벨)를 분석합니다 (수업 자료 난이도 측정용)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "분석할 영어 텍스트"
                            }
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_grammar",
                    "description": "영어 문장의 문법 오류를 검사합니다 (수업 자료 검토용)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "검사할 영어 텍스트"
                            }
                        },
                        "required": ["text"]
                    }
                }
            }
        ]

    def _get_my_class_students(self, teacher_id: str, include_details: bool = False) -> str:
        """자기반 학생 조회"""
        try:
            # Neo4j에서 선생님의 반 정보 조회
            from pathlib import Path

            # 1. teachers.json에서 담당 반 조회
            teachers_file = Path("/home/sh/projects/ClassMate/data/json/teachers.json")
            with open(teachers_file, "r", encoding="utf-8") as f:
                teachers_data = json.load(f)

            assigned_classes = []
            teacher_name = None
            for teacher in teachers_data:
                if teacher["teacher_id"] == teacher_id:
                    assigned_classes = teacher["assigned_classes"]
                    teacher_name = teacher["name"]
                    break

            if not assigned_classes:
                return f"선생님 {teacher_id}의 담당 반 정보를 찾을 수 없습니다."

            # 2. Neo4j에서 해당 반 학생들 조회
            driver = self.graph_rag_service._get_driver()
            database = self.graph_rag_service.neo4j_db
            with driver.session(database=database) as session:
                result = session.run("""
                    MATCH (s:Student)
                    WHERE s.class_id IN $class_ids
                    RETURN s.student_id as student_id,
                           s.name as name,
                           s.grade_label as grade_label,
                           s.cefr as cefr,
                           s.class_id as class_id,
                           s.grammar_score as grammar_score,
                           s.vocabulary_score as vocabulary_score,
                           s.reading_score as reading_score,
                           s.listening_score as listening_score,
                           s.writing_score as writing_score,
                           s.attendance_rate as attendance_rate,
                           s.homework_completion_rate as homework_rate
                    ORDER BY s.student_id
                """, class_ids=assigned_classes)

                students = []
                for record in result:
                    student_info = {
                        "student_id": record["student_id"],
                        "name": record["name"],
                        "grade": record["grade_label"],
                        "cefr": record["cefr"],
                        "class_id": record["class_id"]
                    }

                    if include_details:
                        student_info.update({
                            "grammar": record.get("grammar_score"),
                            "vocabulary": record.get("vocabulary_score"),
                            "reading": record.get("reading_score"),
                            "listening": record.get("listening_score"),
                            "writing": record.get("writing_score"),
                            "attendance_rate": record.get("attendance_rate"),
                            "homework_rate": record.get("homework_rate")
                        })

                    students.append(student_info)

            if not students:
                return f"{teacher_name} 선생님의 담당 반({', '.join(assigned_classes)})에 학생이 없습니다."

            # 결과 포맷팅
            response = f"**{teacher_name} 선생님의 담당 학생 목록** (총 {len(students)}명)\n"
            response += f"**담당 반:** {', '.join(assigned_classes)}\n\n"

            for i, student in enumerate(students, 1):
                response += f"{i}. **{student['name']}** ({student['student_id']})\n"
                response += f"   - 학년: {student['grade']}\n"
                response += f"   - CEFR 레벨: {student['cefr']}\n"

                if include_details:
                    response += f"   - 영역별 점수: 문법 {student.get('grammar', 'N/A')}, 어휘 {student.get('vocabulary', 'N/A')}, 독해 {student.get('reading', 'N/A')}, 듣기 {student.get('listening', 'N/A')}, 쓰기 {student.get('writing', 'N/A')}\n"
                    response += f"   - 출석률: {student.get('attendance_rate', 'N/A')}%, 숙제 수행률: {student.get('homework_rate', 'N/A')}%\n"

                response += "\n"

            return response

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] _get_my_class_students failed: {error_details}")
            return f"학생 조회 중 오류가 발생했습니다: {str(e)}"

    def _search_students_by_score(
        self,
        area: str,
        threshold: int,
        class_id: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """점수 기준 학생 검색"""
        try:
            # Area 한글 → 코드 변환
            area_map = {
                "독해": "RD", "문법": "GR", "어휘": "VO",
                "듣기": "LS", "쓰기": "WR"
            }
            area_code = area_map.get(area, area.upper())

            # TODO: Neo4j Cypher 쿼리로 검색
            # 예: MATCH (s:Student) WHERE s.rd_score < threshold RETURN s

            # 임시: GraphRAG로 검색
            query = f"{area} 점수가 {threshold}점 미만인 학생들"
            if class_id:
                query += f" (반: {class_id})"

            context = self.graph_rag_service.get_rag_context(
                student_id=None,
                query_text=query,
                use_vector_search=True
            )

            return context

        except Exception as e:
            return f"학생 검색 실패: {str(e)}"

    def _search_students_by_behavior(
        self,
        criteria: str,
        threshold: int,
        class_id: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """태도 기준 학생 검색"""
        try:
            # TODO: Neo4j Cypher 쿼리
            # 예: MATCH (s:Student) WHERE s.attendance_rate < threshold

            criteria_map = {
                "attendance": "출석률",
                "homework": "숙제 완료율",
                "both": "출석률과 숙제 완료율"
            }
            criteria_kr = criteria_map.get(criteria, criteria)

            query = f"{criteria_kr}이 {threshold}% 미만인 학생들"
            if class_id:
                query += f" (반: {class_id})"

            context = self.graph_rag_service.get_rag_context(
                student_id=None,
                query_text=query,
                use_vector_search=True
            )

            return context

        except Exception as e:
            return f"학생 검색 실패: {str(e)}"

    def _trigger_exam_upload_ui(self, exam_type: str = "일반") -> str:
        """시험지 업로드 UI 트리거"""
        # 특수 응답 포맷 반환
        return json.dumps({
            "ui_trigger": "exam_upload",
            "exam_type": exam_type,
            "message": f"{exam_type} 시험지 업로드 화면을 열었습니다."
        })

    def _trigger_daily_input_ui(self, teacher_id: str) -> str:
        """기록부 작성 UI 트리거"""
        return json.dumps({
            "ui_trigger": "daily_input",
            "teacher_id": teacher_id,
            "message": "학생 기록부 작성 화면을 열었습니다."
        })

    def _get_student_details(self, student_id: str) -> str:
        """학생 상세 정보 조회"""
        try:
            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text=f"{student_id} 학생의 상세 정보",
                use_vector_search=True
            )
            return context
        except Exception as e:
            return f"학생 정보 조회 실패: {str(e)}"

    def _lookup_word(self, word: str) -> str:
        """영어 단어 검색 (Free Dictionary API)"""
        try:
            service = get_dictionary_service()
            result = service.lookup_word(word)

            if not result.get('success'):
                return f"단어 '{word}'를 찾을 수 없습니다. 철자를 확인해주세요."

            # 결과 포맷팅
            response = f"**{result['word']}** {result.get('phonetic', '')}\n\n"
            response += f"**품사:** {result.get('part_of_speech', 'N/A')}\n\n"
            response += f"**정의:** {result.get('definition', 'N/A')}\n\n"

            if result.get('example'):
                response += f"**예문:** {result['example']}\n\n"

            if result.get('synonyms'):
                synonyms = ', '.join(result['synonyms'])
                response += f"**동의어:** {synonyms}\n\n"

            if result.get('antonyms'):
                antonyms = ', '.join(result['antonyms'])
                response += f"**반의어:** {antonyms}\n\n"

            phonetics = result.get('phonetics', [])
            audio_urls = [p['audio'] for p in phonetics if p.get('audio')]
            if audio_urls:
                response += f"**발음 듣기:** {audio_urls[0]}\n"

            return response
        except Exception as e:
            return f"단어 검색 실패: {str(e)}"

    def _fetch_news(self, category: str = "general", page_size: int = 3) -> str:
        """영어 뉴스 기사 검색 (NewsAPI)"""
        try:
            service = get_news_service()
            result = service.fetch_news(
                category=category,
                language="en",
                page_size=min(page_size, 5),
                country="us"
            )

            if not result.get('success'):
                error_msg = result.get('error', 'Unknown error')
                if "NEWS_API_KEY not configured" in error_msg:
                    return "뉴스 API가 설정되지 않았습니다. 관리자에게 문의하세요."
                return f"뉴스 검색 실패: {error_msg}"

            articles = result.get('articles', [])
            if not articles:
                return f"'{category}' 카테고리의 뉴스를 찾을 수 없습니다."

            # 기사 포맷팅
            response = f"**{category.title()} 카테고리 최신 뉴스** ({len(articles)}개)\n\n"

            for i, article in enumerate(articles, 1):
                response += f"**{i}. {article['title']}**\n"
                response += f"   *출처:* {article['source']}\n"
                if article.get('description'):
                    response += f"   *요약:* {article['description']}\n"
                response += f"   *링크:* {article['url']}\n\n"

            return response
        except Exception as e:
            return f"뉴스 검색 실패: {str(e)}"

    def _analyze_text_difficulty(self, text: str) -> str:
        """텍스트 난이도 분석 (textstat)"""
        try:
            service = get_text_analysis_service()
            result = service.analyze_cefr_level(text)

            if not result.get('success'):
                error_msg = result.get('error', 'Unknown error')
                if "textstat library not installed" in error_msg:
                    return "텍스트 분석 라이브러리가 설치되지 않았습니다. 관리자에게 문의하세요."
                return f"텍스트 분석 실패: {error_msg}"

            # 결과 포맷팅
            response = f"**텍스트 난이도 분석 결과**\n\n"
            response += f"**CEFR 레벨:** {result['cefr_level']}\n"
            response += f"**난이도:** {result['difficulty']}\n"
            response += f"**가독성 점수 (Flesch):** {result['flesch_reading_ease']}/100 (높을수록 쉬움)\n"
            response += f"**학년 수준 (FK Grade):** {result['flesch_kincaid_grade']}학년\n\n"
            response += f"**통계:**\n"
            response += f"- 단어 수: {result['word_count']}개\n"
            response += f"- 문장 수: {result['sentence_count']}개\n"
            response += f"- 평균 문장 길이: {result['avg_sentence_length']}단어\n\n"

            level_descriptions = {
                "A1": "초급 - 매우 쉬운 텍스트",
                "A2": "초급 상 - 쉬운 텍스트",
                "B1": "중급 - 보통 난이도 텍스트",
                "B2": "중급 상 - 어려운 텍스트",
                "C1": "고급 - 매우 어려운 텍스트",
                "C2": "고급 상 - 전문가 수준 텍스트"
            }
            response += f"**레벨 설명:** {level_descriptions.get(result['cefr_level'], 'N/A')}\n"

            return response
        except Exception as e:
            return f"텍스트 분석 실패: {str(e)}"

    def _check_grammar(self, text: str) -> str:
        """문법 검사 (LanguageTool API)"""
        try:
            service = get_grammar_check_service()
            result = service.check_grammar(text, language="en-US")

            if not result.get('success'):
                return f"문법 검사 실패: {result.get('error', 'Unknown error')}"

            error_count = result.get('error_count', 0)
            errors = result.get('errors', [])

            if error_count == 0:
                return "**문법 검사 결과:** 문법 오류가 없습니다! ✅"

            # 오류 포맷팅
            response = f"**문법 검사 결과:** {error_count}개의 오류 발견\n\n"

            for i, error in enumerate(errors[:10], 1):
                response += f"**{i}. {error['message']}**\n"

                offset = error['offset']
                length = error['length']
                error_text = text[offset:offset+length]
                response += f"   *문제:* \"{error_text}\"\n"

                replacements = error.get('replacements', [])
                if replacements:
                    suggestions = ', '.join([f'"{r}"' for r in replacements])
                    response += f"   *제안:* {suggestions}\n"

                category = error.get('category', '')
                if category:
                    response += f"   *유형:* {category}\n"

                response += "\n"

            if error_count > 10:
                response += f"*({error_count - 10}개 오류 더 있음)*\n"

            return response
        except Exception as e:
            return f"문법 검사 실패: {str(e)}"

    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Function 실행"""

        # 함수 타입 분류
        db_functions = ["get_my_class_students", "search_students_by_score", "search_students_by_behavior", "get_student_details"]
        ui_trigger_functions = ["trigger_exam_upload_ui", "trigger_daily_input_ui"]
        external_api_functions = ["lookup_word", "fetch_news", "analyze_text_difficulty", "check_grammar"]

        if function_name in db_functions:
            func_type = "📊 DATABASE QUERY"
            color = Colors.GREEN
        elif function_name in ui_trigger_functions:
            func_type = "🖥️ UI TRIGGER"
            color = Colors.YELLOW
        elif function_name in external_api_functions:
            func_type = "🌐 EXTERNAL API"
            color = Colors.BLUE
        else:
            func_type = "❓ UNKNOWN"
            color = Colors.RED

        print_section(
            "🔧",
            f"FUNCTION CALL - {func_type}",
            f"Function: {function_name}\n"
            f"Arguments: {json.dumps(arguments, ensure_ascii=False, indent=2)}",
            color
        )

        if function_name == "get_my_class_students":
            result = self._get_my_class_students(**arguments)
        elif function_name == "search_students_by_score":
            result = self._search_students_by_score(**arguments)
        elif function_name == "search_students_by_behavior":
            result = self._search_students_by_behavior(**arguments)
        elif function_name == "trigger_exam_upload_ui":
            result = self._trigger_exam_upload_ui(**arguments)
        elif function_name == "trigger_daily_input_ui":
            result = self._trigger_daily_input_ui(**arguments)
        elif function_name == "get_student_details":
            result = self._get_student_details(**arguments)
        elif function_name == "lookup_word":
            result = self._lookup_word(**arguments)
        elif function_name == "fetch_news":
            result = self._fetch_news(**arguments)
        elif function_name == "analyze_text_difficulty":
            result = self._analyze_text_difficulty(**arguments)
        elif function_name == "check_grammar":
            result = self._check_grammar(**arguments)
        else:
            result = f"Unknown function: {function_name}"

        # 결과 미리보기 출력
        result_preview = result[:200] + "..." if len(result) > 200 else result
        print(f"{Colors.GREEN}✅ Function completed: {result_preview}{Colors.RESET}\n")

        return result

    def _parse_ui_trigger(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Function 응답에서 UI 트리거 추출

        Returns:
            {"ui_panel": "exam_upload" | "daily_input", "data": {...}} 또는 None
        """
        try:
            data = json.loads(content)
            if "ui_trigger" in data:
                return {
                    "ui_panel": data["ui_trigger"],
                    "data": data
                }
        except:
            pass
        return None

    def chat(
        self,
        teacher_id: str,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        선생님과 채팅 (Function Calling with Intelligent Routing)

        Args:
            teacher_id: 선생님 ID
            message: 선생님의 메시지
            chat_history: 이전 대화 기록

        Returns:
            Dict with 'message', 'model_info', and optionally 'ui_panel'
        """
        try:
            # ========== 요청 시작 로깅 ==========
            print_box(
                "👨‍🏫 TEACHER CHATBOT REQUEST",
                f"Teacher ID: {teacher_id}\n"
                f"Message: {message}",
                Colors.BLUE
            )

            # ReAct 모드 판단 (복잡한 다단계 질문)
            if self._needs_react(message):
                return self._react_chat(teacher_id, message, chat_history)

            used_models = []  # Track models used

            # Step 1: Route the query to determine complexity
            routing_decision = self._route_query(message, teacher_id)
            used_models.append("gpt-4o-mini")  # Router model

            # Step 2: Select primary model based on routing decision
            if routing_decision == "reasoning":
                primary_model = "o4-mini"
                print(f"🎯 Using reasoning model: {primary_model}")
            else:
                primary_model = "gpt-4.1-mini"
                print(f"🎯 Using intelligence model: {primary_model}")

            # 시스템 프롬프트 (PromptManager 사용)
            system_prompt = PromptManager.get_system_prompt(
                role="teacher_agent",
                model=primary_model,
                context={"teacher_id": teacher_id}
            )

            # 메시지 구성
            messages = [{"role": "system", "content": system_prompt}]

            if chat_history:
                messages.extend(chat_history)

            messages.append({"role": "user", "content": message})

            # Step 3: Call primary model with function calling
            used_models.append(primary_model)

            # Use appropriate parameters based on model type
            if primary_model == "o4-mini":
                # o4-mini uses max_completion_tokens
                response = self.client.chat.completions.create(
                    model="o4-mini",
                    messages=messages,
                    tools=self.functions,
                    tool_choice="auto",
                    max_completion_tokens=10000
                )
            else:
                # gpt-4.1-mini uses max_tokens
                response = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages,
                    tools=self.functions,
                    tool_choice="auto",
                    temperature=0.7
                )

            assistant_message = response.choices[0].message

            # Function 호출 처리
            if assistant_message.tool_calls:
                messages.append(assistant_message)

                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    print(f"🔧 Function Call: {function_name}({arguments})")

                    # Function 실행
                    function_response = self._execute_function(function_name, arguments)

                    # UI 트리거 체크
                    ui_trigger = self._parse_ui_trigger(function_response)

                    if ui_trigger:
                        # UI 트리거인 경우 즉시 반환
                        return {
                            "message": ui_trigger["data"].get("message", ""),
                            "ui_panel": ui_trigger["ui_panel"],
                            "ui_data": ui_trigger["data"],
                            "model_info": {
                                "primary": primary_model,
                                "all_used": list(set(used_models))
                            }
                        }

                    # Function 결과를 메시지에 추가
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response
                    })

                # 최종 응답 생성
                # Use the same model as primary for consistency
                if primary_model == "o4-mini":
                    final_response = self.client.chat.completions.create(
                        model="o4-mini",
                        messages=messages,
                        max_completion_tokens=10000
                    )
                else:
                    final_response = self.client.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=messages,
                        temperature=0.7
                    )

                response_content = final_response.choices[0].message.content

                # Step 4: Quality check for o4-mini responses
                if primary_model == "o4-mini" and not self._check_response_quality(response_content):
                    print(f"⚠️  o4-mini response quality low, falling back to o3...")
                    used_models.append("o3")

                    # Retry with o3 (advanced reasoning)
                    try:
                        final_response_o3 = self.client.chat.completions.create(
                            model="o3",
                            messages=messages,
                            max_completion_tokens=10000
                        )
                        response_content = final_response_o3.choices[0].message.content
                        primary_model = "o3"  # Update primary model
                        print(f"✅ o3 response generated successfully")
                    except Exception as e:
                        print(f"⚠️  o3 fallback failed: {e}, using o4-mini response anyway")

                return {
                    "message": response_content,
                    "model_info": {
                        "primary": primary_model,
                        "all_used": list(set(used_models))
                    }
                }
            else:
                # Function 호출 없이 직접 응답
                response_content = assistant_message.content

                # Step 4: Quality check for o4-mini responses (no function calls)
                if primary_model == "o4-mini" and not self._check_response_quality(response_content):
                    print(f"⚠️  o4-mini response quality low, falling back to o3...")
                    used_models.append("o3")

                    # Retry with o3 (advanced reasoning)
                    try:
                        final_response_o3 = self.client.chat.completions.create(
                            model="o3",
                            messages=messages,
                            max_completion_tokens=10000
                        )
                        response_content = final_response_o3.choices[0].message.content
                        primary_model = "o3"  # Update primary model
                        print(f"✅ o3 response generated successfully")
                    except Exception as e:
                        print(f"⚠️  o3 fallback failed: {e}, using o4-mini response anyway")

                return {
                    "message": response_content,
                    "model_info": {
                        "primary": primary_model,
                        "all_used": list(set(used_models))
                    }
                }

        except Exception as e:
            return {
                "message": f"죄송합니다. 오류가 발생했습니다: {str(e)}",
                "model_info": {"primary": "error", "all_used": []}
            }


# 싱글톤 인스턴스
_teacher_agent_service = None


def get_teacher_agent_service() -> TeacherAgentService:
    """Teacher Agent 서비스 싱글톤 인스턴스 가져오기"""
    global _teacher_agent_service
    if _teacher_agent_service is None:
        _teacher_agent_service = TeacherAgentService()
    return _teacher_agent_service
