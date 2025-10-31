/**
 * Parent Dashboard Page
 * 학부모용 대시보드 - 로그인 후 자녀 학습 현황 확인 및 AI 상담
 */
import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/services';
import {
  BookOpen,
  Bell,
  Settings,
  UserCircle2,
  MessageCircle,
  Send,
  BarChart3,
  TrendingUp,
  Calendar,
  Award,
  PlusCircle,
  Trash2,
  Menu,
  X,
  Volume2,
  VolumeX,
  ChevronDown,
  ChevronUp,
  Square,
} from 'lucide-react';

// Quick Reply interface
interface QuickReply {
  label: string;
  value: string;
}

// Chat session interface
interface ChatSession {
  id: string;
  title: string;
  messages: Array<{ role: 'user' | 'assistant'; content: string; quick_replies?: QuickReply[] }>;
  timestamp: number;
}

// Message Content Renderer - supports audio playback with TTS for listening problems
function MessageContent({ content }: { content: string }) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);

  // Parse speaker information from [SPEAKERS]: line
  const parseSpeakers = (text: string): Array<{ name: string; gender: string; voice?: string }> | null => {
    const speakersMatch = text.match(/\[SPEAKERS\]:\s*(.+?)(?:\n|$)/);
    if (speakersMatch) {
      try {
        const jsonStr = speakersMatch[1].trim();
        const data = JSON.parse(jsonStr);
        return data.speakers || null;
      } catch (e) {
        console.error('Failed to parse speakers JSON:', e);
        return null;
      }
    }
    return null;
  };

  // TTS handler with speaker support
  const handleTTS = (text: string) => {
    if (!('speechSynthesis' in window)) {
      alert('TTS는 이 브라우저에서 지원되지 않습니다.');
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    // Ensure voices are loaded
    let voices = window.speechSynthesis.getVoices();
    if (voices.length === 0) {
      window.speechSynthesis.onvoiceschanged = () => {
        handleTTS(text);
      };
      return;
    }

    // Check if this is a dialogue with speakers
    let speakers = parseSpeakers(text);

    // If no [SPEAKERS] found, try to infer from dialogue
    if (!speakers) {
      const dialoguePattern = /^(Girl|Boy|Woman|Man|Emma|John|Sarah|Michael|Minho):\s/gm;
      const matches = text.match(dialoguePattern);

      if (matches && matches.length > 0) {
        const uniqueSpeakers = new Set<string>();
        matches.forEach(match => {
          const name = match.replace(':', '').trim();
          uniqueSpeakers.add(name);
        });

        speakers = Array.from(uniqueSpeakers).map(name => {
          const lowerName = name.toLowerCase();
          const isFemale = lowerName.includes('girl') || lowerName.includes('woman') ||
                          lowerName === 'emma' || lowerName === 'sarah';
          return {
            name,
            gender: isFemale ? 'female' : 'male',
            voice: isFemale ? 'Samantha' : 'David'
          };
        });
      }
    }

    if (speakers) {
      handleDialogueTTS(text, speakers);
    } else {
      // Simple TTS for non-dialogue
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-US';
      utterance.rate = 0.9;
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
      setIsSpeaking(true);
    }
  };

  // Handle dialogue TTS with speaker separation
  const handleDialogueTTS = (text: string, speakers: Array<{ name: string; gender: string; voice?: string }>) => {
    const allVoices = window.speechSynthesis.getVoices();

    // Remove [SPEAKERS]: line and extract dialogue
    const cleanText = text.replace(/\[SPEAKERS\]:.*\n/, '').trim();

    // Split by speaker labels
    const speakerPattern = new RegExp(`(${speakers.map(s => s.name).join('|')}):\\s*`, 'g');
    const parts = cleanText.split(speakerPattern).filter(p => p.trim());

    // Group into [speaker, text] pairs
    const dialogue: Array<{ speaker: string; text: string; gender: string; voice?: string }> = [];
    for (let i = 0; i < parts.length; i += 2) {
      if (i + 1 < parts.length) {
        const speakerName = parts[i];
        const speakerText = parts[i + 1].trim();
        const speakerInfo = speakers.find(s => s.name === speakerName);
        if (speakerInfo && speakerText) {
          dialogue.push({
            speaker: speakerName,
            text: speakerText,
            gender: speakerInfo.gender,
            voice: speakerInfo.voice
          });
        }
      }
    }

    if (dialogue.length === 0) {
      setIsSpeaking(false);
      return;
    }

    // Play dialogue sequentially
    let currentIndex = 0;
    setIsSpeaking(true);

    const playNext = () => {
      if (currentIndex >= dialogue.length) {
        setIsSpeaking(false);
        return;
      }

      const line = dialogue[currentIndex];
      const utterance = new SpeechSynthesisUtterance(line.text);
      utterance.lang = 'en-US';
      utterance.rate = 0.9;

      // Select voice based on gender
      const voices = window.speechSynthesis.getVoices();
      const usVoices = voices.filter(v => v.lang === 'en-US' || v.lang === 'en_US');

      let targetVoice = null;

      // Priority 1: Try LLM-specified voice
      if (line.voice) {
        targetVoice = usVoices.find(v =>
          v.name.toLowerCase().includes(line.voice!.toLowerCase())
        );
      }

      // Priority 2: Try to find gender-specific voices
      if (!targetVoice) {
        if (line.gender === 'female') {
          targetVoice = usVoices.find(v =>
            v.name.toLowerCase().includes('female') ||
            v.name.toLowerCase().includes('samantha') ||
            v.name.toLowerCase().includes('karen') ||
            v.name.toLowerCase().includes('victoria')
          );
        } else {
          targetVoice = usVoices.find(v =>
            v.name.toLowerCase().includes('male') ||
            v.name.toLowerCase().includes('david') ||
            v.name.toLowerCase().includes('daniel') ||
            v.name.toLowerCase().includes('mark')
          );
        }
      }

      // Priority 3: Use multiple voices if available
      if (!targetVoice && usVoices.length >= 2) {
        const speakerIndex = speakers.findIndex(s => s.name === line.speaker);
        targetVoice = usVoices[speakerIndex % usVoices.length];
      }

      // Priority 4: Use pitch to differentiate
      if (!targetVoice || usVoices.length < 2) {
        if (usVoices.length > 0) {
          targetVoice = usVoices[0];
          const speakerIndex = speakers.findIndex(s => s.name === line.speaker);
          const sameGenderSpeakers = speakers.filter(s => s.gender === line.gender);
          const genderIndex = sameGenderSpeakers.findIndex(s => s.name === line.speaker);

          let pitch: number;
          if (line.gender === 'female') {
            pitch = 1.2 + (genderIndex * 0.2);
          } else {
            pitch = 0.4 + (genderIndex * 0.2);
          }
          utterance.pitch = Math.min(Math.max(pitch, 0.1), 2.0);
        }
      }

      if (targetVoice) {
        utterance.voice = targetVoice;
      }

      utterance.onend = () => {
        currentIndex++;
        setTimeout(playNext, 300);
      };

      utterance.onerror = () => {
        setIsSpeaking(false);
      };

      window.speechSynthesis.speak(utterance);
    };

    playNext();
  };

  // Extract audio URL if present
  const audioUrlMatch = content.match(/\[AUDIO_URL\]:\s*(.+?)(?:\n|$)/);
  const audioUrl = audioUrlMatch ? audioUrlMatch[1].trim() : null;

  // Extract audio dialogue if present (for transcript display)
  const audioMatch = content.match(/\[AUDIO\]:\s*([\s\S]*?)(?:\n\n|\[Question\]|$)/);
  let audioContent = audioMatch ? audioMatch[1].trim() : null;

  // Get full content for TTS (including [SPEAKERS])
  let fullAudioContent = content;

  // Remove special tags from displayed text
  let displayText = content
    .replace(/\[AUDIO_URL\]:.*\n?/g, '')
    .replace(/\[AUDIO\]:[\s\S]*?(?=\n\n|\[Question\]|$)/g, '')
    .replace(/\[SPEAKERS\]:.*\n?/g, '')
    .trim();

  // Parse dialogue for display
  const parseDialogue = (text: string) => {
    const lines = text.split('\n').filter(l => l.trim());
    const dialogue: Array<{ speaker: string; text: string }> = [];

    lines.forEach(line => {
      const match = line.match(/^([A-Z][a-z]+):\s*(.+)$/);
      if (match) {
        dialogue.push({ speaker: match[1], text: match[2] });
      }
    });

    return dialogue;
  };

  const dialogue = audioContent ? parseDialogue(audioContent) : [];

  return (
    <div className="space-y-2">
      {/* Audio Player - High Quality OpenAI TTS */}
      {audioUrl && (
        <div className="py-3 px-4 bg-purple-50 border border-purple-200 rounded-lg mb-2">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-semibold text-purple-900">듣기 문제 오디오</span>
              <span className="text-xs text-purple-600 bg-purple-100 px-2 py-0.5 rounded">고음질</span>
            </div>
            {dialogue.length > 0 && (
              <button
                onClick={() => setShowTranscript(!showTranscript)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer"
              >
                {showTranscript ? (
                  <>
                    <ChevronUp className="w-3.5 h-3.5" />
                    <span className="text-xs">스크립트 숨기기</span>
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3.5 h-3.5" />
                    <span className="text-xs">스크립트 보기</span>
                  </>
                )}
              </button>
            )}
          </div>
          <audio controls className="w-full" src={audioUrl}>
            브라우저가 오디오를 지원하지 않습니다.
          </audio>
          {showTranscript && dialogue.length > 0 && (
            <div className="mt-3 border-t border-purple-200 pt-3 space-y-2">
              {dialogue.map((line, idx) => (
                <div key={idx} className="flex gap-2">
                  <span className="text-xs font-bold text-purple-700 min-w-[60px]">{line.speaker}:</span>
                  <span className="text-sm text-gray-700">{line.text}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Audio Player - Browser TTS Fallback */}
      {!audioUrl && audioContent && (
        <div className="py-3 px-4 bg-purple-50 border border-purple-200 rounded-lg mb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-semibold text-purple-900">듣기 문제 오디오</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowTranscript(!showTranscript)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer"
              >
                {showTranscript ? (
                  <>
                    <ChevronUp className="w-3.5 h-3.5" />
                    <span className="text-xs">스크립트 숨기기</span>
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3.5 h-3.5" />
                    <span className="text-xs">스크립트 보기</span>
                  </>
                )}
              </button>
              <button
                onClick={() => handleTTS(fullAudioContent)}
                className="flex items-center gap-2 px-3 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors cursor-pointer"
              >
                {isSpeaking ? (
                  <>
                    <VolumeX className="w-4 h-4" />
                    <span className="text-xs">정지</span>
                  </>
                ) : (
                  <>
                    <Volume2 className="w-4 h-4" />
                    <span className="text-xs">오디오 재생</span>
                  </>
                )}
              </button>
            </div>
          </div>
          {showTranscript && (
            <div className="mt-3 border-t border-purple-200 pt-3 space-y-2">
              {dialogue.length > 0 ? (
                dialogue.map((line, idx) => (
                  <div key={idx} className="flex gap-2">
                    <span className="text-xs font-bold text-purple-700 min-w-[60px]">{line.speaker}:</span>
                    <span className="text-sm text-gray-700">{line.text}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-700 italic whitespace-pre-line">&quot;{audioContent}&quot;</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Main text content */}
      {displayText && (
        <div className="text-sm">
          {(() => {
            // Parse code blocks (```)
            const codeBlockRegex = /```[\s\S]*?```/g;
            const parts: Array<{ type: 'text' | 'code', content: string }> = [];

            let lastIndex = 0;
            let match;

            while ((match = codeBlockRegex.exec(displayText)) !== null) {
              // Add text before code block
              if (match.index > lastIndex) {
                parts.push({ type: 'text', content: displayText.slice(lastIndex, match.index) });
              }
              // Add code block (remove ``` markers)
              const codeContent = match[0].replace(/```/g, '').trim();
              parts.push({ type: 'code', content: codeContent });
              lastIndex = match.index + match[0].length;
            }

            // Add remaining text
            if (lastIndex < displayText.length) {
              parts.push({ type: 'text', content: displayText.slice(lastIndex) });
            }

            // If no code blocks found, treat entire content as text
            if (parts.length === 0) {
              parts.push({ type: 'text', content: displayText });
            }

            return parts.map((part, partIdx) => {
              if (part.type === 'code') {
                // Render code block with monospace font
                return (
                  <pre key={partIdx} className="font-mono text-xs bg-gray-900 text-gray-100 p-3 rounded my-2 overflow-x-auto whitespace-pre">
                    {part.content}
                  </pre>
                );
              } else {
                // Render text with URL detection
                return (
                  <div key={partIdx} className="whitespace-pre-wrap">
                    {part.content.split('\n').map((line, lineIdx) => {
                      // URL 패턴 매칭 (http://, https://, www.)
                      const urlRegex = /(https?:\/\/[^\s]+|www\.[^\s]+)/g;
                      const urlParts = line.split(urlRegex);

                      return (
                        <p key={lineIdx}>
                          {urlParts.map((urlPart, urlPartIdx) => {
                            if (urlPart.match(urlRegex)) {
                              // URL이면 링크로 변환
                              const url = urlPart.startsWith('www.') ? `https://${urlPart}` : urlPart;
                              return (
                                <a
                                  key={urlPartIdx}
                                  href={url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:text-blue-800 underline cursor-pointer"
                                >
                                  {urlPart}
                                </a>
                              );
                            }
                            // 일반 텍스트
                            return <span key={urlPartIdx}>{urlPart}</span>;
                          })}
                        </p>
                      );
                    })}
                  </div>
                );
              }
            });
          })()}
        </div>
      )}
    </div>
  );
}

export default function ParentDashboard() {
  const navigate = useNavigate();
  const [studentId, setStudentId] = useState<string | null>(null);
  const [parentId, setParentId] = useState<string | null>(null);
  const [loginInput, setLoginInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'chat'>('overview');

  // Chat state
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; quick_replies?: QuickReply[] }>>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Chat session management
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Auto-scroll to bottom when new messages arrive
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Check localStorage for logged-in parent on mount
  useEffect(() => {
    const savedParentId = localStorage.getItem('parentId');
    const savedStudentId = localStorage.getItem('studentId');

    if (savedParentId) {
      setParentId(savedParentId);
      console.log('✅ 학부모 로그인 세션 복원:', savedParentId);

      if (savedStudentId) {
        setStudentId(savedStudentId);
        console.log('✅ 자녀 정보 복원:', savedStudentId);
      }
    } else {
      console.log('⚠️ 학부모 로그인 세션 없음');
    }
  }, []);

  // Fetch student data
  const { data: student, isLoading: studentLoading } = useQuery({
    queryKey: ['student', studentId],
    queryFn: () => api.students.getById(studentId!),
    enabled: !!studentId,
  });

  // Fetch student stats
  const { data: stats } = useQuery({
    queryKey: ['student', 'stats', studentId],
    queryFn: () => api.students.getStats(studentId!),
    enabled: !!studentId,
  });

  // Fetch class info
  const { data: classInfo } = useQuery({
    queryKey: ['class', student?.class_id],
    queryFn: () => api.classes.getById(student!.class_id!),
    enabled: !!student?.class_id,
  });

  // Login handler
  const handleLogin = async () => {
    if (!loginInput.trim() || !passwordInput.trim()) {
      setLoginError('학부모 ID와 비밀번호를 입력하세요.');
      return;
    }

    setIsLoggingIn(true);
    setLoginError('');

    try {
      const response = await fetch('/api/auth/parent/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          student_id: loginInput, // API는 student_id 필드를 받지만 parent_id를 입력받음
          password: passwordInput,
        }),
      });

      const data = await response.json();

      if (data.success) {
        // parent_id와 student_id 모두 저장
        localStorage.setItem('parentId', data.parent_id);
        localStorage.setItem('parentName', data.name);
        if (data.student_id) {
          localStorage.setItem('studentId', data.student_id);
        }
        setParentId(data.parent_id);
        setStudentId(data.student_id);
        setLoginError('');
      } else {
        setLoginError(data.message || '로그인 실패');
      }
    } catch (error) {
      setLoginError('로그인 중 오류가 발생했습니다.');
      console.error('Login error:', error);
    } finally {
      setIsLoggingIn(false);
    }
  };

  // Logout handler
  const handleLogout = () => {
    localStorage.removeItem('parentId');
    localStorage.removeItem('parentName');
    localStorage.removeItem('studentId');
    setParentId(null);
    setStudentId(null);
    setLoginInput('');
    setChatMessages([]);
  };

  // Load chat sessions from localStorage
  useEffect(() => {
    if (parentId) {
      const savedSessions = localStorage.getItem(`parent_chat_sessions_${parentId}`);
      if (savedSessions) {
        try {
          const sessions = JSON.parse(savedSessions);
          setChatSessions(sessions);
        } catch (e) {
          console.error('Failed to load chat sessions:', e);
        }
      }
    }
  }, [parentId]);

  // Scroll to bottom when chat messages change
  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  // Save chat sessions to localStorage
  const saveSessions = (sessions: ChatSession[]) => {
    if (parentId) {
      localStorage.setItem(`parent_chat_sessions_${parentId}`, JSON.stringify(sessions));
      setChatSessions(sessions);
    }
  };

  // Create new chat session
  const createNewChat = () => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: '새로운 상담',
      messages: [],
      timestamp: Date.now(),
    };
    const updatedSessions = [newSession, ...chatSessions];
    saveSessions(updatedSessions);
    setCurrentSessionId(newSession.id);
    setChatMessages([]);
  };

  // Load chat session
  const loadChatSession = (sessionId: string) => {
    const session = chatSessions.find(s => s.id === sessionId);
    if (session) {
      setCurrentSessionId(sessionId);
      setChatMessages(session.messages);
    }
  };

  // Delete chat session
  const deleteChatSession = (sessionId: string) => {
    const updatedSessions = chatSessions.filter(s => s.id !== sessionId);
    saveSessions(updatedSessions);
    if (currentSessionId === sessionId) {
      setCurrentSessionId(null);
      setChatMessages([]);
    }
  };

  // Generate smart title from first message
  const generateChatTitle = (message: string): string => {
    const msg = message.toLowerCase().trim();

    // Pattern matching for common parent queries
    if (msg.includes('성적') || msg.includes('점수')) return '성적 상담';
    if (msg.includes('강점') || msg.includes('약점')) return '강약점 분석';
    if (msg.includes('숙제') || msg.includes('과제')) return '숙제 상담';
    if (msg.includes('출석') || msg.includes('태도')) return '출결/태도';
    if (msg.includes('조언') || msg.includes('도움')) return '학습 조언';
    if (msg.includes('개선') || msg.includes('향상')) return '개선 방안';

    // Default: use first 20 chars with ellipsis
    return message.slice(0, 20) + (message.length > 20 ? '...' : '');
  };

  // Save current chat to session
  const saveCurrentChat = (messages: Array<{ role: 'user' | 'assistant'; content: string; quick_replies?: QuickReply[] }>) => {
    if (!currentSessionId) {
      // Create new session if none exists
      const newSession: ChatSession = {
        id: Date.now().toString(),
        title: messages.length > 0 ? generateChatTitle(messages[0].content) : '새로운 상담',
        messages,
        timestamp: Date.now(),
      };
      const updatedSessions = [newSession, ...chatSessions];
      saveSessions(updatedSessions);
      setCurrentSessionId(newSession.id);
    } else {
      // Update existing session
      const updatedSessions = chatSessions.map(session =>
        session.id === currentSessionId
          ? { ...session, messages, timestamp: Date.now() }
          : session
      );
      saveSessions(updatedSessions);
    }
  };

  // Chat message handler
  const handleSendMessage = async () => {
    if (!chatInput.trim() || !studentId) return;

    const userMessage = chatInput.trim();
    setChatInput('');

    // Add user message to chat
    const newMessages = [...chatMessages, { role: 'user' as const, content: userMessage }];
    console.log(`💬 Parent Chat - Multi-turn: ${newMessages.length} messages (${chatMessages.length} history + 1 new)`);
    setChatMessages(newMessages);
    setIsChatLoading(true);

    try {
      const response = await fetch('/api/chat/parent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          student_id: studentId,
          messages: newMessages,
        }),
      });
      console.log(`📤 Sent ${newMessages.length} messages to /api/chat/parent`);

      const data = await response.json();
      console.log('📦 Parent API Response:', data);
      console.log('🔍 Quick Replies:', data.quick_replies);

      if (data.message) {
        const updatedMessages = [...newMessages, {
          role: 'assistant' as const,
          content: data.message,
          quick_replies: data.quick_replies || undefined
        }];
        console.log('💬 Updated Messages:', updatedMessages);
        setChatMessages(updatedMessages);
        saveCurrentChat(updatedMessages);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessages = [
        ...newMessages,
        { role: 'assistant' as const, content: '죄송합니다. 오류가 발생했습니다. 잠시 후 다시 시도해주세요.' },
      ];
      setChatMessages(errorMessages);
      saveCurrentChat(errorMessages);
    } finally {
      setIsChatLoading(false);
      // Keep focus on input after sending
      setTimeout(() => chatInputRef.current?.focus(), 100);
    }
  };

  // Handle quick reply button click
  const handleSuggestedQuestion = (question: string) => {
    setChatInput(question);
    setTimeout(() => handleSendMessage(), 100);
  };

  // Login screen
  if (!parentId) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <UserCircle2 className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">ClassMate</h1>
            <p className="text-gray-600">학부모용 자녀 학습 관리</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                학부모 ID
              </label>
              <input
                type="text"
                value={loginInput}
                onChange={(e) => {
                  setLoginInput(e.target.value);
                  setLoginError('');
                }}
                onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                placeholder="P-01"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                비밀번호
              </label>
              <input
                type="password"
                value={passwordInput}
                onChange={(e) => {
                  setPasswordInput(e.target.value);
                  setLoginError('');
                }}
                onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                placeholder="parent"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            {loginError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {loginError}
              </div>
            )}

            <button
              onClick={handleLogin}
              disabled={!loginInput.trim() || !passwordInput.trim() || isLoggingIn}
              className="w-full bg-gradient-to-r from-purple-500 to-blue-600 text-white py-3 rounded-lg font-medium hover:from-purple-600 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoggingIn ? '로그인 중...' : '로그인'}
            </button>

            <div className="text-xs text-gray-500 space-y-1">
              <p className="text-center font-medium">테스트 계정</p>
              <p className="text-center">학부모 ID: P-01, P-02, P-03 등</p>
              <p className="text-center">비밀번호: parent</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  if (studentLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  // Student not found
  if (!student) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-500 mb-4">자녀 정보를 찾을 수 없습니다: {studentId}</p>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
          >
            다시 로그인
          </button>
        </div>
      </div>
    );
  }

  // Dashboard
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* 로고 - 메인 화면으로 이동 */}
            <div
              onClick={() => navigate('/')}
              className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
            >
              <BookOpen className="w-6 h-6 text-purple-600" />
              <span className="text-xl font-bold text-gray-900">ClassMate</span>
              <span className="text-sm text-gray-500 ml-2">학부모</span>
            </div>

            <div className="flex items-center gap-4">
              <button className="text-gray-600 hover:text-gray-900">
                <Bell className="w-5 h-5" />
              </button>
              <button className="text-gray-600 hover:text-gray-900">
                <Settings className="w-5 h-5" />
              </button>
              <button onClick={handleLogout} className="text-sm text-gray-600 hover:text-gray-900">
                로그아웃
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Overview Tab */}
      {activeTab === 'overview' && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Student Info Card */}
          <div className="bg-white rounded-2xl shadow-sm p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 mb-1">{student.name} 학생</h1>
                <p className="text-gray-600">{student.grade_label} · {classInfo?.class_name}반</p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">{student.cefr}</div>
                  <div className="text-xs text-gray-500">CEFR 레벨</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{student.percentile_rank}위</div>
                  <div className="text-xs text-gray-500">백분위</div>
                </div>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setActiveTab('overview')}
              className="px-6 py-2 rounded-lg font-medium bg-purple-600 text-white"
            >
              <BarChart3 className="w-4 h-4 inline mr-2" />
              학습 현황
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className="px-6 py-2 rounded-lg font-medium bg-white text-gray-600 hover:bg-gray-50"
            >
              <MessageCircle className="w-4 h-4 inline mr-2" />
              AI 상담
            </button>
          </div>

          {/* Overview Content */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Stats Grid */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">출결 및 과제</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Calendar className="w-5 h-5 text-green-600" />
                    <span className="text-gray-700">출석률</span>
                  </div>
                  <span className="text-lg font-bold text-green-600">
                    {Math.round((student.attendance_rate || 0) * 100)}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <BookOpen className="w-5 h-5 text-blue-600" />
                    <span className="text-gray-700">숙제 완료율</span>
                  </div>
                  <span className="text-lg font-bold text-blue-600">
                    {Math.round((student.homework_completion_rate || 0) * 100)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Scores */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">영역별 점수</h3>
              <div className="space-y-3">
                {[
                  { name: '문법', score: student.grammar_score },
                  { name: '어휘', score: student.vocabulary_score },
                  { name: '독해', score: student.reading_score },
                  { name: '듣기', score: student.listening_score },
                  { name: '쓰기', score: student.writing_score },
                ].map((item, idx) => (
                  <div key={idx}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-gray-600">{item.name}</span>
                      <span className="text-sm font-medium text-gray-900">
                        {item.score ? item.score.toFixed(1) : 'N/A'}
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full"
                        style={{ width: item.score ? `${item.score}%` : '0%' }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Class Info */}
            {classInfo && (
              <div className="bg-white rounded-2xl shadow-sm p-6 md:col-span-2">
                <h3 className="text-lg font-bold text-gray-900 mb-4">수업 정보</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">수업 일정</div>
                    <div className="font-medium text-gray-900">{classInfo.schedule}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">현재 진도</div>
                    <div className="font-medium text-gray-900">{classInfo.progress}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">이번 숙제</div>
                    <div className="font-medium text-gray-900">{classInfo.homework}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">이번 달 시험</div>
                    <div className="font-medium text-gray-900">{classInfo.monthly_test}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Notes */}
            {(student.attitude || student.school_exam_level || student.csat_level) && (
              <div className="bg-white rounded-2xl shadow-sm p-6 md:col-span-2">
                <h3 className="text-lg font-bold text-gray-900 mb-4">학습 태도 및 평가</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {student.attitude && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">학습 태도</div>
                      <div className="font-medium text-gray-900">{student.attitude}</div>
                    </div>
                  )}
                  {student.school_exam_level && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">학교 평가</div>
                      <div className="font-medium text-gray-900">{student.school_exam_level}</div>
                    </div>
                  )}
                  {student.csat_level && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">진단 평가</div>
                      <div className="font-medium text-gray-900">{student.csat_level}</div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

        {/* Chat Tab - Full Height Layout */}
        {activeTab === 'chat' && (
          <div className="flex h-[calc(100vh-64px)]">
            {/* Left Sidebar - Student Info */}
            <div className="w-80 bg-gradient-to-b from-purple-50 to-blue-50 p-6 flex flex-col gap-6 border-r border-gray-200">
              {/* Tab Switch */}
              <button
                onClick={() => setActiveTab('overview')}
                className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-sm hover:shadow-md transition-all text-gray-700 hover:text-purple-600"
              >
                <BarChart3 className="w-4 h-4" />
                <span className="text-sm font-medium">학습 현황으로 이동</span>
              </button>

              {/* Student Info Card */}
              <div className="bg-white rounded-2xl shadow-sm p-6">
                <div className="text-center mb-6">
                  <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-3">
                    <UserCircle2 className="w-12 h-12 text-white" />
                  </div>
                  <h2 className="text-xl font-bold text-gray-900 mb-1">{student.name}</h2>
                  <p className="text-sm text-gray-600">{student.grade_label} · {classInfo?.class_name}반</p>
                </div>

                {/* Stats */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-700">CEFR 레벨</span>
                    <span className="text-xl font-bold text-purple-600">{student.cefr}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-700">백분위</span>
                    <span className="text-xl font-bold text-blue-600">{student.percentile_rank}위</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-700">출석률</span>
                    <span className="text-lg font-bold text-green-600">
                      {Math.round((student.attendance_rate || 0) * 100)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-700">숙제 완료율</span>
                    <span className="text-lg font-bold text-orange-600">
                      {Math.round((student.homework_completion_rate || 0) * 100)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* AI Chat Description */}
              <div className="bg-white rounded-2xl shadow-sm p-4">
                <div className="flex items-center gap-2 mb-2">
                  <MessageCircle className="w-4 h-4 text-purple-600" />
                  <h3 className="text-sm font-bold text-gray-900">AI 학습 상담</h3>
                </div>
                <p className="text-xs text-gray-600 leading-relaxed">
                  자녀의 학습 데이터를 바탕으로 맞춤형 상담을 제공합니다. 궁금한 점을 자유롭게 물어보세요!
                </p>
              </div>
            </div>

            {/* Right Side - Chat Area */}
            <div className="flex-1 flex gap-4 p-4">
              {/* Chat Sessions Sidebar */}
              <div className={`bg-white border border-gray-200 rounded-2xl shadow-sm transition-all duration-300 h-full ${
                isSidebarOpen ? 'w-80' : 'w-0 overflow-hidden'
              }`}>
              {isSidebarOpen && (
                <div className="flex flex-col h-full">
                  {/* Sidebar Header */}
                  <div className="p-4 border-b border-gray-200 space-y-2">
                    <button
                      onClick={createNewChat}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors cursor-pointer"
                    >
                      <PlusCircle className="w-4 h-4" />
                      새 상담
                    </button>

                    {/* Debug button - only in development */}
                    {import.meta.env.DEV && (
                      <button
                        onClick={() => {
                          if (confirm('모든 대화 기록을 삭제하시겠습니까?')) {
                            localStorage.removeItem(`parent_chat_sessions_${parentId}`);
                            setChatSessions([]);
                            setChatMessages([]);
                            setCurrentSessionId(null);
                            alert('대화 기록이 초기화되었습니다!');
                          }
                        }}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-50 text-red-600 border border-red-200 rounded-lg hover:bg-red-100 transition-colors cursor-pointer text-sm"
                      >
                        <Trash2 className="w-4 h-4" />
                        🔧 대화 초기화 (Dev)
                      </button>
                    )}
                  </div>

                  {/* Chat Sessions List */}
                  <div className="flex-1 overflow-y-auto p-2">
                    {chatSessions.length === 0 ? (
                      <div className="text-center text-gray-400 text-sm py-8">
                        대화 기록이 없습니다
                      </div>
                    ) : (
                      chatSessions.map((session) => (
                        <div
                          key={session.id}
                          className={`group flex items-center justify-between p-3 mb-2 rounded-lg cursor-pointer transition-colors ${
                            currentSessionId === session.id
                              ? 'bg-purple-50 border border-purple-200'
                              : 'hover:bg-gray-50 border border-transparent'
                          }`}
                          onClick={() => loadChatSession(session.id)}
                        >
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {session.title}
                            </p>
                            <p className="text-xs text-gray-500">
                              {new Date(session.timestamp).toLocaleDateString('ko-KR', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </p>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteChatSession(session.id);
                            }}
                            className="ml-2 p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 bg-white border border-gray-200 rounded-2xl shadow-sm flex flex-col h-full">
              {/* Chat Header */}
              <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
                  >
                    {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                  </button>
                  <div>
                    <h2 className="text-lg font-bold text-gray-900">AI 학습 상담</h2>
                    <p className="text-xs text-gray-600">
                      {student.name} 학생의 학습 데이터를 바탕으로 상담을 제공합니다.
                    </p>
                  </div>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.length === 0 ? (
                  <div className="text-center text-gray-500 py-12">
                    <MessageCircle className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                    <p className="text-lg font-medium mb-2">안녕하세요, 학부모님!</p>
                    <p className="text-sm">자녀의 학습에 대해 궁금한 점을 물어보세요.</p>
                  </div>
                ) : (
                  chatMessages.map((msg, idx) => (
                    <div key={idx}>
                      <div
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                            msg.role === 'user'
                              ? 'bg-purple-600 text-white'
                              : 'bg-gray-100 text-gray-900'
                          }`}
                        >
                          {msg.role === 'user' ? (
                            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                          ) : (
                            <MessageContent content={msg.content} />
                          )}
                        </div>
                      </div>
                      {/* Quick Reply Buttons - Area Selection */}
                      {(() => {
                        console.log(`🔍 Message ${idx}:`, { role: msg.role, hasQuickReplies: !!msg.quick_replies, count: msg.quick_replies?.length });
                        return msg.role === 'assistant' && msg.quick_replies && msg.quick_replies.length > 0 && (
                          <div className="flex justify-start mt-3">
                            <div className="w-full max-w-[70%] space-y-2">
                              <p className="text-xs text-gray-500 mb-2">문제 유형을 선택하세요</p>
                              <div className="flex flex-wrap gap-2">
                                {msg.quick_replies.map((qr, qrIdx) => (
                                  <button
                                    key={qrIdx}
                                    onClick={() => handleSuggestedQuestion(qr.value)}
                                    className="px-4 py-2 text-sm bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg whitespace-nowrap cursor-pointer"
                                  >
                                    {qr.label}
                                  </button>
                                ))}
                              </div>
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  ))
                )}
                {isChatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-2xl px-4 py-3">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}
                {/* Auto-scroll anchor */}
                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input */}
              <div className="p-4 border-t border-gray-200">
                <div className="flex gap-3 items-end">
                  <textarea
                    ref={chatInputRef as any}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey && !isChatLoading) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    placeholder="메시지를 입력하세요... (Shift+Enter: 줄바꿈)"
                    disabled={isChatLoading}
                    rows={1}
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-100 resize-none max-h-40 overflow-y-auto"
                    style={{ minHeight: '48px' }}
                  />
                  {isChatLoading ? (
                    <button
                      onClick={() => setIsChatLoading(false)}
                      className="px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors cursor-pointer flex items-center gap-2"
                      title="생성 중지"
                    >
                      <Square className="w-4 h-4" />
                      중지
                    </button>
                  ) : (
                    <button
                      onClick={handleSendMessage}
                      disabled={!chatInput.trim()}
                      className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      <Send className="w-4 h-4" />
                      전송
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
        )}
    </div>
  );
}
