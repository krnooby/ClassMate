# -*- coding: utf-8 -*-
"""
Parent Agent Service
OpenAI Function Calling 기반 학부모 상담 시스템
"""
from __future__ import annotations
import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from shared.services import get_graph_rag_service
from shared.prompts import PromptManager


class ParentAgentService:
    """학부모 맞춤 Function Calling 에이전트"""

    def __init__(self):
        """초기화"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key)
        self.graph_rag_service = get_graph_rag_service()

        # Current user message for vector search context
        self.current_user_message = ""

        # Function definitions
        self.functions = self._create_functions()

    def _create_functions(self) -> List[Dict[str, Any]]:
        """OpenAI Function Calling용 function 정의"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_child_info",
                    "description": "자녀의 상세 학습 정보를 조회합니다 (이름, 학년, CEFR 레벨, 강점, 약점, 영역별 점수, 출석률, 숙제 완료율, 학습 태도, 반 정보 등)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "자녀의 학생 ID (예: S-01)"
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_performance",
                    "description": "자녀의 성적 분석 및 학습 추이를 조회합니다 (영역별 강약점, 또래 비교, 개선 추이)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "자녀의 학생 ID"
                            },
                            "focus_area": {
                                "type": "string",
                                "description": "집중 분석할 영역 (독해, 문법, 어휘, 듣기, 쓰기 중 하나, 또는 null일 경우 전체 분석)",
                                "enum": ["독해", "문법", "어휘", "듣기", "쓰기", None]
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_study_advice",
                    "description": "자녀의 약점을 보완하기 위한 맞춤형 학습 조언 및 가정 학습 가이드를 제공합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "자녀의 학생 ID"
                            },
                            "area": {
                                "type": "string",
                                "description": "조언이 필요한 영역 (독해, 문법, 어휘, 듣기, 쓰기 중 하나, 또는 null일 경우 전체 약점 기반)",
                                "enum": ["독해", "문법", "어휘", "듣기", "쓰기", None]
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_attendance_status",
                    "description": "자녀의 출석 현황, 숙제 완료율, 학습 태도 등 일일 학습 기록을 조회합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "자녀의 학생 ID"
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "recommend_improvement_areas",
                    "description": "자녀가 집중적으로 개선해야 할 영역과 구체적인 학습 계획을 추천합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "자녀의 학생 ID"
                            },
                            "priority": {
                                "type": "string",
                                "description": "우선순위 기준 (urgent: 시급한 약점, balanced: 균형 잡힌 학습, strength: 강점 강화)",
                                "enum": ["urgent", "balanced", "strength"]
                            }
                        },
                        "required": ["student_id"]
                    }
                }
            }
        ]

    def _get_child_info(self, student_id: str, query_text: str = "학생 정보 조회") -> str:
        """자녀 정보 조회 실행 (벡터 검색 포함)"""
        try:
            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text=query_text,
                use_vector_search=True
            )

            # 학부모 관점에서 정보 재구성
            if context:
                import re
                # 이름 추출
                name_match = re.search(r'이름: (.+)', context)
                student_name = name_match.group(1) if name_match else "자녀"

                # CEFR 레벨 추출
                cefr_match = re.search(r'CEFR 레벨: ([A-C][1-2])', context)
                cefr_level = cefr_match.group(1) if cefr_match else "N/A"

                return f"""**{student_name} 학생의 학습 현황 (학부모님 관점):**

{context}

**학부모님께 안내 사항:**
- 현재 자녀의 CEFR 레벨은 {cefr_level}입니다
- 정기적인 출석과 숙제 완료가 성적 향상에 중요합니다
- 가정에서도 꾸준한 학습 습관 형성이 필요합니다
"""
            return context
        except Exception as e:
            return f"자녀 정보 조회 실패: {str(e)}"

    def _analyze_performance(self, student_id: str, focus_area: Optional[str] = None) -> str:
        """성적 분석 실행"""
        try:
            # GraphRAG를 통해 성적 정보 조회
            query = f"자녀의 {focus_area} 성적 분석" if focus_area else "자녀의 전체 성적 분석 및 또래 비교"
            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text=query,
                use_vector_search=True
            )

            # 성적 분석 리포트 생성
            analysis = f"""**성적 분석 리포트**

{context}

**또래 비교 분석:**
- 같은 반 학생들과 비교하여 상위권/중위권/하위권 파악
- 영역별 강약점 분석

**개선 추이:**
- 최근 학습 활동 기록을 바탕으로 성장 가능성 예측
- 꾸준한 학습이 필요한 영역 식별
"""
            return analysis

        except Exception as e:
            return f"성적 분석 실패: {str(e)}"

    def _get_study_advice(self, student_id: str, area: Optional[str] = None) -> str:
        """학습 조언 제공"""
        try:
            # GraphRAG를 통해 약점 영역 파악
            query = f"{area} 영역 개선 방안" if area else "전체 약점 개선 방안"
            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text=query,
                use_vector_search=True
            )

            # 학습 조언 생성 (GPT-4o 사용)
            advice_prompt = f"""당신은 교육 전문가입니다. 다음 학생 정보를 바탕으로 학부모님께 맞춤형 학습 조언을 제공해주세요.

**학생 정보:**
{context}

**조언 영역:**
{area if area else "전체 영역"}

**다음 형식으로 답변해주세요:**

1. **현재 상황 요약**
   - 자녀의 강점과 약점 간략히 정리

2. **가정에서 도와주실 수 있는 방법**
   - 구체적이고 실천 가능한 3-5가지 방법
   - 매일 또는 매주 할 수 있는 활동

3. **추천 학습 자료**
   - 영어 학습 앱, 책, 웹사이트 등

4. **학습 시간 및 환경 관리**
   - 효과적인 학습 시간대
   - 집중력을 높이는 환경 조성법

존댓말을 사용하고, 실천 가능한 조언을 제공해주세요.
"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 학부모 상담 전문 교육 컨설턴트입니다."},
                    {"role": "user", "content": advice_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"학습 조언 생성 실패: {str(e)}"

    def _get_attendance_status(self, student_id: str) -> str:
        """출석 및 숙제 현황 조회"""
        try:
            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text="출석률, 숙제 완료율, 학습 태도",
                use_vector_search=False  # 직접 그래프 조회
            )

            return f"""**출석 및 학습 태도 현황**

