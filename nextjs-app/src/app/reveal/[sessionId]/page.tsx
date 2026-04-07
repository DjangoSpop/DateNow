'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Heart, Sparkles, Share2, MessageCircle, ShieldCheck, Zap } from 'lucide-react';
import { CompatibilityCard } from '@/components/CompatibilityCard';
import { ReadinessResult } from '@/types';

export default function RevealPage({ params }: { params: { sessionId: string } }) {
  // Mock readiness result for presentation
  const result: ReadinessResult = {
    score: 82,
    recommendation: 'unlock_direct',
    compatibilityDimensions: {
      values: 85,
      communication: 78,
      lifestyle: 72,
      emotional: 88,
    },
    moderatorNotes: "Both participants demonstrate high levels of mutual respect and clear, honest communication. Their values around family and career are well-aligned.",
    confidence: 0.9,
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-primary-900 flex items-center justify-center p-8 overflow-hidden relative">
      {/* Background Decorative Elements */}
      <motion.div
        animate={{ scale: [1, 1.2, 1], rotate: [0, 90, 0] }}
        transition={{ repeat: Infinity, duration: 20 }}
        className="absolute top-0 right-0 p-40 opacity-10 blur-3xl bg-primary-500 rounded-full"
      />
      <motion.div
        animate={{ scale: [1.2, 1, 1.2], rotate: [0, -90, 0] }}
        transition={{ repeat: Infinity, duration: 15 }}
        className="absolute bottom-0 left-0 p-60 opacity-10 blur-3xl bg-accent-500 rounded-full"
      />

      <div className="max-w-4xl w-full space-y-12 relative z-10 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="inline-flex items-center gap-2 bg-white/10 px-6 py-2 rounded-full text-white backdrop-blur-md border border-white/20 shadow-2xl">
            <Bot size={20} className="text-primary-400" />
            <span className="text-xs font-black uppercase tracking-[0.3em] leading-none">AI Connection Report</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-black text-white tracking-tighter leading-tight drop-shadow-2xl">
            Your Compatibility <br />
            <span className="text-primary-400">Reveal</span>
          </h1>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <CompatibilityCard
            result={result}
            user1Name="James"
            user2Name="Elena"
            onShare={() => alert('Sharing compatibility journey...')}
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-2xl mx-auto"
        >
          <SummaryStat icon={<ShieldCheck size={20} />} title="Respect Level" value="Premium" color="text-primary-400" />
          <SummaryStat icon={<Zap size={20} />} title="Response Pace" value="Matched" color="text-accent-400" />
          <SummaryStat icon={<Sparkles size={20} />} title="Values Alignment" value="Strong" color="text-white" />
        </motion.div>
      </div>
    </div>
  );
}

function SummaryStat({ icon, title, value, color }: { icon: React.ReactNode, title: string, value: string, color: string }) {
  return (
    <div className="bg-white/5 backdrop-blur-md border border-white/10 p-6 rounded-3xl text-center space-y-2 shadow-2xl hover:bg-white/10 transition-all">
      <div className={`${color} flex justify-center`}>{icon}</div>
      <div className="text-[10px] font-black uppercase tracking-widest text-slate-400">{title}</div>
      <div className={`text-xl font-black ${color} tracking-tight`}>{value}</div>
    </div>
  );
}
