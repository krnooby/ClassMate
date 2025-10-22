/**
 * Parent Main Page
 * 학부모 메인 페이지 - 상담하기 & 맞춤학습
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MessageCircle, Send, Calendar, BookOpen, TrendingUp, Zap, Target } from 'lucide-react';

export default function ParentMain() {
  const navigate = useNavigate();
  const [activeFeature, setActiveFeature] = useState<'consultation' | 'custom-learning'>('consultation');

  // Consultation state
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [showOfflineBooking, setShowOfflineBooking] = useState(false);

  // Offline booking state
  const [bookingDate, setBookingDate] = useState('');
  const [bookingTime, setBookingTime] = useState('');
  const [bookingTopic, setBookingTopic] = useState('');

  // Custom learning state
  const [selectedLearningType, setSelectedLearningType] = useState<'general' | 'weakness' | 'advanced' | null>(null);
  const [selectedSubject, setSelectedSubject] = useState('');

  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;

    const userMessage = chatInput.trim();
    setChatInput('');

    // Add user message
    const newMessages = [...chatMessages, { role: 'user' as const, content: userMessage }];
    setChatMessages(newMessages);
    setIsChatLoading(true);

    // Simulate AI response
    setTimeout(() => {
      setChatMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: '안녕하세요, 학부모님! 자녀의 학습에 대해 궁금하신 점이 있으시면 언제든 말씀해주세요. 더 자세한 상담이 필요하시면 오프라인 상담을 예약하실 수도 있습니다. 😊',
        },
      ]);
      setIsChatLoading(false);
    }, 1000);

    // TODO: 실제 AI 상담 API 연동
  };

  const handleOfflineBooking = (e: React.FormEvent) => {
    e.preventDefault();
    alert(`오프라인 상담이 예약되었습니다!\n날짜: ${bookingDate}\n시간: ${bookingTime}\n주제: ${bookingTopic}`);
    setShowOfflineBooking(false);
    setBookingDate('');
    setBookingTime('');
    setBookingTopic('');
  };

  const handleStartCustomLearning = () => {
    if (!selectedLearningType || !selectedSubject) {
      alert('학습 유형과 과목을 선택해주세요!');
      return;
    }
    const typeLabels = {
      general: '일반학습',
      weakness: '취약부분 학습',
      advanced: '선행학습',
    };
    alert(`${typeLabels[selectedLearningType]} - ${selectedSubject} 학습을 시작합니다!`);
    // TODO: 맞춤학습 시작 API 연동
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50">
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
          <h1 className="text-5xl font-bold text-gray-900 mb-4 font-display tracking-tight">학부모 메인 페이지</h1>
          <p className="text-xl text-gray-600 font-medium">자녀의 학습을 효과적으로 관리하고 지원하세요</p>
        </div>

        {/* Feature Tabs */}
        <div className="flex justify-center gap-4 mb-12">
          <button
            onClick={() => setActiveFeature('consultation')}
            className={`flex items-center gap-3 px-8 py-4 rounded-xl font-medium transition-all shadow-md ${
              activeFeature === 'consultation'
                ? 'bg-purple-600 text-white scale-105'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            <MessageCircle className="w-6 h-6" />
            <div className="text-left">
              <div className="font-bold">상담하기</div>
              <div className="text-xs opacity-80">AI 상담 & 오프라인 예약</div>
            </div>
          </button>

          <button
            onClick={() => setActiveFeature('custom-learning')}
            className={`flex items-center gap-3 px-8 py-4 rounded-xl font-medium transition-all shadow-md ${
              activeFeature === 'custom-learning'
                ? 'bg-purple-600 text-white scale-105'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Target className="w-6 h-6" />
            <div className="text-left">
              <div className="font-bold">아이 맞춤학습</div>
              <div className="text-xs opacity-80">일반/취약/선행 학습</div>
            </div>
          </button>
        </div>

        {/* Consultation Section */}
        {activeFeature === 'consultation' && (
          <div className="max-w-4xl mx-auto">
            {!showOfflineBooking ? (
              <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
                {/* Chat Header */}
                <div className="bg-gradient-to-r from-purple-600 to-pink-600 p-6 text-white">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                        <MessageCircle className="w-6 h-6" />
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold">AI 학습 상담</h2>
                        <p className="text-sm opacity-90">자녀의 학습에 대해 궁금한 점을 물어보세요</p>
                      </div>
                    </div>
                    <button
                      onClick={() => setShowOfflineBooking(true)}
                      className="flex items-center gap-2 bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition-colors"
                    >
                      <Calendar className="w-4 h-4" />
                      <span className="text-sm font-medium">오프라인 상담 예약</span>
                    </button>
                  </div>
                </div>

                {/* Chat Messages */}
                <div className="h-96 overflow-y-auto p-6 bg-gray-50 space-y-4">
                  {chatMessages.length === 0 ? (
                    <div className="text-center text-gray-500 py-12">
                      <MessageCircle className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                      <p className="text-lg font-medium text-gray-700 mb-2">안녕하세요, 학부모님! 👋</p>
                      <p className="text-sm">자녀의 학습 상황에 대해 궁금하신 점이 있으신가요?</p>
                      <p className="text-sm">무엇이든 편하게 물어보세요!</p>
                    </div>
                  ) : (
                    chatMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[75%] rounded-2xl px-5 py-3 shadow-sm ${
                            msg.role === 'user'
                              ? 'bg-purple-600 text-white'
                              : 'bg-white text-gray-900 border border-gray-200'
                          }`}
                        >
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        </div>
                      </div>
                    ))
                  )}
                  {isChatLoading && (
                    <div className="flex justify-start">
                      <div className="bg-white border border-gray-200 rounded-2xl px-5 py-3 shadow-sm">
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
                <div className="p-6 bg-white border-t border-gray-200">
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
                      className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-md"
                    >
                      <Send className="w-5 h-5" />
                      전송
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    💡 예시: "아이의 어휘력을 향상시키고 싶어요", "문법 실력이 부족한 것 같아요"
                  </p>
                </div>
              </div>
            ) : (
              /* Offline Booking Form */
              <div className="bg-white rounded-2xl shadow-xl p-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                    <Calendar className="w-6 h-6 text-purple-600" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">오프라인 상담 예약</h2>
                    <p className="text-sm text-gray-600">선생님과 직접 만나 상담을 진행합니다</p>
                  </div>
                </div>

                <form onSubmit={handleOfflineBooking} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        상담 날짜 <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="date"
                        value={bookingDate}
                        onChange={(e) => setBookingDate(e.target.value)}
                        min={new Date().toISOString().split('T')[0]}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        상담 시간 <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={bookingTime}
                        onChange={(e) => setBookingTime(e.target.value)}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        required
                      >
                        <option value="">시간 선택</option>
                        <option value="09:00">오전 9:00</option>
                        <option value="10:00">오전 10:00</option>
                        <option value="11:00">오전 11:00</option>
                        <option value="14:00">오후 2:00</option>
                        <option value="15:00">오후 3:00</option>
                        <option value="16:00">오후 4:00</option>
                        <option value="17:00">오후 5:00</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      상담 주제 <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      value={bookingTopic}
                      onChange={(e) => setBookingTopic(e.target.value)}
                      placeholder="상담하고 싶은 주제를 입력해주세요..."
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg h-32 resize-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setShowOfflineBooking(false)}
                      className="flex-1 bg-gray-200 text-gray-700 py-3 rounded-lg font-medium hover:bg-gray-300 transition-colors"
                    >
                      취소
                    </button>
                    <button
                      type="submit"
                      className="flex-1 bg-purple-600 text-white py-3 rounded-lg font-medium hover:bg-purple-700 transition-colors shadow-lg"
                    >
                      예약하기
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        )}

        {/* Custom Learning Section */}
        {activeFeature === 'custom-learning' && (
          <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-xl p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 bg-pink-100 rounded-xl flex items-center justify-center">
                <Target className="w-6 h-6 text-pink-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">아이 맞춤학습 시키기</h2>
                <p className="text-sm text-gray-600">자녀에게 최적화된 학습 과정을 선택하세요</p>
              </div>
            </div>

            <div className="space-y-8">
              {/* Learning Type Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-4">
                  학습 유형 선택
                </label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <button
                    onClick={() => setSelectedLearningType('general')}
                    className={`p-6 rounded-xl border-2 transition-all text-left ${
                      selectedLearningType === 'general'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-blue-300'
                    }`}
                  >
                    <BookOpen className="w-10 h-10 text-blue-600 mb-3" />
                    <h3 className="font-bold text-gray-900 mb-2">일반학습</h3>
                    <p className="text-sm text-gray-600">정규 교과 과정에 맞춘 기본 학습</p>
                  </button>

                  <button
                    onClick={() => setSelectedLearningType('weakness')}
                    className={`p-6 rounded-xl border-2 transition-all text-left ${
                      selectedLearningType === 'weakness'
                        ? 'border-orange-500 bg-orange-50'
                        : 'border-gray-200 hover:border-orange-300'
                    }`}
                  >
                    <TrendingUp className="w-10 h-10 text-orange-600 mb-3" />
                    <h3 className="font-bold text-gray-900 mb-2">취약부분</h3>
                    <p className="text-sm text-gray-600">부족한 영역을 집중적으로 보완</p>
                  </button>

                  <button
                    onClick={() => setSelectedLearningType('advanced')}
                    className={`p-6 rounded-xl border-2 transition-all text-left ${
                      selectedLearningType === 'advanced'
                        ? 'border-purple-500 bg-purple-50'
                        : 'border-gray-200 hover:border-purple-300'
                    }`}
                  >
                    <Zap className="w-10 h-10 text-purple-600 mb-3" />
                    <h3 className="font-bold text-gray-900 mb-2">선행학습</h3>
                    <p className="text-sm text-gray-600">다음 단계 학습을 미리 준비</p>
                  </button>
                </div>
              </div>

              {/* Subject Selection */}
              {selectedLearningType && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-4">
                    과목 선택
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {['문법', '어휘', '독해', '듣기', '작문', '회화'].map((subject) => (
                      <button
                        key={subject}
                        onClick={() => setSelectedSubject(subject)}
                        className={`p-4 rounded-lg border-2 font-medium transition-all ${
                          selectedSubject === subject
                            ? 'border-pink-500 bg-pink-50 text-pink-700'
                            : 'border-gray-200 text-gray-700 hover:border-pink-300'
                        }`}
                      >
                        {subject}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Start Button */}
              {selectedLearningType && selectedSubject && (
                <button
                  onClick={handleStartCustomLearning}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-4 rounded-lg font-medium hover:from-purple-700 hover:to-pink-700 transition-all shadow-lg hover:shadow-xl"
                >
                  맞춤학습 시작하기
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
