/**
 * Real-Time AI-Moderated Conversation
 * WebSocket-based live conversation with AI podcast host
 */
import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Send, Heart, X, Check, Clock, Users } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

interface Message {
  id: string;
  type: string;
  content: string;
  sender_id: number | null;
  sender_name: string | null;
  timestamp: string;
}

interface SessionState {
  session_id: string;
  stage: string;
  questions_asked: number;
  max_questions: number;
  user1_connected: boolean;
  user2_connected: boolean;
}

export default function RealTimeConversationPage() {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const accessToken = localStorage.getItem('access_token');

  // WebSocket
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [session, setSession] = useState<SessionState | null>(null);
  const [userReady, setUserReady] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [otherUserTyping, setOtherUserTyping] = useState(false);
  const [showDecision, setShowDecision] = useState(false);
  const [myDecision, setMyDecision] = useState<boolean | null>(null);
  const [conversationEnded, setConversationEnded] = useState(false);
  const [finalResult, setFinalResult] = useState<any>(null);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout>();

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // WebSocket connection
  useEffect(() => {
    if (!accessToken || !matchId) return;

    const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
    const wsUrl = `${WS_URL}/ws/conversation/${matchId}?token=${accessToken}`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('✅ Connected to conversation');
      setConnected(true);
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.current.onclose = () => {
      console.log('❌ Disconnected from conversation');
      setConnected(false);
    };

    return () => {
      ws.current?.close();
    };
  }, [matchId, accessToken]);

  const handleWebSocketMessage = (data: any) => {
    console.log('Received:', data);

    switch (data.type) {
      case 'session_state':
        setSession(data.session);
        setMessages(data.messages || []);
        break;

      case 'user_connected':
      case 'user_ready':
        if (data.session) {
          setSession(data.session);
        }
        break;

      case 'conversation_started':
        setMessages(prev => [...prev, data.message]);
        setSession(data.session);
        break;

      case 'message':
        setMessages(prev => [...prev, data.message]);
        setOtherUserTyping(false);
        break;

      case 'typing':
        setOtherUserTyping(true);
        setTimeout(() => setOtherUserTyping(false), 3000);
        break;

      case 'conversation_wrapping_up':
        setMessages(prev => [...prev, data.message]);
        setShowDecision(true);
        break;

      case 'decision_recorded':
        setMyDecision(data.your_decision);
        break;

      case 'conversation_ended':
        setConversationEnded(true);
        setFinalResult(data);
        break;

      case 'user_disconnected':
        // Handle disconnection
        break;
    }
  };

  const sendMessage = (message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  };

  const handleReady = () => {
    sendMessage({ type: 'ready' });
    setUserReady(true);
  };

  const handleSendMessage = () => {
    if (!inputMessage.trim()) return;

    sendMessage({
      type: 'message',
      content: inputMessage
    });

    setInputMessage('');
    setIsTyping(false);
  };

  const handleTyping = (value: string) => {
    setInputMessage(value);

    // Send typing indicator
    if (!isTyping) {
      sendMessage({ type: 'typing' });
      setIsTyping(true);
    }

    // Reset typing indicator after 2s of no typing
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
    }, 2000);
  };

  const handleDecision = (decision: boolean) => {
    sendMessage({
      type: 'decision',
      decision
    });
    setMyDecision(decision);
  };

  const handleContinue = () => {
    if (finalResult?.is_mutual_match) {
      navigate(`/matches/${matchId}/chat`);
    } else {
      navigate('/matches');
    }
  };

  // Waiting room
  if (!session || session.stage === 'waiting') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-calm-50 via-white to-primary-50 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="card max-w-md text-center"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            <Users className="w-16 h-16 text-primary-500 mx-auto mb-4" />
          </motion.div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">
            Waiting for Your Match
          </h2>
          <p className="text-gray-600 mb-6">
            Your AI moderator is preparing the conversation space. Your match will join shortly.
          </p>

          {session?.user1_connected && session?.user2_connected ? (
            <>
              <p className="text-trust-600 font-semibold mb-4">
                ✓ Both users connected!
              </p>
              {!userReady && (
                <button
                  onClick={handleReady}
                  className="btn-primary"
                >
                  I'm Ready to Start
                </button>
              )}
              {userReady && (
                <p className="text-gray-500">
                  Waiting for your match to be ready...
                </p>
              )}
            </>
          ) : (
            <p className="text-gray-500">
              <Clock className="w-5 h-5 inline mr-2" />
              Connecting...
            </p>
          )}
        </motion.div>
      </div>
    );
  }

  // Final decision screen
  if (conversationEnded && finalResult) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-calm-50 via-white to-primary-50 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="card max-w-lg text-center"
        >
          {finalResult.is_mutual_match ? (
            <>
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: [0, 1.2, 1] }}
                transition={{ duration: 0.5 }}
              >
                <Heart className="w-24 h-24 text-accent-500 mx-auto mb-4" fill="currentColor" />
              </motion.div>
              <h2 className="text-4xl font-bold text-gray-800 mb-4">
                It's a Match! 🎉
              </h2>
              <p className="text-xl text-gray-600 mb-8">
                You both want to continue getting to know each other. Start chatting directly!
              </p>
            </>
          ) : (
            <>
              <Check className="w-24 h-24 text-primary-500 mx-auto mb-4" />
              <h2 className="text-3xl font-bold text-gray-800 mb-4">
                Thank You for Participating
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                {finalResult.message}
              </p>
            </>
          )}

          <button
            onClick={handleContinue}
            className="btn-primary"
          >
            {finalResult.is_mutual_match ? 'Start Chatting' : 'Find More Matches'}
          </button>
        </motion.div>
      </div>
    );
  }

  // Main conversation UI
  return (
    <div className="min-h-screen bg-gradient-to-br from-calm-50 via-white to-primary-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <Bot className="w-8 h-8 text-primary-500" />
              </motion.div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">
                  AI-Moderated Conversation
                </h1>
                <p className="text-sm text-gray-500">
                  {connected ? '🟢 Connected' : '🔴 Disconnected'} • Question {session?.questions_asked || 0}/{session?.max_questions || 10}
                </p>
              </div>
            </div>

            {/* Progress */}
            <div className="hidden md:block">
              <div className="w-48 h-2 bg-gray-200 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-primary-500 to-accent-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${((session?.questions_asked || 0) / (session?.max_questions || 10)) * 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="container mx-auto px-4 py-6 max-w-4xl">
        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
          {/* Messages area */}
          <div className="h-[600px] overflow-y-auto p-6 space-y-4">
            <AnimatePresence>
              {messages.map((message, index) => (
                <MessageBubble key={message.id} message={message} index={index} />
              ))}
            </AnimatePresence>

            {/* Typing indicator */}
            {otherUserTyping && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2 text-gray-500"
              >
                <div className="flex gap-1">
                  <motion.div
                    className="w-2 h-2 bg-gray-400 rounded-full"
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                  />
                  <motion.div
                    className="w-2 h-2 bg-gray-400 rounded-full"
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
                  />
                  <motion.div
                    className="w-2 h-2 bg-gray-400 rounded-full"
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
                  />
                </div>
                <span className="text-sm">Typing...</span>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input or Decision area */}
          {showDecision && myDecision === null ? (
            <div className="p-6 bg-gradient-to-r from-primary-50 to-accent-50 border-t border-gray-200">
              <p className="text-center text-gray-700 font-semibold mb-4">
                Would you like to continue getting to know this person?
              </p>
              <div className="flex gap-4 justify-center">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => handleDecision(true)}
                  className="bg-gradient-to-r from-trust-500 to-trust-600 text-white font-bold py-3 px-8 rounded-full shadow-lg flex items-center gap-2"
                >
                  <Heart className="w-5 h-5" />
                  Yes, Continue
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => handleDecision(false)}
                  className="bg-gray-300 hover:bg-gray-400 text-gray-700 font-bold py-3 px-8 rounded-full shadow-lg flex items-center gap-2"
                >
                  <X className="w-5 h-5" />
                  No Thanks
                </motion.button>
              </div>
            </div>
          ) : myDecision !== null ? (
            <div className="p-6 bg-primary-50 border-t border-gray-200 text-center">
              <p className="text-gray-700">
                {myDecision ? '✓ You said yes!' : '✗ You said no'} Waiting for your match's decision...
              </p>
            </div>
          ) : (
            <div className="p-4 bg-white border-t border-gray-200">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => handleTyping(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Type your response..."
                  className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-transparent outline-none"
                />
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim()}
                  className="bg-gradient-to-r from-primary-500 to-primary-600 text-white px-6 py-3 rounded-xl font-semibold shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <Send className="w-5 h-5" />
                </motion.button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message, index }: { message: Message; index: number }) {
  const isAI = message.sender_id === null;
  const isUser = !isAI;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`max-w-[80%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Sender name */}
        <div className={`text-xs text-gray-500 mb-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {isAI ? (
            <span className="flex items-center gap-1">
              <Bot className="w-3 h-3" />
              {message.sender_name}
            </span>
          ) : (
            message.sender_name
          )}
        </div>

        {/* Message bubble */}
        <div
          className={`px-6 py-3 rounded-2xl ${
            isAI
              ? 'bg-gradient-to-br from-primary-100 to-accent-100 border-2 border-primary-200'
              : 'bg-gradient-to-r from-primary-500 to-primary-600 text-white'
          }`}
        >
          <p className={`whitespace-pre-wrap ${isAI ? 'text-gray-800' : 'text-white'}`}>
            {message.content}
          </p>
        </div>

        {/* Timestamp */}
        <div className={`text-xs text-gray-400 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </motion.div>
  );
}
