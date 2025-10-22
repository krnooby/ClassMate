/**
 * Problems Page
 * 문제 검색 및 목록
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { problemsApi } from '../api/services';
import { Search, FileText, Image as ImageIcon, Table, BookOpen } from 'lucide-react';

export default function Problems() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [limit] = useState(20);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [filters, setFilters] = useState({
    area: '',
    difficulty: '',
    cefr: '',
  });

  // List query
  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ['problems', 'list', page, limit, filters],
    queryFn: () => problemsApi.getList({
      skip: page * limit,
      limit,
      area: filters.area || undefined,
      difficulty: filters.difficulty ? Number(filters.difficulty) : undefined,
      cefr: filters.cefr || undefined,
    }),
    enabled: !isSearching,
  });

  // Search query
  const { data: searchData, isLoading: searchLoading, refetch: searchRefetch } = useQuery({
    queryKey: ['problems', 'search', searchQuery],
    queryFn: () => problemsApi.search({ query: searchQuery, limit: 10 }),
    enabled: false,
  });

  const handleSearch = async () => {
    if (searchQuery.trim()) {
      setIsSearching(true);
      await searchRefetch();
    } else {
      setIsSearching(false);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setIsSearching(false);
  };

  const problems = isSearching
    ? searchData?.results.map(r => ({ ...r.problem, _score: r.score })) || []
    : listData?.problems || [];

  const isLoading = isSearching ? searchLoading : listLoading;

  return (
    <div className="min-h-screen bg-gray-50">
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

      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">문제 검색</h1>

      {/* Search Bar */}
      <div className="mb-6 bg-white rounded-lg shadow p-4">
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="문제 검색 (키워드, 내용 등)..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSearch}
            disabled={!searchQuery.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed cursor-pointer flex items-center gap-2"
          >
            <Search className="w-5 h-5" />
            검색
          </button>
          {isSearching && (
            <button
              onClick={handleClearSearch}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 cursor-pointer"
            >
              초기화
            </button>
          )}
        </div>

        {/* Filters */}
        {!isSearching && (
          <div className="flex gap-2 flex-wrap">
            <select
              value={filters.area}
              onChange={(e) => setFilters({ ...filters, area: e.target.value })}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">전체 영역</option>
              <option value="LS">듣기 (LS)</option>
              <option value="RC">독해 (RC)</option>
            </select>
            <select
              value={filters.difficulty}
              onChange={(e) => setFilters({ ...filters, difficulty: e.target.value })}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">전체 난이도</option>
              <option value="1">Level 1</option>
              <option value="2">Level 2</option>
              <option value="3">Level 3</option>
              <option value="4">Level 4</option>
              <option value="5">Level 5</option>
            </select>
            <select
              value={filters.cefr}
              onChange={(e) => setFilters({ ...filters, cefr: e.target.value })}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">전체 CEFR</option>
              <option value="A1">A1</option>
              <option value="A2">A2</option>
              <option value="B1">B1</option>
              <option value="B2">B2</option>
              <option value="C1">C1</option>
              <option value="C2">C2</option>
            </select>
          </div>
        )}

        {isSearching && (
          <div className="mt-2 text-sm text-gray-600">
            검색 결과: "{searchQuery}" ({problems.length}개)
          </div>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-12 gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <div className="text-lg text-gray-600">문제 데이터를 불러오는 중...</div>
        </div>
      )}

      {/* Problems List */}
      {!isLoading && problems.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          문제가 없습니다.
        </div>
      )}

      {!isLoading && problems.length > 0 && (
        <>
          <div className="space-y-4 mb-6">
            {problems.map((problem: any) => (
              <div key={problem.problem_id} className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-blue-500" />
                    <span className="font-bold text-lg">
                      #{problem.item_no || '?'} {problem.problem_id}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {problem.area && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                        {problem.area}
                      </span>
                    )}
                    {problem.difficulty && (
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
                        Level {problem.difficulty}
                      </span>
                    )}
                    {problem.cefr && (
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">
                        {problem.cefr}
                      </span>
                    )}
                  </div>
                </div>

                {/* Stem */}
                {problem.stem && (
                  <div className="mb-3">
                    <p className="text-gray-800 leading-relaxed">{problem.stem}</p>
                  </div>
                )}

                {/* Options */}
                {problem.options && problem.options.length > 0 && (
                  <div className="mb-3 space-y-1">
                    {problem.options.map((option: string, idx: number) => (
                      <div
                        key={idx}
                        className={`px-3 py-2 rounded ${
                          problem.answer === String(idx + 1)
                            ? 'bg-green-50 border border-green-300'
                            : 'bg-gray-50'
                        }`}
                      >
                        <span className="font-medium">{idx + 1}.</span> {option}
                        {problem.answer === String(idx + 1) && (
                          <span className="ml-2 text-green-600 font-bold">✓ 정답</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Assets */}
                <div className="flex gap-4 text-sm text-gray-600">
                  {problem.figures && problem.figures.length > 0 && (
                    <div className="flex items-center gap-1">
                      <ImageIcon className="w-4 h-4" />
                      <span>이미지 {problem.figures.length}개</span>
                    </div>
                  )}
                  {problem.tables && problem.tables.length > 0 && (
                    <div className="flex items-center gap-1">
                      <Table className="w-4 h-4" />
                      <span>표 {problem.tables.length}개</span>
                    </div>
                  )}
                  {problem._score && (
                    <div className="ml-auto text-blue-600">
                      유사도: {problem._score.toFixed(4)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {!isSearching && listData && (
            <div className="flex justify-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                이전
              </button>
              <div className="px-4 py-2 bg-gray-100 rounded-lg">
                {page + 1} / {Math.ceil(listData.total / limit)}
              </div>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={(page + 1) * limit >= listData.total}
                className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                다음
              </button>
            </div>
          )}
        </>
      )}
      </div>
    </div>
  );
}