{context}

**학부모님께 안내:**
- 정기적인 출석이 학습 성과에 가장 중요한 요소입니다
- 숙제는 수업 내용 복습 및 이해도 확인을 위해 필수적입니다
- 학습 태도는 장기적인 영어 실력 향상의 핵심입니다
"""
        except Exception as e:
            return f"출석 현황 조회 실패: {str(e)}"

    def _recommend_improvement_areas(self, student_id: str, priority: str = "urgent") -> str:
        """개선 영역 추천"""
        try:
            # 우선순위 기준에 따라 쿼리 조정
            if priority == "urgent":
                query = "가장 시급하게 개선이 필요한 약점 영역"
            elif priority == "balanced":
                query = "균형 잡힌 학습을 위한 전체 영역 개선 계획"
            else:  # strength
                query = "강점을 더욱 강화하기 위한 심화 학습 방안"

            context = self.graph_rag_service.get_rag_context(
                student_id=student_id,
                query_text=query,
                use_vector_search=True
            )

            # 개선 계획 생성 (GPT-4o 사용)
            plan_prompt = f"""당신은 교육 전문가입니다. 다음 학생 정보를 바탕으로 학부모님께 구체적인 개선 계획을 제시해주세요.

**학생 정보:**
{context}

**우선순위:**
{priority} ({'시급한 약점 개선' if priority == 'urgent' else '균형 잡힌 학습' if priority == 'balanced' else '강점 강화'})

**다음 형식으로 답변해주세요:**

1. **우선 개선 영역 (1-2개)**
   - 영역명과 현재 수준
   - 개선이 필요한 이유

2. **4주 학습 계획**
   - 주차별 학습 목표
   - 구체적인 학습 활동 (매일 10-15분)

