/**
 * Student Main Page
 * 학생 메인 페이지 - AI 학습 시작하기 & 상담하기
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Brain, MessageCircle, Play, Send, BookOpen, Target, Award } from 'lucide-react';

export default function StudentMain() {
  const navigate = useNavigate();
  const [activeFeature, setActiveFeature] = useState<'ai-learning' | 'consultation'>('ai-learning');

  // AI Learning state
  const [selectedTopic, setSelectedTopic] = useState('');
  const [difficulty, setDifficulty] = useState('medium');

  // Consultation state
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  const handleStartLearning = () => {
    if (!selectedTopic) {
      alert('학습할 주제를 선택해주세요!');
      return;
    }
    alert(`${selectedTopic} 학습을 시작합니다!`);
    // TODO: AI 학습 세션 시작 API 연동
  };

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
          content: '안녕하세요! 무엇을 도와드릴까요? 학습에 관한 질문이나 고민이 있으시면 언제든 말씀해주세요. 😊',
        },
      ]);
      setIsChatLoading(false);
    }, 1000);

    // TODO: 실제 AI 상담 API 연동
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-cyan-50">
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
          <h1 className="text-5xl font-bold text-gray-900 mb-4 font-display tracking-tight">학생 메인 페이지</h1>
          <p className="text-xl text-gray-600 font-medium">AI와 함께하는 맞춤형 학습 경험</p>
        </div>

        {/* Feature Tabs */}
        <div className="flex justify-center gap-4 mb-12">
          <button
            onClick={() => setActiveFeature('ai-learning')}
            className={`flex items-center gap-3 px-8 py-4 rounded-xl font-medium transition-all shadow-md ${
              activeFeature === 'ai-learning'
                ? 'bg-blue-600 text-white scale-105'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Brain className="w-6 h-6" />
            <div className="text-left">
              <div className="font-bold">AI 학습 시작하기</div>
              <div className="text-xs opacity-80">맞춤형 학습 문제 풀이</div>
            </div>
          </button>

          <button
            onClick={() => setActiveFeature('consultation')}
            className={`flex items-center gap-3 px-8 py-4 rounded-xl font-medium transition-all shadow-md ${
              activeFeature === 'consultation'
                ? 'bg-blue-600 text-white scale-105'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            <MessageCircle className="w-6 h-6" />
            <div className="text-left">
              <div className="font-bold">상담하기</div>
              <div className="text-xs opacity-80">AI 학습 상담 및 질문</div>
            </div>
          </button>
        </div>

        {/* AI Learning Section */}
        {activeFeature === 'ai-learning' && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-2xl shadow-xl p-8 mb-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                  <Brain className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">AI 학습 시작하기</h2>
                  <p className="text-sm text-gray-600">당신의 수준에 맞는 맞춤형 학습을 제공합니다</p>
                </div>
              </div>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    학습 주제 선택
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {[
                      { id: 'grammar', label: '문법', icon: '📚' },
                      { id: 'vocabulary', label: '어휘', icon: '📖' },
                      { id: 'reading', label: '독해', icon: '📰' },
                      { id: 'listening', label: '듣기', icon: '🎧' },
                      { id: 'writing', label: '작문', icon: '✍️' },
                      { id: 'speaking', label: '회화', icon: '💬' },
                    ].map((topic) => (
                      <button
                        key={topic.id}
                        onClick={() => setSelectedTopic(topic.label)}
                        className={`p-4 rounded-xl border-2 transition-all ${
                          selectedTopic === topic.label
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-blue-300'
                        }`}
                      >
                        <div className="text-3xl mb-2">{topic.icon}</div>
                        <div className="font-medium text-gray-900">{topic.label}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    난이도 선택
                  </label>
                  <div className="flex gap-3">
                    {[
                      { value: 'easy', label: '쉬움', color: 'green' },
                      { value: 'medium', label: '보통', color: 'blue' },
                      { value: 'hard', label: '어려움', color: 'red' },
                    ].map((level) => (
                      <button
                        key={level.value}
                        onClick={() => setDifficulty(level.value)}
                        className={`flex-1 py-3 rounded-lg border-2 font-medium transition-all ${
                          difficulty === level.value
                            ? `border-${level.color}-500 bg-${level.color}-50 text-${level.color}-700`
                            : 'border-gray-200 text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        {level.label}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  onClick={handleStartLearning}
                  className="w-full bg-blue-600 text-white py-4 rounded-lg font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
                >
                  <Play className="w-5 h-5" />
                  학습 시작하기
                </button>
              </div>
            </div>

            {/* Learning Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white rounded-xl shadow p-6 text-center">
                <BookOpen className="w-8 h-8 text-blue-600 mx-auto mb-2" />
                <div className="text-2xl font-bold text-gray-900">24</div>
                <div className="text-sm text-gray-600">오늘 학습</div>
              </div>
              <div className="bg-white rounded-xl shadow p-6 text-center">
                <Target className="w-8 h-8 text-green-600 mx-auto mb-2" />
                <div className="text-2xl font-bold text-gray-900">87%</div>
                <div className="text-sm text-gray-600">정답률</div>
              </div>
              <div className="bg-white rounded-xl shadow p-6 text-center">
                <Award className="w-8 h-8 text-orange-600 mx-auto mb-2" />
                <div className="text-2xl font-bold text-gray-900">15일</div>
                <div className="text-sm text-gray-600">연속 학습</div>
              </div>
            </div>
          </div>
        )}

        {/* Consultation Section */}
        {activeFeature === 'consultation' && (
          <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-xl overflow-hidden">
            {/* Chat Header */}
            <div className="bg-gradient-to-r from-blue-600 to-cyan-600 p-6 text-white">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                  <MessageCircle className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold">AI 학습 상담</h2>
                  <p className="text-sm opacity-90">궁금한 점을 자유롭게 물어보세요!</p>
                </div>
              </div>
            </div>

            {/* Chat Messages */}
            <div className="h-96 overflow-y-auto p-6 bg-gray-50 space-y-4">
              {chatMessages.length === 0 ? (
                <div className="text-center text-gray-500 py-12">
                  <MessageCircle className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                  <p className="text-lg font-medium text-gray-700 mb-2">안녕하세요! 👋</p>
                  <p className="text-sm">학습에 관한 질문이나 고민이 있으신가요?</p>
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
                          ? 'bg-blue-600 text-white'
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
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!chatInput.trim() || isChatLoading}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-md"
                >
                  <Send className="w-5 h-5" />
                  전송
                </button>
              </div>
              <p className="mt-2 text-xs text-gray-500">
                💡 예시: "현재완료 시제가 어려워요", "어휘력을 늘리고 싶어요"
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
