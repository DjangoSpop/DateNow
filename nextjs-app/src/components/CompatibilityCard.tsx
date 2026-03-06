'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Share2, Heart, MessageCircle, Zap, ShieldCheck } from 'lucide-react';
import { ReadinessResult } from '../types';

interface CompatibilityCardProps {
  result: ReadinessResult;
  user1Name: string;
  user2Name: string;
  onShare?: () => void;
}

export const CompatibilityCard: React.FC<CompatibilityCardProps> = ({
  result,
  user1Name,
  user2Name,
  onShare,
}) => {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-primary-600';
    if (score >= 60) return 'text-accent-500';
    return 'text-slate-400';
  };

  return (
    <div className="max-w-md mx-auto bg-white rounded-3xl shadow-2xl overflow-hidden border border-calm-100 p-8 space-y-8 relative">
      <div className="absolute top-0 right-0 p-4">
        <ShieldCheck size={32} className="text-primary-500/20" />
      </div>

      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-extrabold text-slate-800 tracking-tight leading-none">
          {user1Name} & {user2Name}
        </h2>
        <p className="text-sm font-bold uppercase tracking-widest text-primary-500 bg-primary-50 py-1 px-4 rounded-full inline-block">
          Connection Reveal
        </p>
      </div>

      {/* Main Score */}
      <div className="relative h-40 w-40 mx-auto flex items-center justify-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 100 }}
          className="absolute inset-0 bg-gradient-to-br from-primary-50 to-white rounded-full border border-primary-100 shadow-inner"
        />
        <div className="z-10 text-center">
          <motion.div
            initial={{ y: 10 }}
            animate={{ y: 0 }}
            className={`text-6xl font-black ${getScoreColor(result.score)} tracking-tighter`}
          >
            {result.score}%
          </motion.div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mt-1">
            Compatibility
          </div>
        </div>
      </div>

      {/* Dimensions */}
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(result.compatibilityDimensions).map(([dim, score]) => (
          <div key={dim} className="bg-slate-50/50 p-4 rounded-2xl border border-slate-100/50 space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-extrabold uppercase tracking-widest text-slate-400 capitalize">
                {dim}
              </span>
              <span className={`text-xs font-bold ${getScoreColor(score)}`}>{score}%</span>
            </div>
            <div className="h-1 bg-slate-200 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${score}%` }}
                className="h-full bg-primary-500"
              />
            </div>
          </div>
        ))}
      </div>

      {/* Recommendation */}
      <div className="bg-primary-50 p-6 rounded-2xl border border-primary-100 text-center space-y-2 italic text-sm text-slate-700 leading-relaxed shadow-sm">
        <Heart size={20} className="mx-auto text-primary-500 mb-2" />
        "{result.moderatorNotes}"
      </div>

      {/* Actions */}
      <div className="flex gap-4">
        <button
          onClick={onShare}
          className="flex-1 bg-slate-900 text-white py-4 rounded-2xl font-bold flex items-center justify-center gap-2 hover:bg-slate-800 transition-colors shadow-lg active:scale-95 transition-all"
        >
          <Share2 size={18} />
          Share Journey
        </button>
        <button className="flex-1 bg-primary-500 text-white py-4 rounded-2xl font-bold flex items-center justify-center gap-2 hover:bg-primary-600 transition-colors shadow-lg active:scale-95 transition-all">
          <MessageCircle size={18} />
          Direct Chat
        </button>
      </div>

      <div className="text-center">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-300">
          Powered by DateNow AI Readiness Engine
        </p>
      </div>
    </div>
  );
};