3. **중간 점검 방법**
   - 2주 후 확인할 사항
   - 개선 여부 판단 기준

4. **학원과 가정의 역할**
   - 학원에서 제공하는 것
   - 가정에서 도와주실 것

존댓말을 사용하고, 실천 가능한 계획을 제공해주세요.
"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 학부모 상담 전문 교육 컨설턴트입니다."},
                    {"role": "user", "content": plan_prompt}
                ],
                temperature=0.7,
                max_tokens=1200
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"개선 계획 생성 실패: {str(e)}"

    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Function 실행"""
        print(f"🔧 FUNCTION CALLED: {function_name}")
        print(f"📋 ARGUMENTS: {json.dumps(arguments, ensure_ascii=False)}")

        if function_name == "get_child_info":
            # 벡터 검색을 위해 현재 사용자 메시지 전달
            return self._get_child_info(query_text=self.current_user_message, **arguments)
        elif function_name == "analyze_performance":
            return self._analyze_performance(**arguments)
        elif function_name == "get_study_advice":
            return self._get_study_advice(**arguments)
        elif function_name == "get_attendance_status":
            return self._get_attendance_status(**arguments)
        elif function_name == "recommend_improvement_areas":
            return self._recommend_improvement_areas(**arguments)
        else:
            return f"Unknown function: {function_name}"

    def chat(
        self,
        student_id: str,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        학부모와 채팅 (Function Calling)

        Args:
            student_id: 자녀의 학생 ID
            message: 학부모의 메시지
            chat_history: 이전 대화 기록 (선택)

        Returns:
            Dict with 'message' and 'model_info'
        """
        try:
            # 현재 사용자 메시지 저장 (벡터 검색용)
            self.current_user_message = message

            used_models = []  # Track models used

            # PromptManager를 사용해 시스템 프롬프트 생성
            system_prompt = PromptManager.get_system_prompt(
                role="parent",
                model="gpt-4.1-mini",
                context={"student_id": student_id}
            )

            # 메시지 구성 (멀티턴 지원)
            messages = [{"role": "system", "content": system_prompt}]

            # 대화 히스토리 추가
            if chat_history:
                messages.extend(chat_history)

            # 최신 사용자 메시지 추가
            messages.append({"role": "user", "content": message})

            # gpt-4.1-mini로 function calling (빠른 인텔리전스 모델)
            used_models.append("gpt-4.1-mini")
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                tools=self.functions,
                tool_choice="auto",  # 자동으로 도구 선택
                temperature=0.7
            )

            assistant_message = response.choices[0].message

            # Function 호출이 있는 경우
            if assistant_message.tool_calls:
                # Function 실행
                messages.append(assistant_message)

                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    print(f"🔧 Function Call: {function_name}({arguments})")

                    # Track special models used in functions
                    if function_name in ["get_study_advice", "recommend_improvement_areas"]:
                        used_models.append("gpt-4o")

                    # Function 실행
                    function_response = self._execute_function(function_name, arguments)

                    # Function 결과를 메시지에 추가
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_response
                    })

                # Function 결과를 바탕으로 최종 응답 생성
                final_response = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages,
                    temperature=0.7
                )

                response_content = final_response.choices[0].message.content
                return {
                    "message": response_content,
                    "model_info": {
                        "primary": "gpt-4.1-mini",
                        "all_used": list(set(used_models))
                    }
                }
            else:
                # Function 호출 없이 직접 응답
                return {
                    "message": assistant_message.content,
                    "model_info": {
                        "primary": "gpt-4.1-mini",
                        "all_used": ["gpt-4.1-mini"]
                    }
                }

        except Exception as e:
            return {
                "message": f"죄송합니다. 오류가 발생했습니다: {str(e)}",
                "model_info": {"primary": "error", "all_used": []}
            }


# 싱글톤 인스턴스
_parent_agent_service = None


def get_parent_agent_service() -> ParentAgentService:
    """Parent Agent 서비스 싱글톤 인스턴스 가져오기"""
    global _parent_agent_service
    if _parent_agent_service is None:
        _parent_agent_service = ParentAgentService()
    return _parent_agent_service
