import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { GraduationCap, Users, BookOpen, Eye, EyeOff, AlertCircle, LogIn } from 'lucide-react';

type UserRole = 'teacher' | 'student' | 'parent';

interface LoginInfo {
  endpoint: string;
  redirectPath: string;
  placeholder: string;
  examples: string[];
  password: string;
}

const roleConfig: Record<UserRole, LoginInfo> = {
  teacher: {
    endpoint: '/api/auth/teacher/login',
    redirectPath: '/teacher-dashboard',
    placeholder: '선생님 ID (예: T-01)',
    examples: ['T-01', 'T-02', 'T-03', 'T-04'],
    password: 'teacher'
  },
  student: {
    endpoint: '/api/auth/login',
    redirectPath: '/student-dashboard',
    placeholder: '학생 ID (예: S-01)',
    examples: ['S-01', 'S-02', 'S-03'],
    password: 'test'
  },
  parent: {
    endpoint: '/api/auth/parent/login',
    redirectPath: '/parent-dashboard',
    placeholder: '학부모 ID (예: P-01)',
    examples: ['P-01', 'P-02', 'P-03'],
    password: 'parent'
  }
};

// 페이지 경로를 사용자 친화적인 이름으로 변환
const getPageName = (path: string): string => {
  const pageNames: Record<string, string> = {
    '/student-dashboard': '학생 대시보드',
    '/parent-dashboard': '학부모 대시보드',
    '/teacher-dashboard': '선생님 대시보드',
    '/student-main': '학생 메인 페이지',
    '/parent-main': '학부모 메인 페이지',
    '/teacher-main': '선생님 메인 페이지',
    '/problems': '문제 검색',
    '/': '메인 화면'
  };
  return pageNames[path] || path;
};

const UnifiedLogin: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [selectedRole, setSelectedRole] = useState<UserRole>('student');
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [capsLockOn, setCapsLockOn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // URL에서 redirect 파라미터 가져오기
  const redirectPath = searchParams.get('redirect');

  const handleLogin = async () => {
    if (!userId || !password) {
      alert('ID와 비밀번호를 모두 입력해주세요.');
      return;
    }

    setIsLoading(true);

    try {
      const config = roleConfig[selectedRole];
      console.log('🔐 로그인 시도:', { role: selectedRole, id: userId });

      const response = await fetch(config.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: userId,
          password: password,
        }),
      });

      console.log('📡 응답 상태:', response.status);
      const data = await response.json();
      console.log('📦 응답 데이터:', data);

      if (data.success) {
        // 역할별로 localStorage 키 저장
        if (selectedRole === 'teacher') {
          localStorage.setItem('teacherId', data.teacher_id || data.student_id);
          localStorage.setItem('teacherName', data.name);
        } else if (selectedRole === 'student') {
          localStorage.setItem('studentId', data.student_id);
          localStorage.setItem('studentName', data.name);
        } else if (selectedRole === 'parent') {
          localStorage.setItem('parentId', data.parent_id || data.student_id);
          localStorage.setItem('parentName', data.name);
          // 자녀 정보를 위해 student_id도 저장
          if (data.student_id) {
            localStorage.setItem('studentId', data.student_id);
          }
        }

        // 로그인 성공 후 리다이렉트
        // 1. URL에 redirect 파라미터가 있으면 그곳으로 이동
        // 2. 없으면 역할별 기본 대시보드로 이동
        const targetPath = redirectPath || config.redirectPath;
        console.log('✅ 로그인 성공! 이동:', targetPath);
        navigate(targetPath);
      } else {
        alert(data.message || '로그인에 실패했습니다.');
      }
    } catch (error) {
      console.error('❌ 로그인 오류:', error);
      alert('로그인 중 오류가 발생했습니다: ' + (error as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    const isCapsLock = e.getModifierState && e.getModifierState('CapsLock');
    setCapsLockOn(isCapsLock);
    if (e.key === 'Enter' && !isLoading) {
      handleLogin();
    }
  };

  const config = roleConfig[selectedRole];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        {/* 로고 & 제목 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-black rounded-full mb-4">
            <GraduationCap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">ClassMate</h1>
          <p className="text-gray-600">AI 영어 학습 플랫폼</p>
        </div>

        {/* 역할 선택 탭 */}
        <div className="flex gap-2 mb-6 bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setSelectedRole('student')}
            className={`flex-1 py-2.5 px-3 rounded-md font-medium transition-all flex items-center justify-center gap-2 ${
              selectedRole === 'student'
                ? 'bg-white text-black shadow-sm'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>학생</span>
          </button>
          <button
            onClick={() => setSelectedRole('teacher')}
            className={`flex-1 py-2.5 px-3 rounded-md font-medium transition-all flex items-center justify-center gap-2 ${
              selectedRole === 'teacher'
                ? 'bg-white text-black shadow-sm'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            <GraduationCap className="w-4 h-4" />
            <span>선생님</span>
          </button>
          <button
            onClick={() => setSelectedRole('parent')}
            className={`flex-1 py-2.5 px-3 rounded-md font-medium transition-all flex items-center justify-center gap-2 ${
              selectedRole === 'parent'
                ? 'bg-white text-black shadow-sm'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>학부모</span>
          </button>
        </div>

        {/* Redirect 안내 메시지 */}
        {redirectPath && (
          <div className="mb-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-gray-800">
              <AlertCircle className="w-4 h-4" />
              <span>로그인 후 <strong>{getPageName(redirectPath)}</strong>(으)로 이동합니다</span>
            </div>
          </div>
        )}

        {/* 로그인 폼 */}
        <div className="space-y-4">
          {/* ID 입력 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ID
            </label>
            <input
              type="text"
              placeholder={config.placeholder}
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              onKeyPress={handleKeyPress}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent transition"
            />
          </div>

          {/* 비밀번호 입력 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              비밀번호
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="비밀번호"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyPress={handleKeyPress}
                onKeyDown={(e) => {
                  const isCapsLock = e.getModifierState && e.getModifierState('CapsLock');
                  setCapsLockOn(isCapsLock);
                }}
                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent transition"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 transition"
              >
                {showPassword ? (
                  <EyeOff className="w-5 h-5" />
                ) : (
                  <Eye className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>

          {/* Caps Lock 경고 */}
          {capsLockOn && (
            <div className="flex items-center gap-2 text-amber-600 text-sm bg-amber-50 px-3 py-2 rounded-lg">
              <AlertCircle className="w-4 h-4" />
              <span>Caps Lock이 켜져 있습니다</span>
            </div>
          )}

          {/* 로그인 버튼 */}
          <button
            onClick={handleLogin}
            disabled={isLoading}
            className="w-full bg-black text-white py-3 rounded-lg font-semibold hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>로그인 중...</span>
              </>
            ) : (
              <>
                <LogIn className="w-5 h-5" />
                <span>로그인</span>
              </>
            )}
          </button>
        </div>

        {/* 테스트 계정 안내 */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm font-semibold text-gray-700 mb-2">
            📋 테스트 계정 정보
          </p>
          <div className="text-sm text-gray-600 space-y-1">
            <p>
              <span className="font-medium">ID:</span>{' '}
              {config.examples.join(', ')}
            </p>
            <p>
              <span className="font-medium">비밀번호:</span> {config.password}
            </p>
          </div>
        </div>

        {/* 하단 링크 */}
        <div className="mt-6 text-center">
          <button
            onClick={() => navigate('/')}
            className="text-sm text-gray-700 hover:text-black hover:underline"
          >
            메인 페이지로 돌아가기
          </button>
        </div>
      </div>
    </div>
  );
};

export default UnifiedLogin;
