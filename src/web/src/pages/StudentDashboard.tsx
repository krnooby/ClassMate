/**
 * Student Dashboard Page
 * 학생용 대시보드 - 로그인 후 개인 학습 현황 확인
 */
import { useEffect, useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/services';
import {
  BookOpen,
  Award,
  Calendar,
  Bell,
  Settings,
  UserCircle2,
  Play,
  Trophy,
  MessageCircle,
  Target,
  CheckCircle,
  Clock,
  Flame,
  Send,
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

// Chat session interface
interface ChatSession {
  id: string;
  title: string;
  messages: Array<{ role: 'user' | 'assistant'; content: string }>;
  timestamp: number;
}

// Problem Renderer Component - Interactive text mode with TTS support
function ProblemRenderer({ content, onAnswerSelect, isLoading }: { content: string; onAnswerSelect: (answer: string) => void; isLoading?: boolean }) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);

  // Parse speaker information from [SPEAKERS]: line
  const parseSpeakers = (text: string): Array<{ name: string; gender: string; voice?: string }> | null => {
    // Extract the entire [SPEAKERS]: line (everything after [SPEAKERS]: until newline)
    const speakersMatch = text.match(/\[SPEAKERS\]:\s*(.+?)(?:\n|$)/);
    if (speakersMatch) {
      try {
        const jsonStr = speakersMatch[1].trim();
        console.log('🔍 Parsing speakers JSON:', jsonStr);
        const data = JSON.parse(jsonStr);
        console.log('✅ Parsed speakers:', data.speakers);
        return data.speakers || null;
      } catch (e) {
        console.error('❌ Failed to parse speakers JSON:', e, 'Input:', speakersMatch[1]);
        return null;
      }
    }
    return null;
  };

  // TTS handler with speaker support
  const handleTTS = (text: string) => {
    if (!('speechSynthesis' in window)) {
      alert('TTS is not supported in your browser.');
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    console.log('🎤 TTS called with full text:', text);
    console.log('🎤 Text length:', text.length, 'chars');

    // Ensure voices are loaded
    let voices = window.speechSynthesis.getVoices();
    if (voices.length === 0) {
      console.log('⏳ Waiting for voices to load...');
      window.speechSynthesis.onvoiceschanged = () => {
        console.log('✅ Voices loaded, retrying TTS');
        handleTTS(text); // Retry after voices load
      };
      return;
    }

    // Check if this is a dialogue with speakers
    let speakers = parseSpeakers(text);

    // If no [SPEAKERS] found, try to infer from dialogue
    if (!speakers) {
      console.log('⚠️ No [SPEAKERS] found, inferring from dialogue');
      const dialoguePattern = /^(Girl|Boy|Woman|Man|Emma|John|Sarah|Michael|Minho):\s/gm;
      const matches = text.match(dialoguePattern);

      if (matches && matches.length > 0) {
        // Extract unique speaker names
        const uniqueSpeakers = new Set<string>();
        matches.forEach(match => {
          const name = match.replace(':', '').trim();
          uniqueSpeakers.add(name);
        });

        // Infer gender from name
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
        console.log('✅ Inferred speakers:', speakers);
      }
    }

    if (speakers) {
      // Dialogue TTS with speaker separation
      handleDialogueTTS(text, speakers);
    } else {
      // Simple TTS for non-dialogue
      console.log('📢 Using simple TTS (no speakers found)');
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
    console.log('🎤 Starting dialogue TTS with speakers:', speakers);

    // List all available voices
    const allVoices = window.speechSynthesis.getVoices();
    console.log(`🔊 Total available voices: ${allVoices.length}`);
    console.log('Available en-US voices:', allVoices.filter(v => v.lang === 'en-US' || v.lang === 'en_US').map(v => `${v.name} (${v.lang})`));

    // Remove [SPEAKERS]: line and extract dialogue
    const cleanText = text.replace(/\[SPEAKERS\]:.*\n/, '').trim();
    console.log('📝 Clean dialogue text:', cleanText.substring(0, 100) + '...');

    // Split by speaker labels (e.g., "Emma: ", "John: ")
    const speakerPattern = new RegExp(`(${speakers.map(s => s.name).join('|')}):\\s*`, 'g');
    const parts = cleanText.split(speakerPattern).filter(p => p.trim());
    console.log('🔪 Split parts:', parts);

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

    console.log(`📋 Parsed ${dialogue.length} dialogue lines:`, dialogue);

    if (dialogue.length === 0) {
      console.error('❌ No dialogue lines parsed! Check speaker names.');
      setIsSpeaking(false);
      return;
    }

    // Play dialogue sequentially
    let currentIndex = 0;
    setIsSpeaking(true);

    const playNext = () => {
      console.log(`🔊 Playing line ${currentIndex + 1}/${dialogue.length}`);

      if (currentIndex >= dialogue.length) {
        console.log('✅ Dialogue TTS completed');
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

      console.log(`🎭 Line ${currentIndex + 1}: ${line.speaker} (${line.gender})`);

      let targetVoice = null;

      // Priority 1: Try LLM-specified voice (e.g., David, Samantha)
      if (line.voice) {
        targetVoice = usVoices.find(v =>
          v.name.toLowerCase().includes(line.voice!.toLowerCase())
        );
        if (targetVoice) {
          console.log(`✅ Using LLM voice: ${targetVoice.name}`);
        }
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

        if (targetVoice) {
          console.log(`✅ Gender-based voice: ${targetVoice.name}`);
        }
      }

      // Priority 3: Use multiple voices if available (for 3+ speakers)
      if (!targetVoice && usVoices.length >= 2) {
        // Assign unique speaker index based on name
        const speakerIndex = speakers.findIndex(s => s.name === line.speaker);
        // Cycle through available voices
        targetVoice = usVoices[speakerIndex % usVoices.length];
        console.log(`✅ Multi-speaker voice: ${targetVoice.name} (speaker ${speakerIndex + 1}/${speakers.length})`);
      }

      // Priority 4: Use pitch to differentiate (when only 1 voice available)
      if (!targetVoice || usVoices.length < 2) {
        if (usVoices.length > 0) {
          targetVoice = usVoices[0];

          // Assign unique pitch for each speaker based on gender and order
          const speakerIndex = speakers.findIndex(s => s.name === line.speaker);
          const sameGenderSpeakers = speakers.filter(s => s.gender === line.gender);
          const genderIndex = sameGenderSpeakers.findIndex(s => s.name === line.speaker);

          // Base pitch by gender, then adjust by speaker index
          let pitch: number;
          if (line.gender === 'female') {
            // Female: 1.2, 1.4, 1.6 (higher pitches)
            pitch = 1.2 + (genderIndex * 0.2);
          } else {
            // Male: 0.4, 0.6, 0.8 (lower pitches)
            pitch = 0.4 + (genderIndex * 0.2);
          }

          utterance.pitch = Math.min(Math.max(pitch, 0.1), 2.0); // Clamp between 0.1 and 2.0
          console.log(`✅ Using pitch differentiation: ${targetVoice.name} with pitch=${utterance.pitch} (${line.speaker}, gender ${line.gender}, idx=${genderIndex})`);
        }
      }

      if (targetVoice) {
        utterance.voice = targetVoice;
      }

      utterance.onend = () => {
        currentIndex++;
        setTimeout(playNext, 300); // 300ms pause between speakers
      };

      utterance.onerror = () => {
        setIsSpeaking(false);
      };

      window.speechSynthesis.speak(utterance);
    };

    // Start playing
    playNext();
  };

  // New approach: Render text as-is but make entire option lines clickable
  const renderInteractiveText = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let isAudioSection = false;
    let audioLines: string[] = [];
    let fullAudioContent: string[] = []; // Store full content including [SPEAKERS]

    // Check for [AUDIO_URL]: tag (OpenAI TTS generated audio)
    const audioUrlMatch = text.match(/\[AUDIO_URL\]:\s*(.+?)(?:\n|$)/);
    const audioUrl = audioUrlMatch ? audioUrlMatch[1].trim() : null;

    lines.forEach((line, lineIndex) => {
      // Skip [AUDIO_URL]: line (already parsed above)
      if (line.match(/^\[AUDIO_URL\]:/)) {
        return;
      }

      // Check for [AUDIO]: pattern (listening problems)
      if (line.match(/^\[AUDIO\]:/)) {
        isAudioSection = true;
        audioLines = [];
        fullAudioContent = [];
        // Check if content is on the same line
        const sameLine = line.match(/^\[AUDIO\]:\s*(.+)$/);
        if (sameLine && sameLine[1].trim()) {
          audioLines.push(sameLine[1].trim());
          fullAudioContent.push(sameLine[1].trim());
        }
        return;
      }

      // If in audio section, collect lines until we hit [Question] or option pattern
      if (isAudioSection) {
        // Stop collecting if we hit [Question] or option pattern
        // Don't stop on empty lines - keep collecting until we hit actual content markers
        const shouldStop = line.match(/^\[Question\]/) ||
                          line.match(/^[a-e]\)/) ||
                          line.match(/^What |^Where |^When |^Who |^Why |^How /);

        if (shouldStop) {
          // Render the collected audio content
          const audioContent = audioLines.join('\n').trim(); // Join with newlines for better readability
          const fullContent = fullAudioContent.join('\n').trim(); // Full content for TTS

          if (audioContent) {
            // Check if it's a URL
            if (audioContent.match(/^https?:\/\//)) {
              elements.push(
                <div key={`audio-${lineIndex}`} className="py-3 px-4 bg-purple-50 border border-purple-200 rounded-lg mb-2">
                  <div className="flex items-center gap-2 mb-2">
                    <Volume2 className="w-4 h-4 text-purple-600" />
                    <span className="text-sm font-semibold text-purple-900">Listening Audio</span>
                  </div>
                  <audio controls className="w-full" src={audioContent}>
                    Your browser does not support the audio element.
                  </audio>
                </div>
              );
            } else {
              // Parse dialogue with speakers
              const dialogueLines = audioContent.split('\n').filter(l => l.trim());
              const parsedDialogue: Array<{ speaker: string; text: string }> = [];

              dialogueLines.forEach(line => {
                const match = line.match(/^([A-Z][a-z]+):\s*(.+)$/);
                if (match) {
                  parsedDialogue.push({ speaker: match[1], text: match[2] });
                }
              });

              console.log('🔊 Audio section detected');
              console.log('📝 audioContent (display):', audioContent.substring(0, 200));
              console.log('📦 fullContent (for TTS):', fullContent);
              console.log('🎭 Has [SPEAKERS]:', fullContent.includes('[SPEAKERS]'));
              console.log('🎙️ Audio URL:', audioUrl);

              // Check if we have OpenAI TTS audio URL
              if (audioUrl) {
                // Render HTML5 audio player for high-quality TTS
                elements.push(
                  <div key={`audio-${lineIndex}`} className="py-3 px-4 bg-purple-50 border border-purple-200 rounded-lg mb-2">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Volume2 className="w-4 h-4 text-purple-600" />
                        <span className="text-sm font-semibold text-purple-900">Listening Audio</span>
                        <span className="text-xs text-purple-600 bg-purple-100 px-2 py-0.5 rounded">High Quality</span>
                      </div>
                      <button
                        onClick={() => setShowTranscript(!showTranscript)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer"
                      >
                        {showTranscript ? (
                          <>
                            <ChevronUp className="w-3.5 h-3.5" />
                            <span className="text-xs">Hide Script</span>
                          </>
                        ) : (
                          <>
                            <ChevronDown className="w-3.5 h-3.5" />
                            <span className="text-xs">Show Script</span>
                          </>
                        )}
                      </button>
                    </div>
                    <audio controls className="w-full" src={audioUrl}>
                      Your browser does not support the audio element.
                    </audio>
                    {showTranscript && (
                      <div className="mt-3 border-t border-purple-200 pt-3 space-y-2">
                        {parsedDialogue.length > 0 ? (
                          parsedDialogue.map((line, idx) => (
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
                );
              } else {
                // Fallback to browser TTS
                elements.push(
                  <div key={`audio-${lineIndex}`} className="py-3 px-4 bg-purple-50 border border-purple-200 rounded-lg mb-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Volume2 className="w-4 h-4 text-purple-600" />
                        <span className="text-sm font-semibold text-purple-900">Listening Audio</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setShowTranscript(!showTranscript)}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer"
                        >
                          {showTranscript ? (
                            <>
                              <ChevronUp className="w-3.5 h-3.5" />
                              <span className="text-xs">Hide Script</span>
                            </>
                          ) : (
                            <>
                              <ChevronDown className="w-3.5 h-3.5" />
                              <span className="text-xs">Show Script</span>
                            </>
                          )}
                        </button>
                        <button
                          onClick={() => {
                            console.log('▶️ Play button clicked, fullContent:', fullContent);
                            handleTTS(fullContent);
                          }}
                          className="flex items-center gap-2 px-3 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors cursor-pointer"
                        >
                          {isSpeaking ? (
                            <>
                              <VolumeX className="w-4 h-4" />
                              <span className="text-xs">Stop</span>
                            </>
                          ) : (
                            <>
                              <Volume2 className="w-4 h-4" />
                              <span className="text-xs">Play Audio</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                    {showTranscript && (
                      <div className="mt-3 border-t border-purple-200 pt-3 space-y-2">
                        {parsedDialogue.length > 0 ? (
                          parsedDialogue.map((line, idx) => (
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
                );
              }
            }
          }

          isAudioSection = false;
          audioLines = [];
          // Don't return - process this line normally below
        } else {
          // Collect audio line
          if (line.trim()) {
            // Add to full content (including [SPEAKERS]:)
            fullAudioContent.push(line.trim());
            // Add to display content (skip [SPEAKERS]: metadata)
            if (!line.match(/^\[SPEAKERS\]:/)) {
              audioLines.push(line.trim());
            }
          }
          return;
        }
      }

      // Check if line contains an option pattern (a), b), c), etc)
      const optionMatch = line.match(/^(\s*)([a-e]|[1-5])\)\s*(.*)$/);

      if (optionMatch && !/[가-힣]/.test(optionMatch[3])) {
        // This is an option line - make entire line clickable
        const [, , label, optionText] = optionMatch;
        elements.push(
          <div
            key={lineIndex}
            onClick={() => !isLoading && onAnswerSelect(`답은 ${label.toUpperCase()}!`)}
            className={`py-2 px-4 -mx-4 rounded-lg transition-all duration-200 group ${
              isLoading
                ? 'cursor-not-allowed opacity-50'
                : 'cursor-pointer hover:bg-blue-50 hover:text-blue-700'
            }`}
            style={{ userSelect: 'none' }}
          >
            <span className={`font-semibold ${!isLoading && 'group-hover:text-blue-900'}`}>
              {label})
            </span>
            {' '}
            <span className={!isLoading ? 'group-hover:text-blue-800' : ''}>{optionText}</span>
          </div>
        );
      } else {
        // Regular line
        elements.push(
          <div key={lineIndex} className={line.trim() ? 'py-1' : 'h-2'}>
            {line || '\u00A0'}
          </div>
        );
      }
    });

    return <div className="text-sm leading-relaxed">{elements}</div>;
  };

  return (
    <div className="space-y-2">
      {renderInteractiveText(content)}
    </div>
  );
}

export default function StudentDashboard() {
  const navigate = useNavigate();
  const [studentId, setStudentId] = useState<string | null>(null);
  const [loginInput, setLoginInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'ai' | 'features' | 'services'>('dashboard');

  // Quick Reply interface
  interface QuickReply {
    label: string;
    value: string;
  }

  // Chat state
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; quick_replies?: QuickReply[] }>>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [lastModelInfo, setLastModelInfo] = useState<{ primary: string; all_used: string[] } | null>(null);

  // Chat history state
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Auto-scroll to bottom when new messages arrive
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Scroll to bottom when chat messages change
  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  // Progress bar animation when loading
  useEffect(() => {
    if (isChatLoading) {
      setLoadingProgress(0);
      const startTime = Date.now();

      const interval = setInterval(() => {
        const elapsed = Date.now() - startTime;

        // Progress curve: fast at first, then slow down
        // 0-2s: 0-60%, 2-8s: 60-85%, 8s+: 85-92%
        let progress;
        if (elapsed < 2000) {
          progress = (elapsed / 2000) * 60;
        } else if (elapsed < 8000) {
          progress = 60 + ((elapsed - 2000) / 6000) * 25;
        } else {
          progress = 85 + Math.min(((elapsed - 8000) / 20000) * 7, 7);
        }

        setLoadingProgress(Math.min(progress, 92));
      }, 100);

      return () => clearInterval(interval);
    } else {
      // When loading completes, immediately hide progress bar
      setLoadingProgress(0);
    }
  }, [isChatLoading]);

  // Check localStorage for logged-in student
  useEffect(() => {
    const savedStudentId = localStorage.getItem('studentId'); // UnifiedLogin과 일치
    if (savedStudentId) {
      setStudentId(savedStudentId);
    }
  }, []);

  // Load chat sessions from localStorage
  useEffect(() => {
    if (studentId) {
      const savedSessions = localStorage.getItem(`chat_sessions_${studentId}`);
      if (savedSessions) {
        try {
          const sessions = JSON.parse(savedSessions);
          setChatSessions(sessions);
        } catch (e) {
          console.error('Failed to load chat sessions:', e);
        }
      }
    }
  }, [studentId]);

  // Save chat sessions to localStorage
  const saveSessions = (sessions: ChatSession[]) => {
    if (studentId) {
      localStorage.setItem(`chat_sessions_${studentId}`, JSON.stringify(sessions));
      setChatSessions(sessions);
    }
  };

  // Create new chat session
  const createNewChat = () => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: '새로운 대화',
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

    // Pattern matching for common queries
    if (msg.includes('문제') && msg.includes('듣기')) return '듣기 문제';
    if (msg.includes('문제') && msg.includes('독해')) return '독해 문제';
    if (msg.includes('문제') && msg.includes('쓰기')) return '쓰기 문제';
    if (msg.includes('문제') && msg.includes('문법')) return '문법 문제';
    if (msg.includes('문제') && msg.includes('어휘')) return '어휘 문제';
    if (msg.includes('문제')) return '문제 풀기';

    if (msg.includes('강점') || msg.includes('약점')) return '강점/약점 분석';
    if (msg.includes('수업태도') || msg.includes('태도')) return '수업 태도';
    if (msg.includes('숙제')) return '숙제 확인';
    if (msg.includes('시간표') || msg.includes('일정')) return '시간표';
    if (msg.includes('성적') || msg.includes('점수')) return '성적 분석';
    if (msg.includes('추천')) return '학습 추천';

    // Default: use first 20 chars with ellipsis
    return message.slice(0, 20) + (message.length > 20 ? '...' : '');
  };

  // Save current chat to session
  const saveCurrentChat = (messages: Array<{ role: 'user' | 'assistant'; content: string }>) => {
    if (!currentSessionId) {
      // Create new session if none exists
      const newSession: ChatSession = {
        id: Date.now().toString(),
        title: generateChatTitle(messages[0]?.content || '새로운 대화'),
        messages: messages,
        timestamp: Date.now(),
      };
      const updatedSessions = [newSession, ...chatSessions];
      saveSessions(updatedSessions);
      setCurrentSessionId(newSession.id);
    } else {
      // Update existing session
      const updatedSessions = chatSessions.map(session => {
        if (session.id === currentSessionId) {
          return {
            ...session,
            messages: messages,
            title: session.title === '새로운 대화' && messages.length > 0
              ? generateChatTitle(messages[0].content)
              : session.title,
            timestamp: Date.now(),
          };
        }
        return session;
      });
      saveSessions(updatedSessions);
    }
  };

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
      setLoginError('학생 ID와 비밀번호를 입력하세요.');
      return;
    }

    setIsLoggingIn(true);
    setLoginError('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          student_id: loginInput,
          password: passwordInput,
        }),
      });

      const data = await response.json();

      if (data.success) {
        localStorage.setItem('studentId', data.student_id); // UnifiedLogin과 일치
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
    localStorage.removeItem('studentId'); // UnifiedLogin과 일치
    setStudentId(null);
    setLoginInput('');
  };

  // Chat message handler
  const handleSendMessage = async () => {
    if (!chatInput.trim() || !studentId) return;

    const userMessage = chatInput.trim();
    setChatInput('');

    // Add user message to chat
    const newMessages = [...chatMessages, { role: 'user' as const, content: userMessage }];
    setChatMessages(newMessages);
    setIsChatLoading(true);

    try {
      const response = await fetch('/api/chat/student', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          student_id: studentId,
          messages: newMessages,
        }),
      });

      const data = await response.json();

      if (data.message) {
        const updatedMessages = [...newMessages, {
          role: 'assistant' as const,
          content: data.message,
          quick_replies: data.quick_replies || undefined
        }];
        setChatMessages(updatedMessages);
        saveCurrentChat(updatedMessages);

        // Save model info
        if (data.model_info) {
          setLastModelInfo(data.model_info);
        }
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

  // Handle suggested question click - auto-submit
  const handleSuggestedQuestion = async (suggestion: string) => {
    if (!suggestion.trim() || !studentId || isChatLoading) return;

    // Add user message to chat
    const newMessages = [...chatMessages, { role: 'user' as const, content: suggestion }];
    setChatMessages(newMessages);
    setIsChatLoading(true);

    try {
      const response = await fetch('/api/chat/student', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          student_id: studentId,
          messages: newMessages,
        }),
      });

      const data = await response.json();

      if (data.message) {
        const updatedMessages = [...newMessages, {
          role: 'assistant' as const,
          content: data.message,
          quick_replies: data.quick_replies || undefined
        }];
        setChatMessages(updatedMessages);
        saveCurrentChat(updatedMessages);

        // Save model info
        if (data.model_info) {
          setLastModelInfo(data.model_info);
        }
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

  // Login screen
  if (!studentId) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
        {/* Header for login page */}
        <header className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              {/* Logo */}
              <div
                onClick={() => navigate('/')}
                className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
              >
                <BookOpen className="w-6 h-6 text-gray-900" />
                <span className="text-xl font-bold text-gray-900">ClassMate</span>
              </div>

              {/* Login/Signup buttons */}
              <div className="flex items-center gap-3">
                <a
                  href="#"
                  className="text-sm text-gray-600 hover:text-gray-900 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  서비스 소개
                </a>
                <button className="text-sm text-gray-600 hover:text-gray-900 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors">
                  회원가입
                </button>
                <button className="text-sm text-white bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 px-4 py-2 rounded-lg transition-all font-medium shadow-sm">
                  로그인
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Login form */}
        <div className="flex items-center justify-center p-4 pt-20">
          <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <BookOpen className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">ClassMate</h1>
            <p className="text-gray-600">학생용 학습 대시보드</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                학생 ID
              </label>
              <input
                type="text"
                value={loginInput}
                onChange={(e) => {
                  setLoginInput(e.target.value);
                  setLoginError('');
                }}
                onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
                placeholder="S-01"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                placeholder="test"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-3 rounded-lg font-medium hover:from-blue-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isLoggingIn ? '로그인 중...' : '로그인'}
            </button>

            <div className="text-xs text-gray-500 space-y-1">
              <p className="text-center font-medium">테스트 계정</p>
              <p className="text-center">ID: S-01, S-02, S-03 등</p>
              <p className="text-center">비밀번호: test</p>
            </div>
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
          <p className="text-red-500 mb-4">학생 정보를 찾을 수 없습니다: {studentId}</p>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 cursor-pointer"
          >
            다시 로그인
          </button>
        </div>
      </div>
    );
  }

  // Dashboard
  return (
    <div className="min-h-screen bg-white">
      {/* Header Navigation */}
      <header className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div
              onClick={() => navigate('/')}
              className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
            >
              <BookOpen className="w-6 h-6 text-gray-900" />
              <span className="text-xl font-bold text-gray-900">ClassMate</span>
            </div>

            {/* Navigation - Integrated Tabs */}
            <nav className="hidden md:flex items-center gap-2">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-4 py-2 text-sm rounded-lg transition-colors cursor-pointer ${
                  activeTab === 'dashboard'
                    ? 'bg-gray-100 text-gray-900 font-medium'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                대시보드
              </button>
              <button
                onClick={() => setActiveTab('ai')}
                className={`px-4 py-2 text-sm rounded-lg transition-colors cursor-pointer ${
                  activeTab === 'ai'
                    ? 'bg-gray-100 text-gray-900 font-medium'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                AI 챗봇
              </button>
              <button
                onClick={() => setActiveTab('features')}
                className={`px-4 py-2 text-sm rounded-lg transition-colors cursor-pointer ${
                  activeTab === 'features'
                    ? 'bg-gray-100 text-gray-900 font-medium'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                기능 소개
              </button>
              <button
                onClick={() => setActiveTab('services')}
                className={`px-4 py-2 text-sm rounded-lg transition-colors cursor-pointer ${
                  activeTab === 'services'
                    ? 'bg-gray-100 text-gray-900 font-medium'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                서비스 소개
              </button>
            </nav>

            {/* Right Icons */}
            <div className="flex items-center gap-4">
              <button className="text-gray-600 hover:text-gray-900 cursor-pointer">
                <Bell className="w-5 h-5" />
              </button>
              <button className="text-gray-600 hover:text-gray-900 cursor-pointer">
                <Settings className="w-5 h-5" />
              </button>

              {/* User Profile */}
              <div className="flex items-center gap-3 pl-4 border-l border-gray-200">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                    <span className="text-white text-sm font-semibold">
                      {student?.name?.charAt(0) || 'S'}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-gray-900">
                      {student?.name}님
                    </span>
                    <span className="text-xs text-gray-500">
                      {student?.class_id || 'A반'}
                    </span>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  className="text-xs text-gray-500 hover:text-red-600 cursor-pointer px-2 py-1 rounded hover:bg-gray-50 transition-colors"
                >
                  로그아웃
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section - Hidden in AI tab */}
      {activeTab !== 'ai' && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            {/* Profile Image - Smaller */}
            <div className="relative inline-block mb-4">
              <div className="w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center">
                <UserCircle2 className="w-12 h-12 text-gray-400" />
              </div>
              <button className="absolute bottom-0 right-0 w-7 h-7 bg-gray-900 rounded-full flex items-center justify-center text-white hover:bg-gray-800 cursor-pointer">
                <span className="text-sm">+</span>
              </button>
            </div>

            {/* Title - Smaller */}
            <h1 className="text-3xl font-bold text-gray-900 mb-2 font-display tracking-tight">ClassMate</h1>
            <p className="text-gray-600 text-sm max-w-2xl mx-auto mb-6 font-medium">
              AI가 분석하는 나만의 학습 패턴, 데이터로 완성하는 맞춤 교육
            </p>

            {/* Action Buttons - Compact */}
            <div className="flex flex-wrap items-center justify-center gap-3 mb-8">
              <button
                onClick={() => setActiveTab('ai')}
                className="flex items-center gap-2 px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors cursor-pointer"
              >
                <Play className="w-4 h-4" />
                AI 학습 시작하기
              </button>
              <button className="flex items-center gap-2 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
                <Trophy className="w-4 h-4" />
                상황별 페이지
              </button>
              <button className="flex items-center gap-2 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
                <MessageCircle className="w-4 h-4" />
                학부모 페이지
              </button>
              <button className="flex items-center gap-2 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
                <Target className="w-4 h-4" />
                선생님
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Content Area */}
      <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 ${activeTab === 'ai' ? 'py-4' : 'pb-12'}`}>


          {/* Dashboard Content */}
          {activeTab === 'dashboard' && (
            <div className="max-w-5xl mx-auto">
              {/* Section Title */}
              <div className="text-left mb-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">학습 대시보드</h2>
                <p className="text-gray-600">오늘의 학습 진행과 성과를 한눈에 확인해보세요</p>
              </div>

              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
                {/* Card 1: 오늘 학습한 문제 */}
                <div className="bg-white border border-gray-200 rounded-2xl p-6 text-left">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <BookOpen className="w-5 h-5 text-blue-600" />
                    </div>
                    <span className="text-sm text-gray-600">오늘</span>
                  </div>
                  <div className="mb-3">
                    <div className="text-3xl font-bold text-gray-900 mb-1">24</div>
                    <div className="text-sm text-gray-600">오늘 학습한 문제</div>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: '60%' }} />
                  </div>
                  <div className="mt-2 text-xs text-gray-500">진행중 · 12개</div>
                </div>

                {/* Card 2: 정답률 */}
                <div className="bg-white border border-gray-200 rounded-2xl p-6 text-left">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    </div>
                    <span className="text-sm text-gray-600">오늘</span>
                  </div>
                  <div className="mb-3">
                    <div className="text-3xl font-bold text-gray-900 mb-1">
                      {student.homework_completion_rate
                        ? Math.round(student.homework_completion_rate * 100)
                        : 87}
                      %
                    </div>
                    <div className="text-sm text-gray-600">정답률</div>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div className="bg-green-500 h-1.5 rounded-full" style={{ width: '87%' }} />
                  </div>
                  <div className="mt-2 text-xs text-gray-500">목표 · 90점</div>
                </div>

                {/* Card 3: 학습 시간 */}
                <div className="bg-white border border-gray-200 rounded-2xl p-6 text-left">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                      <Clock className="w-5 h-5 text-purple-600" />
                    </div>
                    <span className="text-sm text-gray-600">오늘</span>
                  </div>
                  <div className="mb-3">
                    <div className="text-3xl font-bold text-gray-900 mb-1">2시간 30분</div>
                    <div className="text-sm text-gray-600">학습 시간</div>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div className="bg-purple-500 h-1.5 rounded-full" style={{ width: '83%' }} />
                  </div>
                  <div className="mt-2 text-xs text-gray-500">목표 · 3시간</div>
                </div>

                {/* Card 4: 연속 학습일 */}
                <div className="bg-white border border-gray-200 rounded-2xl p-6 text-left">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                      <Flame className="w-5 h-5 text-orange-600" />
                    </div>
                    <span className="text-sm text-gray-600">오늘</span>
                  </div>
                  <div className="mb-3">
                    <div className="text-3xl font-bold text-gray-900 mb-1">15일</div>
                    <div className="text-sm text-gray-600">연속 학습일</div>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div className="bg-orange-500 h-1.5 rounded-full" style={{ width: '50%' }} />
                  </div>
                  <div className="mt-2 text-xs text-gray-500">목표 · 30일</div>
                </div>
              </div>

              {/* Recent Activities */}
              <div className="text-left">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-xl font-bold text-gray-900 mb-1">최근 학습 활동</h3>
                    <p className="text-sm text-gray-600">오늘 완료한 학습 내용을 확인해보세요</p>
                  </div>
                </div>

                <div className="space-y-4">
                  {classInfo && [
                    { subject: '영어', topic: classInfo.progress || '현재완료시제', time: '3시간 전', score: 92 },
                    { subject: '영어', topic: classInfo.homework || '과거완료시', time: '14시간 전', score: 78 },
                    { subject: '영어', topic: classInfo.monthly_test || '수동태 구문', time: '2시간 전', score: 85 },
                  ].map((activity, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <div className="text-sm text-gray-600">{activity.subject}</div>
                        <div className="font-medium text-gray-900">{activity.topic}</div>
                        <div className="text-sm text-gray-500">{activity.time}</div>
                      </div>
                      <div className={`text-lg font-bold ${
                        activity.score >= 90 ? 'text-green-600' :
                        activity.score >= 80 ? 'text-blue-600' :
                        'text-orange-600'
                      }`}>
                        {activity.score}점
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* AI Chatbot Tab */}
          {activeTab === 'ai' && (
            <div className="max-w-7xl mx-auto">
              <div className="flex gap-4 h-[calc(100vh-120px)]">
                {/* Sidebar */}
                <div className={`bg-white border border-gray-200 rounded-2xl shadow-sm transition-all duration-300 ${
                  isSidebarOpen ? 'w-80' : 'w-0 overflow-hidden'
                }`}>
                  {isSidebarOpen && (
                    <div className="flex flex-col h-full">
                      {/* Sidebar Header */}
                      <div className="p-4 border-b border-gray-200 space-y-2">
                        <button
                          onClick={createNewChat}
                          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors cursor-pointer"
                        >
                          <PlusCircle className="w-4 h-4" />
                          새 대화
                        </button>

                        {/* Debug button - only in development */}
                        {import.meta.env.DEV && (
                          <button
                            onClick={() => {
                              if (confirm('모든 대화 기록을 삭제하시겠습니까?')) {
                                localStorage.removeItem(`chat_sessions_${studentId}`);
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
                                  ? 'bg-blue-50 border border-blue-200'
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
                <div className="flex-1 bg-white border border-gray-200 rounded-2xl shadow-sm flex flex-col">
                  {/* Chat Header */}
                  <div className="p-6 border-b border-gray-200 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                        className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
                      >
                        {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                      </button>
                      <div>
                        <h2 className="text-2xl font-bold text-gray-900">AI 학습 상담</h2>
                        <p className="text-sm text-gray-600">
                          {student.name}님의 학습 데이터를 기반으로 맞춤형 상담을 제공합니다.
                        </p>
                      </div>
                    </div>

                    {/* Model Info - Header Right (Dev Only) */}
                    {import.meta.env.DEV && lastModelInfo && (
                      <div className="flex items-center">
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-900 text-white rounded-full text-xs font-mono shadow-md">
                          <span className="font-bold">🤖</span>
                          <span className="text-gray-300">{lastModelInfo.primary}</span>
                          {lastModelInfo.all_used.length > 1 && (
                            <>
                              <span className="text-gray-500">+</span>
                              <span className="text-purple-300">{lastModelInfo.all_used.filter(m => m !== lastModelInfo.primary).join(', ')}</span>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Chat Messages */}
                  <div className="flex-1 overflow-y-auto p-6 space-y-4">
                    {chatMessages.length === 0 ? (
                      <div className="text-center text-gray-500 py-12">
                        <MessageCircle className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                        <p className="text-lg font-medium mb-2">안녕하세요, {student.name}님!</p>
                        <p className="text-sm">궁금한 점이나 학습 상담이 필요하시면 메시지를 보내주세요.</p>
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
                                  ? 'bg-blue-500 text-white'
                                  : 'bg-gray-100 text-gray-900'
                              }`}
                            >
                              {msg.role === 'assistant' && msg.content.includes(')') && /([a-e]|[1-5])\)/.test(msg.content) ? (
                                <ProblemRenderer
                                  content={msg.content}
                                  isLoading={isChatLoading}
                                  onAnswerSelect={(answer) => {
                                    // answer is already formatted (e.g., "답은 A!")
                                    const newMessages = [...chatMessages, { role: 'user' as const, content: answer }];
                                    setChatMessages(newMessages);
                                    setIsChatLoading(true);

                                  fetch('/api/chat/student', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                      student_id: studentId,
                                      messages: newMessages,
                                    }),
                                  })
                                  .then(res => res.json())
                                  .then(data => {
                                    if (data.message) {
                                      const updatedMessages = [...newMessages, { role: 'assistant' as const, content: data.message }];
                                      setChatMessages(updatedMessages);
                                      saveCurrentChat(updatedMessages);
                                    }
                                  })
                                  .catch(error => {
                                    console.error('Chat error:', error);
                                    const errorMessages = [...newMessages, { role: 'assistant' as const, content: '오류가 발생했습니다.' }];
                                    setChatMessages(errorMessages);
                                  })
                                  .finally(() => setIsChatLoading(false));
                                }} />
                              ) : (
                                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                              )}
                            </div>
                          </div>
                          {/* Quick Reply Buttons for this message */}
                          {msg.role === 'assistant' && msg.quick_replies && msg.quick_replies.length > 0 && (
                            <div className="flex justify-start mt-3">
                              <div className="w-full space-y-2">
                                <p className="text-xs text-gray-500 mb-2">문제 유형 선택</p>
                                <div className="flex gap-2 overflow-x-auto pb-2" style={{ scrollbarWidth: 'thin' }}>
                                  {msg.quick_replies.map((qr, qrIdx) => (
                                    <button
                                      key={qrIdx}
                                      onClick={() => handleSuggestedQuestion(qr.value)}
                                      disabled={isChatLoading}
                                      className="px-4 py-2 text-sm bg-gradient-to-r from-blue-500 to-purple-600 text-white border border-blue-300 rounded-full hover:from-blue-600 hover:to-purple-700 hover:border-blue-500 hover:shadow-lg transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed font-medium whitespace-nowrap flex-shrink-0"
                                    >
                                      {qr.label}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                    {isChatLoading && (
                      <div className="flex justify-start">
                        <div className="bg-gray-100 rounded-2xl px-4 py-3 min-w-[280px] max-w-sm">
                          <div className="space-y-2">
                            {/* Progress bar with percentage */}
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2">
                                <div className="flex gap-1">
                                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                                <span className="text-xs text-gray-600 font-medium">답변 생성 중</span>
                              </div>
                              <span className="text-xs font-semibold text-blue-600">{Math.round(loadingProgress)}%</span>
                            </div>
                            {/* Progress bar */}
                            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-300 ease-out"
                                style={{ width: `${loadingProgress}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    {/* Auto-scroll anchor */}
                    <div ref={messagesEndRef} />
                  </div>

                  {/* Suggested Questions */}
                  {chatMessages.length === 0 && (
                    <div className="px-6 pb-4">
                      <p className="text-xs text-gray-500 mb-3">추천 질문</p>
                      <div className="flex flex-wrap gap-2">
                        {[
                          "📊 나의 강점과 약점에 대해 알려줘",
                          "💬 내 수업태도는 어떤것같아?",
                          "📝 오늘 우리반 숙제 뭐야?",
                          "📅 시간표 알려줘"
                        ].map((suggestion, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleSuggestedQuestion(suggestion)}
                            disabled={isChatLoading}
                            className="px-4 py-2 text-sm bg-gradient-to-r from-blue-50 to-purple-50 text-gray-700 border border-blue-200 rounded-full hover:from-blue-100 hover:to-purple-100 hover:border-blue-400 hover:text-blue-700 hover:shadow-md transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Chat Input */}
                  <div className="p-6 border-t border-gray-200">
                    <div className="flex gap-3">
                      <input
                        ref={chatInputRef}
                        type="text"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && !isChatLoading && handleSendMessage()}
                        placeholder="메시지를 입력하세요..."
                        disabled={isChatLoading}
                        className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
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
                          className="px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer flex items-center gap-2"
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
          {activeTab === 'features' && (
            <div className="text-center py-12">
              <p className="text-gray-600">기능 소개 페이지 준비 중입니다.</p>
            </div>
          )}
          {activeTab === 'services' && (
            <div className="text-center py-12">
              <p className="text-gray-600">서비스 소개 페이지 준비 중입니다.</p>
            </div>
          )}
        </div>
      </div>
  );
}
