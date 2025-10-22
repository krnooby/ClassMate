# -*- coding: utf-8 -*-
"""
Student Agent Service (Proxy)
⚠️ DEPRECATED: This module has moved to student.services.agent_service

이 파일은 하위 호환성을 위해 유지되며, student.services로 리다이렉트합니다.
새로운 코드에서는 `from student.services import get_student_agent_service`를 사용하세요.
"""
import warnings

# Deprecation warning
warnings.warn(
    "api.services.student_agent_service is deprecated. "
    "Use 'from student.services import get_student_agent_service' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location
from student.services.agent_service import (
    StudentAgentService,
    get_student_agent_service
)

__all__ = ["StudentAgentService", "get_student_agent_service"]
