/**
 * Dashboard Page
 * 전체 통계 대시보드
 */
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../api/services';
import { BarChart3, Users, FileText, Image, Table, BookOpen, GraduationCap } from 'lucide-react';
import Logo from '../components/Logo';

export default function Dashboard() {
  const { data: overview, isLoading, error } = useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: () => dashboardApi.getOverview(),
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <div className="text-lg text-gray-600">데이터를 불러오는 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="text-red-500 text-lg">⚠️ 데이터를 불러올 수 없습니다</div>
        <div className="text-gray-600 text-sm">{(error as Error).message}</div>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors cursor-pointer"
        >
          다시 시도
        </button>
      </div>
    );
  }

  if (!overview) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Hero Section */}
      <div className="bg-white border-b-4 border-blue-500 shadow-md py-8">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-8">
              <Logo variant="full" />
              <div className="border-l-2 border-gray-300 pl-8">
                <h1 className="text-4xl font-bold text-gray-800 mb-2">관리자 대시보드</h1>
                <p className="text-gray-600 text-lg">학습 데이터 및 통계를 한눈에 확인하세요</p>
              </div>
            </div>
            <div className="hidden lg:block">
              <GraduationCap className="w-24 h-24 text-blue-400 opacity-40" />
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          <div className="bg-white rounded-2xl shadow-xl p-7 border-t-4 border-blue-500 hover:shadow-2xl hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">총 문제</p>
                <p className="text-4xl font-extrabold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
                  {overview.problems.total}
                </p>
                <p className="text-xs text-gray-400 mt-2">등록된 문제 수</p>
              </div>
              <div className="bg-gradient-to-br from-blue-400 to-blue-600 rounded-2xl p-4 shadow-lg">
                <FileText className="w-9 h-9 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-7 border-t-4 border-green-500 hover:shadow-2xl hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">총 학생</p>
                <p className="text-4xl font-extrabold bg-gradient-to-r from-green-600 to-emerald-500 bg-clip-text text-transparent">
                  {overview.students.total}
                </p>
                <p className="text-xs text-gray-400 mt-2">등록된 학생 수</p>
              </div>
              <div className="bg-gradient-to-br from-green-400 to-green-600 rounded-2xl p-4 shadow-lg">
                <Users className="w-9 h-9 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-7 border-t-4 border-purple-500 hover:shadow-2xl hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">테이블</p>
                <p className="text-4xl font-extrabold bg-gradient-to-r from-purple-600 to-pink-500 bg-clip-text text-transparent">
                  {overview.problems.tables}
                </p>
                <p className="text-xs text-gray-400 mt-2">문제 내 표 개수</p>
              </div>
              <div className="bg-gradient-to-br from-purple-400 to-purple-600 rounded-2xl p-4 shadow-lg">
                <Table className="w-9 h-9 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-7 border-t-4 border-orange-500 hover:shadow-2xl hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">이미지</p>
                <p className="text-4xl font-extrabold bg-gradient-to-r from-orange-600 to-red-500 bg-clip-text text-transparent">
                  {overview.problems.figures}
                </p>
                <p className="text-xs text-gray-400 mt-2">문제 내 그림 개수</p>
              </div>
              <div className="bg-gradient-to-br from-orange-400 to-orange-600 rounded-2xl p-4 shadow-lg">
                <Image className="w-9 h-9 text-white" />
              </div>
            </div>
          </div>
        </div>

        {/* Distribution Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Area Distribution */}
          <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2 text-gray-800 border-b pb-3">
              <BarChart3 className="w-6 h-6 text-blue-600" />
              영역별 문제 분포
            </h2>
            <div className="space-y-4">
              {overview.problems.area_distribution.map((item) => (
                <div key={item.area} className="flex items-center gap-3">
                  <div className="w-28 font-semibold text-gray-700">{item.area}</div>
                  <div className="flex-1 bg-gray-100 rounded-full h-8 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-blue-600 h-8 rounded-full flex items-center justify-end pr-3 text-white text-sm font-medium transition-all duration-500 hover:from-blue-600 hover:to-blue-700"
                      style={{
                        width: `${Math.max((item.count / overview.problems.total) * 100, 5)}%`,
                      }}
                    >
                      {item.count}
                    </div>
                  </div>
                  <div className="w-12 text-right text-sm text-gray-600">
                    {Math.round((item.count / overview.problems.total) * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Difficulty Distribution */}
          <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2 text-gray-800 border-b pb-3">
              <BarChart3 className="w-6 h-6 text-green-600" />
              난이도별 문제 분포
            </h2>
            <div className="space-y-4">
              {overview.problems.difficulty_distribution.map((item) => (
                <div key={item.difficulty} className="flex items-center gap-3">
                  <div className="w-28 font-semibold text-gray-700">Level {item.difficulty}</div>
                  <div className="flex-1 bg-gray-100 rounded-full h-8 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-green-500 to-green-600 h-8 rounded-full flex items-center justify-end pr-3 text-white text-sm font-medium transition-all duration-500 hover:from-green-600 hover:to-green-700"
                      style={{
                        width: `${Math.max((item.count / overview.problems.total) * 100, 5)}%`,
                      }}
                    >
                      {item.count}
                    </div>
                  </div>
                  <div className="w-12 text-right text-sm text-gray-600">
                    {Math.round((item.count / overview.problems.total) * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* CEFR Distribution */}
          <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2 text-gray-800 border-b pb-3">
              <Users className="w-6 h-6 text-purple-600" />
              학생 CEFR 레벨 분포
            </h2>
            <div className="space-y-4">
              {overview.students.cefr_distribution.map((item) => (
                <div key={item.cefr} className="flex items-center gap-3">
                  <div className="w-28 font-semibold text-gray-700">{item.cefr}</div>
                  <div className="flex-1 bg-gray-100 rounded-full h-8 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-purple-600 h-8 rounded-full flex items-center justify-end pr-3 text-white text-sm font-medium transition-all duration-500 hover:from-purple-600 hover:to-purple-700"
                      style={{
                        width: `${Math.max((item.count / overview.students.total) * 100, 5)}%`,
                      }}
                    >
                      {item.count}
                    </div>
                  </div>
                  <div className="w-12 text-right text-sm text-gray-600">
                    {Math.round((item.count / overview.students.total) * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
