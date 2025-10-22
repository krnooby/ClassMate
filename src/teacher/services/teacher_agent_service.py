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
from shared.services import get_graph_rag_service
from shared.prompts import PromptManager


class TeacherAgentService:
    """선생님 맞춤 Function Calling 에이전트"""

    def __init__(self):
        """초기화"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key)
        self.graph_rag_service = get_graph_rag_service()

        # Function definitions
        self.functions = self._create_functions()

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
            }
        ]

    def _get_my_class_students(self, teacher_id: str, include_details: bool = False) -> str:
        """자기반 학생 조회"""
        try:
            # GraphRAG로 선생님의 반 정보 조회
            query = f"선생님 {teacher_id}의 반 학생들 목록"
            context = self.graph_rag_service.get_rag_context(
                student_id=None,  # Teacher query
                query_text=query,
                use_vector_search=False
            )

            # TODO: 실제로는 Neo4j에서 teacher -> class -> students 조회
            # 현재는 GraphRAG 결과 반환
            return context

        except Exception as e:
            return f"학생 조회 실패: {str(e)}"

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

    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Function 실행"""
        print(f"🔧 FUNCTION CALLED: {function_name}")
        print(f"📋 ARGUMENTS: {json.dumps(arguments, ensure_ascii=False)}")

        if function_name == "get_my_class_students":
            return self._get_my_class_students(**arguments)
        elif function_name == "search_students_by_score":
            return self._search_students_by_score(**arguments)
        elif function_name == "search_students_by_behavior":
            return self._search_students_by_behavior(**arguments)
        elif function_name == "trigger_exam_upload_ui":
            return self._trigger_exam_upload_ui(**arguments)
        elif function_name == "trigger_daily_input_ui":
            return self._trigger_daily_input_ui(**arguments)
        elif function_name == "get_student_details":
            return self._get_student_details(**arguments)
        else:
            return f"Unknown function: {function_name}"

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
        선생님과 채팅 (Function Calling)

        Args:
            teacher_id: 선생님 ID
            message: 선생님의 메시지
            chat_history: 이전 대화 기록

        Returns:
            Dict with 'message', 'model_info', and optionally 'ui_panel'
        """
        try:
            used_models = ["gpt-4.1-mini"]

            # 시스템 프롬프트 (PromptManager 사용)
            system_prompt = PromptManager.get_system_prompt(
                role="teacher_agent",
                model="gpt-4.1-mini",
                context={"teacher_id": teacher_id}
            )

            # 메시지 구성
            messages = [{"role": "system", "content": system_prompt}]

            if chat_history:
                messages.extend(chat_history)

            messages.append({"role": "user", "content": message})

            # Function calling
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
                                "primary": "gpt-4.1-mini",
                                "all_used": used_models
                            }
                        }

                    # Function 결과를 메시지에 추가
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response
                    })

                # 최종 응답 생성
                final_response = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages,
                    temperature=0.7
                )

                return {
                    "message": final_response.choices[0].message.content,
                    "model_info": {
                        "primary": "gpt-4.1-mini",
                        "all_used": used_models
                    }
                }
            else:
                # Function 호출 없이 직접 응답
                return {
                    "message": assistant_message.content,
                    "model_info": {
                        "primary": "gpt-4.1-mini",
                        "all_used": used_models
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
