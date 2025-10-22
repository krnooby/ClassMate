/**
 * Teacher Dashboard Component
 * 선생님 전용 - 시험지 업로드, 파싱, Daily Input
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle, XCircle, Clock, List, Users, PlusCircle, MessageCircle, Send, Eye, EyeOff, AlertCircle, BookOpen } from 'lucide-react';
import ExamUploadZone from '../components/ExamUploadZone';
import StudentRecordEditor from '../components/StudentRecordEditor';
import type { GroupedExamFiles } from '../utils/fileNameParser';

interface ParseJob {
  job_id: string;
  exam_id: string;
  status: string;
  progress: number;
  created_at: string;
}

interface ParseStatus {
  job_id: string;
  status: string;
  message: string;
  progress: number;
  results?: {
    problems?: { count: number; file: string };
    figures?: { count: number; file: string };
    tables?: { count: number; file: string };
  };
  error?: string;
}

interface Student {
  student_id: string;
  name: string;
  grade_code: string;
  grade_label: string;
  cefr: string;
  class_id?: string;
}

interface DailyInput {
  input_id: string;
  student_id: string;
  student_name: string;
  date: string;
  content: string;
  category: string;
  teacher_id: string;
  created_at: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export default function TeacherDashboard() {
  const navigate = useNavigate();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginInput, setLoginInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [teacherName, setTeacherName] = useState('');
  const [teacherId, setTeacherId] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [capsLockOn, setCapsLockOn] = useState(false);

  // 탭 관리
  const [activeTab, setActiveTab] = useState<'aichat' | 'upload' | 'dailyinput'>('aichat');

  // AI 챗봇 state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [uiPanel, setUiPanel] = useState<string | null>(null); // 'exam_upload' | 'daily_input' | null
  const [uiData, setUiData] = useState<any>(null);

  // Exam upload states removed - now using ExamUploadZone component

  const [parseStatus, setParseStatus] = useState<ParseStatus | null>(null);
  const [parseJobs, setParseJobs] = useState<ParseJob[]>([]);

  // Daily Input 상태
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [dailyInputDate, setDailyInputDate] = useState(new Date().toISOString().split('T')[0]);
  const [dailyInputContent, setDailyInputContent] = useState('');
  const [dailyInputCategory, setDailyInputCategory] = useState('vocabulary');
  const [submittingInput, setSubmittingInput] = useState(false);
  const [studentInputs, setStudentInputs] = useState<DailyInput[]>([]);

  // 로그인 체크
  useEffect(() => {
    const storedTeacherId = localStorage.getItem('teacherId');
    const name = localStorage.getItem('teacherName');
    if (storedTeacherId && name) {
      setIsLoggedIn(true);
      setTeacherName(name);
      setTeacherId(storedTeacherId);
    }
  }, []);

  // 학생 목록 조회
  useEffect(() => {
    if (isLoggedIn && teacherId) {
      fetchStudents();
    }
  }, [isLoggedIn, teacherId]);

  // 파싱 작업 목록 조회
  useEffect(() => {
    if (isLoggedIn && activeTab === 'upload') {
      fetchParseJobs();
      const interval = setInterval(fetchParseJobs, 5000); // 5초마다 갱신
      return () => clearInterval(interval);
    }
  }, [isLoggedIn, activeTab]);

  // Parse status polling removed - now handled by ExamUploadZone component

  const fetchStudents = async () => {
    try {
      const response = await fetch(`/api/teachers/my-students/${teacherId}`);
      const data = await response.json();
      setStudents(data.students || []);
    } catch (error) {
      console.error('Failed to fetch students:', error);
    }
  };

  const fetchParseJobs = async () => {
    try {
      const response = await fetch('/api/teachers/parse-jobs');
      const data = await response.json();
      setParseJobs(data.jobs || []);
    } catch (error) {
      console.error('Failed to fetch parse jobs:', error);
    }
  };

  const fetchParseStatus = async (jobId: string) => {
    try {
      const response = await fetch(`/api/teachers/parse-status/${jobId}`);
      const data = await response.json();
      setParseStatus(data);

      // 작업 완료 또는 실패 시 폴링 중지
      if (data.status === 'completed' || data.status === 'failed') {
        setCurrentJobId(null);
      }
    } catch (error) {
      console.error('Failed to fetch parse status:', error);
    }
  };

  const handleLogin = async () => {
    try {
      console.log('🔐 로그인 시도:', { id: loginInput, password: '***' });

      const response = await fetch('/api/auth/teacher/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: loginInput,
          password: passwordInput,
        }),
      });

      console.log('📡 응답 상태:', response.status);

      const data = await response.json();
      console.log('📦 응답 데이터:', data);

      if (data.success) {
        localStorage.setItem('teacherId', data.student_id);
        localStorage.setItem('teacherName', data.name);
        setIsLoggedIn(true);
        setTeacherId(data.student_id);
        setTeacherName(data.name);
      } else {
        alert(data.message);
      }
    } catch (error) {
      console.error('❌ 로그인 오류:', error);
      alert('로그인 중 오류가 발생했습니다: ' + (error as Error).message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('teacherId');
    localStorage.removeItem('teacherName');
    setIsLoggedIn(false);
    setTeacherName('');
    setTeacherId('');
  };

  const handleDailyInputSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedStudent || !dailyInputContent) {
      alert('학생과 내용을 입력해주세요.');
      return;
    }

    setSubmittingInput(true);

    try {
      const response = await fetch('/api/teachers/daily-input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: selectedStudent.student_id,
          date: dailyInputDate,
          content: dailyInputContent,
          category: dailyInputCategory,
          teacher_id: teacherId,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        alert('Daily Input이 저장되었습니다!');
        setDailyInputContent('');
        // Refresh inputs if same student is selected
        if (selectedStudent) {
          fetchStudentInputs(selectedStudent.student_id);
        }
      } else {
        alert(`저장 실패: ${data.detail}`);
      }
    } catch (error) {
      alert('저장 중 오류 발생');
    } finally {
      setSubmittingInput(false);
    }
  };

  const fetchStudentInputs = async (studentId: string) => {
    try {
      const response = await fetch(`/api/teachers/daily-inputs/${studentId}`);
      const data = await response.json();
      setStudentInputs(data.inputs || []);
    } catch (error) {
      console.error('Failed to fetch student inputs:', error);
      setStudentInputs([]);
    }
  };

  // AI 챗봇 메시지 전송
  const sendChatMessage = async () => {
    if (!chatInput.trim() || chatLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: chatInput
    };

    setChatMessages(prev => [...prev, userMessage]);
    setChatInput('');
    setChatLoading(true);

    try {
      const response = await fetch('/api/chat/teacher', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          teacher_id: teacherId,
          messages: [...chatMessages, userMessage].map(msg => ({
            role: msg.role,
            content: msg.content
          }))
        })
      });

      const data = await response.json();

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.message
      };

      setChatMessages(prev => [...prev, assistantMessage]);

      // UI 패널 트리거 확인
      if (data.ui_panel) {
        setUiPanel(data.ui_panel);
        setUiData(data.ui_data);
      }

    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: '죄송합니다. 오류가 발생했습니다.'
      };
      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleStudentSelect = (student: Student) => {
    setSelectedStudent(student);
    fetchStudentInputs(student.student_id);
  };

  const handleFilesReady = async (exams: GroupedExamFiles[]) => {
    if (exams.length === 0) {
      alert('업로드할 파일이 없습니다.');
      return;
    }

    setUploading(true);

    try {
      const uploadPromises = exams.map(async (exam) => {
        if (!exam.question) {
          throw new Error(`시험 "${exam.examId}"에 문제지 파일이 없습니다.`);
        }

        const formData = new FormData();
        formData.append('exam_id', exam.examId);
        formData.append('question_file', exam.question);
        if (exam.answer) formData.append('answer_file', exam.answer);
        if (exam.solution) formData.append('solution_file', exam.solution);

        const response = await fetch('/api/teachers/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`${exam.examId}: ${errorData.detail || '업로드 실패'}`);
        }

        return await response.json();
      });

      const results = await Promise.all(uploadPromises);

      alert(
        `${results.length}개 시험 업로드 완료!\n\n` +
        results.map((r, i) => `${exams[i].examId}: Job ID ${r.job_id}`).join('\n')
      );

      // 첫 번째 작업 추적
      if (results.length > 0) {
        setCurrentJobId(results[0].job_id);
        setParseStatus(null);
      }

      setQuestionFile(null);
      setAnswerFile(null);
      setSolutionFile(null);

      // 작업 목록 새로고침
      fetchParseJobs();
    } catch (error) {
      console.error('Upload error:', error);
      alert(`업로드 중 오류 발생: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
    } finally {
      setUploading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-6 h-6 text-green-500" />;
      case 'failed':
        return <XCircle className="w-6 h-6 text-red-500" />;
      case 'processing':
        return <Clock className="w-6 h-6 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-6 h-6 text-gray-400" />;
    }
  };

  // 로그인 화면
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
          <h1 className="text-2xl font-bold text-center mb-6">선생님 로그인</h1>

          <div className="space-y-4">
            <div>
              <input
                type="text"
                placeholder="선생님 ID (예: T-01)"
                value={loginInput}
                onChange={(e) => setLoginInput(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg"
              />
            </div>

            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="비밀번호"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                onKeyPress={(e) => {
                  // Caps Lock 감지
                  const isCapsLock = e.getModifierState && e.getModifierState('CapsLock');
                  setCapsLockOn(isCapsLock);

                  if (e.key === 'Enter') handleLogin();
                }}
                onKeyDown={(e) => {
                  const isCapsLock = e.getModifierState && e.getModifierState('CapsLock');
                  setCapsLockOn(isCapsLock);
                }}
                className="w-full px-4 py-2 pr-10 border rounded-lg"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showPassword ? (
                  <EyeOff className="w-5 h-5" />
                ) : (
                  <Eye className="w-5 h-5" />
                )}
              </button>
            </div>

            {capsLockOn && (
              <div className="flex items-center gap-2 text-amber-600 text-sm bg-amber-50 px-3 py-2 rounded-lg">
                <AlertCircle className="w-4 h-4" />
                <span>Caps Lock이 켜져 있습니다</span>
              </div>
            )}

            <button
              onClick={handleLogin}
              className="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 cursor-pointer"
            >
              로그인
            </button>
          </div>

          <div className="text-sm text-gray-500 text-center mt-4 space-y-1">
            <p className="font-medium">테스트 계정:</p>
            <p>ID: T-01, T-02, T-03, T-04</p>
            <p>비밀번호: teacher</p>
          </div>
        </div>
      </div>
    );
  }

  // 선생님 대시보드
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <div className="bg-white shadow">
        <div className="container mx-auto px-4 py-4">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-4">
              {/* 로고 - 메인 화면으로 이동 */}
              <div
                onClick={() => navigate('/')}
                className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
              >
                <BookOpen className="w-6 h-6 text-gray-900" />
                <span className="text-xl font-bold text-gray-900">ClassMate</span>
              </div>
              <div className="h-6 w-px bg-gray-300"></div>
              <h1 className="text-xl font-bold text-gray-700">선생님 대시보드</h1>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-gray-700">{teacherName} 선생님</span>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 cursor-pointer"
              >
                로그아웃
              </button>
            </div>
          </div>

          {/* 탭 네비게이션 */}
          <div className="flex gap-2 border-b">
            <button
              onClick={() => setActiveTab('aichat')}
              className={`px-4 py-2 font-medium transition-colors cursor-pointer ${
                activeTab === 'aichat'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-blue-600'
              }`}
            >
              <div className="flex items-center gap-2">
                <MessageCircle className="w-5 h-5" />
                <span>AI 챗봇</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('dailyinput')}
              className={`px-4 py-2 font-medium transition-colors cursor-pointer ${
                activeTab === 'dailyinput'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-blue-600'
              }`}
            >
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                <span>학생 기록 작성</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`px-4 py-2 font-medium transition-colors cursor-pointer ${
                activeTab === 'upload'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-blue-600'
              }`}
            >
              <div className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                <span>시험지 업로드</span>
              </div>
            </button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {/* AI 챗봇 탭 */}
        {activeTab === 'aichat' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-200px)]">
            {/* 좌측: AI 챗봇 */}
            <div className="bg-white rounded-lg shadow p-6 flex flex-col">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <MessageCircle className="w-6 h-6" />
                AI 업무 도우미
              </h2>

              {/* 채팅 메시지 */}
              <div className="flex-1 overflow-y-auto mb-4 space-y-4">
                {chatMessages.length === 0 && (
                  <div className="text-center text-gray-500 py-12">
                    <p className="mb-4">무엇을 도와드릴까요?</p>
                    <div className="text-sm space-y-2">
                      <p>• "우리반 학생들 보여줘"</p>
                      <p>• "독해 70점 미만 학생 검색"</p>
                      <p>• "시험지 업로드"</p>
                      <p>• "학생 기록부 작성"</p>
                    </div>
                  </div>
                )}

                {chatMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] p-3 rounded-lg ${
                        msg.role === 'user'
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                ))}

                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 p-3 rounded-lg">
                      <p className="text-gray-500">입력 중...</p>
                    </div>
                  </div>
                )}
              </div>

              {/* 입력창 */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendChatMessage()}
                  placeholder="메시지를 입력하세요..."
                  className="flex-1 px-4 py-2 border rounded-lg"
                  disabled={chatLoading}
                />
                <button
                  onClick={sendChatMessage}
                  disabled={chatLoading || !chatInput.trim()}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed cursor-pointer"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* 우측: 동적 패널 */}
            <div className="bg-white rounded-lg shadow p-6">
              {!uiPanel && (
                <div className="text-center text-gray-500 py-12">
                  <p>AI 챗봇과 대화하면 여기에 관련 정보가 표시됩니다.</p>
                </div>
              )}

              {uiPanel === 'exam_upload' && (
                <div>
                  <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <Upload className="w-6 h-6" />
                    시험지 업로드
                  </h2>

                  <ExamUploadZone onUploadComplete={() => {
                    setUiPanel(null);
                    fetchParseJobs();
                  }} />
                </div>
              )}

              {uiPanel === 'daily_input' && (
                <div>
                  <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                    <Users className="w-6 h-6" />
                    학생 기록부 작성
                  </h2>

                  <form onSubmit={handleDailyInputSubmit} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        학생 선택 <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={selectedStudent?.student_id || ''}
                        onChange={(e) => {
                          const student = students.find(s => s.student_id === e.target.value);
                          setSelectedStudent(student || null);
                          if (student) {
                            fetchStudentInputs(student.student_id);
                          }
                        }}
                        className="w-full px-4 py-2 border rounded-lg"
                        required
                      >
                        <option value="">학생을 선택하세요...</option>
                        {students.map((student) => (
                          <option key={student.student_id} value={student.student_id}>
                            {student.name} ({student.student_id})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        날짜
                      </label>
                      <input
                        type="date"
                        value={dailyInputDate}
                        onChange={(e) => setDailyInputDate(e.target.value)}
                        className="w-full px-4 py-2 border rounded-lg"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        카테고리
                      </label>
                      <select
                        value={dailyInputCategory}
                        onChange={(e) => setDailyInputCategory(e.target.value)}
                        className="w-full px-4 py-2 border rounded-lg"
                      >
                        <option value="vocabulary">어휘</option>
                        <option value="grammar">문법</option>
                        <option value="reading">독해</option>
                        <option value="listening">듣기</option>
                        <option value="writing">쓰기</option>
                        <option value="homework">숙제</option>
                        <option value="behavior">수업 태도</option>
                        <option value="other">기타</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        내용 <span className="text-red-500">*</span>
                      </label>
                      <textarea
                        value={dailyInputContent}
                        onChange={(e) => setDailyInputContent(e.target.value)}
                        className="w-full px-4 py-2 border rounded-lg h-32"
                        placeholder="오늘의 학습 내용, 특이사항 등을 입력하세요..."
                        required
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={submittingInput || !selectedStudent}
                      className="w-full py-3 bg-green-500 text-white font-medium rounded-lg hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed cursor-pointer"
                    >
                      {submittingInput ? '저장 중...' : '저장'}
                    </button>
                  </form>

                  {selectedStudent && studentInputs.length > 0 && (
                    <div className="mt-6">
                      <h3 className="font-medium mb-3">최근 입력 기록</h3>
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {studentInputs.slice(0, 3).map((input) => (
                          <div key={input.input_id} className="p-3 bg-gray-50 border rounded-lg text-sm">
                            <div className="flex justify-between mb-1">
                              <span className="font-medium">{input.date}</span>
                              <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                                {input.category}
                              </span>
                            </div>
                            <p className="text-gray-700 line-clamp-2">{input.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* 학생 기록 작성 탭 (구 Daily Input) */}
        {activeTab === 'dailyinput' && (
          <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6">
            {/* 학생 목록 */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Users className="w-6 h-6" />
                담당 학생 ({students.length})
              </h2>

              <div className="space-y-2 max-h-[700px] overflow-y-auto">
                {students.map((student) => (
                  <button
                    key={student.student_id}
                    onClick={() => handleStudentSelect(student)}
                    className={`w-full text-left p-3 rounded-lg transition-colors cursor-pointer ${
                      selectedStudent?.student_id === student.student_id
                        ? 'bg-indigo-50 border-2 border-indigo-500'
                        : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                    }`}
                  >
                    <p className="font-medium">{student.name}</p>
                    <p className="text-sm text-gray-600">{student.grade_label}</p>
                    <p className="text-xs text-gray-500">CEFR: {student.cefr}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* 학생 기록 편집기 */}
            <div className="bg-white rounded-lg shadow p-6">
              {selectedStudent ? (
                <StudentRecordEditor
                  student={selectedStudent}
                  onSaved={() => {
                    // 저장 후 학생 목록 새로고침
                    fetchStudents();
                  }}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-center py-12 text-gray-500">
                  <div>
                    <Users className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p className="text-lg font-medium">왼쪽에서 학생을 선택하세요</p>
                    <p className="text-sm mt-2">학생의 출석, 숙제, 특이사항, 점수 정보를 관리할 수 있습니다</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 시험지 업로드 탭 */}
        {activeTab === 'upload' && (
          <div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* 파일 업로드 폼 */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Upload className="w-6 h-6" />
              시험지 업로드
            </h2>

            <ExamUploadZone onFilesReady={handleFilesReady} />
          </div>

          {/* 파싱 상태 */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <FileText className="w-6 h-6" />
              파싱 상태
            </h2>

            {parseStatus ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  {getStatusIcon(parseStatus.status)}
                  <div className="flex-1">
                    <p className="font-medium">{parseStatus.status}</p>
                    <p className="text-sm text-gray-600">{parseStatus.message}</p>
                  </div>
                </div>

                {/* 프로그레스 바 */}
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div
                    className="bg-blue-500 h-4 rounded-full transition-all"
                    style={{ width: `${parseStatus.progress}%` }}
                  />
                </div>
                <p className="text-sm text-gray-600 text-center">{parseStatus.progress}%</p>

                {/* 결과 */}
                {parseStatus.results && (
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h3 className="font-medium text-green-800 mb-2">파싱 완료!</h3>
                    <ul className="space-y-1 text-sm text-green-700">
                      {parseStatus.results.problems && (
                        <li>문제: {parseStatus.results.problems.count}개</li>
                      )}
                      {parseStatus.results.figures && (
                        <li>이미지: {parseStatus.results.figures.count}개</li>
                      )}
                      {parseStatus.results.tables && (
                        <li>테이블: {parseStatus.results.tables.count}개</li>
                      )}
                    </ul>
                  </div>
                )}

                {/* 에러 */}
                {parseStatus.error && (
                  <div className="bg-red-50 p-4 rounded-lg">
                    <p className="text-sm text-red-700">{parseStatus.error}</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">
                파싱 작업이 없습니다.
              </p>
            )}
          </div>
        </div>

        {/* 파싱 작업 목록 */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <List className="w-6 h-6" />
            파싱 작업 목록
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left">시험 ID</th>
                  <th className="px-4 py-2 text-left">상태</th>
                  <th className="px-4 py-2 text-left">진행률</th>
                  <th className="px-4 py-2 text-left">생성일시</th>
                  <th className="px-4 py-2 text-left">액션</th>
                </tr>
              </thead>
              <tbody>
                {parseJobs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      파싱 작업이 없습니다.
                    </td>
                  </tr>
                ) : (
                  parseJobs.map((job) => (
                    <tr key={job.job_id} className="border-t">
                      <td className="px-4 py-3">{job.exam_id}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-1 rounded text-sm ${
                            job.status === 'completed'
                              ? 'bg-green-100 text-green-800'
                              : job.status === 'failed'
                              ? 'bg-red-100 text-red-800'
                              : job.status === 'processing'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">{job.progress}%</td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {new Date(job.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => {
                            setCurrentJobId(job.job_id);
                            fetchParseStatus(job.job_id);
                          }}
                          className="text-blue-500 hover:underline text-sm cursor-pointer"
                        >
                          상세보기
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
          </div>
        )}
      </div>
    </div>
  );
}
