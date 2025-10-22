/**
 * Teacher Main Page
 * 선생님 메인 페이지 - Daily Input 입력 & 파일 업로드
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, PlusCircle, Calendar, Send, BookOpen } from 'lucide-react';

export default function TeacherMain() {
  const navigate = useNavigate();
  const [activeFeature, setActiveFeature] = useState<'daily-input' | 'file-upload'>('daily-input');

  // Daily Input state
  const [studentName, setStudentName] = useState('');
  const [inputDate, setInputDate] = useState(new Date().toISOString().split('T')[0]);
  const [inputContent, setInputContent] = useState('');
  const [inputCategory, setInputCategory] = useState('vocabulary');

  // File Upload state
  const [examId, setExamId] = useState('');
  const [questionFile, setQuestionFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleDailyInputSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    alert('Daily Input이 저장되었습니다!');
    // TODO: API 연동
    setInputContent('');
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!examId || !questionFile) {
      alert('시험 ID와 파일을 선택해주세요.');
      return;
    }

    setUploading(true);
    // TODO: API 연동
    setTimeout(() => {
      alert('파일 업로드 및 파싱이 시작되었습니다!');
      setUploading(false);
      setExamId('');
      setQuestionFile(null);
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* 로고 - 메인 화면으로 이동 */}
            <div
              onClick={() => navigate('/')}
              className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
            >
              <BookOpen className="w-6 h-6 text-gray-900" />
              <span className="text-xl font-bold text-gray-900">ClassMate</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-12">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4 font-display tracking-tight">선생님 메인 페이지</h1>
          <p className="text-xl text-gray-600 font-medium">학생 관리와 교육 자료를 효율적으로 관리하세요</p>
        </div>

        {/* Feature Tabs */}
        <div className="flex justify-center gap-4 mb-12">
          <button
            onClick={() => setActiveFeature('daily-input')}
            className={`flex items-center gap-3 px-8 py-4 rounded-xl font-medium transition-all shadow-md ${
              activeFeature === 'daily-input'
                ? 'bg-indigo-600 text-white scale-105'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            <PlusCircle className="w-6 h-6" />
            <div className="text-left">
              <div className="font-bold">Daily Input 입력</div>
              <div className="text-xs opacity-80">학생별 일일 학습 내용 기록</div>
            </div>
          </button>

          <button
            onClick={() => setActiveFeature('file-upload')}
            className={`flex items-center gap-3 px-8 py-4 rounded-xl font-medium transition-all shadow-md ${
              activeFeature === 'file-upload'
                ? 'bg-indigo-600 text-white scale-105'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Upload className="w-6 h-6" />
            <div className="text-left">
              <div className="font-bold">파일 업로드</div>
              <div className="text-xs opacity-80">시험지 파싱 및 문제 생성</div>
            </div>
          </button>
        </div>

        {/* Daily Input Form */}
        {activeFeature === 'daily-input' && (
          <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-xl p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
                <Calendar className="w-6 h-6 text-indigo-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Daily Input 입력</h2>
                <p className="text-sm text-gray-600">학생의 일일 학습 내용을 기록하세요</p>
              </div>
            </div>

            <form onSubmit={handleDailyInputSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    학생 이름 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={studentName}
                    onChange={(e) => setStudentName(e.target.value)}
                    placeholder="홍길동"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    날짜 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    value={inputDate}
                    onChange={(e) => setInputDate(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  카테고리
                </label>
                <select
                  value={inputCategory}
                  onChange={(e) => setInputCategory(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  <option value="vocabulary">Vocabulary (어휘)</option>
                  <option value="grammar">Grammar (문법)</option>
                  <option value="speaking">Speaking (회화)</option>
                  <option value="writing">Writing (작문)</option>
                  <option value="reading">Reading (독해)</option>
                  <option value="listening">Listening (듣기)</option>
                  <option value="other">Other (기타)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  학습 내용 <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={inputContent}
                  onChange={(e) => setInputContent(e.target.value)}
                  placeholder="오늘 학생에게 제공한 학습 내용을 입력하세요...&#10;예: 현재완료 시제 개념 설명 및 연습 문제 10개 풀이"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg h-40 resize-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  required
                />
              </div>

              <button
                type="submit"
                className="w-full bg-indigo-600 text-white py-4 rounded-lg font-medium hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
              >
                <Send className="w-5 h-5" />
                Daily Input 저장
              </button>
            </form>
          </div>
        )}

        {/* File Upload Form */}
        {activeFeature === 'file-upload' && (
          <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-xl p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                <FileText className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">파일 업로드</h2>
                <p className="text-sm text-gray-600">시험지를 업로드하면 AI가 자동으로 문제를 파싱합니다</p>
              </div>
            </div>

            <form onSubmit={handleFileUpload} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  시험 ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={examId}
                  onChange={(e) => setExamId(e.target.value)}
                  placeholder="예: 2026_09_mock"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  required
                />
                <p className="mt-1 text-xs text-gray-500">시험을 식별할 수 있는 고유한 ID를 입력하세요</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  문제지 파일 (PDF/이미지) <span className="text-red-500">*</span>
                </label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-purple-500 transition-colors">
                  <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={(e) => setQuestionFile(e.target.files?.[0] || null)}
                    className="hidden"
                    id="file-upload"
                    required
                  />
                  <label
                    htmlFor="file-upload"
                    className="cursor-pointer text-purple-600 hover:text-purple-700 font-medium"
                  >
                    파일 선택
                  </label>
                  {questionFile && (
                    <p className="mt-2 text-sm text-gray-600">선택된 파일: {questionFile.name}</p>
                  )}
                  <p className="mt-2 text-xs text-gray-500">PDF, PNG, JPG 형식 지원</p>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="font-medium text-blue-900 mb-2">📚 처리 과정</h3>
                <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                  <li>OpenDataLoader로 PDF/이미지 읽기</li>
                  <li>VLM(Vision Language Model)으로 문제 파싱</li>
                  <li>문제, 그림, 표 자동 추출</li>
                  <li>구조화된 데이터로 저장</li>
                </ol>
              </div>

              <button
                type="submit"
                disabled={uploading}
                className="w-full bg-purple-600 text-white py-4 rounded-lg font-medium hover:bg-purple-700 transition-colors flex items-center justify-center gap-2 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    업로드 중...
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    파일 업로드 및 파싱 시작
                  </>
                )}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
