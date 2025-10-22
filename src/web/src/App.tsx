/**
 * Main App Component
 * 라우팅 및 전역 상태 관리
 */
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BarChart3, Users, FileText, Bell, Settings, User, BookOpen, RotateCcw, Filter } from 'lucide-react';

import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Students from './pages/Students';
import Problems from './pages/Problems';
import StudentDashboard from './pages/StudentDashboard';
import ParentDashboard from './pages/ParentDashboard';
import TeacherDashboard from './pages/TeacherDashboard';
import TeacherMain from './pages/TeacherMain';
import StudentMain from './pages/StudentMain';
import ParentMain from './pages/ParentMain';
import UnifiedLogin from './pages/UnifiedLogin';
import Logo from './components/Logo';

// React Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Login page */}
          <Route path="/login" element={<UnifiedLogin />} />

          {/* Full-screen pages with their own headers */}
          <Route path="/student-dashboard" element={<StudentDashboard />} />
          <Route path="/parent-dashboard" element={<ParentDashboard />} />
          <Route path="/teacher-dashboard" element={<TeacherDashboard />} />
          <Route path="/teacher-main" element={<TeacherMain />} />
          <Route path="/student-main" element={<StudentMain />} />
          <Route path="/parent-main" element={<ParentMain />} />

          {/* Pages with shared navigation */}
          <Route path="*" element={
            <div className="min-h-screen bg-white">
              {/* Navigation - Only for admin/teacher pages */}
              <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4">
                  <div className="flex items-center justify-between h-28">
                    {/* Logo */}
                    <Link to="/" className="cursor-pointer">
                      <Logo variant="simple" />
                    </Link>

                    {/* Center Menu */}
                    <div className="flex gap-8">
                      <Link
                        to="/"
                        className="text-gray-700 hover:text-gray-900 transition-colors cursor-pointer"
                      >
                        대시보드
                      </Link>
                      <Link
                        to="/problems"
                        className="text-gray-700 hover:text-gray-900 transition-colors cursor-pointer"
                      >
                        문제 생성
                      </Link>
                      <Link
                        to="/students"
                        className="text-gray-700 hover:text-gray-900 transition-colors cursor-pointer"
                      >
                        복습
                      </Link>
                      <Link
                        to="/dashboard"
                        className="text-gray-700 hover:text-gray-900 transition-colors cursor-pointer"
                      >
                        조건
                      </Link>
                    </div>

                    {/* Right Menu Icons */}
                    <div className="flex items-center gap-4">
                      <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                        <Bell className="w-5 h-5 text-gray-700" />
                      </button>
                      <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                        <Settings className="w-5 h-5 text-gray-700" />
                      </button>
                      <Link
                        to="/login"
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium cursor-pointer"
                      >
                        로그인
                      </Link>
                    </div>
                  </div>
                </div>
              </nav>

              {/* Nested Routes */}
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/students" element={<Students />} />
                <Route path="/problems" element={<Problems />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          } />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
