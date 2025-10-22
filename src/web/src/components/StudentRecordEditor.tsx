import React, { useState, useEffect } from 'react';
import { Save, User, BookOpen, FileText, BarChart3, AlertCircle } from 'lucide-react';

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

interface StudentRecordEditorProps {
  student: Student;
  onSaved: () => void;
}

const StudentRecordEditor: React.FC<StudentRecordEditorProps> = ({ student, onSaved }) => {
  const [activeSection, setActiveSection] = useState<'attendance' | 'homework' | 'notes' | 'scores'>('attendance');
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

  // 학생 상세 정보 불러오기
  useEffect(() => {
    if (student) {
      fetchStudentDetail();
    }
  }, [student]);

  const fetchStudentDetail = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/teachers/student-detail/${student.student_id}`);
      const data = await response.json();

      if (data.success) {
        const detail = data.student;
        setStudentDetail(detail);

        // 상태 업데이트
        setTotalSessions(detail.attendance.total_sessions);
        setAbsent(detail.attendance.absent);
        setPerception(detail.attendance.perception);

        setAssigned(detail.homework.assigned);
        setMissed(detail.homework.missed);

        setAttitude(detail.notes.attitude || '');
        setSchoolExamLevel(detail.notes.school_exam_level || '');
        setCsatLevel(detail.notes.csat_level || '');

        setGrammar(detail.assessment.radar_scores.grammar);
        setVocabulary(detail.assessment.radar_scores.vocabulary);
        setReading(detail.assessment.radar_scores.reading);
        setListening(detail.assessment.radar_scores.listening);
        setWriting(detail.assessment.radar_scores.writing);
      }
    } catch (error) {
      console.error('Failed to fetch student detail:', error);
      alert('학생 정보를 불러오는데 실패했습니다: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);

    try {
      const updateData: any = {};

      // 섹션별로 변경된 데이터만 전송
      if (activeSection === 'attendance') {
        updateData.attendance = { total_sessions: totalSessions, absent, perception };
      } else if (activeSection === 'homework') {
        updateData.homework = { assigned, missed };
      } else if (activeSection === 'notes') {
        updateData.notes = { attitude, school_exam_level: schoolExamLevel, csat_level: csatLevel };
      } else if (activeSection === 'scores') {
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
    <div className="space-y-4">
      {/* 학생 정보 헤더 */}
      <div className="flex items-center gap-3 pb-4 border-b">
        <User className="w-6 h-6 text-indigo-600" />
        <div>
          <h3 className="text-lg font-semibold">{student.name}</h3>
          <p className="text-sm text-gray-500">
            {student.grade_label} · CEFR {student.cefr}
          </p>
        </div>
      </div>

      {/* 섹션 탭 */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveSection('attendance')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeSection === 'attendance'
              ? 'text-indigo-600 border-b-2 border-indigo-600'
              : 'text-gray-600 hover:text-indigo-600'
          }`}
        >
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            <span>출석</span>
          </div>
        </button>
        <button
          onClick={() => setActiveSection('homework')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeSection === 'homework'
              ? 'text-indigo-600 border-b-2 border-indigo-600'
              : 'text-gray-600 hover:text-indigo-600'
          }`}
        >
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            <span>숙제</span>
          </div>
        </button>
        <button
          onClick={() => setActiveSection('notes')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeSection === 'notes'
              ? 'text-indigo-600 border-b-2 border-indigo-600'
              : 'text-gray-600 hover:text-indigo-600'
          }`}
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>특이사항</span>
          </div>
        </button>
        <button
          onClick={() => setActiveSection('scores')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeSection === 'scores'
              ? 'text-indigo-600 border-b-2 border-indigo-600'
              : 'text-gray-600 hover:text-indigo-600'
          }`}
        >
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            <span>영역별 점수</span>
          </div>
        </button>
      </div>

      {/* 섹션 내용 */}
      <div className="py-4">
        {activeSection === 'attendance' && (
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
          </div>
        )}

        {activeSection === 'homework' && (
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
          </div>
        )}

        {activeSection === 'notes' && (
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
          </div>
        )}

        {activeSection === 'scores' && (
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
          </div>
        )}
      </div>

      {/* 저장 버튼 */}
      <div className="flex justify-end pt-4 border-t">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Save className="w-4 h-4" />
          <span>{saving ? '저장 중...' : '저장'}</span>
        </button>
      </div>
    </div>
  );
};

export default StudentRecordEditor;
