import React, { useState, useEffect } from 'react';
import { Save, User, BookOpen, FileText, BarChart3, AlertCircle, Calendar } from 'lucide-react';

interface Student {
  student_id: string;
  name: string;
  grade_label: string;
  cefr: string;
}

interface StudentDetail {
  student_id: string;
  name: string;
  attendance: {
    total_sessions: number;
    absent: number;
    perception: number;
  };
  homework: {
    assigned: number;
    missed: number;
  };
  notes: {
    attitude: string;
    school_exam_level: string;
    csat_level: string;
  };
  assessment: {
    radar_scores: {
      grammar: number;
      vocabulary: number;
      reading: number;
      listening: number;
      writing: number;
    };
  };
}

interface DailyInput {
  input_id: string;
  student_id: string;
  student_name: string;
  date: string;
  content: string;
  category: string;
  summary?: string;
  teacher_id: string;
  created_at: string;
}

interface StudentRecordEditorProps {
  student: Student;
  onSaved: () => void;
}

const StudentRecordEditor: React.FC<StudentRecordEditorProps> = ({ student, onSaved }) => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [studentDetail, setStudentDetail] = useState<StudentDetail | null>(null);

  // 출석 정보
  const [totalSessions, setTotalSessions] = useState(0);
  const [absent, setAbsent] = useState(0);
  const [perception, setPerception] = useState(0);

  // 숙제 정보
  const [assigned, setAssigned] = useState(0);
  const [missed, setMissed] = useState(0);

  // 특이사항
  const [attitude, setAttitude] = useState('');
  const [schoolExamLevel, setSchoolExamLevel] = useState('');
  const [csatLevel, setCsatLevel] = useState('');

  // 영역별 점수
  const [grammar, setGrammar] = useState(0);
  const [vocabulary, setVocabulary] = useState(0);
  const [reading, setReading] = useState(0);
  const [listening, setListening] = useState(0);
  const [writing, setWriting] = useState(0);

  // Daily Input 정보
  const [dailyInputs, setDailyInputs] = useState<DailyInput[]>([]);
  const [dailyInputDate, setDailyInputDate] = useState(new Date().toISOString().split('T')[0]);
  const [dailyInputContent, setDailyInputContent] = useState('');
  const [submittingInput, setSubmittingInput] = useState(false);

  // 학생 상세 정보 불러오기
  useEffect(() => {
    if (student) {
      fetchStudentDetail();
      fetchDailyInputs();
      // 폼 초기화 (새 학생 선택 시)
      resetForms();
    }
  }, [student]);

  const resetForms = () => {
    // 출석, 숙제, 특이사항, 점수 폼을 빈 상태로 초기화하지 않음
    // (기존 데이터를 보여주되, 선생님이 필요한 부분만 수정)
  };

  const fetchStudentDetail = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/teachers/student-detail/${student.student_id}`);
      const data = await response.json();

      if (data.success) {
        const detail = data.student;
        // 읽기 전용으로만 저장 (입력 필드에는 채우지 않음)
        setStudentDetail(detail);

        // 입력 폼은 초기화된 상태로 유지 (빈 칸)
        setTotalSessions(0);
        setAbsent(0);
        setPerception(0);
        setAssigned(0);
        setMissed(0);
        setAttitude('');
        setSchoolExamLevel('');
        setCsatLevel('');
        setGrammar(0);
        setVocabulary(0);
        setReading(0);
        setListening(0);
        setWriting(0);
      }
    } catch (error) {
      console.error('Failed to fetch student detail:', error);
      alert('학생 정보를 불러오는데 실패했습니다: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDailyInputs = async () => {
    try {
      const response = await fetch(`/api/teachers/daily-inputs/${student.student_id}`);
      const data = await response.json();
      setDailyInputs(data.inputs || []);
    } catch (error) {
      console.error('Failed to fetch daily inputs:', error);
      setDailyInputs([]);
    }
  };

  const handleDailyInputSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!dailyInputContent.trim()) {
      alert('내용을 입력해주세요.');
      return;
    }

    setSubmittingInput(true);

    try {
      const teacherId = localStorage.getItem('teacherId');
      const response = await fetch('/api/teachers/daily-input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: student.student_id,
          date: dailyInputDate,
          content: dailyInputContent,
          teacher_id: teacherId,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        alert('일일 기록이 저장되었습니다! (요약 및 임베딩 자동 생성 완료)');
        setDailyInputContent('');
        fetchDailyInputs(); // Refresh inputs
      } else {
        alert(`저장 실패: ${data.detail}`);
      }
    } catch (error) {
      alert('저장 중 오류 발생');
    } finally {
      setSubmittingInput(false);
    }
  };

  const handleSave = async (section: 'attendance' | 'homework' | 'notes' | 'scores') => {
    setSaving(true);

    try {
      const updateData: any = {};

      // 섹션별로 변경된 데이터만 전송
      if (section === 'attendance') {
        updateData.attendance = { total_sessions: totalSessions, absent, perception };
      } else if (section === 'homework') {
        updateData.homework = { assigned, missed };
      } else if (section === 'notes') {
        updateData.notes = { attitude, school_exam_level: schoolExamLevel, csat_level: csatLevel };
      } else if (section === 'scores') {
        updateData.radar_scores = { grammar, vocabulary, reading, listening, writing };
      }

      const response = await fetch(`/api/teachers/student-record/${student.student_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      });

      const data = await response.json();

      if (data.success) {
        alert('저장되었습니다!');
        onSaved();
      } else {
        alert('저장 실패: ' + data.message);
      }
    } catch (error) {
      console.error('Save error:', error);
      alert('저장 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  // 전체 일괄 저장
  const handleSaveAll = async () => {
    setSaving(true);

    try {
      const updateData = {
        attendance: { total_sessions: totalSessions, absent, perception },
        homework: { assigned, missed },
        notes: { attitude, school_exam_level: schoolExamLevel, csat_level: csatLevel },
        radar_scores: { grammar, vocabulary, reading, listening, writing }
      };

      const response = await fetch(`/api/teachers/student-record/${student.student_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      });

      const data = await response.json();

      if (data.success) {
        alert('전체 저장 완료!');
        onSaved();
      } else {
        alert('저장 실패: ' + data.message);
      }
    } catch (error) {
      console.error('Save all error:', error);
      alert('저장 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-500">학생 정보 불러오는 중...</div>
      </div>
    );
  }

  const attendanceRate = totalSessions > 0 ? Math.round(((totalSessions - absent) / totalSessions) * 100) : 0;
  const homeworkRate = assigned > 0 ? Math.round(((assigned - missed) / assigned) * 100) : 0;

  return (
    <div className="space-y-6 max-h-[calc(100vh-250px)] overflow-y-auto pr-2">
      {/* 학생 정보 헤더 */}
      <div className="flex items-center gap-3 pb-4 border-b sticky top-0 bg-white z-10">
        <User className="w-6 h-6 text-indigo-600" />
        <div>
          <h3 className="text-lg font-semibold">{student.name}</h3>
          <p className="text-sm text-gray-500">
            {student.grade_label} · CEFR {student.cefr}
          </p>
        </div>
      </div>

      {/* 일일 기록 섹션 */}
      <div className="space-y-4 pb-6 border-b">
        <h4 className="text-lg font-bold flex items-center gap-2 text-indigo-600">
          <Calendar className="w-5 h-5" />
          일일 기록
        </h4>
        <div>
          <div className="space-y-6">
            {/* Daily Input 입력 폼 */}
            <form onSubmit={handleDailyInputSubmit} className="space-y-4 pb-6 border-b">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  날짜
                </label>
                <input
                  type="date"
                  value={dailyInputDate}
                  onChange={(e) => setDailyInputDate(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  내용 <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={dailyInputContent}
                  onChange={(e) => setDailyInputContent(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg"
                  rows={4}
                  placeholder="오늘의 학습 내용, 특이사항 등을 입력하세요..."
                  required
                />
              </div>

              <div className="bg-blue-50 p-3 rounded-lg">
                <p className="text-sm text-blue-900">
                  💡 저장하면 GPT-4o-mini가 자동으로 주제를 파악하여 요약하고, Qwen3가 임베딩을 생성하여 RAG 검색이 가능합니다.
                </p>
              </div>

              <button
                type="submit"
                disabled={submittingInput || !dailyInputContent.trim()}
                className="w-full py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Save className="w-4 h-4" />
                <span>{submittingInput ? '저장 중...' : '일일 기록 저장'}</span>
              </button>
            </form>

            {/* 최근 입력 기록 목록 */}
            <div>
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                최근 입력 기록 ({dailyInputs.length}개)
              </h4>

              {dailyInputs.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>아직 입력된 기록이 없습니다.</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[500px] overflow-y-auto">
                  {dailyInputs.map((input) => (
                    <div key={input.input_id} className="p-4 bg-gray-50 border rounded-lg hover:bg-gray-100 transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">{input.date}</span>
                          <span className="px-2 py-0.5 text-xs bg-indigo-100 text-indigo-700 rounded">
                            {input.category}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">
                          {new Date(input.created_at).toLocaleString('ko-KR')}
                        </span>
                      </div>

                      {input.summary && (
                        <div className="mb-2 p-2 bg-blue-50 border-l-2 border-blue-500 rounded">
                          <p className="text-sm text-blue-900 font-medium">📝 요약: {input.summary}</p>
                        </div>
                      )}

                      <p className="text-gray-700 text-sm whitespace-pre-wrap">{input.content}</p>

                      <div className="mt-2 text-xs text-gray-500">
                        작성자: {input.teacher_id}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 출석 섹션 */}
      <div className="space-y-4 pb-6 border-b">
        <h4 className="text-lg font-bold flex items-center gap-2 text-green-600">
          <BookOpen className="w-5 h-5" />
          출석
        </h4>

        {/* 현재 저장된 출석 정보 (읽기 전용) */}
        {studentDetail && (
          <div className="p-3 bg-green-50 rounded-lg border border-green-200">
            <p className="text-xs font-semibold text-green-700 mb-2">현재 저장된 출석 정보</p>
            <div className="grid grid-cols-3 gap-2 text-sm text-green-800">
              <p><span className="font-medium">총 수업:</span> {studentDetail.attendance.total_sessions}회</p>
              <p><span className="font-medium">결석:</span> {studentDetail.attendance.absent}회</p>
              <p><span className="font-medium">지각:</span> {studentDetail.attendance.perception}회</p>
            </div>
            <p className="text-sm text-green-800 mt-2">
              <span className="font-medium">출석률:</span> {
                studentDetail.attendance.total_sessions > 0
                  ? Math.round(((studentDetail.attendance.total_sessions - studentDetail.attendance.absent) / studentDetail.attendance.total_sessions) * 100)
                  : 0
              }%
            </p>
          </div>
        )}

        <div>
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  총 수업 횟수
                </label>
                <input
                  type="number"
                  value={totalSessions}
                  onChange={(e) => setTotalSessions(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border rounded-lg"
                  min="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  결석 횟수
                </label>
                <input
                  type="number"
                  value={absent}
                  onChange={(e) => setAbsent(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border rounded-lg"
                  min="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  지각 횟수
                </label>
                <input
                  type="number"
                  value={perception}
                  onChange={(e) => setPerception(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border rounded-lg"
                  min="0"
                />
              </div>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg">
              <p className="text-sm font-medium text-blue-900">
                출석률: {attendanceRate}%
              </p>
            </div>
            <button
              onClick={() => handleSave('attendance')}
              disabled={saving}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? '저장 중...' : '출석 정보 저장'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 숙제 섹션 */}
      <div className="space-y-4 pb-6 border-b">
        <h4 className="text-lg font-bold flex items-center gap-2 text-blue-600">
          <FileText className="w-5 h-5" />
          숙제
        </h4>

        {/* 현재 저장된 숙제 정보 (읽기 전용) */}
        {studentDetail && (
          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-xs font-semibold text-blue-700 mb-2">현재 저장된 숙제 정보</p>
            <div className="grid grid-cols-2 gap-2 text-sm text-blue-800">
              <p><span className="font-medium">부여:</span> {studentDetail.homework.assigned}건</p>
              <p><span className="font-medium">미제출:</span> {studentDetail.homework.missed}건</p>
            </div>
            <p className="text-sm text-blue-800 mt-2">
              <span className="font-medium">완료율:</span> {
                studentDetail.homework.assigned > 0
                  ? Math.round(((studentDetail.homework.assigned - studentDetail.homework.missed) / studentDetail.homework.assigned) * 100)
                  : 0
              }%
            </p>
          </div>
        )}

        <div>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  부여된 숙제 수
                </label>
                <input
                  type="number"
                  value={assigned}
                  onChange={(e) => setAssigned(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border rounded-lg"
                  min="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  미제출 횟수
                </label>
                <input
                  type="number"
                  value={missed}
                  onChange={(e) => setMissed(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border rounded-lg"
                  min="0"
                />
              </div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <p className="text-sm font-medium text-green-900">
                숙제 완료율: {homeworkRate}%
              </p>
            </div>
            <button
              onClick={() => handleSave('homework')}
              disabled={saving}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? '저장 중...' : '숙제 정보 저장'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 특이사항 섹션 */}
      <div className="space-y-4 pb-6 border-b">
        <h4 className="text-lg font-bold flex items-center gap-2 text-orange-600">
          <AlertCircle className="w-5 h-5" />
          특이사항
        </h4>

        {/* 현재 저장된 특이사항 (읽기 전용) */}
        {studentDetail && (
          <div className="p-3 bg-orange-50 rounded-lg border border-orange-200">
            <p className="text-xs font-semibold text-orange-700 mb-2">현재 저장된 특이사항</p>
            <div className="space-y-1 text-sm text-orange-800">
              <p><span className="font-medium">수업 태도:</span> {studentDetail.notes.attitude || '-'}</p>
              <p><span className="font-medium">학교 시험:</span> {studentDetail.notes.school_exam_level || '-'}</p>
              <p><span className="font-medium">모의고사/수능:</span> {studentDetail.notes.csat_level || '-'}</p>
            </div>
          </div>
        )}

        <div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                수업 태도
              </label>
              <textarea
                value={attitude}
                onChange={(e) => setAttitude(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                rows={3}
                placeholder="예: 수업시간에 음식물 섭취함"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                학교 시험 수준
              </label>
              <input
                type="text"
                value={schoolExamLevel}
                onChange={(e) => setSchoolExamLevel(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="예: 초등 성취도 4수준, 내신 8등급 수준"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                모의고사/수능 수준
              </label>
              <input
                type="text"
                value={csatLevel}
                onChange={(e) => setCsatLevel(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="예: 기초학력진단 4수준, 모의수능 9등급 수준"
              />
            </div>
            <button
              onClick={() => handleSave('notes')}
              disabled={saving}
              className="px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? '저장 중...' : '특이사항 저장'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 영역별 점수 섹션 */}
      <div className="space-y-4 pb-6 border-b">
        <h4 className="text-lg font-bold flex items-center gap-2 text-purple-600">
          <BarChart3 className="w-5 h-5" />
          영역별 점수
        </h4>

        {/* 현재 저장된 점수 (읽기 전용) */}
        {studentDetail && (
          <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
            <p className="text-xs font-semibold text-purple-700 mb-2">현재 저장된 영역별 점수</p>
            <div className="grid grid-cols-3 gap-2 text-sm text-purple-800">
              <p><span className="font-medium">문법:</span> {studentDetail.assessment.radar_scores.grammar.toFixed(1)}</p>
              <p><span className="font-medium">어휘:</span> {studentDetail.assessment.radar_scores.vocabulary.toFixed(1)}</p>
              <p><span className="font-medium">독해:</span> {studentDetail.assessment.radar_scores.reading.toFixed(1)}</p>
              <p><span className="font-medium">듣기:</span> {studentDetail.assessment.radar_scores.listening.toFixed(1)}</p>
              <p><span className="font-medium">쓰기:</span> {studentDetail.assessment.radar_scores.writing.toFixed(1)}</p>
            </div>
          </div>
        )}

        <div>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Grammar (문법)
                </label>
                <input
                  type="number"
                  value={grammar}
                  onChange={(e) => setGrammar(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border rounded-lg"
                  min="0"
                  max="100"
                  step="0.1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Vocabulary (어휘)
                </label>
                <input
                  type="number"
                  value={vocabulary}
                  onChange={(e) => setVocabulary(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border rounded-lg"
                  min="0"
                  max="100"
                  step="0.1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reading (독해)
                </label>
                <input
                  type="number"
                  value={reading}
                  onChange={(e) => setReading(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border rounded-lg"
                  min="0"
                  max="100"
                  step="0.1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Listening (듣기)
                </label>
                <input
                  type="number"
                  value={listening}
                  onChange={(e) => setListening(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border rounded-lg"
                  min="0"
                  max="100"
                  step="0.1"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Writing (쓰기)
                </label>
                <input
                  type="number"
                  value={writing}
                  onChange={(e) => setWriting(parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border rounded-lg"
                  min="0"
                  max="100"
                  step="0.1"
                />
              </div>
            </div>
            <button
              onClick={() => handleSave('scores')}
              disabled={saving}
              className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? '저장 중...' : '영역별 점수 저장'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 전체 일괄 저장 버튼 */}
      <div className="pt-4 border-t">
        <button
          onClick={handleSaveAll}
          disabled={saving}
          className="w-full py-2.5 bg-gray-900 text-white font-semibold text-sm rounded-lg hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
        >
          <Save className="w-4 h-4" />
          <span>{saving ? '저장 중...' : '전체 일괄 저장'}</span>
        </button>
      </div>
    </div>
  );
};

export default StudentRecordEditor;
