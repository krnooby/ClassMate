/**
 * Students Page
 * 학생 목록 및 검색
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { studentsApi } from '../api/services';
import { Search, User } from 'lucide-react';

export default function Students() {
  const [page, setPage] = useState(0);
  const [limit] = useState(20);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  // List query
  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ['students', 'list', page, limit],
    queryFn: () => studentsApi.getList({ skip: page * limit, limit }),
    enabled: !isSearching,
  });

  // Search query
  const { data: searchData, isLoading: searchLoading, refetch: searchRefetch } = useQuery({
    queryKey: ['students', 'search', searchQuery],
    queryFn: () => studentsApi.search({ query: searchQuery, limit: 10 }),
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

  const students = isSearching
    ? searchData?.results.map(r => ({ ...r.student, _score: r.score })) || []
    : listData?.students || [];

  const isLoading = isSearching ? searchLoading : listLoading;

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">학생 관리</h1>

      {/* Search Bar */}
      <div className="mb-6 bg-white rounded-lg shadow p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="학생 검색 (이름, 레벨 등)..."
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

        {isSearching && (
          <div className="mt-2 text-sm text-gray-600">
            검색 결과: "{searchQuery}" ({students.length}명)
          </div>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-12 gap-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <div className="text-lg text-gray-600">학생 데이터를 불러오는 중...</div>
        </div>
      )}

      {/* Students List */}
      {!isLoading && students.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          학생이 없습니다.
        </div>
      )}

      {!isLoading && students.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {students.map((student: any) => (
              <div key={student.student_id} className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-start gap-3">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <User className="w-6 h-6 text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-lg truncate">{student.name}</h3>
                    <p className="text-sm text-gray-600">{student.student_id}</p>

                    <div className="mt-3 space-y-1">
                      {student.grade_label && (
                        <div className="text-sm">
                          <span className="text-gray-600">학년:</span>{' '}
                          <span className="font-medium">{student.grade_label}</span>
                        </div>
                      )}
                      {student.cefr && (
                        <div className="text-sm">
                          <span className="text-gray-600">CEFR:</span>{' '}
                          <span className="font-medium">{student.cefr}</span>
                        </div>
                      )}
                      {student.percentile_rank !== undefined && (
                        <div className="text-sm">
                          <span className="text-gray-600">백분위:</span>{' '}
                          <span className="font-medium">{student.percentile_rank}%</span>
                        </div>
                      )}
                      {student.attendance_rate !== undefined && (
                        <div className="text-sm">
                          <span className="text-gray-600">출석률:</span>{' '}
                          <span className="font-medium">{(student.attendance_rate * 100).toFixed(1)}%</span>
                        </div>
                      )}
                      {student._score && (
                        <div className="text-sm text-blue-600">
                          유사도: {student._score.toFixed(4)}
                        </div>
                      )}
                    </div>

                    {student.summary && (
                      <p className="mt-2 text-sm text-gray-600 line-clamp-2">
                        {student.summary}
                      </p>
                    )}
                  </div>
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
  );
}
