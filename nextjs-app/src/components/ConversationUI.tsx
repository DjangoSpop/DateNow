'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Bot, User, Send, CheckCircle, Info } from 'lucide-react';
import { Message, SessionStage } from '../types';

interface ConversationUIProps {
  messages: Message[];
  currentStage: SessionStage;
  onSendMessage: (content: string) => void;
  isModeratorTyping: boolean;
  user1Name: string;
  user2Name: string;
}

export const ConversationUI: React.FC<ConversationUIProps> = ({
  messages,
  currentStage,
  onSendMessage,
  isModeratorTyping,
  user1Name,
  user2Name,
}) => {
  const [inputValue, setInputValue] = React.useState('');

  const handleSend = () => {
    if (inputValue.trim()) {
      onSendMessage(inputValue);
      setInputValue('');
    }
  };

  return (
    <div className="flex flex-col h-[600px] max-w-2xl mx-auto bg-white rounded-2xl shadow-xl overflow-hidden border border-calm-100">
      {/* Header */}
      <div className="p-4 bg-gradient-to-r from-primary-500 to-primary-600 text-white flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Bot size={24} />
          <h2 className="font-semibold tracking-wide">AI Moderator</h2>
        </div>
        <div className="flex items-center gap-2 text-xs bg-white/20 px-3 py-1 rounded-full backdrop-blur-sm uppercase tracking-tighter">
          <span className="opacity-70">Stage:</span>
          <span className="font-bold">{currentStage}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-calm-50/30 to-white">
        {messages.map((msg, idx) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className={`flex ${msg.type === 'moderator' ? 'justify-center' : 'justify-end'}`}
          >
            <div
              className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed shadow-sm ${
                msg.type === 'moderator'
                  ? 'bg-white border border-primary-100 text-slate-700 italic text-center'
                  : 'bg-primary-500 text-white rounded-tr-none'
              }`}
            >
              <div className="flex items-center gap-1 mb-1 opacity-70 text-[10px] uppercase font-bold tracking-widest">
                {msg.type === 'moderator' ? <Bot size={12} /> : <User size={12} />}
                {msg.senderName || (msg.type === 'moderator' ? 'Moderator' : 'You')}
              </div>
              {msg.content}
            </div>
          </motion.div>
        ))}
        {isModeratorTyping && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-center"
          >
            <div className="bg-white border border-primary-100 p-3 rounded-2xl flex gap-1">
              <span className="w-1.5 h-1.5 bg-primary-300 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce [animation-delay:0.2s]" />
              <span className="w-1.5 h-1.5 bg-primary-500 rounded-full animate-bounce [animation-delay:0.4s]" />
            </div>
          </motion.div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-calm-100 bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder={`Message ${user2Name}...`}
            className="flex-1 px-4 py-2 bg-slate-50 rounded-full border-none focus:ring-2 focus:ring-primary-500 transition-all outline-none text-sm"
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim()}
            className="p-2 bg-primary-500 text-white rounded-full hover:bg-primary-600 disabled:opacity-50 transition-colors shadow-md"
          >
            <Send size={20} />
          </button>
        </div>
        <div className="mt-3 flex items-center gap-2 text-[10px] text-slate-400 uppercase tracking-widest font-bold">
          <Info size={12} />
          Your messages are moderated for safety and respect.
        </div>
      </div>
    </div>
  );
};
