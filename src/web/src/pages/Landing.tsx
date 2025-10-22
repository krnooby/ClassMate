/**
 * Landing Page Component
 * ClassMate 메인 랜딩 페이지
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Users, Target, MessageSquare, Bell, Settings, User, Activity, Clock, Award, TrendingUp } from 'lucide-react';

export default function Landing() {
  const navigate = useNavigate();
  const [showLoginAlert, setShowLoginAlert] = useState(false);

  // 로그인 상태 확인
  const checkLoginAndNavigate = (targetPath: string) => {
    // localStorage에서 로그인 정보 확인
    const studentId = localStorage.getItem('studentId');
    const parentId = localStorage.getItem('parentId');
    const teacherId = localStorage.getItem('teacherId');

    // 로그인되어 있으면 해당 페이지로 이동
    if (studentId || parentId || teacherId) {
      navigate(targetPath);
    } else {
      // 로그인 안 되어 있으면 경고 표시
      setShowLoginAlert(true);
      setTimeout(() => {
        setShowLoginAlert(false);
        // 로그인 페이지로 이동 (원래 가려던 페이지 정보 포함)
        navigate(`/login?redirect=${encodeURIComponent(targetPath)}`);
      }, 2000); // 2초 후 로그인 페이지로 이동
    }
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Top Navigation Bar */}
      <nav className="fixed top-0 left-0 right-0 bg-white border-b border-gray-200 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div onClick={() => navigate('/')} className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity">
              <BookOpen className="w-6 h-6 text-gray-900" />
              <span className="text-xl font-bold text-gray-900">ClassMate</span>
            </div>

            {/* Right Menu */}
            <div className="flex items-center gap-3">
              {/* 학습 대시보드 버튼 */}
              <button
                onClick={() => checkLoginAndNavigate('/student-dashboard')}
                className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Activity className="w-4 h-4" />
                <span className="font-medium">학습 대시보드</span>
              </button>

              {/* 로그인 버튼 */}
              <button
                onClick={() => navigate('/login')}
                className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
              >
                로그인
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 로그인 필요 경고 모달 */}
      {showLoginAlert && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md mx-4 animate-bounce">
            <div className="text-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-2">로그인이 필요합니다!</h3>
              <p className="text-gray-600 mb-4">AI 학습을 시작하려면 먼저 로그인해주세요.</p>
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span>로그인 페이지로 이동 중...</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Hero Section */}
      <section className="pt-28 pb-12 px-4">
        <div className="max-w-4xl mx-auto text-center">
          {/* Logo */}
          <div className="mb-1">
            <img
              src="/classmate-logo.png"
              alt="ClassMate"
              className="mx-auto h-56 object-contain"
            />
          </div>

          {/* Description */}
          <p className="text-gray-600 text-xl mb-8 max-w-2xl mx-auto font-medium">
            AI가 분석하는 나만의 학습 패턴, 데이터로 완성하는 맞춤 교육
          </p>

          {/* Action Buttons */}
          <div className="flex flex-wrap justify-center gap-4 mb-12">
            <button
              onClick={() => checkLoginAndNavigate('/student-dashboard')}
              className="flex items-center gap-2 bg-black text-white px-6 py-3 rounded-lg hover:bg-gray-800 transition-colors shadow-md cursor-pointer"
            >
              <Activity className="w-5 h-5" />
              <span className="font-medium">AI 학습 시작하기</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 18l6-6-6-6"/>
              </svg>
            </button>

            <button
              onClick={() => checkLoginAndNavigate('/student-dashboard')}
              className="flex items-center gap-2 bg-gray-100 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer"
            >
              <Users className="w-5 h-5" />
              <span className="font-medium">성적표 페이지</span>
            </button>

            <button
              onClick={() => checkLoginAndNavigate('/student-dashboard')}
              className="flex items-center gap-2 bg-gray-100 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer"
            >
              <Target className="w-5 h-5" />
              <span className="font-medium">맞춤형 페이지</span>
            </button>

            <button
              onClick={() => checkLoginAndNavigate('/student-dashboard')}
              className="flex items-center gap-2 bg-gray-100 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer"
            >
              <MessageSquare className="w-5 h-5" />
              <span className="font-medium">설명하기</span>
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
