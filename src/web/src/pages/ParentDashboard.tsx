/**
 * Parent Dashboard Page
 * 학부모용 대시보드 - 로그인 후 자녀 학습 현황 확인 및 AI 상담
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/services';
import {
  BookOpen,
  Bell,
  Settings,
  UserCircle2,
  MessageCircle,
  Send,
  BarChart3,
  TrendingUp,
  Calendar,
  Award,
} from 'lucide-react';

export default function ParentDashboard() {
  const navigate = useNavigate();
  const [studentId, setStudentId] = useState<string | null>(null);
  const [parentId, setParentId] = useState<string | null>(null);
  const [loginInput, setLoginInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'chat'>('overview');

  // Chat state
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Check localStorage for logged-in parent
  useEffect(() => {
    const savedParentId = localStorage.getItem('parentId');
    const savedStudentId = localStorage.getItem('studentId'); // API가 student_id도 반환함
    if (savedParentId) {
      setParentId(savedParentId);
      // student_id는 API 응답에서 받아서 사용
      if (savedStudentId) {
        setStudentId(savedStudentId);
      }
    }
  }, []);

  // Fetch student data
  const { data: student, isLoading: studentLoading } = useQuery({
    queryKey: ['student', studentId],
    queryFn: () => api.students.getById(studentId!),
    enabled: !!studentId,
  });

  // Fetch student stats
  const { data: stats } = useQuery({
    queryKey: ['student', 'stats', studentId],
    queryFn: () => api.students.getStats(studentId!),
    enabled: !!studentId,
  });

  // Fetch class info
  const { data: classInfo } = useQuery({
    queryKey: ['class', student?.class_id],
    queryFn: () => api.classes.getById(student!.class_id!),
    enabled: !!student?.class_id,
  });

  // Login handler
  const handleLogin = async () => {
    if (!loginInput.trim() || !passwordInput.trim()) {
      setLoginError('학부모 ID와 비밀번호를 입력하세요.');
      return;
    }

    setIsLoggingIn(true);
    setLoginError('');

    try {
      const response = await fetch('/api/auth/parent/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          student_id: loginInput, // API는 student_id 필드를 받지만 parent_id를 입력받음
          password: passwordInput,
        }),
      });

      const data = await response.json();

      if (data.success) {
        // parent_id와 student_id 모두 저장
        localStorage.setItem('parentId', data.parent_id);
        localStorage.setItem('parentName', data.name);
        if (data.student_id) {
          localStorage.setItem('studentId', data.student_id);
        }
        setParentId(data.parent_id);
        setStudentId(data.student_id);
        setLoginError('');
      } else {
        setLoginError(data.message || '로그인 실패');
      }
    } catch (error) {
      setLoginError('로그인 중 오류가 발생했습니다.');
      console.error('Login error:', error);
    } finally {
      setIsLoggingIn(false);
    }
  };

  // Logout handler
  const handleLogout = () => {
    localStorage.removeItem('parentId');
    localStorage.removeItem('parentName');
    localStorage.removeItem('studentId');
    setParentId(null);
    setStudentId(null);
    setLoginInput('');
    setChatMessages([]);
  };

  // Chat message handler
  const handleSendMessage = async () => {
    if (!chatInput.trim() || !studentId) return;

    const userMessage = chatInput.trim();
    setChatInput('');

    // Add user message to chat
    const newMessages = [...chatMessages, { role: 'user' as const, content: userMessage }];
    setChatMessages(newMessages);
    setIsChatLoading(true);

    try {
      const response = await fetch('/api/chat/parent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          student_id: studentId,
          messages: newMessages,
        }),
      });

      const data = await response.json();

      if (data.message) {
        setChatMessages([...newMessages, { role: 'assistant', content: data.message }]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setChatMessages([
        ...newMessages,
        { role: 'assistant', content: '죄송합니다. 오류가 발생했습니다. 잠시 후 다시 시도해주세요.' },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  // Login screen
  if (!parentId) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <UserCircle2 className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">ClassMate</h1>
            <p className="text-gray-600">학부모용 자녀 학습 관리</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                학부모 ID
              </label>
              <input
                type="text"
                value={loginInput}
                onChange={(e) => {
                  setLoginInput(e.target.value);
                  setLoginError('');
                }}
                onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                placeholder="P-01"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                비밀번호
              </label>
              <input
                type="password"
                value={passwordInput}
                onChange={(e) => {
                  setPasswordInput(e.target.value);
                  setLoginError('');
                }}
                onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                placeholder="parent"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            {loginError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {loginError}
              </div>
            )}

            <button
              onClick={handleLogin}
              disabled={!loginInput.trim() || !passwordInput.trim() || isLoggingIn}
              className="w-full bg-gradient-to-r from-purple-500 to-blue-600 text-white py-3 rounded-lg font-medium hover:from-purple-600 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoggingIn ? '로그인 중...' : '로그인'}
            </button>

            <div className="text-xs text-gray-500 space-y-1">
              <p className="text-center font-medium">테스트 계정</p>
              <p className="text-center">학부모 ID: P-01, P-02, P-03 등</p>
              <p className="text-center">비밀번호: parent</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  if (studentLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  // Student not found
  if (!student) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-500 mb-4">자녀 정보를 찾을 수 없습니다: {studentId}</p>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
          >
            다시 로그인
          </button>
        </div>
      </div>
    );
  }

  // Dashboard
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* 로고 - 메인 화면으로 이동 */}
            <div
              onClick={() => navigate('/')}
              className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
            >
              <BookOpen className="w-6 h-6 text-purple-600" />
              <span className="text-xl font-bold text-gray-900">ClassMate</span>
              <span className="text-sm text-gray-500 ml-2">학부모</span>
            </div>

            <div className="flex items-center gap-4">
              <button className="text-gray-600 hover:text-gray-900">
                <Bell className="w-5 h-5" />
              </button>
              <button className="text-gray-600 hover:text-gray-900">
                <Settings className="w-5 h-5" />
              </button>
              <button onClick={handleLogout} className="text-sm text-gray-600 hover:text-gray-900">
                로그아웃
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Student Info Card */}
        <div className="bg-white rounded-2xl shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-1">{student.name} 학생</h1>
              <p className="text-gray-600">{student.grade_label} · {classInfo?.class_name}반</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{student.cefr}</div>
                <div className="text-xs text-gray-500">CEFR 레벨</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{student.percentile_rank}위</div>
                <div className="text-xs text-gray-500">백분위</div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'overview'
                ? 'bg-purple-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            <BarChart3 className="w-4 h-4 inline mr-2" />
            학습 현황
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-6 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'chat'
                ? 'bg-purple-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            <MessageCircle className="w-4 h-4 inline mr-2" />
            AI 상담
          </button>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Stats Grid */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">출결 및 과제</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Calendar className="w-5 h-5 text-green-600" />
                    <span className="text-gray-700">출석률</span>
                  </div>
                  <span className="text-lg font-bold text-green-600">
                    {Math.round((student.attendance_rate || 0) * 100)}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <BookOpen className="w-5 h-5 text-blue-600" />
                    <span className="text-gray-700">숙제 완료율</span>
                  </div>
                  <span className="text-lg font-bold text-blue-600">
                    {Math.round((student.homework_completion_rate || 0) * 100)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Scores */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">영역별 점수</h3>
              <div className="space-y-3">
                {[
                  { name: '문법', score: student.grammar_score },
                  { name: '어휘', score: student.vocabulary_score },
                  { name: '독해', score: student.reading_score },
                  { name: '듣기', score: student.listening_score },
                  { name: '쓰기', score: student.writing_score },
                ].map((item, idx) => (
                  <div key={idx}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-gray-600">{item.name}</span>
                      <span className="text-sm font-medium text-gray-900">
                        {item.score ? item.score.toFixed(1) : 'N/A'}
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full"
                        style={{ width: item.score ? `${item.score}%` : '0%' }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Class Info */}
            {classInfo && (
              <div className="bg-white rounded-2xl shadow-sm p-6 md:col-span-2">
                <h3 className="text-lg font-bold text-gray-900 mb-4">수업 정보</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">수업 일정</div>
                    <div className="font-medium text-gray-900">{classInfo.schedule}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">현재 진도</div>
                    <div className="font-medium text-gray-900">{classInfo.progress}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">이번 숙제</div>
                    <div className="font-medium text-gray-900">{classInfo.homework}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">이번 달 시험</div>
                    <div className="font-medium text-gray-900">{classInfo.monthly_test}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Notes */}
            {(student.attitude || student.school_exam_level || student.csat_level) && (
              <div className="bg-white rounded-2xl shadow-sm p-6 md:col-span-2">
                <h3 className="text-lg font-bold text-gray-900 mb-4">학습 태도 및 평가</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {student.attitude && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">학습 태도</div>
                      <div className="font-medium text-gray-900">{student.attitude}</div>
                    </div>
                  )}
                  {student.school_exam_level && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">학교 평가</div>
                      <div className="font-medium text-gray-900">{student.school_exam_level}</div>
                    </div>
                  )}
                  {student.csat_level && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">진단 평가</div>
                      <div className="font-medium text-gray-900">{student.csat_level}</div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="bg-white rounded-2xl shadow-sm">
            {/* Chat Header */}
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 mb-2">AI 학습 상담</h2>
              <p className="text-gray-600">
                {student.name} 학생의 학습 데이터를 바탕으로 전문적인 상담을 제공합니다.
              </p>
            </div>

            {/* Chat Messages */}
            <div className="h-96 overflow-y-auto p-6 space-y-4">
              {chatMessages.length === 0 ? (
                <div className="text-center text-gray-500 py-12">
                  <MessageCircle className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-lg font-medium mb-2">안녕하세요, 학부모님!</p>
                  <p className="text-sm">자녀의 학습에 대해 궁금한 점을 물어보세요.</p>
                </div>
              ) : (
                chatMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                        msg.role === 'user'
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                ))
              )}
              {isChatLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-2xl px-4 py-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Chat Input */}
            <div className="p-6 border-t border-gray-200">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !isChatLoading && handleSendMessage()}
                  placeholder="메시지를 입력하세요..."
                  disabled={isChatLoading}
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!chatInput.trim() || isChatLoading}
                  className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <Send className="w-4 h-4" />
                  전송
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
